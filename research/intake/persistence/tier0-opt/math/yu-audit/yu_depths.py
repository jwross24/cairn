import json
import sys
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/yu-audit")

import yu_chain as C

DEPTHS = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h3-h4/depths.jsonl"
VARIANTS = ["bk", "t1_13", "main_rig", "main13", "t2_13"]


def depth_under(row, u):
    worst = 1
    for rep in row["reps"]:
        rec = rep["recorded"]
        if rec[0] == "CLOSED-cut":
            continue
        d = rec[1]
        for dd in sorted(int(x) for x in rep["bounds"]):
            b = rep["bounds"][str(dd)]
            if b == "cut" or (b is not None and b > u):
                d = dd
                break
        worst = max(worst, d)
    return worst


def main():
    rows = [json.loads(line) for line in open(DEPTHS)]
    Fs = {v: C.make_F(v) for v in VARIANTS}
    cache = {}

    def U(v, k, a):
        if (v, k, a) not in cache:
            cache[(v, k, a)] = C.best(k, a, Fs[v])[0]
        return cache[(v, k, a)]

    trans = {v: Counter() for v in ["old"] + VARIANTS}
    for row in rows:
        k, a = row["k"], row["a"]
        before = depth_under(row, row["logU_recorded"])
        line = [row["key"][0], row["key"][1], a, k, row["logU_recorded"], before]
        trans["old"][(before, before)] += 1
        for v in VARIANTS:
            u = U(v, k, a)
            d = depth_under(row, u)
            trans[v][(before, d)] += 1
            line += [round(u, 1), d]
        print(*line, flush=True)
    for v in VARIANTS:
        moved = sum(c for (b, d), c in trans[v].items() if d < b)
        print(v, "moved", moved, "of", len(rows), {f"{b}->{d}": c for (b, d), c in sorted(trans[v].items())})
    print("before-depth histogram", Counter(depth_under(r, r["logU_recorded"]) for r in rows))
    print("depth after, main", Counter(depth_under(r, U("main", r["k"], r["a"])) for r in rows))
    print("depth after, bk", Counter(depth_under(r, U("bk", r["k"], r["a"])) for r in rows))


if __name__ == "__main__":
    main()
