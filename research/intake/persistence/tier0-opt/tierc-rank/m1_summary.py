import sys, json
from collections import Counter

rows = [json.loads(l) for l in open(sys.argv[1])]
n = len(rows)
keys = ["r2_one_ended", "r1_one_ended", "r1_bd", "mv", "mv_bd", "r2_two_ended", "r1_two_ended"]
q = lambda v, f: sorted(v)[int(f * (len(v) - 1))]
print("patterns", n, "k range", min(r["k"] for r in rows), q([r["k"] for r in rows], 0.5), max(r["k"] for r in rows), "a median", q([r["a"] for r in rows], 0.5))
for k in keys:
    v = [r[k] for r in rows]
    d = [r["D_" + k] for r in rows]
    print("%-14s log10 G: min %.1f med %.1f max %.1f | D: min %d med %d max %d | D<=6: %.3f" % (k, min(v), q(v, 0.5), max(v), min(d), q(d, 0.5), max(d), sum(1 for x in d if x <= 6) / n))
print("median log10 gain  r2->r1 (Matveev):", q([r["r2_one_ended"] - r["r1_one_ended"] for r in rows], 0.5), " r1->mv:", q([r["r1_one_ended"] - r["mv"] for r in rows], 0.5), " r2->mv:", q([r["r2_one_ended"] - r["mv"] for r in rows], 0.5))
print("median first-gap BD gain (r1 -> r1_bd):", q([r["r1_one_ended"] - r["r1_bd"] for r in rows], 0.5))
for src, dst in (("r2_two_ended", "r1_two_ended"), ("r2_one_ended", "mv")):
    c = Counter(r["D_" + src] - r["D_" + dst] for r in rows)
    print("depth saving", src, "->", dst, dict(sorted(c.items())))
