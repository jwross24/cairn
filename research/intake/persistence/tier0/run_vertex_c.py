#!/usr/bin/env python3
"""Full vertex through the C level-12 pass: python3 run_vertex_c.py <s> <known,children> [ncores] [max_patterns]"""
import sys, json, time, os
from collections import Counter
from math import comb
from tier0v2 import multisets
from run_c import run
s=int(sys.argv[1]); known=[int(x) for x in sys.argv[2].split(',')] if len(sys.argv)>2 and sys.argv[2] else []
ncores=int(sys.argv[3]) if len(sys.argv)>3 else os.cpu_count(); budget=float(sys.argv[4]) if len(sys.argv)>4 else 1e30
def npat(M):
    p=12
    for d,k in Counter(M).items(): p*=comb(12+k-1,k)
    return p
eqs=sorted([tuple(sorted(M)) for M in multisets(s)], key=npat)
print(f"vertex {s}: {len(eqs)} multisets, {sum(1 for M in eqs if npat(M)<=budget)} within budget, total patterns {sum(npat(M) for M in eqs if npat(M)<=budget):.3e}", file=sys.stderr, flush=True)
found=set(); nopen=0; done=0
for M in eqs:
    if npat(M)>budget: continue
    t0=time.time(); r=run(s,M,known,ncores=ncores)
    sols=sorted(y for y in r['solutions'] if y>=10); found|=set(sols); nopen+=len(r['open']); done+=1
    print(json.dumps(dict(s=s,M=M,npat=npat(M),open=len(r['open']),sols=sols,bounds=r['bounds'],exceptional=r['exceptional'],c_stats=r['c_stats'],levels=[(L,n,sv,cls) for (L,ps,n,sv,cls,el) in r['levels']],secs=round(time.time()-t0))), flush=True)
    print(f"  M={M} patterns={npat(M):.2e} {'CLOSED' if not r['open'] else 'OPEN('+str(len(r['open']))+')'} sols={sols} {round(time.time()-t0)}s", file=sys.stderr, flush=True)
print(json.dumps(dict(vertex=s, done=done, total=len(eqs), open_patterns=nopen, children=sorted(found), known=sorted(known), complete=(found==set(known)))), flush=True)
print(f"VERTEX {s}: {done}/{len(eqs)} multisets run; open patterns {nopen}; children {sorted(found)} known {sorted(known)}", file=sys.stderr, flush=True)
