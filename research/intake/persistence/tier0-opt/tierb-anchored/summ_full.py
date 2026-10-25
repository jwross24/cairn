import sys, json, math, random, collections
vi, tag, p = sys.argv[1], sys.argv[2], float(sys.argv[3])
exp = {}
for l in open(f"work/expect_v{vi}.txt"):
    y, k, nu, n = l.split(); exp[(y, int(k), int(nu))] = int(n)
got = {}; byw = collections.Counter(); byw_t = collections.Counter(); bya = collections.Counter()
for l in open(f"work/full_v{vi}_emit.out"):
    t = l.split()
    if t[0] != "T": continue
    key = (t[1], int(t[2]), int(t[3])); tot, s = int(t[5]), int(t[6]); got[key] = tot
    c = "w0" if key[1] == 0 else "w>=1"
    byw[c] += s; byw_t[c] += tot
mism = sum(1 for k in exp if got.get(k) != exp[k])
N = sum(byw_t.values()); S = sum(byw.values())
res = [json.loads(l) for l in open(f"results_{tag}.jsonl")]
lab = collections.Counter(r["label"] for r in res)
cpu = [r["cpu_s"] for r in res]; n = len(cpu); mu = sum(cpu) / n
random.seed(2); bs = sorted(sum(random.choices(cpu, k=n)) / n for _ in range(2000))
byk = collections.defaultdict(list)
for r in res: byk[r["n"]].append(r["cpu_s"])
w1 = [r for r in res if r["k_wrap"] != 0]
out = {"vi": vi, "N": N, "survivors": S, "rate": S / N, "mismatch_vs_census": mism, "by_wrap": {c: [byw_t[c], byw[c], byw[c] / max(1, byw_t[c])] for c in byw},
       "emitted": n, "labels": dict(lab), "cpu_mean": mu, "cpu_mean_ci": [bs[50], bs[1949]], "cpu_median": sorted(cpu)[n // 2], "cpu_max": max(cpu),
       "max_rss_mb": max(r["maxrss_mb"] for r in res), "bill_cpu_s": S * mu, "bill_ci": [S * bs[50], S * bs[1949]],
       "by_k": {str(k): [len(v), sum(v) / len(v), max(v)] for k, v in sorted(byk.items())}, "wrap_ge1_emitted": len(w1)}
json.dump(out, open(f"full_v{vi}.json", "w"), indent=1)
print(json.dumps(out))
