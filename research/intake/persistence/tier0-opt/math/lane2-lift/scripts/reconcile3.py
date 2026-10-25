import json, os, sys, math, random, pickle, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
exec(open(os.path.join(HERE, "scripts", "reconcile2.py")).read().split("lo = [e for e in eqs")[0])
bins = [(0, 0.3), (0.3, 0.7), (0.7, 1.01)]
KMIN = int(os.environ.get("KMIN", "13"))
random.seed(11)
coefs = {}
for lo_, hi_ in bins:
    es = [e for e in eqs if lo_ <= e["f2"] < hi_ and e["k"] >= KMIN]
    X = design(es, ["k"]); y = np.array([e["open"] for e in es], float); off = np.log([e["npat"] for e in es])
    b = poisson(X, y, off); bs = []
    for _ in range(300):
        idx = [random.randrange(len(es)) for _ in range(len(es))]
        bs.append(poisson(X[idx], y[idx], off[idx]))
    bs = np.array(bs)
    coefs[(lo_, hi_)] = (b, bs)
    print("f2 [%.1f,%.1f) k>=%d: n=%d  ln rate = %.2f + %.3f k ; slope boot 5-95%% [%.3f, %.3f]; rate at k=16 %.2e" % (lo_, hi_, KMIN, len(es), b[0], b[1], np.percentile(bs[:, 1], 5), np.percentile(bs[:, 1], 95), math.exp(b[0] + 16 * b[1])))
def total(sel):
    P = C = 0.0
    for t in tb:
        for (lo_, hi_) in bins:
            if lo_ <= t["f2"] < hi_:
                b = coefs[(lo_, hi_)][0] if sel == "fit" else coefs[(lo_, hi_)][1][sel]
                op = t["npat"] * math.exp(b[0] + b[1] * t["k"])
                if sel == "flat": pass
                P += op; C += op * t["ec0"] * math.exp(0.627 - 0.068 * t["k"])
    return P, C
def total_flat():
    # rate held at its value at k = 16 (plateau hypothesis) for k > 16
    P = C = 0.0
    for t in tb:
        for (lo_, hi_) in bins:
            if lo_ <= t["f2"] < hi_:
                b = coefs[(lo_, hi_)][0]; k = min(t["k"], 16)
                op = t["npat"] * math.exp(b[0] + b[1] * k); P += op; C += op * t["ec0"] * math.exp(0.627 - 0.068 * t["k"])
    return P, C
P, C = total("fit"); print("stratified fit (extrapolated slope): parents %.2e children(trend bias) %.2e" % (P, C))
ps = sorted(total(i)[0] for i in range(300)); cs = sorted(total(i)[1] for i in range(300))
print("  bootstrap 5-95%%: parents %.2e .. %.2e ; children %.2e .. %.2e" % (ps[15], ps[285], cs[15], cs[285]))
P, C = total_flat(); print("plateau hypothesis (rate frozen at k=16 value): parents %.2e children %.2e" % (P, C))
wf = collections.Counter()
for t in tb:
    kb = "k<=16" if t["k"] <= 16 else ("17-22" if t["k"] <= 22 else "23-29")
    wf[(kb, "f2>=0.7" if t["f2"] >= 0.7 else ("0.3-0.7" if t["f2"] >= 0.3 else "<0.3"))] += t["npat"]
tot = sum(wf.values())
for k_, v in sorted(wf.items()): print("  Tier B patterns share", k_, "%.3f" % (v / tot))
