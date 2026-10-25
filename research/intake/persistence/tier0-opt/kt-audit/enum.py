import sys, json, glob, os
sys.dont_write_bytecode=True
sys.path.insert(0,'/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
from tier0v2 import two_adic_bound
P='/Users/jwross/Documents/cairn/research/intake/persistence/'
files=[P+'tier0/trees_c.jsonl',P+'tier0/trees_mac.jsonl',P+'tier0/trees_mac.jsonl.eqs.jsonl',P+'tier0/run72_final.jsonl',P+'tier0/runall_final.jsonl']+sorted(glob.glob(P+'tier0-opt/*.jsonl'))+sorted(glob.glob(P+'tier0-opt/golden/*.jsonl'))
rows={}
for f in files:
    for l in open(f):
        try: d=json.loads(l)
        except Exception: continue
        eqs=d['eqs'] if 'eqs' in d else [d]
        for e in eqs:
            if isinstance(e,list): continue
            if 'M' not in e: continue
            s=e.get('s',d.get('s'))
            lv=[x[0] for x in e.get('levels',[])]
            key=(s,tuple(e['M']))
            r=rows.setdefault(key,{'files':set(),'lv':set()})
            r['files'].add(os.path.relpath(f,P)); r['lv']|=set(lv)
out=[]
for (s,M),r in rows.items():
    mx=max(r['lv']) if r['lv'] else None
    if mx and mx>12:
        A=two_adic_bound(M)
        out.append((s,M,A,sorted(r['lv']),sorted(r['files'])))
json.dump([[s,list(M),A,lv,fs] for s,M,A,lv,fs in out],open('eqs_lift.json','w'))
print(len(rows),'eqs',len(out),'with lvlN levels; A>=64:',sum(1 for o in out if o[2]>=64), 'max A',max(o[2] for o in out))
for o in sorted(out,key=lambda o:-o[2])[:15]: print(o[0],o[1],o[2],o[3],o[4])
