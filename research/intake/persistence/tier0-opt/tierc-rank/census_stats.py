import sys, json, random
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from statlib import *

POP = {0: 1718, 1: 104651, 2: 1003249}


def load(path):
    vals = []
    n = 0
    for ln in open(path):
        t = ln.split()
        if not t:
            continue
        n += 1
        T = int(t[-1].split(":")[1])
        if T:
            vals.append(T)
    return n, vals


def stratum(path, rank, exact, seed):
    n, vals = load(path)
    pop = POP[rank]
    out = {"rank": rank, "pairs_in_stratum": pop, "pairs_run": n, "anchored_pairs_run": len(vals), "exact": exact}
    if exact:
        out["anchored_pairs"] = len(vals)
        out["patterns"] = sum(vals)
        out["patterns_ci95"] = [sum(vals), sum(vals)]
        out["draws"] = [float(sum(vals))] * 4000
    else:
        lo, hi = clopper_pearson(len(vals), n)
        out["anchored_frac"] = len(vals) / n
        out["anchored_frac_ci95"] = [lo, hi]
        out["anchored_pairs"] = len(vals) / n * pop
        out["anchored_pairs_ci95"] = [lo * pop, hi * pop]
        tot = sum(vals) * pop / n
        l, h, draws = boot_total(vals, n, pop, 4000, seed)
        out["patterns"] = tot
        out["patterns_ci95"] = [l, h]
        out["draws"] = draws
        out["max_pattern_cell"] = max(vals) if vals else 0
        out["top3_share_of_sample"] = sum(sorted(vals)[-3:]) / sum(vals) if vals else 0
    return out


def main():
    spec = json.load(open(sys.argv[1]))
    res = []
    for i, s in enumerate(spec):
        res.append(stratum(s["path"], s["rank"], s["exact"], 100 + i))
    rng = random.Random(7)
    tot = sum(r["patterns"] for r in res)
    shares = {}
    for r in res:
        sh = []
        for j in range(4000):
            ds = [rr["draws"][rng.randrange(4000)] if not rr["exact"] else rr["draws"][0] for rr in res]
            s = sum(ds)
            sh.append(ds[res.index(r)] / s)
        sh.sort()
        shares[r["rank"]] = {"share": r["patterns"] / tot, "ci95": [sh[100], sh[3899]]}
    ds_tot = []
    for j in range(4000):
        ds_tot.append(sum(rr["draws"][rng.randrange(4000)] if not rr["exact"] else rr["draws"][0] for rr in res))
    ds_tot.sort()
    for r in res:
        r.pop("draws")
    print(json.dumps({"strata": res, "total_patterns": tot, "total_ci95": [ds_tot[100], ds_tot[3899]], "shares": shares}, indent=1))


main()
