import sys, json
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
import gmpy2
from gmpy2 import mpfr
from m1lib import tfun, solve_gen, LOGU, LN10, depth_needed
from chainrank import matveev_c, prodlog, alphas_for

rows = [json.loads(l) for l in open(sys.argv[1])]
cache = {}
vals = []
for r in rows:
    key = (r["k"], r["a"], r["which"])
    if key not in cache:
        k, a, which = key
        p = 3 if which == "b" else 7
        top = alphas_for(a, 1, which)
        k0f = lambda x: matveev_c(len(top)) * prodlog(top) * tfun(x, a)
        k1f = lambda x: matveev_c(3) * prodlog([p, 10]) * tfun(x, a)
        s1f = lambda x: (k0f(x) + LOGU) / LN10
        cache[key] = float(solve_gen(k, s1f, k1f))
    vals.append((cache[key], r["r1_one_ended"], r["mv"], r["r2_one_ended"]))
n = len(vals)
q = lambda v, f: sorted(v)[int(f * (len(v) - 1))]
fold = [v[0] for v in vals]
print("patterns", n, "distinct", len(cache))
print("Matveev rank 1 folded: median log10 G %.1f range %.1f..%.1f; D median %d range %d..%d; D<=6 share %.3f" % (q(fold, 0.5), min(fold), max(fold), q([depth_needed(x) for x in fold], 0.5), min(depth_needed(x) for x in fold), max(depth_needed(x) for x in fold), sum(1 for x in fold if depth_needed(x) <= 6) / n))
print("median gain folded vs unfolded rank 1:", q([v[1] - v[0] for v in vals], 0.5), " kit vs folded:", q([v[0] - v[2] for v in vals], 0.5))
