import sys, time, json, os, subprocess, tempfile, shutil
import run_c
from math import comb
from collections import Counter
s=int(sys.argv[1]); M=tuple(int(x) for x in sys.argv[2].split(','))
T={'lvl12_wall':0.0,'lift':{}, 'lvlN_proc':{}}
cur={'L':None}
orig_run=subprocess.run
def timed_run(args,*a,**k):
    t=time.time(); r=orig_run(args,*a,**k)
    if isinstance(args,list) and str(args[0]).endswith('lvlN'):
        T['lvlN_proc'][cur['L']]=T['lvlN_proc'].get(cur['L'],0)+time.time()-t
    return r
run_c.subprocess.run=timed_run
orig_make=run_c.make_c_lift
def make(Mx,workdir,ncores=1):
    inner=orig_make(Mx,workdir,ncores)
    def lift(Lp,L,surv,fg):
        cur['L']=L; t=time.time(); out=inner(Lp,L,surv,fg)
        T['lift'][L]={'wall':time.time()-t,'parents':len(surv),'children_out':len(out[0])}
        return out
    return lift
run_c.make_c_lift=make
orig_popen=subprocess.Popen
class P(orig_popen):
    def __init__(self,args,*a,**k):
        self.t0=time.time(); self.is12=isinstance(args,list) and str(args[0]).endswith('lvl12'); super().__init__(args,*a,**k)
    def communicate(self,*a,**k):
        r=super().communicate(*a,**k)
        if self.is12: T['lvl12_wall']=max(T['lvl12_wall'],time.time()-self.t0)
        return r
run_c.subprocess.Popen=P
wd=tempfile.mkdtemp(prefix='liftshare_',dir='/private/tmp/persist-gpu/work')
t0=time.time(); r=run_c.run(s,M,[],ncores=1,workdir=wd)
tot=time.time()-t0
shutil.rmtree(wd,ignore_errors=True)
T['total']=tot; T['eq']=f"{s}_{''.join(map(str,M))}"; T['levels']=[(L,n,sv) for (L,ps,n,sv,cls,el) in r['levels']]; T['open']=len(r['open']); T['c_stats']=dict(r['c_stats'])
print(json.dumps(T))
