import sys
from collections import defaultdict, Counter
def digits(n, b):
    out=[]
    while n: out.append(n % b); n//=b
    return out[::-1]
def dprod(n,b):
    p=1
    for d in digits(n,b): p*=d
    return p
def scan(b, D):
    primes=[p for p in range(2,b) if all(p%q for q in range(2,p)) and any(d%p==0 for d in range(2,b))]
    lim=b**D
    zf=[]
    def rec(i, val):
        if i==len(primes):
            if val>=b and 0 not in digits(val,b): zf.append(val)
            return
        v=val
        while v<lim:
            rec(i+1, v); v*=primes[i]
    rec(0,1)
    def orbit_end(x):
        while x>=b: x=dprod(x,b)
        return x
    def pers(n):
        c=0
        while n>=b: n=dprod(n,b); c+=1
        return c
    def qmax(s):
        q=0
        for p in primes:
            while s%p==0: s//=p; q+=1
        return q
    trees=defaultdict(list)
    for y in zf: trees[orbit_end(y)].append(y)
    print(f"base {b}: primes {primes}, zero-free S-units in [{b}, {b}^{D}): {len(zf)}; target 0: {len(trees[0])}")
    for t in sorted(trees):
        if t==0: continue
        V=trees[t]; qs=[qmax(s) for s in V]; mp=max(pers(y) for y in V)
        print(f"   target {t}: {len(V)} vertices, max q {max(qs)}, top q {sorted(Counter(qs).items())[-3:]}, max pers(N) {mp+1}, largest vertex {max(V)} ({len(digits(max(V),b))} digits)")
for b,D in ((8,70),(9,70),(12,45)):
    scan(b,D)
