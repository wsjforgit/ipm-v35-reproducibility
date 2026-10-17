#!/usr/bin/env python3
"""Evaluate a newly generated 2019 TREC-PM full-snapshot retrieval quartet.

This stage opens official qrels only after a pre-registered four-condition saved
run exists. Reports per-topic and aggregate *descriptive* retrieval effects,
without pretending that previously exposed qrels form an untouched gold test.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import statistics

METHODS = ("G00","G01","G10","G11")
SCHEMA = "pm2019-fts5-full-corpus-retrieval-evaluation-v1"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_qrels(path):
    q=collections.defaultdict(dict)
    for line in path.read_text().splitlines():
        parts=line.split()
        if len(parts)!=4:raise ValueError("Malformed NIST 2019 qrel")
        topic,_,doc,grade=parts
        g=int(grade)
        if not 0<=g<=2:raise ValueError("Invalid relevance grade")
        if doc in q[topic] and q[topic][doc]!=g:raise ValueError("Conflicting label")
        q[topic][doc]=g
    return q

def metric(q, ranked, gain_type):
    n=10
    if gain_type=="linear":gain=lambda r:float(r)
    elif gain_type=="exp2":gain=lambda r:float(2**r-1)
    else:raise ValueError(gain_type)
    a=sum(gain(q.get(doc,0))/math.log2(i+2) for i,doc in enumerate(ranked[:n]))
    top=sorted((gain(v) for v in q.values()),reverse=True)[:n]
    idcg=sum(v/math.log2(i+2) for i,v in enumerate(top))
    return a/idcg if idcg>0 else 0.

def eval_one(q, docs):
    positives={k for k,v in q.items() if v>0}
    k=len(positives)
    ret={ 'nDCG10_linear':metric(q,docs,'linear'),
          'nDCG10_exp2':metric(q,docs,'exp2'),
          'P10':sum(d in positives for d in docs[:10])/10.0,
          'Recall100':sum(d in positives for d in docs[:100])/k if k else 0.0,
          'Rprec':sum(d in positives for d in docs[:k])/k if k else 0.0,
          'judged_positive_count':k }
    return ret

def interaction(dic, key):
    return dic["G11"][key]-dic["G10"][key]-dic["G01"][key]+dic["G00"][key]

def analyze(source,qrel):
    if source["status"]!="FROZEN_NEW_FULL_CORPUS_RETRIEVAL_BEFORE_JUDGMENT":
        raise ValueError("Not a full corpus preregistered retrieval run")
    if source["topics_scored"]!=40 or source["corpus_doc_count"]!=306238:
        raise ValueError("Incomplete full snapshot input")
    topics={t["topic_id"]:t for t in source["topic_results"]}
    if len(topics)!=40:raise ValueError("Missing 2019 official topic")
    assert len(qrel)==38,(len(qrel),set(topics)-set(qrel))
    per=[]
    for topic in sorted(qrel,key=int):
        group=topics[topic]
        scored={}
        for arm in METHODS:
            ranks=group["methods"][arm]["ranked_ids_and_scores"]
            assert group["methods"][arm]["n_results"]==len(ranks)
            if any(int(row["rank"])!=i+1 for i,row in enumerate(ranks)):
                raise ValueError("Invalid rank ordinal")
            ids=[row["doc_id"] for row in ranks]
            if len(ids)!=len(set(ids)):raise ValueError("Duplicate doc")
            scored[arm]=eval_one(qrel[topic],ids)
        interactions={k:interaction(scored,k) for k in ('nDCG10_linear','nDCG10_exp2','P10','Recall100','Rprec')}
        per.append({'topic_id':topic,'metrics_by_arm':scored,'interactions':interactions})
    averages={}
    for m in ('nDCG10_linear','nDCG10_exp2','P10','Recall100','Rprec'):
        by_arm={arm:statistics.mean(row['metrics_by_arm'][arm][m] for row in per)
                for arm in METHODS}
        deltas=[row['interactions'][m] for row in per]
        averages[m]={
          'method_means':by_arm,
          'factorial_interaction':interaction({arm:{m:v} for arm,v in by_arm.items()},m),
          'positive_topic_deltas':sum(x>0 for x in deltas),
          'negative_topic_deltas':sum(x<0 for x in deltas),
          'zero_topic_deltas':sum(x==0 for x in deltas),
          'per_topic_interaction_min_max':[min(deltas),max(deltas)],
          'leave_one_topic_out_interaction_range':[
              min(statistics.mean(y for j,y in enumerate(deltas) if j!=i) for i in range(len(deltas))),
              max(statistics.mean(y for j,y in enumerate(deltas) if j!=i) for i in range(len(deltas)))
          ],
        }
    return {'schema':SCHEMA,'test_topics':len(per),'all_corpus_topics_scored':40,
            'protocol':'full 2019 trial-corpus index; lexical BM25 FTS5 2x2; no new neural training',
            'qrels':'NIST 2019 official trials trec-eval judgements; grades 0/1/2',
            'numeric_metric_definitions':'linear nDCG@10 primary, exp2 secondary; binary positive for P10/Recall100/Rprec',
            'units':'matched same 2019 corpus and topic within this external task; not matched BCKB source-role interaction',
            'external_validity_limits':[
              'Study authors already had historical access to 2019 qrels; this is not an unseen gold test.',
              '2019 clinical-trial-only roles and fields differ materially from BCKB four-source documentary queries.',
              'The FTS5 stemming/tokenization is a new baseline, not exact replay of historical bm25s/Lucene index.',
              'No statistical significance is claimed because independent topic exchangeability has not been verified.',
              'Full XML trial corpus and official qrels are not redistributed in the release.',
            ],
            'means_and_interactions':averages,'per_topic_results':per,
            }

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--retrieval-json",type=Path,required=True)
    a.add_argument("--qrels",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    x=a.parse_args()
    if x.output.exists():raise SystemExit("Refuse to overwrite existing report")
    source=json.loads(x.retrieval_json.read_text())
    q=load_qrels(x.qrels)
    result=analyze(source,q)
    result['source_hashes']={'retrieval':sha(x.retrieval_json),'official_qrels':sha(x.qrels)}
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({'report':str(x.output),'topics':result['test_topics'],
                      'primary_interaction':result['means_and_interactions']['nDCG10_linear']['factorial_interaction'],
                      'nDCG_method_means':result['means_and_interactions']['nDCG10_linear']['method_means']},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
