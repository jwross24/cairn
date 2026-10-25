import json, os, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from compare import diff, H
recs={}
for l in open(f'{H}/runs_slice.jsonl'):
    r=json.loads(l)
    if r['rc']==0: recs[(r['tag'],r['lo'],r['hi'],r['which'])]=r
for (t,lo,hi,w) in sorted(recs):
    if w!='prod' or (t,lo,hi,'fix2') not in recs: continue
    p=f'{H}/runs/{t}.nu{lo}-{hi}.'
    d=diff(p+'prod.sorted.gz',p+'fix2.sorted.gz') if recs[(t,lo,hi,'prod')]['sha256']!=recs[(t,lo,hi,'fix2')]['sha256'] else 'IDENTICAL'
    print(t,f'nu[{lo},{hi})',recs[(t,lo,hi,'prod')]['lines'],recs[(t,lo,hi,'fix2')]['lines'],d)
