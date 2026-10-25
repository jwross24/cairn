import json, glob, os, collections, math
T0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/"
TB = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/tierb-lift/logs/"
sweep = {}
for f in (T0 + "trees_mac.jsonl.eqs.jsonl",):
    for l in open(f):
        try: e = json.loads(l)
        except Exception: continue
        if "levels" in e and "s" in e:
            sweep[(e["s"], tuple(sorted(e["M"])))] = e
tb = []
for f in glob.glob(TB + "h12_*.jsonl"):
    for l in open(f):
        r = json.loads(l)
        if "lift24" in r: tb.append(r)
print("tierb-lift rows with lift24:", len(tb), "npat min", min(r["npat"] for r in tb))
byk = collections.defaultdict(lambda: [0, 0, 0, 0])
match = both = 0; rat = []
for r in tb:
    d = byk[r["k"]]; d[0] += r["npat"]; d[1] += r["lift24"]["parents"]; d[2] += r["lift24"]["children"]; d[3] += 1
    e = sweep.get((r["s"], tuple(sorted(r["M"]))))
    if e:
        L = {l[0]: l for l in e["levels"]}
        op = L[12][3].get("OPEN", 0) if len(L[12]) > 3 else None
        both += 1
        if op == r["lift24"]["parents"] and e["npat"] == r["npat"]: match += 1
        else: rat.append((r["k"], r["lift24"]["parents"], op, r["npat"], e["npat"], r["s"]))
print("rows also in sweep:", both, "identical (parents, npat):", match)
for x in rat[:15]: print("  differ k,tb_parents,sweep_open,tb_npat,sweep_npat,s:", x)
print("k  rows  npat  tb_parents/npat  tb_children/npat  tb_children/parent")
for k in sorted(byk):
    n, p, c, m = byk[k]
    print("%2d %3d %.2e %.2e %.2e %.0f" % (k, m, n, p / n, c / n, c / p if p else float("nan")))

print("--- same-equation ratio sweep OPEN / tierb parents, by k (rows present in both)")
rk = collections.defaultdict(list)
for r in tb:
    e = sweep.get((r["s"], tuple(sorted(r["M"]))))
    if not e: continue
    L = {l[0]: l for l in e["levels"]}
    op = L[12][3].get("OPEN", 0)
    if r["lift24"]["parents"]: rk[r["k"]].append((op / r["lift24"]["parents"], op, r["lift24"]["parents"], r["s"]))
for k in sorted(rk):
    v = rk[k]; print(k, len(v), "ratio median %.2f min %.2f max %.2f" % (sorted(x[0] for x in v)[len(v)//2], min(x[0] for x in v), max(x[0] for x in v)), "eq-identical", sum(1 for x in v if x[0]==1.0))
print("--- vertices of tierb rows: ", collections.Counter(r["s"] for r in tb))
print("--- rows by k and vertex for k>=15")
for r in tb:
    if r["k"]>=15: print(r["s"], r["k"], r["M"][:6], "...", r["npat"], r["lift24"]["parents"], r["lift24"]["children"], "sweep" , (sweep.get((r["s"], tuple(sorted(r["M"])))) or {}).get("levels", [[0,0,0,{}]])[0][3] if (sweep.get((r["s"], tuple(sorted(r["M"])))) ) else None)
