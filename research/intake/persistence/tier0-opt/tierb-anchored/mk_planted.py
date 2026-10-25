import sys
src, out = sys.argv[1], sys.argv[2]
rows = [l.split() for l in open(src) if not l.startswith("T")][:6]
with open(out, "w") as f:
    for t in rows:
        y, k, nu, a, n = t[:5]
        De = [tuple(map(int, x.split(":"))) for x in t[5:]]
        lo = min(range(len(De)), key=lambda i: De[i][1])
        d, e = De[lo]
        De[lo] = (d, e + 1 if e + 1 < 96 else e - 1)
        f.write(" ".join([y, k, nu] + [f"{d}:{e}" for d, e in De]) + "\n")
