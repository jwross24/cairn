import json, random, math, collections, glob

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


def load_costs(files):
    cost = collections.defaultdict(float)
    lab = {}
    cens = {}
    for fn in files:
        for ln in open(fn):
            r = json.loads(ln)
            cost[r["id"]] += r["cpu_s"]
            lab[r["id"]] = "BUDGET" if r["label"] == "ERROR" else r["label"]
            cens[r["id"]] = bool(r["killed"]) or r["label"] == "ERROR"
    return cost, lab, cens


def load_meta(fn, widx=None):
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


cost, lab, cens = load_costs(["results_def1.jsonl", "results_raised1.jsonl", "results_def3.jsonl", "results_raised3.jsonl"])
meta = load_meta("data/survivors_meta.tsv")
meta.update(load_meta("data/survivors_meta_b3.tsv"))
ids = sorted(meta)
c0 = [cost[i] for i in ids]
N0t, S0t = tested("tally_*.json")
n0 = sum(N0t.values())
print("W0 tested", n0, "survivors", len(ids), "tally survivors", sum(S0t.values()))
costo, labo, censo = load_costs(["results_o1.jsonl"])
metao = load_meta("data/survivors_meta_o1.tsv")
idso = sorted(metao)
cw = [costo[i] for i in idso]
Nwt, Swt = tested("otally_*.json")
nw = sum(Nwt.values())
print("WN tested", nw, "survivors", len(idso), "tally", sum(Swt.values()))
print("labels W0", dict(collections.Counter(lab[i] for i in ids)), "WN", dict(collections.Counter(labo[i] for i in idso)), "censored", sum(cens[i] for i in ids))
mean0 = sum(c0) / len(c0)
print("W0 mean cpu %.2f median %.2f max %.1f; WN mean %.2f" % (mean0, sorted(c0)[len(c0) // 2], max(c0), sum(cw) / len(cw)))
p0, pw = len(ids) / n0, len(idso) / nw
sec0 = N_W0 * p0 * mean0
secw = N_WN * pw * sum(cw) / len(cw)
print("W0 survivors %.3g (rate %.3g CP95 [%.3g, %.3g]) WN survivors %.3g" % (N_W0 * p0, p0, 0, cp_upper(len(ids), n0), N_WN * pw))
print("W0 bill core-years %.3g; WN bill core-years %.3g; total %.3g core-years = %.4g core-days" % (sec0 / YR, secw / YR, (sec0 + secw) / YR, (sec0 + secw) / 86400))

byk = collections.defaultdict(list)
for i, x in zip(ids, c0):
    byk[meta[i]["k"]].append(x)
grp = lambda k: "<=24" if k <= 24 else ("32-34" if k >= 32 else str(k))
g = collections.defaultdict(list)
gN = collections.Counter()
for k, v in byk.items():
    g[grp(k)] += v
for k, v in N0t.items():
    gN[grp(k)] += v
print("k-group | tested | survivors | rate | n,mean,median,max cpu s | share of cpu")
tot0 = sum(c0)
for key in ["<=24", "25", "26", "27", "28", "29", "30", "31", "32-34"]:
    if key in ("30", "31"):
        v = byk.get(int(key), [])
        gn = N0t.get(int(key), 0)
    else:
        v = g[key]
        gn = gN[key]
    if v:
        print(key, gn, len(v), "%.2e" % (len(v) / gn), round(sum(v) / len(v), 1), round(sorted(v)[len(v) // 2], 1), round(max(v), 1), round(sum(v) / tot0, 3))
    else:
        print(key, gn, 0, "0 (CP95 upper %.2e)" % cp_upper(0, gn))

rng = random.Random(23)
B = 20000


def pois(lam):
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


def boot(extra_w0=None, sub=None):
    res = []
    for _ in range(B):
        u = math.exp(rng.gauss(0, 0.07))
        pool = (c0 if sub is None else sub) + (extra_w0 or [])
        m0 = pois(len(c0) * len(pool) / len(c0)) if False else pois(len(pool))
        s0 = sum(pool[rng.randrange(len(pool))] for _ in range(m0)) / (n0 if not extra_w0 else n0 + 25082)
        mw = pois(len(cw))
        sw = sum(cw[rng.randrange(len(cw))] for _ in range(mw)) / nw
        res.append((N_W0 * s0 + N_WN * sw) * u)
    res.sort()
    return res[int(0.025 * B)], res[int(0.5 * B)], res[int(0.975 * B)]


lo, md, hi = boot()
tot = sec0 + secw
print("bootstrap total core-years [%.3g, %.3g] median %.3g central %.3g" % (lo / YR, hi / YR, md / YR, tot / YR))
for nm, x in (("low", lo), ("central", tot), ("high", hi)):
    print(nm, "core-days %.3g core-years %.3g; 10 cores %.3g years; 1000 cores %.3g days" % (x / 86400, x / YR, x / YR / 10, x / 86400 / 1000))

ce0 = [cens[i] for i in ids]
sub = [7200.0 if f else x for x, f in zip(c0, ce0)]
print("censored (BUDGET) survivors", sum(ce0), [(i, meta[i]["k"], round(cost[i], 1)) for i, f in zip(ids, ce0) if f])
loS, mdS, hiS = boot(None, sub)
secS = N_W0 * (sum(sub) / n0) + secw
print("BUDGET cases at 7200 s: central %.3g core-years, bootstrap [%.3g, %.3g]" % (secS / YR, loS / YR, hiS / YR))
old = []
for i in ("C1", "C2", "C3", "C4", "C5"):
    old.append(sum(json.loads(l)["cpu_s"] for l in open("results_ctrl.jsonl") if json.loads(l)["id"] == i))
print("old five costs", [round(x, 1) for x in old])
lo2, md2, hi2 = boot(old)
pooled_mean = (sum(c0) + sum(old)) / (n0 + 25082)
sec_p = N_W0 * pooled_mean + secw
print("pooled with old 25082 patterns/5 survivors: central %.3g core-years, bootstrap [%.3g, %.3g]" % (sec_p / YR, lo2 / YR, hi2 / YR))

nun = sum(v for k, v in N0t.items() if k >= 32) + sum(v for k, v in Nwt.items() if k >= 32)
nun0 = sum(v for k, v in N0t.items() if k >= 32)
sun = sum(v for k, v in S0t.items() if k >= 32)
ub = cp_upper(sun, nun0)
pat = N_W0 * nun0 / n0
print("k>=32 wrap0 tested", nun0, "survivors", sun, "CP95 upper rate %.3g -> up to %.3g survivors" % (ub, pat * ub))
for cc in (max(c0), 7200.0):
    print("  at %.0f s each: %.3g core-years" % (cc, pat * ub * cc / YR))
big = sum(1 for x in c0 if x >= 600)
ubq = cp_upper(big, len(c0))
print("survivors with cpu >= 600 s: %d of %d, CP95 upper fraction %.3g" % (big, len(c0), ubq))
tail = N_W0 * p0 * ubq * 7200.0
print("tail scenario: upper fraction at 7200 s each adds %.3g core-years (replaces, not adds, their share of the mean)" % (tail / YR))
print("hi + k>=32 at 7200 s + tail: %.3g core-years" % ((hi + pat * ub * 7200.0 + tail) / YR))
