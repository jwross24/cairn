import json, random, math, collections, glob, os
B = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-r2bill/"
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
SCALE = 1003249 / 40000
N_W0 = 1442653443 * SCALE
N_WN = 4286108096 * SCALE
YR = 86400 * 365.25


def cp_upper(x, n, conf=0.975):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        p = 0.0
        term = (1 - mid) ** n
        for i in range(x + 1):
            if i > 0:
                term *= (n - i + 1) / i * mid / (1 - mid)
            p += term
        if p > 1 - conf:
            lo = mid
        else:
            hi = mid
    return hi


def load_meta(fn):
    m = {}
    for ln in open(fn):
        t = ln.rstrip("\n").split("\t")
        m[t[0]] = {"k": int(t[1]), "a": int(t[2])}
    return m


def tested(pattern):
    N = collections.Counter()
    S = collections.Counter()
    for f in glob.glob(pattern):
        t = json.load(open(f))
        for k, v in t["tested_by_k"].items():
            N[int(k)] += v
        for k, v in t["surv_by_k"].items():
            S[int(k)] += v
    return N, S


new = json.load(open(HERE + "newcpu_wm.json"))
meta = load_meta(B + "data/survivors_meta.tsv")
meta.update(load_meta(B + "data/survivors_meta_b3.tsv"))
ids = sorted(meta)
c0 = [new[i] for i in ids]
N0t, S0t = tested(B + "tally_*.json")
n0 = sum(N0t.values())
metao = load_meta(B + "data/survivors_meta_o1.tsv")
idso = sorted(metao)
cw = [new[i] for i in idso]
Nwt, Swt = tested(B + "otally_*.json")
nw = sum(Nwt.values())
print("W0 survivors", len(ids), "tested", n0, "WN survivors", len(idso), "tested", nw)
mean0 = sum(c0) / len(c0)
p0, pw = len(ids) / n0, len(idso) / nw
sec0 = N_W0 * p0 * mean0
secw = N_WN * pw * sum(cw) / len(cw)
print("new W0 mean cpu %.3f median %.3f max %.3f; WN mean %.3f" % (mean0, sorted(c0)[len(c0) // 2], max(c0), sum(cw) / len(cw)))
print("W0 bill core-years %.4g, WN %.4g, total %.4g = %.4g core-days = %.4g core-hours" % (sec0 / YR, secw / YR, (sec0 + secw) / YR, (sec0 + secw) / 86400, (sec0 + secw) / 3600))
rng = random.Random(23)
BS = 20000


def pois(lam):
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


def boot(c0x, cwx):
    res = []
    for _ in range(BS):
        u = math.exp(rng.gauss(0, 0.07))
        m0 = pois(len(c0x))
        s0 = sum(c0x[rng.randrange(len(c0x))] for _ in range(m0)) / n0
        mw = pois(len(cwx))
        sw = sum(cwx[rng.randrange(len(cwx))] for _ in range(mw)) / nw
        res.append((N_W0 * s0 + N_WN * sw) * u)
    res.sort()
    return res[int(0.025 * BS)], res[int(0.5 * BS)], res[int(0.975 * BS)]


lo, md, hi = boot(c0, cw)
print("bootstrap core-years [%.4g, %.4g] median %.4g" % (lo / YR, hi / YR, md / YR))
floor = 0.04
c0f = [max(x - floor, 0.0) for x in c0]
cwf = [max(x - floor, 0.0) for x in cw]
secf = N_W0 * p0 * sum(c0f) / len(c0f) + N_WN * pw * sum(cwf) / len(cwf)
lof, mdf, hif = boot(c0f, cwf)
print("batched (0.04 s process start-up removed): central %.4g core-years [%.4g, %.4g]" % (secf / YR, lof / YR, hif / YR))
nun0 = sum(v for k, v in N0t.items() if k >= 32)
sun = sum(v for k, v in S0t.items() if k >= 32)
ub = cp_upper(sun, nun0)
pat = N_W0 * nun0 / n0
big = sum(1 for x in c0 if x >= 1.0)
ubq = cp_upper(big, len(c0))
for stand in (10.0, 100.0):
    print("stand-in %.0f s: k>=32 up to %.3g survivors -> %.4g core-years; tail fraction (cost >= 1 s: %d of %d, CP95 upper %.3g) -> %.4g core-years" % (stand, pat * ub, pat * ub * stand / YR, big, len(c0), ubq, N_W0 * p0 * ubq * stand / YR))
    print("   envelope: hi + both = %.4g core-years" % ((hi + pat * ub * stand + N_W0 * p0 * ubq * stand) / YR))
byk = collections.defaultdict(list)
for i, x in zip(ids, c0): byk[meta[i]["k"]].append(x)
for k in sorted(byk):
    if k >= 24:
        v = byk[k]; print(k, len(v), "mean %.3f max %.2f" % (sum(v) / len(v), max(v)))
json.dump({"c0": c0, "cw": cw, "central_cy": (sec0 + secw) / YR, "lo": lo / YR, "hi": hi / YR}, open(HERE + "bill_new.json", "w"))
