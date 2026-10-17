#!/usr/bin/env python3
"""Pre-registered 2019 TREC PM lexical 2x2 retrieval from full historical XML snapshot.

This stage intentionally NEVER opens qrels or any previously observed labels.
SQLite FTS5 BM25 and fixed four condition strings; all conditions share the
same full 306,238-document collection. CPU only. Not a BCKB four-source
replication. Writes private ranked NCT IDs/scores for independent evaluation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import xml.etree.ElementTree as ET

STOP = {"a","an","and","for","in","of","on","the","to","with"}
MAPPING = {
    "G00": ("fts_raw","Q0"),
    "G01": ("fts_raw","Q1"),
    "G10": ("fts_label","Q0"),
    "G11": ("fts_label","Q1"),
}
SCHEMA = "pm2019-full-corpus-fts5-new-lexical-factorial-v1"

def sha(f):
    return hashlib.sha256(f.read_bytes()).hexdigest()

def token(text):
    values=re.findall(r"[a-z0-9]+",text.lower())
    unique=list(dict.fromkeys(w for w in values if w not in STOP))
    return unique

def topics_load(path):
    xml=ET.parse(str(path)).getroot()
    topics=[]
    for row in xml.findall("topic"):
        number=row.attrib.get("number")
        data={field:(row.findtext(field) or "").strip() for field in ("disease","gene","demographic")}
        if not number or not data["disease"]:raise ValueError("Malformed official topic")
        flat=" ".join(data.values())
        labelled="condition "+data["disease"]+" eligibility "+data["gene"]+" "+data["demographic"]
        variants={"Q0":token(flat),"Q1":token(labelled)}
        if any(not x for x in variants.values()):raise ValueError("Empty query variant")
        topics.append({"id":number,"fields":data,"query_tokens":variants})
    if len(topics)!=40 or len({x["id"] for x in topics})!=40:
        raise ValueError("Unexpected official 2019 topic collection")
    return topics

def fts_expr(words):
    # Quoted literal disjunction, fixed tokenizer and stopwords.
    return " OR ".join('"'+w+'"' for w in words)

def score(conn,table,expr,limit):
    if table not in ("fts_raw","fts_label"):
        raise ValueError("Illegal FTS table")
    query=f"""
SELECT doc_map.nctid, bm25({table}) AS score
FROM {table} JOIN doc_map ON doc_map.rid={table}.rowid
WHERE {table} MATCH ?
ORDER BY score ASC, doc_map.nctid ASC LIMIT ?
"""
    result=conn.execute(query,(expr,limit)).fetchall()
    if len({x[0] for x in result})!=len(result):
        raise ValueError("Duplicate NCT ID")
    return [{"doc_id":r[0],"score":r[1],"rank":i+1} for i,r in enumerate(result)]

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--sqlite",type=Path,required=True)
    pa.add_argument("--topics",type=Path,required=True)
    pa.add_argument("--output",type=Path,required=True)
    pa.add_argument("--topic-limit",type=int,default=40)
    a=pa.parse_args()
    if a.output.exists():raise SystemExit("Refuse overwrite: "+str(a.output))
    if a.topic_limit not in (5,40):raise ValueError("Only predeclared 5-topic pilot or 40-topic run")
    all_topics=topics_load(a.topics)
    conn=sqlite3.connect(f"file:{a.sqlite}?mode=ro",uri=True,timeout=90)
    conn.execute("PRAGMA query_only=ON")
    count=conn.execute("SELECT COUNT(*) FROM doc_map").fetchone()[0]
    if a.topic_limit==40 and count!=306238:
        raise ValueError("All four full-index arms must cover 306,238 original trials")
    records=[]
    t0=time.time()
    for i,topic in enumerate(all_topics[:a.topic_limit],1):
        case={"topic_id":topic["id"],"queries":topic["query_tokens"],"methods":{}}
        for name,(table,qname) in MAPPING.items():
            t=time.monotonic()
            hits=score(conn,table,fts_expr(topic["query_tokens"][qname]),1000)
            case["methods"][name]={"n_results":len(hits),"elapsed_ms":round(1000*(time.monotonic()-t),1),"ranked_ids_and_scores":hits}
        records.append(case)
        print(json.dumps({"topic_scored":topic["id"],"progress":f"{i}/{a.topic_limit}",
            "retrieved":[case["methods"][m]["n_results"] for m in MAPPING],
            "elapsed":round(time.time()-t0,1)},ensure_ascii=False),flush=True)
    conn.close()
    obj={
      "schema":SCHEMA,"status":"PIPELINE_PILOT_NO_QRELS" if a.topic_limit==5 else "FROZEN_NEW_FULL_CORPUS_RETRIEVAL_BEFORE_JUDGMENT",
      "topics_scored":a.topic_limit,"same_corpus_all_arms":True,
      "corpus_doc_count":count,"db_sha256":None,
      "official_topics_sha256":sha(a.topics),
      "param":{"fts":"SQLite FTS5 porter unicode61; bm25 default; ascending, NCT tie","OR_fixed_stopwords":sorted(STOP),
               "R0":"raw identical clinical trial field text without tags",
               "R1":"same content with fixed literal field labels",
               "Q0":"flat disease+gene+demographic",
               "Q1":"condition disease eligibility gene demographic",
               "topk":1000},
      "retrieval_seconds":round(time.time()-t0,2),
      "author_retrospective_limit":"Earlier qrels have been accessed in this project, so this is not a pristine label-blind scientific study despite this stage avoiding qrels.",
      "no_clinical_validation":True,
      "topic_results":records,
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"output":str(a.output),"topics":a.topic_limit,"total_runs":a.topic_limit*4,
        "bytes":a.output.stat().st_size,"seconds":obj["retrieval_seconds"]},ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
