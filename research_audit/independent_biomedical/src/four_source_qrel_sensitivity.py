#!/usr/bin/env python3
"""Post-outcome four-source reference-family sensitivity on frozen BCKB Formal40.

Labels are inferred from documentary parent-ID *prefixes* and must NOT be
confused with independent source-role correctness or clinical relevance.
Drops/keeps whole source families in the study-created qrels while holding the
original nine method ranked IDs unchanged. Reports scoreable-topic count and
all descriptive effects without new p-values or CI recalibration.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,pathlib,statistics,sys
FAMILIES=("clinical_trial","drug_label","guidance","case_report")
def family(value):
 if value.startswith("NCT"):return "clinical_trial"
 if value.startswith("drug_label::"):return "drug_label"
 if value.startswith("PMC"):return "guidance"
 if value.startswith("case_report::"):return "case_report"
 raise ValueError("Unknown source family; do not guess "+str(value)[:60])
def metric(ids,positives):
 import math
 if not positives:return None
 dcg=sum(1/math.log2(i+2) for i,id in enumerate(ids[:10]) if id in positives)
 ideal=sum(1/math.log2(i+2) for i in range(min(10,len(positives))))
 return dcg/ideal
def score(qrels,runs,kept):
 per={str(t["topic_id"]):{} for t in qrels}
 for r in runs:
  id=str(r["topic_id"])
  if r["method"] in ("G00","G01","G10","G11"):
   per[id][r["method"]]=r["parent_ids"]
 samples=[]
 for q in qrels:
  id=str(q["topic_id"])
  positives={v for v in q["primary_parent_ids"] if family(v) in kept}
  if not positives:
   samples.append({"topic_id":id,"excluded_no_positive":True,"interaction":None})
   continue
  scores={m:metric(per[id][m],positives) for m in ("G00","G01","G10","G11")}
  diff=scores["G11"]-scores["G10"]-scores["G01"]+scores["G00"]
  samples.append({"topic_id":id,"excluded_no_positive":False,"positive_count":len(positives),"scores":scores,"interaction":diff})
 valid=[x["interaction"] for x in samples if x["interaction"] is not None]
 return {"kept_families":sorted(kept),"scoreable_topics":len(valid),"total_topics":len(samples),
 "average_factorial_interaction":statistics.mean(valid) if valid else None,
 "positive_topic_effects":sum(x>0 for x in valid),
 "negative_topic_effects":sum(x<0 for x in valid),
 "zero_topic_effects":sum(x==0 for x in valid),
 "scope":"post-outcome altered qrels; not independent relevance or causal inference"}
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--qrels",type=pathlib.Path,required=True)
 a.add_argument("--runs",type=pathlib.Path,required=True)
 a.add_argument("--out",type=pathlib.Path,required=True)
 x=a.parse_args()
 if x.out.exists():raise FileExistsError(x.out)
 q=json.loads(x.qrels.read_text());runs=json.loads(x.runs.read_text())
 assert len(q)==40 and len(runs)==360
 ids=[pid for query in q for pid in query["primary_parent_ids"]]
 counts=collections.Counter(family(pid) for pid in ids)
 unique={cat:len(set(pid for pid in ids if family(pid)==cat)) for cat in FAMILIES}
 if set(counts)!=set(FAMILIES):raise ValueError("Missing expected source family")
 baseline=score(q,runs,set(FAMILIES))
 result={"scope":"source-family qrel perturbation, post-outcome only",
         "qrel_counts_by_family":counts,
         "unique_parent_ids_by_family":unique,
         "baseline":baseline,
         "leave_one_family_out":{fam:score(q,runs,set(FAMILIES)-{fam}) for fam in FAMILIES},
         "only_one_family":{fam:score(q,runs,{fam}) for fam in FAMILIES},
         "input_sha256":{"qrels":hashlib.sha256(x.qrels.read_bytes()).hexdigest(),
                         "runs":hashlib.sha256(x.runs.read_bytes()).hexdigest()},
         "limitations":["Changing which source families count as relevant changes the evaluation target, not the retrieval system.",
          "Source-role validity is not independently annotated; rule-derived silver reference labels remain coupled to fields.",
          "If a topic has no positives in one family, it is excluded from that family's conditional average.",
          "This result is descriptive exploratory sensitivity, not a hypothesis test or data-independent gold evaluation."]}
 assert abs(baseline["average_factorial_interaction"]-.14438650633397873)<1e-9
 x.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
 print(json.dumps({'baseline':baseline['average_factorial_interaction'],'counts':dict(counts),
  'leave_family_out':{x:round(v['average_factorial_interaction'],6) for x,v in result['leave_one_family_out'].items()},
  'only_family':{x:(round(v['average_factorial_interaction'],6),v['scoreable_topics']) for x,v in result['only_one_family'].items()}},ensure_ascii=False))
if __name__=="__main__":main()
