import sys,os,time,json,resource,subprocess
sys.path.insert(0,'/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
import run_c, tier0v2
run_c.HERE='/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/reference'
acc={}
def add(k,v): acc[k]=acc.get(k,0)+v
def child_cpu():
    r=resource.getrusage(resource.RUSAGE_CHILDREN); return r.ru_utime+r.ru_stime
# wrap Popen.communicate for lvl12, subprocess.run for lvlN
_run=subprocess.run
def trun(cmd,*a,**k):
    c0=child_cpu(); t0=time.time(); r=_run(cmd,*a,**k); add('lvlN_cpu',child_cpu()-c0); add('lvlN_wall',time.time()-t0); return r
run_c.subprocess.run=trun
_P=subprocess.Popen
class P(_P):
    def communicate(s,*a,**k):
        c0=child_cpu(); t0=time.time(); r=super().communicate(*a,**k); add('lvl12_cpu',child_cpu()-c0); add('lvl12_wall',time.time()-t0); return r
run_c.subprocess.Popen=P
_d=tier0v2.descend
def td(*a,**k):
    t0=time.process_time(); r=_d(*a,**k); add('descent_cpu',time.process_time()-t0); add('ndescent',1); return r
tier0v2.descend=td
_ex=run_c.export
def tex(*a,**k):
    t0=time.process_time(); r=_ex(*a,**k); add('export12_cpu',time.process_time()-t0); return r
run_c.export=tex
_el=run_c.export_level
def tel(*a,**k):
    t0=time.process_time(); r=_el(*a,**k); add('exportN_cpu',time.process_time()-t0); return r
run_c.export_level=tel
if __name__=='__main__':
    s=int(sys.argv[1]); M=tuple(int(x) for x in sys.argv[2].split(','))
    t0=time.process_time(); w0=time.time()
    r=run_c.run(s,M,[],ncores=1)
    tot=time.process_time()-t0
    out=dict(s=s,M=M,load=os.getloadavg()[0],py_cpu_total=tot,wall=time.time()-w0,**acc)
    out['npat']=r['c_stats']['patterns']; out['c_stats']=r['c_stats']
    out['levels']=[(L,n,sv,cls) for (L,ps,n,sv,cls,el) in r['levels']]; out['open']=len(r['open'])
    print(json.dumps(out))
