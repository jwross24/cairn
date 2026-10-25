import json, collections, math, random
res = [json.loads(l) for l in open("results_all2.jsonl")]
n = len(res)
lab = collections.Counter(r["label"] for r in res)
w = collections.defaultdict(collections.Counter)
for r in res: w["w0" if r["k_wrap"] == 0 else "w>=1"][r["label"]] += 1
cpu = [r["cpu_s"] for r in res]
byk = collections.defaultdict(list)
for r in res: byk[r["n"]].append(r)
rows = {}
for k, v in sorted(byk.items()):
    c = sorted(x["cpu_s"] for x in v)
    rows[k] = {"n": len(v), "cut": sum(1 for x in v if x["label"] == "closed by the cut"), "sand": sum(1 for x in v if x["label"].startswith("closed by the sandwich")),
               "mean": sum(c) / len(c), "median": c[len(c) // 2], "max": c[-1]}
random.seed(3); bs = sorted(sum(random.choices(cpu, k=20000)) / 20000 for _ in range(500))
c = sorted(cpu)
out = {"n": n, "labels": dict(lab), "by_wrap": {k: dict(v) for k, v in w.items()}, "cpu_total": sum(cpu), "cpu_mean": sum(cpu) / n, "cpu_mean_ci95_sample20000": [bs[12], bs[487]],
       "cpu_median": c[n // 2], "cpu_p99": c[int(n * .99)], "cpu_max": c[-1], "max_rss_mb": max(r["maxrss_mb"] for r in res), "killed": sum(1 for r in res if r["killed"]),
       "by_digits": rows, "stage_raised": sum(1 for r in res if r["stage"] == "raised")}
json.dump(out, open("summ_v0.json", "w"), indent=1)
print(json.dumps(out)[:3000])
