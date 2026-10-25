import sys, os, json, math, random, collections
from math import comb, factorial

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = os.path.normpath(os.path.join(HERE, "..", "..", "..", "tier0"))
sys.path.insert(0, T0)
sys.dont_write_bytecode = True
from tier0v2 import multisets

TIER_B = [71663616, 226492416, 1194891264, 169869312, 4182119424, 1792336896, 13884223438848, 2113929216, 1811939328, 11329339392, 4444263936, 3699376128, 1783627776]
random.seed(20261021)

E_ = []
for l in open(T0 + "/trees_mac.jsonl.eqs.jsonl"):
    try:
        E_.append(json.loads(l))
    except Exception:
        pass
for l in open(T0 + "/trees_c.jsonl"):
    try:
        r = json.loads(l)
    except Exception:
        continue
    for e in r.get("eqs", []):
        if isinstance(e, dict) and "levels" in e:
            E_.append(e)
seen = set(); eq = []
for e in E_:
    if e.get("npat", 0) <= 2e6 or "levels" not in e:
        continue
    key = (e.get("s"), tuple(e["M"]), e["npat"])
    if key in seen:
        continue
    seen.add(key)
    L = {l[0]: l for l in e["levels"]}
    f12 = L[12][3] if len(L[12]) > 3 else {}
    op = f12.get("OPEN", 0)
    n24 = L[24][1] if 24 in L else None
    eq.append(dict(M=tuple(sorted(e["M"])), k=len(e["M"]), npat=e["npat"], sv12=L[12][2], open12=op, n24=n24))
print("equations", len(eq))


def poly_expect_prod(n, R=12):
    # E over uniform residues of prod_r (m_r + 1) for n digits: n!/R^n [x^n] ((1+x) e^x)^R
    base = [0.0] * (n + 1)
    for m in range(n + 1):
        base[m] = (m + 1) / factorial(m)
    res = [1.0] + [0.0] * n
    for _ in range(R):
        new = [0.0] * (n + 1)
        for i, a in enumerate(res):
            if a == 0:
                continue
            for j in range(n + 1 - i):
                new[i + j] += a * base[j]
        res = new
    return factorial(n) * res[n] / R ** n


_cache = {}


def EC0(M):
    c = collections.Counter(M)
    out = 2.0
    for d, n in c.items():
        if n not in _cache:
            _cache[n] = poly_expect_prod(n)
        out *= _cache[n]
    return out


def ols(xs, ys, ws=None):
    n = len(xs)
    ws = ws or [1.0] * n
    W = sum(ws); mx = sum(w * x for w, x in zip(ws, xs)) / W; my = sum(w * y for w, y in zip(ws, ys)) / W
    sxx = sum(w * (x - mx) ** 2 for w, x in zip(ws, xs)); sxy = sum(w * (x - mx) * (y - my) for w, x, y in zip(ws, xs, ys))
    b = sxy / sxx
    return my - b * mx, b


def fit_boot(rows, xf, yf, B=400, wf=None):
    xs = [xf(r) for r in rows]; ys = [yf(r) for r in rows]; ws = [wf(r) for r in rows] if wf else None
    a, b = ols(xs, ys, ws)
    bs = []
    n = len(rows)
    for _ in range(B):
        idx = [random.randrange(n) for _ in range(n)]
        try:
            bs.append(ols([xs[i] for i in idx], [ys[i] for i in idx], [ws[i] for i in idx] if ws else None))
        except ZeroDivisionError:
            pass
    res = [yy - (a + b * x) for x, yy in zip(xs, ys)]
    sd = (sum(r * r for r in res) / max(1, n - 2)) ** 0.5
    return a, b, bs, sd


KLO = int(os.environ.get("KLO", "11"))
rows = [r for r in eq if r["k"] >= KLO and r["open12"] > 0]
print("rows for open-rate fit (k >= %d, open12 > 0): %d" % (KLO, len(rows)))
a1, b1, bs1, sd1 = fit_boot(rows, lambda r: r["k"], lambda r: math.log(r["open12"] / r["npat"]), wf=lambda r: r["open12"] ** 0.5)
print("ln(open12/npat) = %.3f + %.4f k (resid sd %.2f); slope boot 5-95%%: %.4f..%.4f" % (a1, b1, sd1, sorted(x[1] for x in bs1)[int(.05 * len(bs1))], sorted(x[1] for x in bs1)[int(.95 * len(bs1))]))
for k in (16, 20, 24, 26, 29):
    preds = sorted(math.exp(a + b * k) for a, b in bs1)
    print("  k=%d open12/npat: point %.3e, slope-boot 5-95%% %.2e..%.2e; with equation spread x/ /%.1f" % (k, math.exp(a1 + b1 * k), preds[int(.05 * len(preds))], preds[int(.95 * len(preds))], math.exp(1.645 * sd1)))
rows24 = [r for r in eq if r["k"] >= KLO and r["open12"] > 0 and r["n24"]]
bias = []
for r in rows24:
    bias.append(math.log((r["n24"] / r["open12"]) / EC0(r["M"])))
