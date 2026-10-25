import sys, os, json, subprocess, collections
sys.dont_write_bytecode=True
T0='/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0,T0)
os.environ['DESCENT_MAX']='1e18'
from export_cfg import export
from tier0v2 import solve_equation
from lattice import Coset
PROD=T0+'/lvlN'; FIX='/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/lift-ideation/lvlNf'
s=int(sys.argv[1]); M=tuple(int(x) for x in sys.argv[2].split(',')); W=sys.argv[3]; nsamp=int(sys.argv[4])
tag=f"{s}_{''.join(map(str,M))}"; q=len(M)
cfg=export(M,'/tmp/_unused_cfg.txt') if False else None
import tempfile
tmpd=tempfile.mkdtemp(prefix='ktpy_'); cfg=export(M,tmpd+'/c.txt'); U2=cfg['U2']
par=f'{W}/parents24_prod.txt'; cfgL=f'{W}/cfgL24.txt'
head=f'{tmpd}/head.txt'
with open(par) as f, open(head,'w') as g:
    for i,l in enumerate(f):
        if i>=3000: break
        g.write(l)
lines=open(head).read().splitlines()
def run(b):
    p=subprocess.run(['nice','-n','10',b,cfgL,head],capture_output=True,text=True); c=collections.Counter()
    for l in p.stdout.splitlines():
        f=l.split()
        if f[0] in('OPEN','EXACT'): c[int(f[1])]+=1
    return c
cp=run(PROD); cf=run(FIX)
cand=sorted(set(cp)|set(cf), key=lambda i:-(abs(cp[i]-cf[i])))
print('subset 3000 parents: prod total',sum(cp.values()),'fixed total',sum(cf.values()))
agree_f=agree_p=0; n=0
for i in cand[:nsamp]:
    f=lines[i].split(); a,nu=int(f[0]),int(f[1]); eps=tuple(int(x) for x in f[2:2+q]); v0=(int(f[2+q]),int(f[3+q]))
    par_=(a,nu,eps,Coset(v0,tuple(U2[0]),tuple(U2[1])))
    r=solve_equation(s,M,[],verbose=False,l12=[par_],l12_n_in=1,levels=(12,24))
    py=[x for x in r['levels'] if x[0]==24]
    npy=(py[0][3],py[0][4]) if py else None
    print('pidx',i,'a',a,'prod',cp[i],'fixed',cf[i],'python (prefilter-survivors, classes)',npy,flush=True)
