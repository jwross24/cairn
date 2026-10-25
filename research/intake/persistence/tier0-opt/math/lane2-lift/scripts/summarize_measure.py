import json, math, os, statistics, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = [json.loads(l) for l in open(os.path.join(HERE, "logs", "measure.jsonl"))]
content = {r["eq"]: r for r in json.load(open(os.path.join(HERE, "logs", "content.json")))}
PR = [73, 137, 99990001]


def wilson_eff(p, n, z=1.96):
    if n <= 0:
        return (p, p)
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(max(p * (1 - p), 0) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def weighted(group, getk):
    """children-weighted rate of an event; each equation contributes N_e (children) * k_e/n_e.
    denominator = children with all residues nonzero (estimated as N_e * nz_e / sampled_e)."""
    num = den = 0.0
    var = 0.0
    for r in group:
        m = r["meas"]
        n_e = m["sampled"] - sum(m["zero_p"])
        if n_e <= 0:
            continue
        N = r["children_gate"]
        nzfrac = n_e / m["sampled"]
        Nnz = N * nzfrac
        k = getk(m)
        p_e = k / n_e
        num += Nnz * p_e
        den += Nnz
        if r["rho"] < 1.0:
            var += (Nnz ** 2) * p_e * (1 - p_e) / n_e
    p = num / den
    se2 = var / den ** 2
    neff = p * (1 - p) / se2 if se2 > 0 else float("inf")
    lo, hi = wilson_eff(p, neff) if neff != float("inf") else (p, p)
    return p, lo, hi


def fmt(t):
    return "%.4g [%.4g, %.4g]" % t


sel = [r for r in rows if r["meas"] and r["A"] < 64]
hi = [r for r in rows if r["meas"] and r["A"] >= 64]
for label, group in (("A<64", sel), ("A>=64 (parents unverified, level-12 audit pending)", hi)):
    if not group:
        continue
    N = sum(r["children_gate"] for r in group)
    samp = sum(r["meas"]["sampled"] for r in group)
    print("##", label, "equations", len(group), "children (exact, from gate)", N, "sampled", samp)
    comps = content[group[0]["eq"]]["comps"]
    zero = [weighted(group, lambda m, i=i: m["zero_p"][i] * 1.0) for i in range(3)]
    print("zero residue (child value = 0 mod p) per prime (fraction of all children, weighted; denominators here are all sampled):")
    for i, p in enumerate(PR):
        num = sum(r["children_gate"] * r["meas"]["zero_p"][i] / r["meas"]["sampled"] for r in group)
        print("  p=%d zero fraction %.4g" % (p, num / N))
    print("per-prime marginal fail (residue outside the projection of the allowed coset onto that prime), among nonzero children:")
    for i, p in enumerate(PR):
        print("  p=%d fail %s   design pass %s" % (p, fmt(weighted(group, lambda m, i=i: m["pfail"][i])), {73: "2/72", 137: "34/136", 99990001: "111100/99990000"}[p]))
    print("per l-part joint component marginal fail (hs/size = design survival):")
    for c, comp in enumerate(comps):
        print("  comp %d primes %s mods %s hs/size=%d/%d  fail %s  design-fail %.4g" % (c, [PR[j] for j in comp["idx"]], comp["mod"], comp["hs"], comp["size"], fmt(weighted(group, lambda m, c=c: m["cfail"][c])), 1 - comp["hs"] / comp["size"]))
    print("all components pass (coset test): %s   design 1/259200 = %.4g" % (fmt(weighted(group, lambda m: m["pass"])), 1 / 259200))

    def histsum(m, pred):
        return sum(v for k, v in m["hist"].items() if pred(int(k)))

    print("cascade, children-weighted survival after each stage (nonzero children):")
    orders = {"2,3,5": [0, 1, 2], "5,3,2": [2, 1, 0], "3,5,2": [1, 2, 0], "2,5,3": [0, 2, 1], "5,2,3": [2, 0, 1], "3,2,5": [1, 0, 2]}
    for name, od in orders.items():
        seq = []
        cum = 0
        for c in od:
            cum |= 1 << c
            seq.append(fmt(weighted(group, lambda m, cum=cum: histsum(m, lambda mk: (mk & cum) == 0))))
        print("  order %-6s %s" % (name, " -> ".join(seq)))
    print("conditional survival of the 2-part after 5-part, of the 3-part after 5-part, children-weighted:")
    for (i, j) in ((2, 0), (2, 1), (0, 1), (1, 0), (0, 2), (1, 2)):
        a = weighted(group, lambda m, i=i: histsum(m, lambda mk: (mk >> i) & 1 == 0))
        b = weighted(group, lambda m, i=i, j=j: histsum(m, lambda mk: (mk >> i) & 1 == 0 and (mk >> j) & 1 == 0))
        print("  P(c%d ok | c%d ok) = %.4g" % (j, i, b[0] / a[0]))
    per_eq = {}
    for c, comp in enumerate(comps[:3]):
        vals = [r["meas"]["cfail"][c] / max(1, r["meas"]["sampled"] - sum(r["meas"]["zero_p"])) for r in group if r["meas"]["sampled"] > 1000]
        print("  comp %d per-equation fail min/median/max: %.4f / %.4f / %.4f" % (c, min(vals), statistics.median(vals), max(vals)))
    z = [sum(r["meas"]["zero_p"]) / r["meas"]["sampled"] for r in group if r["meas"]["sampled"] > 1000]
    print("zero fraction per equation min/median/max: %.4g / %.4g / %.4g" % (min(z), statistics.median(z), max(z)))
    print("rho=1 (exact) equations", sum(1 for r in group if r["rho"] == 1.0), "sampled equations", sum(1 for r in group if r["rho"] < 1.0))
