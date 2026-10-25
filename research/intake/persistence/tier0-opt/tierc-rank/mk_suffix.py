import sys, random

src, L, n, seed, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
rows = open(src).read().split("\n")
rows = [r for r in rows if r.strip()]
suf = rows[L:]
random.seed(seed)
pick = random.sample(suf, n)
with open(out, "w") as f:
    for r in pick:
        f.write(r + "\n")
print("suffix pairs", len(suf), "sampled", len(pick))
