import sys, random, bisect
from collections import Counter

prefix, sample, suffix_pairs, n, seed, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
mode = sys.argv[7] if len(sys.argv) > 7 else "all"


def cells(path, scale):
    items = []
    npairs = 0
    for ln in open(path):
        t = ln.split()
        if not t or not t[-1].startswith("T:"):
            continue
        npairs += 1
        y, k = t[0], int(t[1])
        for tok in t[2:-1]:
            nu, c = tok.split(":")
            items.append((y, k, int(nu), int(c) * scale))
    return items, npairs


a, na = cells(prefix, 1.0)
b0, nb = cells(sample, 1.0)
scale = suffix_pairs / nb
b = [(y, k, nu, c * scale) for (y, k, nu, c) in b0]
items = a + b
if mode == "w0":
    items = [it for it in items if it[1] == 0]
elif mode == "other":
    items = [it for it in items if it[1] != 0]
cum = []
s = 0.0
for it in items:
    s += it[3]
    cum.append(s)
random.seed(seed)
cnt = Counter()
for _ in range(n):
    cnt[bisect.bisect_right(cum, random.random() * s)] += 1
with open(out, "w") as f:
    for i, m in sorted(cnt.items()):
        y, k, nu, c = items[i]
        f.write(f"{y} {k} {nu} {m}\n")
print("mode", mode, "prefix pairs", na, "sample pairs", nb, "scale", scale, "population patterns (est)", s, "distinct cells", len(cnt))
