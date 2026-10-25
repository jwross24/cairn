import sys, json, math
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
import importlib.util
src = open("costmodel.py").read().replace("\nmain()\n", "\n")
ns = {}
exec(compile(src, "costmodel_lib", "exec"), ns)
kappa = ns["calib"]()
rows = [json.loads(l) for l in open(sys.argv[1])]
pp = [ns["per_pattern"](r, kappa) for r in rows]
n = len(pp)


def q(v, f):
    v = sorted(v)
    return v[int(f * (len(v) - 1))]


nodes = [x[4] for x in pp]
ncases = [x[2] for x in pp]
a = [x[0] for x in pp]
k = [x[1] for x in pp]
cost = [x[3] * x[4] * 0.0449 for x in pp]
print("n", n)
for name, v in (("a", a), ("k", k), ("log10 ncases1", [math.log10(x) for x in ncases]), ("log10 nodes", [math.log10(x) for x in nodes]), ("p_surv", [x[3] for x in pp]), ("log10 cost_s", [math.log10(max(c, 1e-9)) for c in cost])):
    print(name, [round(q(v, f), 2) for f in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)])
tot = sum(cost)
sc = sorted(cost, reverse=True)
print("top1 share of mean", sc[0] / tot, "top10 share", sum(sc[:10]) / tot, "top100 share", sum(sc[:100]) / tot)
print("median cost seconds", q(cost, 0.5), "mean", tot / n)
sub = [x for x in pp if x[3] > 0.5]
print("fraction with p_surv>0.5", len(sub) / n)
print("median nodes among p>0.5", q([x[4] for x in sub], 0.5) if sub else None)
