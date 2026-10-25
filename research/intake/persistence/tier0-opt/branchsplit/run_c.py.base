#!/usr/bin/env python3
"""Drive the C level-12 pass for one (s, multiset), then finish in Python (descent + lifting)."""
import sys, os, json, subprocess, time
from collections import Counter
from export_cfg import export
import pydesc
from tier0v2 import solve_equation, canon, factor237
from lattice import Coset
import math
HERE=os.path.dirname(os.path.abspath(__file__))
from export_level import export as export_level
def make_c_lift(M, workdir, ncores=1):
    M=tuple(sorted(M)); q=len(M)
    def lift(L_prev, L, survivors, fg):
        cfgp=f"{workdir}/cfgL{L}.txt"; info=export_level(M, L, cfgp)
        Uo=info['U_old']; Un=info['U_new']
        par=f"{workdir}/parents{L}.txt"
        with open(par,'w') as f:
            for (a,nu,eps,co) in survivors: f.write(f"{a} {nu} "+' '.join(map(str,eps))+f" {co.v0[0]} {co.v0[1]}\n")
        out=subprocess.run([f"{HERE}/lvlN", cfgp, par],capture_output=True,text=True)
        assert out.returncode==0, out.stderr
        parts=out.stderr.split(); stats={k:int(v) for k,v in zip(parts[0::2],parts[1::2]) if v.lstrip('-').isdigit()}
        surv=[]; seen=set()
        for line in out.stdout.splitlines():
            f=line.split()
            if f[0] not in ('OPEN','EXACT'): continue
            pidx,a,nu=int(f[1]),int(f[2]),int(f[3]); eps=tuple(int(x) for x in f[4:4+q]); t1,t2=int(f[4+q]),int(f[5+q])
            pa=survivors[pidx]; b=pa[3].v0[0]+t1*Uo[0][0]+t2*Uo[1][0]; c=pa[3].v0[1]+t1*Uo[0][1]+t2*Uo[1][1]
            nu2,eps2=canon(M,nu,eps); key=(a,nu2,eps2)
            if key in seen: continue
            seen.add(key); surv.append((a,nu2,eps2,Coset((b,c),tuple(Un[0]),tuple(Un[1]))))
        return surv, stats.get('children',0), stats
    return lift

