import json, random, math, collections, glob

N0 = 1442653443 * 1003249 / 40000
NPAT = 0
for f in glob.glob("tally_*.json"):
    NPAT += sum(json.load(open(f))["tested_by_k"].values())
meta = {}
for ln in open("data/survivors_meta.tsv"):
    t = ln.split("\t")
    meta[t[0]] = {"k": int(t[1]), "a": int(t[2])}
cost = collections.defaultdict(float)
lab = {}
cens = {}
for ln in open("results_def1.jsonl"):
    r = json.loads(ln)
    cost[r["id"]] += r["cpu_s"]
    lab[r["id"]] = r["label"]
    cens[r["id"]] = bool(r["killed"])
for ln in open("results_raised1.jsonl"):
    r = json.loads(ln)
    cost[r["id"]] += r["cpu_s"]
    lab[r["id"]] = r["label"]
    cens[r["id"]] = bool(r["killed"])
ids = sorted(meta)
n = len(ids)
c = [cost[i] for i in ids]
cn = [cens[i] for i in ids]
print("survivors", n, "patterns tested", NPAT, "N0 %.4g" % N0)
print("labels", dict(collections.Counter(lab.values())), "censored", sum(cn))
mean = sum(c) / n
tot = N0 * mean / NPAT * n
print("mean cpu per survivor %.2f s median %.2f max %.1f" % (mean, sorted(c)[n // 2], max(c)))
p = n / NPAT
print("survivor rate %.3g, population survivors %.3g" % (p, N0 * p))
secs = N0 * p * mean
print("bill cpu-s %.3g core-days %.3g core-years %.3g" % (secs, secs / 86400, secs / 86400 / 365.25))
byk = collections.defaultdict(list)
for i, x in zip(ids, c):
    byk[meta[i]["k"]].append(x)
grp = lambda k: "<=24" if k <= 24 else ("30-31" if k >= 30 else str(k))
g = collections.defaultdict(list)
for k, v in byk.items():
    g[grp(k)] += v
print("k-group: n, mean, median, max, share of total")
for key in ["<=24", "25", "26", "27", "28", "29", "30-31"]:
    v = g[key]
    print(key, len(v), round(sum(v) / len(v), 1), round(sorted(v)[len(v) // 2], 1), round(max(v), 1), round(sum(v) / sum(c), 3))
rng = random.Random(11)
B = 20000
res = []
for _ in range(B):
    m = 0
    L = math.exp(-n)
    lam = n
    m = int(round(rng.gauss(lam, math.sqrt(lam))))
    s = sum(c[rng.randrange(n)] for _ in range(m))
    u = math.exp(rng.gauss(0, 0.07))
    res.append(N0 / NPAT * s * u)
res.sort()
lo, hi = res[int(0.025 * B)], res[int(0.975 * B)]
print("bootstrap total cpu-s [%.3g, %.3g]" % (lo, hi))
for nm, x in (("low", lo), ("central", secs), ("high", hi)):
    print(nm, "core-days %.3g core-years %.3g; on 10 cores %.3g years; on 1000 cores %.3g days" % (x / 86400, x / 86400 / 365.25, x / 86400 / 365.25 / 10, x / 86400 / 1000))
nunseen = sum(v for kk, v in {32: 14605, 33: 2352, 34: 229}.items())
upper_rate = 3.69 / nunseen
extra_pat = N0 * nunseen / NPAT
for cc in (max(c), 7200.0):
    ex = extra_pat * upper_rate * cc
    print("k 32-34 unseen: survivors at 95%% upper rate %.3g, each cost %.0f s -> %.3g core-years" % (extra_pat * upper_rate, cc, ex / 86400 / 365.25))
