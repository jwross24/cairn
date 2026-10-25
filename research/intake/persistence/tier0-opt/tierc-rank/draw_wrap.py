import sys, random, bisect
from collections import Counter

src, n, seed, out, mode = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
items = []
tot_all = 0
tot_w0 = 0
for ln in open(src):
    t = ln.split()
    if t[-1].startswith("OVERFLOW"):
        continue
    y, k = t[0], int(t[1])
    for tok in t[2:-1]:
        nu, c = tok.split(":")
        c = int(c)
        tot_all += c
        if k == 0:
            tot_w0 += c
        if (mode == "w0") == (k == 0):
            items.append((y, k, int(nu), c))
cum = []
s = 0
for it in items:
    s += it[3]
    cum.append(s)
random.seed(seed)
cnt = Counter()
for _ in range(n):
    r = random.randrange(s)
    cnt[bisect.bisect_right(cum, r)] += 1
with open(out, "w") as f:
    for i, m in sorted(cnt.items()):
        y, k, nu, c = items[i]
        f.write(f"{y} {k} {nu} {m}\n")
print("mode", mode, "stratum patterns", s, "all patterns", tot_all, "wrap0 patterns", tot_w0, "wrap0 share", tot_w0 / tot_all, "distinct cells", len(cnt))
