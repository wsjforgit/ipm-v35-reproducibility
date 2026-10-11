"""Independent float64 score check and portable RRF rank reconstruction.

--local-embeddings checks the private Q/D matrices and exports identifiers,
never source full text. The default mode uses exported identifiers and scores.
"""
from pathlib import Path
import json,math,hashlib,argparse,gzip
p=argparse.ArgumentParser();p.add_argument('--dataset',choices=['e19','eclef'],required=True);p.add_argument('--local-embeddings',action='store_true');p.add_argument('--input-root',type=Path);a=p.parse_args()
B=Path(__file__).resolve().parent;S=B/'external_ip'/a.dataset
def load(p):
 if p.exists(): return json.loads(p.read_text())
 gz=p.with_name(p.name+'.gz')
 if gz.exists():
  with gzip.open(gz,'rt',encoding='utf-8') as f: return json.load(f)
 raise FileNotFoundError(str(p))

def sha(p):
 if p.exists(): payload=p.read_bytes()
 else: payload=gzip.decompress(p.with_name(p.name+'.gz').read_bytes())
 return hashlib.sha256(payload).hexdigest()

runs=load(S/'RUNS.json')['runs']
if a.local_embeddings:
 import numpy as np
 assert a.input_root is not None,'--local-embeddings requires the archive kaggle --input-root'
 E=a.input_root/(a.dataset+'_neural_input')
 fn=E/('candidates.jsonl.gz' if a.dataset=='e19' else 'docs.jsonl')
 with gzip.open(fn,'rt') if fn.suffix=='.gz' else fn.open() as f:docs=[json.loads(x) for x in f if x.strip()]
 topics=[json.loads(x) for x in (E/'topics.jsonl').read_text().splitlines() if x.strip()]
 lex={x['topic_id']:x for x in load(E/'lexical_runs.json')['runs']}
 ids=[x['nct_id' if a.dataset=='e19' else 'pmid'] for x in docs];ix={x:i for i,x in enumerate(ids)}
 Q=np.load(S/'Q.npy');D=np.load(S/'D.npy',mmap_mode='r')
 assert np.isfinite(Q).all() and np.isfinite(D).all()
 exported=[];maxerr=0;pair_inversions=0;checked=0;tops=0
 for qi,(t,r) in enumerate(zip(topics,runs)):
  assert t['topic_id']==r['topic_id']
  l=lex[t['topic_id']]
  if a.dataset=='e19':
   cand=list(dict.fromkeys(l['X00_RAW_FLAT']['ids'][:1000]+l['X11_FIELD_STRUCTQ']['ids'][:1000]));bm=l['X00_RAW_FLAT']['ids'][:1000]
  else:cand=[x for x in t['candidate_pmids'] if x in ix];bm=l['BM25_TITLE']['ids']
  v=np.einsum('ij,j->i',D[[ix[x] for x in cand]].astype('float64'),Q[qi].astype('float64'),optimize=False)
  expected={x:float(v[i]) for i,x in enumerate(cand)}
  saved=r['MEDCPT_RAW_IP'];assert set(saved['ids'])==set(cand)
  for x,y in zip(saved['ids'],saved['scores']):
   assert math.isfinite(y);maxerr=max(maxerr,abs(y-expected[x]));checked+=1
  assert maxerr<.0001,('float32/float64 disagreement',maxerr)
  # Near ties can reorder under a changed arithmetic runtime; retained scores
  # and their fixed candidate-index tie convention define the executed run.
  positions={x:i for i,x in enumerate(cand)}
  order=sorted(cand,key=lambda x:(-expected[x],positions[x]))
  tops+=order[:10]==saved['ids'][:10]
  pair_inversions+=sum(expected[x]+.0001<expected[y] for x,y in zip(saved['ids'],saved['ids'][1:]))
  exported.append({'topic_id':t['topic_id'],'candidate_ids':cand,'BM25_ids':bm})
 assert pair_inversions==0
 (S/'RANK_INPUTS.json').write_text(json.dumps({'inputs':exported,'scope':'Identifiers and lexical ranks only; source text excluded'},indent=2))
 numeric={'float64_score_values_checked':checked,'maximum_absolute_error':maxerr,'non_tie_order_inversions':pair_inversions,'exact_float64_top10_topics':tops,'total_topics':len(runs),'all_embeddings_finite':True,'scope':'Independent arithmetic comparison against frozen float32 scores; float64 is not a new ranking experiment'}
else:numeric=load(S/'NUMERICAL_REPLAY.json').get('numerical_check',{})
inputs={x['topic_id']:x for x in load(S/'RANK_INPUTS.json')['inputs']};n=0
for r in runs:
 i=inputs[r['topic_id']];cand=i['candidate_ids'];saved=r['MEDCPT_RAW_IP'];score=dict(zip(saved['ids'],saved['scores']));ci={x:j for j,x in enumerate(cand)}
 assert sorted(cand,key=lambda x:(-score[x],ci[x]))==saved['ids']
 mr={x:j+1 for j,x in enumerate(saved['ids'])};br={x:j+1 for j,x in enumerate(i['BM25_ids'])}
 scores={x:1/(60+br.get(x,1001))+1/(60+mr[x]) for x in cand}
 rr=sorted(cand,key=lambda x:(-scores[x],x));assert rr==r['RRF_RAW_IP']['ids']
 assert all(abs(scores[x]-s)<1e-15 for x,s in zip(rr,r['RRF_RAW_IP']['scores']))
 n+=len(cand)
result={'status':'PASS','dataset':a.dataset,'topics':len(runs),'ranking_outputs_reconstructed':2*len(runs),'RRF_score_values_checked':n,'numerical_check':numeric,'RUNS_sha256':sha(S/'RUNS.json'),'rank_inputs_sha256':sha(S/'RANK_INPUTS.json'),'new_neural_inference':False}
(S/'NUMERICAL_REPLAY.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