print("children per OPEN parent: measured/analytic-uniform E[C0]: median %.3f, 5-95%% %.3f..%.3f (n=%d)" % (math.exp(sorted(bias)[len(bias) // 2]), math.exp(sorted(bias)[int(.05 * len(bias))]), math.exp(sorted(bias)[int(.95 * len(bias))]), len(bias)))
bmed = math.exp(sorted(bias)[len(bias) // 2])
byk = collections.defaultdict(list)
for r in rows24:
    byk[r["k"]].append((r["n24"] / r["open12"]) / EC0(r["M"]))
for k in sorted(byk):
    v = sorted(byk[k]); print("  k=%d bias median %.3f n=%d" % (k, v[len(v) // 2], len(v)))

gate = [json.loads(l) for l in open(os.path.join(HERE, "..", "..", "join24swap", "gate.jsonl"))]
d = {r["eq"]: r for r in gate if r["phase"] == "diff" and r["level"] == "24"}
par = json.load(open(os.path.join(HERE, "logs", "direct48.json")))
ns_rows = []
for e, c24, c48 in par:
    r = d[e]
    ns_rows.append((r["children"][0], r["cpu_new"], r["cpu_ref"], e))
heavy = [x for x in ns_rows if x[0] > 5e8]
print("measured join24 ns/child on equations with >5e8 children:", ["%.2f" % (x[1] / x[0] * 1e9) for x in heavy], " ref ns/child:", ["%.1f" % (x[2] / x[0] * 1e9) for x in heavy])

# Tier B model
tot_p = tot_c = 0.0
per = []
NS_JOIN = float(os.environ.get("NS_JOIN", "1.6e-9"))
for s in TIER_B:
    pp = cc = 0.0; kmax = 0; npat_tot = 0
    for M in multisets(s):
        M = tuple(sorted(M)); k = len(M); kmax = max(kmax, k)
        npt = 12
        for dg, n in collections.Counter(M).items():
            npt *= comb(12 + n - 1, n)
        npat_tot += npt
        op = npt * math.exp(a1 + b1 * k)
        ch = op * EC0(M) * bmed
        pp += op; cc += ch
    per.append((s, kmax, npat_tot, pp, cc))
    tot_p += pp; tot_c += cc
for s, kmax, npt, pp, cc in per:
    print("vertex %d kmax %d patterns %.3e open parents %.3e children %.3e children/parent %.3e (%.2e s at %.1f ns)" % (s, kmax, npt, pp, cc, cc / pp, cc * NS_JOIN, NS_JOIN * 1e9))
print("TOTAL open parents %.3e children %.3e ; core-seconds at %.1f ns/child: %.3e = %.3e core-days" % (tot_p, tot_c, NS_JOIN * 1e9, tot_c * NS_JOIN, tot_c * NS_JOIN / 86400))
chat_par = sum(p[2] for p in per) * 5e-3
chat_ch = 0.0
for s in TIER_B:
    for M in multisets(s):
        k = len(M); npt = 12
        for dg, n in collections.Counter(M).items():
            npt *= comb(12 + n - 1, n)
        chat_ch += npt * 5e-3 * 2 ** (k + 1)
print("chat reading: parents %.3e (5e-3 x patterns), children %.3e (x 2^(k+1)), seconds at 1 ns %.3e" % (chat_par, chat_ch, chat_ch * 1e-9))

lst = []
for s in TIER_B:
    for M in multisets(s):
        M = tuple(sorted(M)); k = len(M); npt = 12
        for dg, n in collections.Counter(M).items():
            npt *= comb(12 + n - 1, n)
        lst.append((k, npt, EC0(M)))
tp = []; tc = []
for a, b in bs1:
    tp.append(sum(npt * math.exp(a + b * k) for k, npt, e in lst))
    tc.append(sum(npt * math.exp(a + b * k) * e * bmed for k, npt, e in lst))
tp.sort(); tc.sort()
print("bootstrap (fit uncertainty only) 5-95%%: open parents %.2e .. %.2e, children %.2e .. %.2e" % (tp[int(.05 * len(tp))], tp[int(.95 * len(tp))], tc[int(.05 * len(tc))], tc[int(.95 * len(tc))]))
sdres = sd1
print("single-equation residual sd of ln(open/npat) = %.2f (x/ %.1f at 90%%)" % (sdres, math.exp(1.645 * sdres)))
# alternative bias trend: ln(bias) linear in k
import statistics
ks = sorted(byk); xs = [k for k in ks if len(byk[k]) >= 4]; ys = [math.log(sorted(byk[k])[len(byk[k]) // 2]) for k in xs]
ab, bb = ols(xs, ys)
print("bias trend ln(bias) = %.3f + %.4f k; bias(20)=%.2f bias(26)=%.2f bias(29)=%.2f" % (ab, bb, math.exp(ab + bb * 20), math.exp(ab + bb * 26), math.exp(ab + bb * 29)))
tc2 = sum(npt * math.exp(a1 + b1 * k) * e * math.exp(ab + bb * k) for k, npt, e in lst)
print("children with trending bias: %.3e (x%.2f of constant-bias)" % (tc2, tc2 / tot_c))
