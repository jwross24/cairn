import gzip, sys, os, collections
H=os.path.dirname(os.path.abspath(__file__))
tag,lo,hi=sys.argv[1],sys.argv[2],sys.argv[3]
toks=open(f'{H}/cfgs/cfg_{tag}.txt').read().split(None,200)
L,A,q=map(int,toks[:3]); digits=list(map(int,toks[3:3+q]))
cnt=collections.Counter(digits)
def alive(a,eps,b,c):
    Y=pow(2,a,1000)*pow(3,b,1000)*pow(7,c,1000)%1000
    ph=collections.Counter(zip(digits,eps)); have=collections.Counter()
    for i in range(3):
        d=(Y//10**i)%10
        if d==0: return False
        if d==1: continue
        have[d]+=1
        if have[d]>cnt[d] or ph[(d,i)]<1: return False
    return True
def load(w):
    with gzip.open(f'{H}/runs/{tag}.nu{lo}-{hi}.{w}.sorted.gz','rt') as g: return set(g)
P,F=load('prod'),load('fix2')
dropped=F-P; spur=P-F
def pr(l):
    f=l.split(); return int(f[1]),tuple(int(x) for x in f[3:3+q]),int(f[3+q]),int(f[4+q])
print('fix2-only (dropped by prod):',len(dropped),'by a:',dict(collections.Counter(pr(l)[0] for l in dropped)),'tail-alive violations:',sum(not alive(*pr(l)) for l in dropped))
print('fix2 all lines tail-alive violations:',sum(not alive(*pr(l)) for l in F))
import random; random.seed(2); S=random.sample(sorted(spur),min(200000,len(spur)))
print('prod-only (spurious) sample',len(S),'by a:',dict(collections.Counter(pr(l)[0] for l in S)),'alive (should be 0 except a=68):',collections.Counter((pr(l)[0],alive(*pr(l))) for l in S if pr(l)[0]==68))
