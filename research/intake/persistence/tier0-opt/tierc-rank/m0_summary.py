import sys, json
rows = [json.loads(l) for l in open(sys.argv[1])]
ab = [r["a_bound_log10"] for r in rows]
ks = [r["k"] for r in rows]
x0ok = sum(1 for r in rows if r.get("x0") is not None and (1 << r["x0"]) == r["y"])
print("n", len(rows), "a_bound log10 range", min(ab), max(ab), "digit counts", min(ks), max(ks), "x0 == anchor exponent:", x0ok)
