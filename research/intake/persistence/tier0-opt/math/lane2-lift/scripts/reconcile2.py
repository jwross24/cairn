import json, os, sys, math, random, pickle, collections
import numpy as np
from math import factorial
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
eqs = json.load(open(HERE + "/logs/eqs_open.json")); tb = pickle.load(open(HERE + "/logs/tierb_ms.pkl", "rb"))
def design(es, cols): return np.array([[1.0] + [e[c] for c in cols] for e in es])
def poisson(X, y, off, it=60):
    b = np.zeros(X.shape[1]); b[0] = math.log(max(y.sum() / np.exp(off).sum(), 1e-12))
    for _ in range(it):
        mu = np.exp(X @ b + off); z = X @ b + (y - mu) / np.maximum(mu, 1e-12)
        bn = np.linalg.solve(X.T @ (X * mu[:, None]) + 1e-9 * np.eye(X.shape[1]), X.T @ (mu * z))
        if np.max(abs(bn - b)) < 1e-10: return bn
        b = bn
    return b
def poly(n, R=12):
    base = [(m + 1) / factorial(m) for m in range(n + 1)]; res = [1.0] + [0.0] * n
    for _ in range(R):
        new = [0.0] * (n + 1)
        for i, a in enumerate(res):
            for j in range(n + 1 - i): new[i + j] += a * base[j]
        res = new
    return factorial(n) * res[n] / R ** n
cache = {}
def EC0(M):
    out = 2.0
    for d, n in collections.Counter(M).items():
        if n not in cache: cache[n] = poly(n)
        out *= cache[n]
    return out
for t in tb: t["ec0"] = EC0(t["M"])
random.seed(7)
lo = [e for e in eqs if e["k"] >= 9]
y = np.array([e["open"] for e in lo], float); off = np.log([e["npat"] for e in lo])
res = {}
for name, cols in (("k", ["k"]), ("k+f2", ["k", "f2"])):
    X = design(lo, cols); b = poisson(X, y, off)
    bs = []
    for _ in range(300):
        idx = [random.randrange(len(lo)) for _ in range(len(lo))]
        bs.append(poisson(X[idx], y[idx], off[idx]))
    Xt = design(tb, cols); npt = np.array([t["npat"] for t in tb]); ec = np.array([t["ec0"] for t in tb]); kk = np.array([t["k"] for t in tb])
    def tot(bb, bias):
        op = npt * np.exp(Xt @ bb)
        return op.sum(), (op * ec * bias).sum()
    ab, bb_ = 0.627, -0.068   # bias trend from COSTMODEL.md
    bias_tr = np.exp(ab + bb_ * kk); bias_c = 0.82
    P, Cc = tot(b, bias_c); _, Ct = tot(b, bias_tr)
    ps = sorted(tot(x, bias_c)[0] for x in bs); cs = sorted(tot(x, bias_tr)[1] for x in bs); cc = sorted(tot(x, bias_c)[1] for x in bs)
    res[name] = (P, Cc, Ct, ps[15], ps[285], cs[15], cc[285])
    print("%-5s parents %.2e [%.2e, %.2e] ; children const-bias %.2e, trend-bias %.2e ; children 5-95%% over fit: %.2e .. %.2e" % (name, P, ps[15], ps[285], Cc, Ct, cs[15], cc[285]))
    for k in (20, 26, 29):
        sel = [t for t in tb if t["k"] == k]
        if sel:
            x = design(sel, cols); op = (np.exp(x @ b) * np.array([t["npat"] for t in sel])).sum() / sum(t["npat"] for t in sel)
            print("   Tier B patterns at k=%d: rate %.2e (pattern-weighted f2 %.2f)" % (k, op, sum(t["f2"]*t["npat"] for t in sel)/sum(t["npat"] for t in sel)))
