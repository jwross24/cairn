import sys, json, time
from collections import defaultdict
from gmpy2 import mpz
from run_c import run
EQS = [(864,(2,2,3,3,4,6)),(432,(2,2,2,2,3,3,3)),(672,(2,2,2,3,4,7)),(864,(2,2,2,2,3,3,6)),
       (1161216,(4,7,8,8,8,9,9)),(1161216,(6,6,7,8,8,8,9))]
def dp(x):
    p = 1
    for ch in str(x): p *= int(ch)
    return p
def kids():
    rows=[l.split() for l in open('zf_below_1e4000.txt') if l.startswith('ZF')]
    S=[int(mpz(2)**int(a)*mpz(3)**int(b)*mpz(7)**int(c)) for _,d,a,b,c,p in rows]
    k=defaultdict(list)
    for y in S:
        if y>=10: k[dp(y)].append(y)
    return k
if __name__=="__main__":
    out=sys.argv[1]; nc=int(sys.argv[2]); K=kids()
    with open(out,'w') as f:
        for s,M in EQS:
            t0=time.time(); r=run(s,M,K[s],ncores=nc); dt=time.time()-t0
            rec=dict(s=s,M=M,open=len(r['open']),sols=sorted(y for y in r['solutions'] if y>=10),bounds=r['bounds'],exceptional=r['exceptional'],
                     c_stats=r['c_stats'],levels=[(L,n,sv,cls) for (L,ps,n,sv,cls,el) in r['levels']],closed=r['closed'],complete_below=r['complete_below'])
            f.write(json.dumps(rec,sort_keys=True)+'\n'); f.flush()
            print(s,M,round(dt,2),file=sys.stderr,flush=True)
