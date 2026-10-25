import math, json
from math import comb
sys_digits = {2:(1,0,0),3:(0,1,0),4:(2,0,0),6:(1,1,0),7:(0,0,1),8:(3,0,0),9:(0,2,0)}
VERT = {"3416267673274176":(6,27,1),"128421199872":(23,7,1),"913217421312":(29,5,1),
        "727326941773824":(39,3,2),"112717121716224":(34,8,0),"1438916737499136":(24,6,6)}
def multisets(e):
    ds = [2,3,4,6,7,8,9]
    out = []
    def rec(i, rem, cur):
        if i == len(ds):
            if rem == (0,0,0): out.append(dict(cur))
            return
        d = ds[i]; v = sys_digits[d]
        m = 0
        r = rem
        while all(x >= 0 for x in r):
            if m: cur[d] = m
            rec(i+1, r, cur)
            cur.pop(d, None)
            m += 1
            r = tuple(a-b for a,b in zip(r, v))
            if v == (0,0,0): break
    rec(0, e, {})
    return out
def npat(M, L):
    n = L
    for m in M.values(): n *= comb(L+m-1, m)
    return n
rho96 = 7.2574e-38
res = {}
for s, e in VERT.items():
    Ms = multisets(e)
    assert math.prod(d**m for M in Ms[:1] for d,m in M.items()) == int(s)
    n12 = sum(npat(M,12) for M in Ms); n96 = sum(npat(M,96) for M in Ms)
    maxn = max(npat(M,96) for M in Ms)
    ks = [sum(M.values()) for M in Ms]
    res[s] = dict(multisets=len(Ms), N12=n12, N96=n96, N96_max_eq=maxn, kmin=min(ks), kmax=max(ks),
                  mu_uniform=n96*rho96, sqrtN96=math.sqrt(n96), sqrt_max_eq=math.sqrt(maxn))
    print(s, len(Ms), f"N12={n12:.3e} N96={n96:.3e} maxEq={maxn:.3e} mu={n96*rho96:.3e} sqrtN={math.sqrt(n96):.3e} k={min(ks)}-{max(ks)}")
json.dump(res, open("tierc_budget.json","w"))
