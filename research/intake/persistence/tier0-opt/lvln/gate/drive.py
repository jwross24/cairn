import sys, os, json, time, resource, subprocess
D=sys.argv[1]; s=sys.argv[2]; known=sys.argv[3] if len(sys.argv)>3 else ''
sys.path.insert(0,D); os.chdir(D)
import run_c
from tier0v2 import multisets
from collections import Counter
from math import comb
acc={}; REC=[]; TAG=['x']; SAVE=os.environ.get('SAVE')
def ru():
    r=resource.getrusage(resource.RUSAGE_CHILDREN); return r.ru_utime+r.ru_stime
def add(k,w,c):
    a=acc.setdefault(k,[0.0,0.0]); a[0]+=w; a[1]+=c
class Shim:
    PIPE=subprocess.PIPE
    @staticmethod
    def run(cmd,**kw):
        w=time.time(); c=ru(); r=subprocess.run(cmd,**kw); add(os.path.basename(cmd[0]),time.time()-w,ru()-c)
        if os.path.basename(cmd[0])=='lvlN':
            import hashlib
            lv=os.path.basename(cmd[1])
            ln=sorted(r.stdout.splitlines())
            REC.append(dict(cfg=lv,rawsha=hashlib.sha256(r.stdout.encode()).hexdigest(),sortsha=hashlib.sha256('\n'.join(ln).encode()).hexdigest(),nlines=len(ln),stderr=r.stderr.strip(),rc=r.returncode))
            if SAVE:
                d=f"{SAVE}/{TAG[0]}"; os.makedirs(d,exist_ok=True)
                import shutil; shutil.copy(cmd[1],f"{d}/{lv}"); shutil.copy(cmd[2],f"{d}/{os.path.basename(cmd[2])}")
        return r
    class Popen(subprocess.Popen):
        pass
run_c.subprocess=Shim
orig_export=run_c.export_level
def ex(*a,**k):
    w=time.time(); r=orig_export(*a,**k); add('export_level',time.time()-w,0); return r
run_c.export_level=ex
# lvl12 launched via Popen: time whole communicate window
class P12:
    def __init__(self,cmd,**kw):
        self.p=subprocess.Popen(cmd,**kw); self.t=time.time(); self.c=ru(); self.cmd=cmd
    def communicate(self):
        r=self.p.communicate(); self.returncode=self.p.returncode; add('lvl12',time.time()-self.t,0); return r
Shim.Popen=P12
def npat(M):
    p=12
    for d,k in Counter(M).items(): p*=comb(12+k-1,k)
    return p
kn=[int(x) for x in known.split(',')] if known else []
eqs=sorted([tuple(sorted(M)) for M in multisets(int(s))], key=npat)
ONLY=os.environ.get('ONLY')
if ONLY: eqs=[M for M in eqs if ''.join(map(str,M)) in ONLY.split(',')]
tot=time.time()
for M in eqs:
    acc.clear(); REC.clear(); TAG[0]=''.join(map(str,M)); t0=time.time(); c0=ru()
    r=run_c.run(int(s),M,kn,ncores=1)
    wall=time.time()-t0
    print(json.dumps(dict(M=M,npat=npat(M),wall=round(wall,2),children_cpu=round(ru()-c0,2),acc={k:[round(x,2) for x in v] for k,v in acc.items()},open=len(r['open']),load=os.getloadavg()[0],stats=r['c_stats'],lvln=list(REC),sols=sorted(y for y in r['solutions'] if y>=10))),flush=True)
print('TOTAL',time.time()-tot)
