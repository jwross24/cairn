import json, os, sys, math, collections, random
import numpy as np
T0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/"
sys.path.insert(0, T0); sys.dont_write_bytecode = True
from tier0v2 import multisets
from math import comb
eqs = []; seen = set()
for l in open(T0 + "trees_mac.jsonl.eqs.jsonl"):
    try: e = json.loads(l)
    except Exception: continue
    if "levels" not in e or e.get("npat", 0) <= 2e6: continue
    key = (e.get("s"), tuple(sorted(e["M"])), e["npat"])
    if key in seen: continue
    seen.add(key)
    L = {x[0]: x for x in e["levels"]}
    op = L[12][3].get("OPEN", 0) if len(L[12]) > 3 else 0
    M = e["M"]; k = len(M)
    eqs.append(dict(k=k, f2=M.count(2) / k, f3=M.count(3) / k, fb=sum(1 for d in M if d >= 6) / k, npat=e["npat"], open=op, s=e.get("s")))
print("equations", len(eqs), "with open>0:", sum(1 for e in eqs if e["open"] > 0))

def design(es, cols):
    return np.array([[1.0] + [e[c] for c in cols] for e in es])

def poisson(X, y, off, it=60):
    b = np.zeros(X.shape[1]); b[0] = math.log(max(y.sum() / np.exp(off).sum(), 1e-12))
    for _ in range(it):
        mu = np.exp(X @ b + off); W = mu
        z = X @ b + (y - mu) / np.maximum(mu, 1e-12)
        A = X.T @ (X * W[:, None]) + 1e-9 * np.eye(X.shape[1])
        bn = np.linalg.solve(A, X.T @ (W * z))
        if np.max(abs(bn - b)) < 1e-10: b = bn; break
        b = bn
    return b

def fit(es, cols, B=300, seed=1):
    X = design(es, cols); y = np.array([e["open"] for e in es], float); off = np.log([e["npat"] for e in es])
    b = poisson(X, y, off)
    mu = np.exp(X @ b + off)
    disp = ((y - mu) ** 2 / np.maximum(mu, 1e-9)).sum() / (len(y) - len(b))
    rng = random.Random(seed); bs = []
    n = len(es)
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        sub = [es[i] for i in idx]
        bs.append(poisson(design(sub, cols), np.array([e["open"] for e in sub], float), np.log([e["npat"] for e in sub])))
    return b, np.array(bs), disp

lo = [e for e in eqs if e["k"] >= 9]
for cols in (["k"], ["k", "f2"], ["k", "f2", "f3"], ["k", "f2", "fb"]):
    b, bs, disp = fit(lo, cols)
    print("cols", cols, "coef", np.round(b, 4), "boot sd", np.round(bs.std(0), 4), "overdispersion", round(disp, 1))
# holdout: fit on k<=14, predict k>=15
tr = [e for e in eqs if 9 <= e["k"] <= 14]; te = [e for e in eqs if e["k"] >= 15]
for cols in (["k"], ["k", "f2"]):
    b, bs, disp = fit(tr, cols, B=50)
    X = design(te, cols); mu = np.exp(X @ b) * np.array([e["npat"] for e in te])
    print("holdout cols", cols, "predicted open", round(mu.sum()), "observed", sum(e["open"] for e in te), "n", len(te))
json.dump(eqs, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "eqs_open.json"), "w"))
# Tier B compositions
TIER_B = [71663616, 226492416, 1194891264, 169869312, 4182119424, 1792336896, 13884223438848, 2113929216, 1811939328, 11329339392, 4444263936, 3699376128, 1783627776]
tb = []
for s in TIER_B:
    for M in multisets(s):
        M = list(M); k = len(M); npt = 12
        for d, n in collections.Counter(M).items(): npt *= comb(12 + n - 1, n)
        tb.append(dict(s=s, k=k, f2=M.count(2) / k, f3=M.count(3) / k, fb=sum(1 for d in M if d >= 6) / k, npat=npt, M=M))
w = sum(t["npat"] for t in tb)
print("Tier B pattern-weighted mean f2 %.2f f3 %.2f fb %.2f k %.1f" % (sum(t["f2"]*t["npat"] for t in tb)/w, sum(t["f3"]*t["npat"] for t in tb)/w, sum(t["fb"]*t["npat"] for t in tb)/w, sum(t["k"]*t["npat"] for t in tb)/w))
sw = sum(e["npat"] for e in lo if e["k"] >= 13)
print("sweep (k>=13) pattern-weighted mean f2 %.2f" % (sum(e["f2"]*e["npat"] for e in lo if e["k"]>=13)/sw))
import pickle; pickle.dump(tb, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "tierb_ms.pkl"), "wb"))
