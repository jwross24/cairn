import sys, json, math
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1d import uncut_nodes
from depth1c import v2
from uppp import depth_for, exact_e

CL = {0: [3], 1: [2], 2: [2, 7], 3: [2], 4: [2, 3], 5: [2] * 8, 6: [2] * 6, 7: [2] * 2, 8: [2] * 2 + [3] * 2, 9: [2] + [3] * 3}
w31 = [(d, e) for e, l in CL.items() for d in l]
u, nc = uncut_nodes(3 ** 3 * 7 ** 10, w31, 3)
print("k31 pattern: uncut nodes", u, "ncases1", nc, "avg nodes per depth-1 case", u / nc, "actual nodes 440640 with S1=2 -> per surviving case", 440640 / 2)
rows = [json.loads(l) for l in open(sys.argv[1])]
per = []
for r in rows:
    w = [tuple(x) for x in r["words"]]
    a = v2(r["y"])
    D, x = depth_for(len(w), a)
    E = exact_e(D, a)
    u, nc = uncut_nodes(r["y"], w, E)
    per.append(u / nc)
per.sort()
n = len(per)
print("patterns", n, "avg nodes per depth-1 case quantiles (log10)", [round(math.log10(per[int(f * (n - 1))]), 2) for f in (0, 0.1, 0.5, 0.9, 1.0)], "mean", sum(per) / n)
