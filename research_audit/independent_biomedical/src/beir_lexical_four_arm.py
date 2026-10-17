#!/usr/bin/env python3
"""Locked public-BEIR external benchmark: no training, no model selection by qrels.

Usage:
  --stage index --dataset scifact|nfcorpus
  --stage retrieve --dataset scifact|nfcorpus
  --stage score --dataset scifact|nfcorpus
Original corpora, qrels and full saved rankings are local-only.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, math, os, pathlib, re, sqlite3, statistics, time, zipfile
B = pathlib.Path(os.environ.get("CMPB_BEIR_WORKDIR", pathlib.Path(__file__).resolve().parents[1])).expanduser().resolve()
PROTOCOL = B/"protocol/00_PREREGISTERED_BEIR_EXTERNAL_PROTOCOL.json"
METHODS=("G00","G01","G10","G11")
STOP={"a","an","and","for","in","of","on","the","to","with"}
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def read_members(name:str):
 f=B/"private_data"/f"{name}.zip"
 with zipfile.ZipFile(f) as z:
  return {field:z.read(f"{name}/{field}") for field in ("corpus.jsonl","queries.jsonl","qrels/test.tsv")}
def records(bs):
 return [json.loads(line) for line in bs.decode().splitlines() if line.strip()]
def tokens(s):
 toks=re.findall(r"[a-z0-9]+",s.lower())
 return list(dict.fromkeys(k for k in toks if k not in STOP))[:48]
def query_expr(tok):return " OR ".join('"'+x+'"' for x in tok)
def init_index(dataset):
 d=B/"private_data"/dataset
 d.mkdir(exist_ok=True)
 db=d/"fts5_independent.sqlite"
 receipt=d/"INDEX_HASHES_AND_COUNT.json"
 if receipt.exists():
  x=json.loads(receipt.read_text())
  if x.get("complete"):return x
 if db.exists(): raise RuntimeError("Index exists without complete receipt; inspect rather than overwrite")
 p=read_members(dataset)
 rows=records(p["corpus.jsonl"])
 conn=sqlite3.connect(str(db))
 conn.execute("PRAGMA journal_mode=WAL")
 conn.execute("CREATE TABLE ids(rid INTEGER PRIMARY KEY, docid TEXT UNIQUE NOT NULL)")
 for kind in ("raw","tag"):
  conn.execute(f"CREATE VIRTUAL TABLE fts_{kind} USING fts5(body, tokenize='porter unicode61')")
 for i,case in enumerate(rows,1):
  docid=str(case["_id"])
  title=str(case.get("title") or "")
  text=str(case.get("text") or "")
  if not (title or text):raise ValueError("Empty document")
  raw=" ".join(x for x in (title,text) if x)
  tagged="title "+title+" abstract "+text
  conn.execute("INSERT INTO ids(rid,docid) VALUES(?,?)",(i,docid))
  conn.execute("INSERT INTO fts_raw(rowid,body) VALUES(?,?)",(i,raw))
  conn.execute("INSERT INTO fts_tag(rowid,body) VALUES(?,?)",(i,tagged))
  if i%400==0:conn.commit()
 conn.commit()
 size=conn.execute("SELECT COUNT(*) FROM ids").fetchone()[0]
 assert size==len(rows)
 for kind in ("raw","tag"):assert conn.execute(f"SELECT COUNT(*) FROM fts_{kind}").fetchone()[0]==size
 conn.close()
 obj={"version":"beir-bounded-external-lexical-v1","dataset":dataset,"complete":True,"num_docs":size,
 "input_corpus_sha256":sha(p["corpus.jsonl"]),"archive_sha256":sha((B/"private_data"/f"{dataset}.zip").read_bytes()),
 "query_field_design":"R0 raw title+body; R1 title and abstract fixed label words; FTS5 porter unicode61 default BM25"}
 receipt.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
 return obj
def retrieve(dataset):
 p=read_members(dataset)
 raw_queries={str(r["_id"]):str(r["text"]) for r in records(p["queries.jsonl"])}
 qlines=p["qrels/test.tsv"].decode().splitlines()
 selected=sorted(set(row["query-id"] for row in csv.DictReader(qlines,delimiter="\t")))
 if not selected: raise ValueError("Test split has no query IDs")
 if not set(selected).issubset(raw_queries):raise ValueError("BEIR query IDs incomplete")
 protocol=json.loads(PROTOCOL.read_text())
 assert protocol["preregistered_before_downloading_or_opening_any_official_qrels_for_these_datasets"]
 assert len(selected)==protocol["benchmarks"][dataset]["official_test_topics_expected"],(len(selected),dataset)
 root=B/"private_outputs"
 final=root/f"{dataset}_saved_new_4arm_ranks.jsonl"
 if final.exists():raise ValueError("Frozen new run already exists; no overwrite")
 index=B/"private_data"/dataset/"fts5_independent.sqlite"
 if not index.exists():raise ValueError("Run index stage first")
 db=sqlite3.connect(f"file:{index}?mode=ro",uri=True,timeout=80)
 db.execute("PRAGMA query_only=ON")
 arms={"G00":("raw",False),"G01":("raw",True),"G10":("tag",False),"G11":("tag",True)}
 start=time.monotonic()
 with final.open("x",encoding="utf-8") as output:
  for i,qid in enumerate(selected,1):
   qt=tokens(raw_queries[qid])
   if not qt:raise ValueError("Empty tokenized natural language query")
   tagged=list(dict.fromkeys(qt+["title","abstract"]))
   assert len(tagged)<=50
   seq={}
   for method,(kind,add) in arms.items():
    toks=tagged if add else qt
    expr=query_expr(toks)
    table="fts_"+kind
    # NOTE: cannot interpolate user text except via SQLite bound MATCH parameter.
    sql=f"""SELECT ids.docid,bm25({table}) AS score FROM {table}
      JOIN ids ON ids.rid={table}.rowid WHERE {table} MATCH ?
      ORDER BY score ASC, ids.docid ASC LIMIT 1000"""
    hits=db.execute(sql,(expr,)).fetchall()
    # Empty candidate sets are legitimate query outcomes; retain [] and count as zero ranking metrics.
    if len({doc for doc,score in hits})!=len(hits):raise AssertionError("Duplicate rank")
    seq[method]=hits
   output.write(json.dumps({"query_id":qid,"ranks":seq},ensure_ascii=False,separators=(",",":"))+"\n")
   if i%25==0:output.flush()
   if i%60==0:print(json.dumps({"dataset":dataset,"scored":i,"total":len(selected),"seconds":round(time.monotonic()-start,1)}),flush=True)
 db.close()
 with final.open() as f:rows=sum(bool(x.strip()) for x in f)
 assert rows==len(selected)
 return {"dataset":dataset,"queries":rows,"ranking_pairs":rows*4,"file_bytes":final.stat().st_size,
         "saved_ranks_sha256":sha(final.read_bytes()),"seconds":round(time.monotonic()-start,2)}
def dcg(qrels,ids,exp2=False):
 g=(lambda v:2**v-1) if exp2 else (lambda v:v)
 actual=sum(g(max(0,qrels.get(doc,0)))/math.log2(i+2) for i,doc in enumerate(ids[:10]))
 ideal=sum(g(v)/math.log2(i+2) for i,v in enumerate(sorted((max(0,x) for x in qrels.values()),reverse=True)[:10]))
 return actual/ideal if ideal else 0.0
def eval_rank(qrels,ids):
 pos={d for d,v in qrels.items() if v>0}
 return {"ndcg10_linear":dcg(qrels,ids),"ndcg10_exp2":dcg(qrels,ids,True),
         "p10":sum(x in pos for x in ids[:10])/10,
         "recall100":sum(x in pos for x in ids[:100])/len(pos) if pos else 0.0}
def effect(x,metric):
 return x["G11"][metric]-x["G10"][metric]-x["G01"][metric]+x["G00"][metric]
def evaluate(dataset):
 p=read_members(dataset)
 judgments=collections.defaultdict(dict)
 for x in csv.DictReader(p["qrels/test.tsv"].decode().splitlines(),delimiter="\t"):
  judgments[x["query-id"]][x["corpus-id"]]=int(x["score"])
 rankpath=B/"private_outputs"/f"{dataset}_saved_new_4arm_ranks.jsonl"
 rows=[json.loads(x) for x in rankpath.read_text().splitlines()]
 if len(rows)!=len(judgments): raise ValueError("Mismatch query judgments")
 validids={str(x["_id"]) for x in records(p["corpus.jsonl"])}
 values=[];positives=[]
 for row in rows:
  qid=row["query_id"]; y=judgments[qid]
  if any(d not in validids for d in y): raise ValueError("qrel unknown doc id")
  x={}
  for m in METHODS:
   ids=[str(d) for d,s in row["ranks"][m]]
   if len(ids)!=len(set(ids)): raise ValueError("duplicate ranked document IDs")
   x[m]=eval_rank(y,ids)
  values.append({"query_id":qid,"metrics":x})
  positives.append({d for d,s in y.items() if s>0})
 metric_keys=list(values[0]["metrics"]["G00"])
 aggregate={}
 for metric in metric_keys:
  means={m:statistics.mean(v["metrics"][m][metric] for v in values) for m in METHODS}
  ds=[effect(v["metrics"],metric) for v in values]
  aggregate[metric]={"means":means,"factorial_interaction":effect({m:{metric:x} for m,x in means.items()},metric),
    "query_positive_deltas":sum(x>0 for x in ds),"query_negative_deltas":sum(x<0 for x in ds),
    "query_zero_deltas":sum(x==0 for x in ds),
    "LOO_range":[min((sum(ds)-d)/(len(ds)-1) for d in ds),max((sum(ds)-d)/(len(ds)-1) for d in ds)]}
 shared=sum(bool(a&c) for i,a in enumerate(positives) for c in positives[i+1:])
 n=len(positives)
 out={"dataset":dataset,"source":"BEIR original test qrels; independently curated by upstream benchmark; not breast-cancer four-source relevance gold",
 "corpus_docs":len(validids),"judged_test_queries":len(values),
 "judged_query_pairs_sharing_positive":shared,"all_query_pairs":n*(n-1)//2,
 "scope":"new full-corpus FTS5 2x2 naive lexical prefixes, no trained model, no new clinical gold; datasets evaluated separately",
 "aggregate":aggregate,
 "input_sha256":{"corpus":sha(p["corpus.jsonl"]),"queries":sha(p["queries.jsonl"]),"official_qrels":sha(p["qrels/test.tsv"]),"saved_runs":sha(rankpath.read_bytes())},
 "limitations":["No four-source roles or breast-cancer-specific gold in these external benchmarks.",
 "SciFact is scientific claim/abstract evidence and NFCorpus is health/nutrition retrieval; no metric pooling.",
 "Static lexical marker tokens do not constitute semantic source-role inference.",
 "Test qrels pre-existing and publicly exposed: do not claim blinding or statistically independent queries without checks."],
 "per_query_derived":values}
 file=B/"private_outputs"/f"{dataset}_independent_judged_evaluation.json"
 if file.exists():raise ValueError("No overwrite")
 file.write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
 return {"dataset":dataset,"judged_test_queries":len(values),"docs":len(validids),"shared_query_positive_pairs":shared,
         "mean_ndcg10_by_condition":aggregate["ndcg10_linear"]["means"],
         "interaction":aggregate["ndcg10_linear"]["factorial_interaction"],
         "other_metrics":{k:x["factorial_interaction"] for k,x in aggregate.items()}}
def main():
 pa=argparse.ArgumentParser()
 pa.add_argument("--dataset",choices=("scifact","nfcorpus"),required=True)
 pa.add_argument("--stage",choices=("index","retrieve","score"),required=True)
 args=pa.parse_args()
 result={"index":init_index,"retrieve":retrieve,"score":evaluate}[args.stage](args.dataset)
 print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
