import os
#!/usr/bin/env python3
"""Run the generic engine over all nonzero-target vertices of base b. python3 run_base.py <b> <D> <levels> [out.jsonl]"""
import sys, json, time
from collections import defaultdict, Counter
from engine_b import Base, solve_equation, brute
b=int(sys.argv[1]); D=int(sys.argv[2]); levels=tuple(int(x) for x in sys.argv[3].split(',')); outp=sys.argv[4] if len(sys.argv)>4 else None
base=Base(b)
# enumerate zero-free S-units below b^D
lim=b**D; zf=[]
def rec(i,val):
    if i==len(base.dp):
        if val>=b and 0 not in base.digits(val): zf.append(val)
        return
    v=val
    while v<lim: rec(i+1,v); v*=base.dp[i]
rec(0,1)
def orbit_end(x):
    while x>=b: x=base.dprod(x)
    return x
kids=defaultdict(list)
for y in zf: kids[base.dprod(y)].append(y)
verts=sorted({(orbit_end(y),y) for y in zf if orbit_end(y)!=0} | {(d,d) for d in range(1,b)})
print(f"base {b}: {len(verts)} vertices (incl. roots) over nonzero targets", file=sys.stderr, flush=True)
done=set()
if outp and os.path.exists(outp):
    for line in open(outp):
        try: done.add(json.loads(line)['s'])
        except Exception: pass
out=open(outp,'a') if outp else None
summary=Counter()
for t,s in sorted(verts, key=lambda v:(v[1])):
    if s in done:
        print(f"  skip s={s} (already in {outp})", file=sys.stderr, flush=True); continue
    t0=time.time(); found=set(); nopen=0; eqs=[]; incomplete=False; bounds=[]
    for M in base.multisets(s):
        kn=sorted(set(brute(base,M,12))|{y for y in kids[s] if Counter(d for d in base.digits(y) if d!=1)==Counter(M)})
        try:
            r=solve_equation(base,s,M,kn,levels)
        except AssertionError as e:
            print(f"  s={s} M={M}: {e}", file=sys.stderr, flush=True); incomplete=True; continue
        sols={y for y in r['solutions'] if y>=b}
        # exceptional small point of each open pattern (recorded: bounded exps, nu, eps, y, is-solution)
        exceptional=[]
        for (bv,nu,eps,co) in r['open']:
            pt=co.nearest(); y=None; issol=False
            if all(c>=0 for c in pt) and max(pt)<200:
                y=1
                for p,a in zip(base.bounded,bv): y*=p**a
                for q,v in zip(base.free,pt): y*=q**v
                dg=base.digits(y)
                if y>=b and 0 not in dg and Counter(d for d in dg if d!=1)==Counter(M) and len(dg)%levels[-1]==nu%levels[-1] and y%b: sols.add(y); issol=True
            exceptional.append([list(bv),nu,list(eps),y,issol])
        found|=sols; nopen+=len(r['open'])
        if r['bound_digits']: bounds.append(r['bound_digits'])
        eqs.append(dict(M=M,open=len(r['open']),sols=sorted(sols),brute=kn,exceptional=exceptional,levels=[(L,n,sv,cls) for (L,ps,n,sv,cls,el) in r['levels']]))
        if set(kn)-sols: incomplete=True
    st='INCOMPLETE' if incomplete else ('CLOSED' if nopen==0 else f"CLOSED BELOW 10^{min(bounds):.1e} DIGITS")
    summary[st.split()[0]]+=1
    rec_=dict(base=b,target=t,s=s,known=sorted(kids[s]),found=sorted(found),open=nopen,status=st,secs=round(time.time()-t0),eqs=eqs)
    if out: out.write(json.dumps(rec_)+'\n'); out.flush()
    print(f"  target {t} s={s} ({'.'.join(map(str,base.digits(s)))}_b) {st}; children {sorted(found)} known {sorted(kids[s])} {rec_['secs']}s", file=sys.stderr, flush=True)
print("SUMMARY", dict(summary), file=sys.stderr)
