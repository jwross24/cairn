import gzip, sys, os, random
H=os.path.dirname(os.path.abspath(__file__))
tag=sys.argv[1]
toks=open(f'{H}/cfgs/cfg_{tag}.txt').read().split(None,200)
L,A,q=map(int,toks[:3]); digits=list(map(int,toks[3:3+q]))
cnt={}
for d in digits: cnt[d]=cnt.get(d,0)+1
def alive(a,nu,eps,b,c):
    Y=pow(2,a,1000)*pow(3,b,1000)*pow(7,c,1000)%1000
    have={}; ph={}
    for d,e in zip(digits,eps): ph[(d,e)]=ph.get((d,e),0)+1
    for i in range(3):
        d=(Y//10**i)%10
        if d==0: return False
        if d==1: continue
        have[d]=have.get(d,0)+1
        if have[d]>cnt.get(d,0): return False
        if ph.get((d,i),0)<1: return False
    return True
def load(w):
    S=set()
    with gzip.open(f'{H}/runs/{tag}.{w}.sorted.gz','rt') as g:
        for l in g: S.add(l)
    return S
P=load('prod'); F1=load('fix1'); F2=load('fix2')
def parse(l):
    f=l.split(); return int(f[1]),int(f[2]),tuple(int(x) for x in f[3:3+q]),int(f[3+q]),int(f[4+q])
def chk(S,name,want,sample=None):
    S=list(S)
    if sample and len(S)>sample: random.seed(1); S=random.sample(S,sample)
    bad=sum(1 for l in S if alive(*parse(l))!=want)
    print(f'{tag} {name}: checked {len(S)} lines, expected tail-alive={want}, violations={bad}')
chk(F2,'fix2 (all lines, a>=64 and a<64)',True)
chk(F2-F1,'fix2 minus fix1 (dropped by fix1)',True)
chk(P-F2,'prod minus fix2 (spurious in prod)',False,sample=300000)
