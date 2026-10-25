import sys, json, time
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
import gmpy2
from m0lib import *
from chainrank import log10_bound, alphas_for

src, out = sys.argv[1], sys.argv[2]
inflate = int(sys.argv[3]) if len(sys.argv) > 3 else None
t0 = time.time()
L = L2()
print("ord_{R96}(2) = %d  (~10^%.2f)" % (L, math.log10(L)), "factor/order time %.1fs" % (time.time() - t0))
g0 = {}
res = Counter()
reasons = Counter()
with open(out, "w") as g:
    for ln in open(src):
        r = json.loads(ln)
        words = [tuple(w) for w in r["words"]]
        k = len(words)
        if k not in g0:
            g0[k] = int(gmpy2.mpz(gmpy2.mpfr(10) ** gmpy2.mpfr(float(log10_bound(alphas_for(1, 0), 0, 1))))) + 1
        ab = max(fonga_bound(words), t7_bound(k, g0[k]))
        if inflate is not None:
            ab = 10 ** inflate
        d = decide(r["nu"], words, ab, L)
        d["a_bound_log10"] = round(math.log10(ab), 2)
        d["y"], d["k"], d["nu"] = r["y"], k, r["nu"]
        res[d["verdict"]] += 1
        reasons[d.get("reason", "")] += 1
        g.write(json.dumps(d) + "\n")
print(dict(res))
print(dict(reasons))
