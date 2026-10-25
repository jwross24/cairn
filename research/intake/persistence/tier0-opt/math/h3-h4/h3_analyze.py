import json
import sys
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h3-h4")
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")

import h3_sharp as H
import h3_fold as F

DEPTHS = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h3-h4/depths.jsonl"
MODES = ["old", "old+kit", "old+k0zero", "last", "last+kit", "last+k0zero", "fold"]


def bound_for(mode, k, a, cache={}):
    key = (mode, k, a)
    if key in cache:
        return cache[key]
    if mode == "fold":
        v = F.best(k, a)[0]
    elif mode in ("old+kit", "last+kit", "old+k0zero", "last+k0zero") and a != 0:
        v = bound_for(mode.split("+")[0], k, a)
    else:
        v = H.log10_int(H.solve(k, a, H.MODES[mode]))
    cache[key] = v
    return v


def depth_under(row, u):
    worst = 1
    for rep in row["reps"]:
        rec = rep["recorded"]
        if rec[0] == "CLOSED-cut":
            continue
        dstar = rec[1]
        d = dstar
        for dd in sorted(int(x) for x in rep["bounds"]):
            b = rep["bounds"][str(dd)]
            if b == "cut" or (b is not None and b > u):
                d = dd
                break
        worst = max(worst, d)
    return worst


def main():
    rows = [json.loads(l) for l in open(DEPTHS)]
    bad = 0
    for row in rows:
        for rep in row["reps"]:
            for dd, b in rep["bounds"].items():
                if b not in ("cut", None) and b > row["logU_recorded"] + 0.06:
                    bad += 1
            c = rep.get("control")
            if c and c["bound"] is not None and abs(c["bound"] - c["recorded"]) > 0.011:
                bad += 1000
    print("rows", len(rows), "consistency violations", bad)
    res = {m: Counter() for m in MODES}
    tab = Counter()
    for row in rows:
        k, a = row["k"], row["a"]
        before = depth_under(row, bound_for("old", k, a))
        line = [row["key"][0], row["key"][1], a, k, round(bound_for("old", k, a), 1), before]
        for m in MODES:
            u = bound_for(m, k, a)
            d = depth_under(row, u)
            res[m][before - d] += 1
            tab[(m, before, d)] += 1
            line += [round(u, 1), d]
        print(*line)
    print("depth drop histogram per mode (drop: count)")
    for m in MODES:
        print(m, dict(sorted(res[m].items())))
    print("before->after transitions")
    for m in MODES:
        print(m, {f"{b}->{d}": c for (mm, b, d), c in sorted(tab.items()) if mm == m})
    print("before-depth histogram", Counter(depth_under(r, bound_for("old", r["k"], r["a"])) for r in rows))


if __name__ == "__main__":
    main()
