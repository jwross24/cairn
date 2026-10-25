import json, os, math
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
rows = {}
for name in ("J24", "BEST", "LA", "DH"):
    rows[name] = {json.loads(l)["eq"]: json.loads(l) for l in open(os.path.join(HERE, "logs", f"eval_{name}.jsonl"))}
par = {e: sum(1 for _ in open(f"{S}/{e}/parents24.txt")) for e in rows["J24"]}
print("children per parent C, ns/child for join24 and BEST (equations with >= 1e8 children):")
pts = []
for e, r in sorted(rows["J24"].items(), key=lambda kv: kv[1]["children"]):
    if r["children"] < 1e8 or par[e] == 0:
        continue
    C = r["children"] / par[e]
    b = rows["BEST"][e]
    pts.append((C, r["cpu"] / r["children"] * 1e9, b["cpu"] / b["children"] * 1e9, rows["LA"][e]["cpu"] / r["children"] * 1e9, rows["DH"][e]["cpu"] / r["children"] * 1e9))
    print("  C=%8.0f  join24 %.2f ns  BEST %.2f ns  LA %.2f ns  DH %.2f" % pts[-1])
def ols(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b
for idx, nm in ((1, "join24"), (2, "BEST"), (3, "LA"), (4, "DH")):
    a, b = ols([math.log(p[0]) for p in pts], [math.log(p[idx]) for p in pts])
    print("%s: ns/child ~ exp(%.2f) * C^%.2f  -> at C=3e5: %.2f ns, C=2e6: %.2f ns (extrapolated beyond C=6.5e4)" % (nm, a, b, math.exp(a) * 3e5 ** b, math.exp(a) * 2e6 ** b))
