from pathlib import Path
import json,math,collections,statistics
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
q={x['topic_id']:set(x['primary_parent_ids']) for x in read('DOCUMENTARY_QRELS.json')}
runs={(x['topic_id'],x['method']):x['parent_ids'] for x in read('FORMAL_RUNS.json')}
freq=collections.Counter(d for gold in q.values() for d in gold)
def score(order,gold,weighted=False):
 w={d:(1/freq[d] if weighted else 1) for d in gold}
 ideal=sum(v/math.log2(i+2) for i,v in enumerate(sorted(w.values(),reverse=True)[:10]))
 return sum(w.get(d,0)/math.log2(i+2) for i,d in enumerate(order[:10]))/ideal if ideal else 0
expected=read('E7_METRIC_RECOMPUTATION.json')['per_topic']
for x in expected:
 t,m=x['topic_id'],x['method'];assert abs(score(runs[t,m],q[t])-x['ndcg10'])<1e-12,(t,m)
v=[]
for t in sorted(q):
 s={m:score(runs[t,m],q[t],True) for m in ['G00','G01','G10','G11']};v.append(s['G11']-s['G10']-s['G01']+s['G00'])
interaction=statistics.mean(v);assert abs(interaction-read('E3.json')['weighted_interaction'])<1e-12
print('Formal metric rows reproduced:',len(expected));print('Weighted interaction:',interaction)
print('Documentary verification only; no independent clinical validation.')
