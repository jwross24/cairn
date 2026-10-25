import sys,os,time,json
sys.path.insert(0,'/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
import subprocess,run_c
run_c.HERE='/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/reference'
NU=int(os.environ.get('NU','1')); CAP=int(os.environ.get('PCAP','2000'))
_P=subprocess.Popen
def P(cmd,*a,**k):
    if os.path.basename(cmd[0])=='lvl12' and len(cmd)==4: cmd=[cmd[0],cmd[1],'0',str(NU)]
    return _P(cmd,*a,**k)
run_c.subprocess.Popen=P
_m=run_c.make_c_lift
def mk(M,wd,nc=1):
    f=_m(M,wd,nc)
    def lift(Lp,L,surv,fg):
        if L==24: surv=surv[:CAP]
        return f(Lp,L,surv,fg)
    return lift
run_c.make_c_lift=mk
s=int(sys.argv[1]); M=tuple(int(x) for x in sys.argv[2].split(','))
t0=time.time(); r=run_c.run(s,M,[],ncores=1)
lv=[(L,n,sv) for (L,ps,n,sv,c,el) in r['levels']]
print(json.dumps(dict(s=s,q=len(M),npat_sample=r['c_stats']['patterns'],nu=NU,levels=lv,secs=round(time.time()-t0,1))),flush=True)
