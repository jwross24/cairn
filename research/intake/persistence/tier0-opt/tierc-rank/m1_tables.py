import sys, json
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from m1lib import *
from chainrank import log10_bound, alphas_for, two_ended_log10

cases = [tuple(int(x) for x in t.split(",")) for t in sys.argv[2].split(";")]
which = sys.argv[3] if len(sys.argv) > 3 else "b"
out = open(sys.argv[1], "w")
for k, a in cases:
    row = {"k": k, "a": a, "which": which}
    row["r2_one_ended"] = float(log10_bound(alphas_for(a, 2), k, a))
    row["r1_one_ended"] = float(one_ended_variant(k, a, which, "r1"))
    row["r1_bd"] = float(one_ended_variant(k, a, which, "r1bd"))
    row["mv"] = float(one_ended_variant(k, a, which, "mv"))
    row["mv_bd"] = float(one_ended_variant(k, a, which, "mvbd"))
    row["r2_two_ended"] = float(two_ended_log10(k, a, 2)[0])
    row["r1_two_ended"] = float(two_ended_log10(k, a, 1, which)[0])
    for key in ("r2_one_ended", "r1_one_ended", "r1_bd", "mv", "mv_bd", "r2_two_ended", "r1_two_ended"):
        row["D_" + key] = depth_needed(row[key])
    out.write(json.dumps(row) + "\n")
    out.flush()
    print(json.dumps(row))
