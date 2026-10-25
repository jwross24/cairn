import sys, json, math
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1d import analyze_rank
from depth1c import v2
from statlib import clopper_pearson
from uppp import depth_for, exact_e

path = sys.argv[1]
kind = sys.argv[2] if len(sys.argv) > 2 else "2"
kind = 2 if kind == "2" else kind
rows = [json.loads(l) for l in open(path)]
n = len(rows)
surv = []
ks, as_, ncs = [], [], []
for r in rows:
    w = [tuple(x) for x in r["words"]]
    y = r["y"]
    k = kind
    if k == "auto":
        k = "b" if y % 3 == 0 else "c"
    s1, nodes, nc = analyze_rank(y, w, 1, k)
    ks.append(len(w))
    as_.append(v2(y))
    ncs.append(nc)
    if s1:
        D, x = depth_for(len(w), v2(y))
        E = exact_e(D, v2(y))
        s1e, nodesE, _ = analyze_rank(y, w, E, k)
        surv.append({"y": y, "k": len(w), "a": v2(y), "s1": s1, "ncases1": nc, "E": E, "nodes": nodesE, "words": r["words"], "nu": r["nu"], "wrap": r["k"]})
lo, hi = clopper_pearson(len(surv), n)
ncs_sorted = sorted(ncs)
print("patterns", n, "survivors", len(surv), "rate CP95", [lo, len(surv) / n, hi])
print("k quantiles", [sorted(ks)[int(f * (n - 1))] for f in (0, 0.5, 1)], "a quantiles", [sorted(as_)[int(f * (n - 1))] for f in (0, 0.5, 0.9, 1)])
print("ncases1 quantiles", [ncs_sorted[int(f * (n - 1))] for f in (0, 0.5, 0.9, 0.99, 1)], "frac ncases1>=1e6", sum(1 for x in ncs if x >= 1e6) / n)
with open(sys.argv[3] if len(sys.argv) > 3 else "/dev/null", "w") as f:
    for s in surv:
        f.write(json.dumps(s) + "\n")
