import json, math
rows = [json.loads(l) for l in open("r2_cost_rows.jsonl")]
nc = sorted(r["ncases1"] for r in rows)
n = len(nc)
print("n", n, "mean ncases1", sum(nc) / n, "expected survivors (independence model) per pattern", sum(x / 640000 for x in nc) / n, "total expected in sample", sum(x / 640000 for x in nc))
print("quantiles", [nc[int(f * (n - 1))] for f in (0, 0.5, 0.9, 0.99, 1.0)])
print("P(S1>0)=", sum(1 for r in rows if r["s1"] > 0))