def run(s, M, known, ncores=2, workdir=None, verbose=False, clift=None):
    if clift is None: clift = os.environ.get('NOCLIFT') is None
    import tempfile, shutil
    M=tuple(sorted(M)); tag=f"{s}_{''.join(map(str,M))}"
    cleanup = workdir is None
    if workdir is None: workdir = tempfile.mkdtemp(prefix='persist_')
    cfgp=f"{workdir}/cfg_{tag}.txt"; cfg=export(M, cfgp)
    L=cfg['L']; U2=cfg['U2']
    # split nu ranges across cores
    procs=[]; outs=[]
    for i in range(ncores):
        lo=L*i//ncores; hi=L*(i+1)//ncores
        outp=f"{workdir}/l12_{tag}_{i}.txt"; outs.append(outp)
        procs.append(subprocess.Popen([f"{HERE}/lvl12", cfgp, str(lo), str(hi)], stdout=open(outp,'w'), stderr=subprocess.PIPE, text=True))
    stats=Counter()
    for p in procs:
        _,err=p.communicate(); assert p.returncode==0, err
        for tok in err.split():
            pass
        parts=err.split()
        for k,v in zip(parts[0::2], parts[1::2]):
            try: stats[k]+=int(v)
            except ValueError: pass
    # parse
    q=len(M)
    scan = pydesc.scan12(outs, q) if pydesc.ENABLED else None
    if scan is not None:
        surv = pydesc.RawSurv(outs, M, U2, scan[0]); exact = []
        for line in scan[1]:
            f=line.split()
            a,nu=int(f[1]),int(f[2]); eps=tuple(int(x) for x in f[3:3+q]); b,c=int(f[3+q]),int(f[4+q]); Y=int(f[5+q])
            exact.append((a,nu,eps,b,c,Y))
    else:
        surv=[]; exact=[]
        for outp in outs:
            for line in open(outp):
                f=line.split()
                if f[0]=='OPEN':
                    a,nu=int(f[1]),int(f[2]); eps=tuple(int(x) for x in f[3:3+q]); b,c=int(f[3+q]),int(f[4+q])
                    nu2,eps2=canon(M,nu,eps)
                    surv.append((a,nu2,eps2,Coset((b,c),tuple(U2[0]),tuple(U2[1]))))
                elif f[0]=='EXACT':
                    a,nu=int(f[1]),int(f[2]); eps=tuple(int(x) for x in f[3:3+q]); b,c=int(f[3+q]),int(f[4+q]); Y=int(f[5+q])
                    exact.append((a,nu,eps,b,c,Y))
    # verify exact candidates
    sols=set()
    for a,nu,eps,b,c,Y in exact:
        fct=factor237(Y)
        if fct and fct[0]==a and Coset((b,c),tuple(U2[0]),tuple(U2[1])).contains(fct[1],fct[2]):
            sols.add(Y)
    kn=[y for y in known if Counter(ch for ch in str(y) if ch!='1')==Counter(str(d) for d in M)]
    r=solve_equation(s, M, kn, verbose=verbose, l12=surv, l12_n_in=stats['patterns'], presolved=sols, lift_fn=(make_c_lift(M, workdir) if clift else None))
    r['c_stats']=dict(stats)
    # open patterns: nearest coset point (Babai) and certified digit bound for any other solution
    r['bounds']=[]; r['exceptional']=[]
    for (a,nu,eps,co) in r['open']:
        u=co.u1; norm=math.hypot(u[0],u[1]); digits=int(norm/(2*math.sqrt(2))*math.log10(3))
        from fractions import Fraction
        u1,u2=co.u1,co.u2; v0=co.v0; det=u1[0]*u2[1]-u1[1]*u2[0]
        x=round(Fraction(-v0[0]*u2[1]+v0[1]*u2[0],det)); yy=round(Fraction(v0[0]*u1[1]-v0[1]*u1[0],det))
        # exact nearest point among the rounding neighbours (Babai on a Lagrange-reduced basis)
        best=None
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                bb=v0[0]+(x+dx)*u1[0]+(yy+dy)*u2[0]; cc=v0[1]+(x+dx)*u1[1]+(yy+dy)*u2[1]
                nn=bb*bb+cc*cc
                if best is None or nn<best[0]: best=(nn,bb,cc)
        b0,c0=best[1],best[2]
        r['bounds'].append(digits)
        if b0>=0 and c0>=0 and max(b0,c0)<norm/2:
            y=2**a*3**b0*7**c0; sY=str(y)
            ok='0' not in sY and Counter(ch for ch in sY if ch!='1')==Counter(str(d) for d in M) and len(sY)%12==nu%12
            if ok and y>=10: r['solutions'].add(y)
            r['exceptional'].append((a, y if y<10**40 else f"~10^{len(sY)}", ok))
    r['open_patterns']=dict(level=int(r['levels'][-1][0]), M=[int(d) for d in M], items=[dict(a=int(a),nu=int(nu),eps=[int(e) for e in eps],v0=[int(x) for x in co.v0],u1=[int(x) for x in co.u1],u2=[int(x) for x in co.u2]) for (a,nu,eps,co) in r['open']])
    found={y for y in r['solutions'] if y>=10}
    r['closed']=(not r['open']) and found==set(kn)
    r['complete_below']=found==set(kn)
    if cleanup: shutil.rmtree(workdir, ignore_errors=True)
    return r
if __name__=="__main__":
    s=int(sys.argv[1]); M=tuple(int(x) for x in sys.argv[2].split(',')); known=[int(x) for x in sys.argv[3].split(',')] if len(sys.argv)>3 and sys.argv[3] else []
    t0=time.time(); r=run(s,M,known,verbose=True)
    print(json.dumps(dict(s=s,M=M,closed=r['closed'],open=len(r['open']),sols=sorted(y for y in r['solutions'] if y>=10),c_stats=r['c_stats'],
                          levels=[(L,n,sv,cls) for (L,ps,n,sv,cls,el) in r['levels']],secs=round(time.time()-t0))))
