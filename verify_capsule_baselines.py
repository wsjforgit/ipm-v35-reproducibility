"""Compare deterministic replay output to shipped baselines with numeric tolerance."""
from pathlib import Path
import json,hashlib,math
B=Path(__file__).resolve().parent
baseline=json.loads((B/'REPLAY_BASELINES.json').read_text());differences=[];numeric=0;maximum=0.0
def compare(a,b,path):
 global numeric,maximum
 if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):
  numeric+=1;maximum=max(maximum,abs(a-b));assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12),(path,a,b)
  if a!=b:differences.append(path)
 elif isinstance(a,dict):
  assert isinstance(b,dict) and a.keys()==b.keys(),path
  for k in a:compare(a[k],b[k],path+'/'+str(k))
 elif isinstance(a,list):
  assert isinstance(b,list) and len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
 else:assert a==b,(path,a,b)
for name,expected in baseline.items():compare(expected,json.loads((B/name).read_text()),name)
print(json.dumps({'status':'PASS','baseline_files':len(baseline),'numeric_values':numeric,'roundoff_differences':len(differences),'max_abs_difference':maximum,'tolerance':1e-12,'note':'Curated standalone capsule baselines only; this is not full private release seal validation'}))
