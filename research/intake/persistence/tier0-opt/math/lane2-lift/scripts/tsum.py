import json, collections, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = [json.loads(l) for l in open(os.path.join(HERE, "logs", "timing.jsonl"))]
best = collections.defaultdict(lambda: 1e9); ok = collections.defaultdict(lambda: True)
for r in rows:
    best[(r["eq"], r["cfg"])] = min(best[(r["eq"], r["cfg"])], r["cpu"]); ok[(r["eq"], r["cfg"])] &= r["ok"]
eqs = sorted({r["eq"] for r in rows}); cfgs = []
for r in rows:
    if r["cfg"] not in cfgs: cfgs.append(r["cfg"])
print("min-of-reps CPU seconds (nice 10, load 35-65); ratio = J24 / config")
print("%-10s" % "cfg", *["%-26s" % e[:26] for e in eqs])
for c in cfgs:
    cells = []
    for e in eqs:
        if (e, c) in best:
            b = best.get((e, "J24"))
            base = b if b and b < 1e8 else best.get((e, "L0"), None)
            cells.append("%6.2fs x%-5.2f %s" % (best[(e, c)], (base / best[(e, c)]) if base else float("nan"), "" if ok[(e, c)] else "MISMATCH"))
        else:
            cells.append("-")
    print("%-10s" % c, *["%-26s" % x for x in cells])
