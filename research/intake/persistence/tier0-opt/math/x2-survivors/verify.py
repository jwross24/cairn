import collections, json, math, os, random, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
C = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
R = int("1" * 24)
dig = {}
rows = [json.loads(l) for l in open(os.path.join(HERE, "survivors.jsonl"))]
n_ver = bad = 0
kap = collections.Counter(); anchors = collections.Counter(); kviol = 0
for r in rows:
    if r["eq"] not in dig:
        dig[r["eq"]] = list(map(int, open(os.path.join(C, r["eq"], "cfgL24.txt")).read().split("\n")[1].split()))
    if not r["shadow"]:
        continue
    d = dig[r["eq"]]
    cols = [0] * 64
    for i in range(r["nu"]):
        cols[i] += 1
    for dd, e in zip(d, r["eps"]):
        cols[e] += dd - 1
    V = sum(c * 10 ** i for i, c in enumerate(cols))
    y = int(r["y"]); a, b, c = r["abc"]
    n_ver += 1
    if not (V == y + r["kappa"] * R and y == 2 ** a * 3 ** b * 7 ** c and 0 < y < R):
        bad += 1
    if r["kappa"] > 8 * r["k"]:
        kviol += 1
    kap[r["kappa"]] += 1
    anchors[y] += 1
sizes = collections.Counter(len(str(y)) for y in anchors)
print("shadows verified", n_ver, "bad", bad, "kappa>8k", kviol)
print("kappa hist", sorted(kap.items())[:12], "max", max(kap))
print("distinct anchors", len(anchors), "digit-length hist", sorted(sizes.items()))
print("top anchors", [(y, n) for y, n in anchors.most_common(6)])
