import json, sys, math, random, collections
vi = int(sys.argv[1])
m = json.load(open(f"work/smp_v{vi}_meta.json"))
p = m["p"]
lines = [l for l in open(f"work/smp_v{vi}_emit.out") if not l.startswith("T")]
res = [json.loads(l) for l in open(f"results_sv{vi}.jsonl")]
res.sort(key=lambda r: r["id"])
assert len(res) == len(lines)
cost = collections.defaultdict(float); ns = collections.Counter(); lab = collections.Counter()
for l, r in zip(lines, res):
    t = l.split()
    key = f"{t[0]} {t[1]} {t[2]}"
    cost[key] += r["cpu_s"]; ns[key] += 1; lab[r["label"]] += 1
draws = []
for key, mu in m["mult"].items():
    tot, s = m["tot"][key]
    draws += [(s / tot, cost[key] / p / tot, s, tot)] * mu
N = m["N"]; n = len(draws)
def ci(xs):
    mu = sum(xs) / len(xs); sd = math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)); return mu, 1.96 * sd / math.sqrt(len(xs))
rate, rh = ci([d[0] for d in draws]); cpp, ch = ci([d[1] for d in draws])
random.seed(1); bs = []
for _ in range(2000):
    smp = [draws[random.randrange(n)] for _ in range(n)]
    r = sum(x[0] for x in smp) / n; c = sum(x[1] for x in smp) / n
    bs.append((r, c, c / r if r else 0))
q = lambda i: (sorted(b[i] for b in bs)[50], sorted(b[i] for b in bs)[1949])
cps = cpp / rate if rate else 0
out = {"vi": vi, "s": m["s"], "N": N, "rate": rate, "rate_ci": q(0), "survivors_est": N * rate, "survivors_ci": [N * x for x in q(0)],
       "cpu_per_surv": cps, "cpu_per_surv_ci": q(2), "bill_cpu_s": N * cpp, "bill_ci": [N * x for x in q(1)],
       "emitted": len(lines), "labels": dict(lab), "max_cpu": max(r["cpu_s"] for r in res), "max_rss_mb": max(r["maxrss_mb"] for r in res),
       "mean_cpu_emitted": sum(r["cpu_s"] for r in res) / len(res), "draws": n}
json.dump(out, open(f"est_v{vi}.json", "w"), indent=1)
print(json.dumps(out))
