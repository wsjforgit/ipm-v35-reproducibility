#!/usr/bin/env python3
"""Per-topic agreement between Python 2019 external evaluation and NIST trec_eval.

trec_eval source is *only* used in local validation, not republished. The four
TREC run files are newly generated author-derived rankings, while the official
2019 judged relevance file remains local, outside public GitHub.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

METHODS=["G00","G01","G10","G11"]
def verify(bin,qrels,run_dir,own_report):
    original=json.loads(own_report.read_text())
    by_topic={x["topic_id"]:x for x in original["per_topic_results"]}
    assert len(by_topic)==38
    diffs=[]
    averages={}
    for arm in METHODS:
        fn=run_dir/f"PM2019_FTS5_{arm}.run"
        call=subprocess.run([str(bin),"-q","-m","ndcg_cut.10","-m","P.10",
                             "-m","recall.100",str(qrels),str(fn)],
                            capture_output=True,text=True,timeout=55)
        if call.returncode!=0:raise RuntimeError(call.stderr[-800:])
        reported={}
        for line in call.stdout.splitlines():
            bits=line.split()
            if len(bits)!=3:continue
            measure,topic,value=bits
            reported[(measure,topic)]=float(value)
        assert ("ndcg_cut_10","all") in reported
        for topic,entry in by_topic.items():
            compare={"ndcg_cut_10":"nDCG10_linear","P_10":"P10","recall_100":"Recall100"}
            for label,key in compare.items():
                external=reported[(label,topic)]
                internal=entry["metrics_by_arm"][arm][key]
                tolerance=0.00005001
                if abs(external-internal)>tolerance:
                    raise AssertionError(f"trec_eval drift: {arm},{topic},{key}, {external} != {internal}")
                diffs.append(abs(external-internal))
        official=reported[("ndcg_cut_10","all")]
        internal=original["means_and_interactions"]["nDCG10_linear"]["method_means"][arm]
        if abs(official-internal)>0.00005001:
            raise AssertionError("Aggregate trec_eval drift")
        averages[arm]={"trec_eval_ndcg_cut_10":official,"Python_ndcg10":internal,
                       "run_sha256":hashlib.sha256(fn.read_bytes()).hexdigest()}
    return {"validated_topics":38,"run_arms":len(METHODS),"comparisons":len(diffs),
            "largest_abs_rounded_delta":max(diffs),
            "all_absolute_differences_below_0_00005001":True,
            "official_trec_eval":averages,
            "qrels_SHA256":hashlib.sha256(qrels.read_bytes()).hexdigest(),
            "independent_method":"NIST trec_eval (local compiled executable from usnistgov/trec_eval)",
            "no_new_ground_truth":True}
def main():
    pa=argparse.ArgumentParser()
    for key in ("trec_eval","qrels","runs","our_report","out"):
        pa.add_argument("--"+key.replace("_","-"),type=Path,required=True)
    a=pa.parse_args()
    if a.out.exists():raise SystemExit("Refusing overwrite")
    data=verify(a.trec_eval,a.qrels,a.runs,a.our_report)
    a.out.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"validated":data["comparisons"],"max_delta":data["largest_abs_rounded_delta"],"out":str(a.out)},ensure_ascii=False))
if __name__=="__main__":main()
