#!/usr/bin/env python3
"""Generate the paper tables from sweep outputs. Usage: python3 tables.py out.md jsonl [jsonl ...]"""
import sys, json
from collections import Counter, defaultdict
from math import comb
from gmpy2 import mpz
out=sys.argv[1]; files=sys.argv[2:]
recs={}
for f in files:
    for l in open(f):
        try: r=json.loads(l)
        except Exception: continue
        if 's' in r and 'found' in r: recs.setdefault(r['s'], r)   # first file wins (cloud/Mac agree)
rows=[l.split() for l in open('zf_below_1e4000.txt') if l.startswith('ZF')]
S=[int(mpz(2)**int(a)*mpz(3)**int(b)*mpz(7)**int(c)) for _,d,a,b,c,p in rows]
def dp(x):
    p=1
    for ch in str(x): p*=int(ch)
    return p
def orbit_end(x):
    while x>=10: x=dp(x)
    return x
kids=defaultdict(list)
for y in S:
    if y>=10: kids[dp(y)].append(y)
verts=sorted({(orbit_end(y) if y>=10 else y, y) for y in S+[2,4,6,8] if (orbit_end(y) if y>=10 else y) in (2,4,6,8)}, key=lambda t:(t[0],t[1]))
def e237(y):
    e=[0,0,0]
    for i,p in enumerate((2,3,7)):
        while y%p==0: y//=p; e[i]+=1
    return tuple(e)
closed=[];bounded=[];incomplete=[];uncovered=[]
for d,s in verts:
    r=recs.get(s)
    if r is None: uncovered.append((d,s)); continue
    if r['closed']: closed.append((d,s,r))
    elif r['complete_below']: bounded.append((d,s,r))
    else: incomplete.append((d,s,r))
with open(out,'w') as f:
    w=f.write
    w(f"# Tables ({len(recs)} vertices computed; {len(closed)} closed, {len(bounded)} closed below a height, {len(incomplete)} incomplete, {len(uncovered)} not computed)\n\n")
    w("## Table A — closed vertices (children exactly as in T_Δ)\n\n| Δ | s = 2^a3^b7^c | children |\n|---|---|---|\n")
    for d,s,r in closed: w(f"| {d} | {s} = 2^{e237(s)[0]}3^{e237(s)[1]}7^{e237(s)[2]} | {', '.join(map(str,r['found'])) or '—'} |\n")
    w("\n## Table B — closed below a height (open patterns remain)\n\n| Δ | s | children | open patterns | height bound (digits) |\n|---|---|---|---|---|\n")
    for d,s,r in bounded: w(f"| {d} | {s} | {', '.join(map(str,r['found'])) or '—'} | {r['open']} | 10^{r['digit_bound']:.2e} |\n")
    if incomplete:
        w("\n## INCOMPLETE (a known child was not recovered — a finding)\n\n")
        for d,s,r in incomplete: w(f"- Δ={d} s={s}: found {r['found']} known {r['known']}\n")
    w("\n## Table D — vertices not computed\n\n| Δ | s | known children | multisets | patterns |\n|---|---|---|---|---|\n")
    from tier0v2 import multisets
    def npat(M):
        p=12
        for dd,k in Counter(M).items(): p*=comb(12+k-1,k)
        return p
    for d,s in uncovered:
        Ms=multisets(s); w(f"| {d} | {s} | {', '.join(map(str,kids[s])) or '—'} | {len(Ms)} | {sum(npat(M) for M in Ms):.2e} |\n")
print(f"wrote {out}: closed {len(closed)}, bounded {len(bounded)}, incomplete {len(incomplete)}, uncovered {len(uncovered)}")
