import sys, json, random
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from statlib import *

POP = {0: 1718, 1: 104651, 2: 1003249}


def load(path):
    vals = []
    n = 0
    for ln in open(path):
        t = ln.split()
        if not t or not t[-1].startswith("T:"):
            continue
        n += 1
        T = int(t[-1].split(":")[1])
        if T:
            vals.append(T)
    return n, vals


def stratum(spec, seed):
    rank = spec["rank"]
    out = {"rank": rank, "pairs_in_stratum": POP[rank]}
    if spec["mode"] == "exact":
        n, vals = load(spec["path"])
        out.update({"pairs_run": n, "anchored_pairs": len(vals), "patterns": sum(vals), "patterns_ci95": [sum(vals), sum(vals)], "anchored_pairs_ci95": [len(vals), len(vals)], "exact": True})
        out["draws"] = [float(sum(vals))] * 4000
    elif spec["mode"] == "sample":
        n, vals = load(spec["path"])
        pop = POP[rank]
        lo, hi = clopper_pearson(len(vals), n)
        l, h, draws = boot_total(vals, n, pop, 4000, seed)
        out.update({"pairs_run": n, "anchored_pairs_run": len(vals), "anchored_frac": len(vals) / n, "anchored_frac_ci95": [lo, hi], "anchored_pairs": len(vals) / n * pop, "anchored_pairs_ci95": [lo * pop, hi * pop], "patterns": sum(vals) * pop / n, "patterns_ci95": [l, h], "exact": False, "draws": draws})
    else:
        pn, pv = load(spec["prefix"])
        sn, sv = load(spec["sample"])
        spairs = spec["suffix_pairs"]
        assert pn + spairs == POP[rank]
        lo, hi = clopper_pearson(len(sv), sn)
        l, h, draws = boot_total(sv, sn, spairs, 4000, seed)
        pt = sum(pv)
        out.update({"prefix_pairs": pn, "prefix_anchored": len(pv), "prefix_patterns": pt, "suffix_pairs": spairs, "suffix_sample": sn, "suffix_anchored_in_sample": len(sv),
                    "anchored_pairs": len(pv) + len(sv) / sn * spairs, "anchored_pairs_ci95": [len(pv) + lo * spairs, len(pv) + hi * spairs],
                    "patterns": pt + sum(sv) * spairs / sn, "patterns_ci95": [pt + l, pt + h], "exact": False, "draws": [pt + d for d in draws]})
    return out


def main():
    specs = json.load(open(sys.argv[1]))
    res = [stratum(s, 100 + i) for i, s in enumerate(specs)]
    rng = random.Random(7)
    tot = sum(r["patterns"] for r in res)
    shares = {}
    for r in res:
        sh = []
        for _ in range(4000):
            ds = [rr["draws"][rng.randrange(4000)] for rr in res]
            sh.append(ds[res.index(r)] / sum(ds))
        sh.sort()
        shares[r["rank"]] = {"share": r["patterns"] / tot, "ci95": [sh[100], sh[3899]]}
    dt = sorted(sum(rr["draws"][rng.randrange(4000)] for rr in res) for _ in range(4000))
    for r in res:
        r.pop("draws")
    print(json.dumps({"strata": res, "total_patterns": tot, "total_ci95": [dt[100], dt[3899]], "shares": shares}, indent=1))


main()
