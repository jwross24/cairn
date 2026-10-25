import sys, json, random
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from costmodel3 import eval_patterns, T_CERT, T_VERIFY
from statlib import clopper_pearson


def cells(path):
    out = []
    n = 0
    for ln in open(path):
        t = ln.split()
        if not t or not t[-1].startswith("T:"):
            continue
        n += 1
        T = int(t[-1].split(":")[1])
        if T:
            out.append((int(t[1]) == 0, T))
    return n, out


def main():
    cfg = json.load(open(sys.argv[1]))
    rng = random.Random(9)
    pn, pc = cells(cfg["prefix"])
    sn, sc = cells(cfg["sample"])
    spairs = cfg["suffix_pairs"]
    pre_tot = sum(t for _, t in pc)
    pre_w0 = sum(t for f, t in pc if f)
    scale = spairs / sn
    tot_pt = pre_tot + scale * sum(t for _, t in sc)
    w0_pt = pre_w0 + scale * sum(t for f, t in sc if f)
    f0 = w0_pt / tot_pt
    ntot, f0d = [], []
    for _ in range(3000):
        mm = rng.binomialvariate(sn, len(sc) / sn)
        idx = [sc[rng.randrange(len(sc))] for _ in range(mm)]
        st = sum(t for _, t in idx) * scale
        sw = sum(t for f, t in idx if f) * scale
        ntot.append(pre_tot + st)
        f0d.append((pre_w0 + sw) / (pre_tot + st))
    ntot.sort()
    res = {"N_patterns": [ntot[75], tot_pt, ntot[2924]], "wrap0_share": f0, "wrap0_share_ci95": [sorted(f0d)[75], sorted(f0d)[2924]]}
    strata = {nm: eval_patterns(p, cfg["kind"], nm) for nm, p in cfg["samples"].items()}
    stats = {}
    for nm, ev in strata.items():
        n = len(ev)
        sv = [1.0 if e["s1"] else 0.0 for e in ev]
        cs = [e["nodes"] * (T_CERT + T_VERIFY) for e in ev]
        stats[nm] = (n, sv, cs)
        lo, hi = clopper_pearson(int(sum(sv)), n)
        res["stratum_" + nm] = {"n": n, "survivors": int(sum(sv)), "rate_cp95": [lo, sum(sv) / n, hi], "survivor_nodes": sorted(e["nodes"] for e in ev if e["s1"]), "survivor_E": [e["E"] for e in ev if e["s1"]]}
    S, C = [], []
    for i in range(3000):
        nt = ntot[rng.randrange(3000)]
        f = f0d[rng.randrange(3000)]
        ss = cc = 0.0
        for nm, wt in (("w0", f), ("other", 1 - f)):
            n, sv, cs = stats[nm]
            ss += wt * sum(sv[rng.randrange(n)] for _ in range(n)) / n
            cc += wt * sum(cs[rng.randrange(n)] for _ in range(n)) / n
        S.append(nt * ss)
        C.append(nt * cc / 86400)
    S.sort()
    C.sort()
    ps = pc_ = 0.0
    for nm, wt in (("w0", f0), ("other", 1 - f0)):
        n, sv, cs = stats[nm]
        ps += wt * sum(sv) / n
        pc_ += wt * sum(cs) / n
    res["survivors_total"] = [S[75], tot_pt * ps, S[2924]]
    res["core_days_total_cert_verify"] = [C[75], tot_pt * pc_ / 86400, C[2924]]
    res["core_years_total"] = [x / 365.25 for x in res["core_days_total_cert_verify"]]
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
