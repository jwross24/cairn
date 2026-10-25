"""usage: stageprof.py <srcdir> <s> <known> [ncores]  -- runs run_vertex_c-equivalent loop with stage timers"""
import sys, os, time, json, subprocess, resource
srcdir=sys.argv[1]; s=int(sys.argv[2]); known=[int(x) for x in sys.argv[3].split(',')] if sys.argv[3] else []; nc=int(sys.argv[4]) if len(sys.argv)>4 else 3
os.chdir(srcdir); sys.path.insert(0,srcdir)
import run_c, tier0v2
from collections import Counter
from math import comb
acc=Counter()
def timed(mod,name,key):
    f=getattr(mod,name)
    def w(*a,**k):
        t=time.perf_counter(); r=f(*a,**k); acc[key]+=time.perf_counter()-t; return r
    setattr(mod,name,w)
timed(run_c,'export','export12'); timed(run_c,'export_level','exportN'); timed(tier0v2,'descend','descent')
_run=subprocess.run
def trun(cmd,*a,**k):
    t=time.perf_counter(); r=_run(cmd,*a,**k); acc['lvlN_wall']+=time.perf_counter()-t; acc['nlvlN']+=1; return r
run_c.subprocess.run=trun
_P=subprocess.Popen
class P(_P):
    def communicate(s_,*a,**k):
        t=time.perf_counter(); r=super().communicate(*a,**k); acc['lvl12_wall']+=time.perf_counter()-t; return r
run_c.subprocess.Popen=P
timed(tier0v2,'solve_equation','solve_equation')
import export_level, export_cfg
def objw(mod,name):
    c=getattr(mod,name)
    def w(*a,**k):
        t=time.perf_counter(); r=c(*a,**k); acc['setup_obj']+=time.perf_counter()-t; return r
    setattr(mod,name,w)
for m in (tier0v2,export_level,export_cfg):
    for n in ('PrimeData','FastLevel','FastLevelGen'):
        if hasattr(m,n): objw(m,n)
timed(tier0v2,'classify','classify')
import pydesc as _pd
timed(_pd,'classify_batch','cbatch') if hasattr(tier0v2,'pydesc') else None
if hasattr(_pd,'RawSurv'):
    timed(_pd.RawSurv,'classify','raw_classify'); timed(_pd,'scan12','scan12')
_mk=run_c.make_c_lift
def mk(*a,**k):
    f=_mk(*a,**k)
    def g(*a2,**k2):
        t=time.perf_counter(); r=f(*a2,**k2); acc['lift_total']+=time.perf_counter()-t; return r
    return g
run_c.make_c_lift=mk
timed(tier0v2,'canon','canon')
run_c.solve_equation=tier0v2.solve_equation
def npat(M):
    p=12
    for d,k in Counter(M).items(): p*=comb(12+k-1,k)
    return p
eqs=sorted([tuple(sorted(M)) for M in tier0v2.multisets(s)], key=npat)
if os.environ.get('EQ'): eqs=[tuple(int(x) for x in os.environ['EQ'].split(','))]
tot0=time.perf_counter(); rows=[]
for M in eqs:
    a0=Counter(acc); t=time.perf_counter()
    r=run_c.run(s,M,known,ncores=nc)
    w=time.perf_counter()-t
    d={k:acc[k]-a0[k] for k in acc}; d['wall']=w; d['M']=M; d['npat']=npat(M)
    d['nsurv12']=r['levels'][0][3]; rows.append(d)
    print(json.dumps({k:(round(v,3) if isinstance(v,float) else v) for k,v in d.items()}),flush=True)
print('TOTAL',round(time.perf_counter()-tot0,2),{k:round(v,2) for k,v in acc.items()})
