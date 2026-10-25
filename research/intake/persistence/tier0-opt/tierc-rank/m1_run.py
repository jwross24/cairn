import sys, json
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from m1lib import *
from chainrank import log10_bound, alphas_for, two_ended_log10

src, out = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(src)]


def v2(n):
    return (n & -n).bit_length() - 1


cache = {}
res = []
for r in rows:
    y = r["y"]
    which = "b" if y % 3 == 0 else "c"
    a = v2(y)
    k = len(r["words"])
    key = (k, a, which)
    if key not in cache:
        row = {"k": k, "a": a, "which": which}
        row["r2_one_ended"] = float(log10_bound(alphas_for(a, 2), k, a))
        row["r1_one_ended"] = float(one_ended_variant(k, a, which, "r1"))
        row["r1_bd"] = float(one_ended_variant(k, a, which, "r1bd"))
        row["mv"] = float(one_ended_variant(k, a, which, "mv"))
        row["mv_bd"] = float(one_ended_variant(k, a, which, "mvbd"))
        row["r2_two_ended"] = float(two_ended_log10(k, a, 2)[0])
        row["r1_two_ended"] = float(two_ended_log10(k, a, 1, which)[0])
        for kk in ("r2_one_ended", "r1_one_ended", "r1_bd", "mv", "mv_bd", "r2_two_ended", "r1_two_ended"):
            row["D_" + kk] = depth_needed(row[kk])
        cache[key] = row
    res.append(dict(cache[key], y=y))
with open(out, "w") as f:
    for r in res:
        f.write(json.dumps(r) + "\n")
print("patterns", len(res), "distinct (k,a,which)", len(cache))
