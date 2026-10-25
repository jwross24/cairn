import sys, json, os
sys.dont_write_bytecode=True
T0='/Users/jwross/Documents/cairn/research/intake/persistence/tier0/'
sys.path.insert(0,T0); os.chdir(T0)
from collections import Counter, defaultdict
from math import comb
from gmpy2 import mpz
from tier0v2 import multisets, two_adic_bound
zf='zf_below_1e4000.txt'; cap=2e13
skip=set()
for f in ['runall_final.jsonl','trees_c.jsonl']:
    for l in open(f):
        try: skip.add(json.loads(l)['s'])
        except Exception: pass
rows=[l.split() for l in open(zf) if l.startswith('ZF')]
S=[int(mpz(2)**int(a)*mpz(3)**int(b)*mpz(7)**int(c)) for _,d,a,b,c,p in rows]
def dp(x):
    p=1
    for ch in str(x): p*=int(ch)
    return p
def orbit_end(x):
    while x>=10: x=dp(x)
    return x
def npat(M):
    p=12
    for d,k in Counter(M).items(): p*=comb(12+k-1,k)
    return p
verts=[]
for y in S+[2,4,6,8]:
    e=orbit_end(y) if y>=10 else y
    if e not in (2,4,6,8) or y in skip: continue
    tot=sum(npat(tuple(sorted(M))) for M in multisets(y))
    if tot<=cap: verts.append((tot,e,y))
verts=sorted(set(verts))
done_v=set()
for l in open('trees_mac.jsonl'):
    try: done_v.add(json.loads(l)['s'])
    except Exception: pass
done_e=set()
for l in open('trees_mac.jsonl.eqs.jsonl'):
    try:
        d=json.loads(l); done_e.add((d['s'],tuple(d['M'])))
    except Exception: pass
pending=[v for v in verts if v[2] not in done_v]
out=[]
for tot,e,s in pending:
    for M in sorted((tuple(sorted(M)) for M in multisets(s)),key=npat):
        A=two_adic_bound(M)
        if A>=64: out.append(dict(s=s,vertex_pat=tot,M=list(M),A=A,npat=npat(M),done=(s,M) in done_e))
json.dump(dict(n_vertices=len(verts),n_pending=len(pending),pending_first=[p[2] for p in pending][:15],eqs=out),open('remaining_A64.json','w'))
print(len(verts),'vertices',len(pending),'pending; A>=64 equations in pending vertices:',len(out),'not yet done:',sum(1 for o in out if not o['done']))
for o in out: print(o['s'],o['M'],o['A'],o['npat'],'done' if o['done'] else 'TODO')
