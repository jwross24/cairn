import sys, json, math, random
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1c import analyze, v2
from uppp import depth_for, exact_e
from statlib import clopper_pearson

T_CERT = 0.02319973129992738
T_VERIFY = 0.02166669526143791

path = sys.argv[1]
pop = [float(x) for x in sys.argv[2:5]]
out = sys.argv[5]
rows = [json.loads(l) for l in open(path)]
recs = []
for r in rows:
    words = [tuple(w) for w in r["words"]]
    a = v2(r["y"])
    k = len(words)
    D, x = depth_for(k, a)
    E = exact_e(D, a)
    s1, nodes, nc = analyze(r["y"], words, E)
    s1b, nodesb, _ = analyze(r["y"], words, max(E - 1, 1))
    s1c, nodesc, _ = analyze(r["y"], words, E + 1)
    recs.append({"a": a, "k": k, "D": D, "E": E, "u2": x, "s1": s1, "ncases1": nc, "nodes": nodes, "nodes_Em1": nodesb, "nodes_Ep1": nodesc})
with open(out, "w") as f:
    for r in recs:
        f.write(json.dumps(r) + "\n")
n = len(recs)
surv = sum(1 for r in recs if r["s1"] > 0)
lo, hi = clopper_pearson(surv, n)
rng = random.Random(11)


def boot(vals, reps=4000):
    res = []
    for _ in range(reps):
        s = 0.0
        for _ in range(n):
            s += vals[rng.randrange(n)]
        res.append(s / n)
    res.sort()
    return res[100], sum(vals) / n, res[3899]


nodes = [r["nodes"] for r in recs]
cost_vc = [r["nodes"] * (T_CERT + T_VERIFY) for r in recs]
cost_c = [r["nodes"] * T_CERT for r in recs]
cost_lo = [r["nodes_Em1"] * T_CERT for r in recs]
cost_hi = [r["nodes_Ep1"] * (T_CERT + T_VERIFY) for r in recs]
sv = [1.0 if r["s1"] > 0 else 0.0 for r in recs]
res = {
    "n": n,
    "depth1_survivors": surv,
    "depth1_survival_rate": [lo, surv / n, hi],
    "D_counts": {str(d): sum(1 for r in recs if r["D"] == d) for d in sorted(set(r["D"] for r in recs))},
    "E_counts": {str(d): sum(1 for r in recs if r["E"] == d) for d in sorted(set(r["E"] for r in recs))},
    "median_k": sorted(r["k"] for r in recs)[n // 2],
    "median_a": sorted(r["a"] for r in recs)[n // 2],
    "median_ncases1": sorted(r["ncases1"] for r in recs)[n // 2],
}
q = lambda v, f: sorted(v)[int(f * (len(v) - 1))]
surv_nodes = [r["nodes"] for r in recs if r["s1"] > 0]
if surv_nodes:
    res["survivor_nodes_quantiles"] = {str(f): q(surv_nodes, f) for f in (0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)}
tot = lambda trip: [t * p for t, p in zip(trip, pop)]
res["mean_node_count_per_anchored_pattern_cond_all"] = boot(nodes)
res["mean_core_s_per_pattern_cert_verify"] = boot(cost_vc)
res["core_days_total_cert_verify"] = [x / 86400 for x in tot(boot(cost_vc))]
res["core_days_total_cert_only"] = [x / 86400 for x in tot(boot(cost_c))]
res["core_days_total_E_minus_1_cert_only"] = [x / 86400 for x in tot(boot(cost_lo))]
res["core_days_total_E_plus_1_cert_verify"] = [x / 86400 for x in tot(boot(cost_hi))]
res["survivors_total"] = [x for x in tot(boot(sv))]
res["core_days_if_32s_per_survivor"] = [x * 32 / 86400 for x in tot(boot(sv))]
sc = sorted(cost_vc, reverse=True)
res["top1_share"] = sc[0] / sum(cost_vc) if sum(cost_vc) else 0
res["top10_share"] = sum(sc[:10]) / sum(cost_vc) if sum(cost_vc) else 0
print(json.dumps(res, indent=1))
