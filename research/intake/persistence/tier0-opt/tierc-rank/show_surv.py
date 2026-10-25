import json
from collections import Counter

for l in open("r2g_survivors.jsonl"):
    r = json.loads(l)
    y = r["y"]
    f = {}
    for p in (2, 3, 7):
        c = 0
        z = y
        while z % p == 0:
            z //= p
            c += 1
        f[p] = c
    cl = Counter(e for d, e in r["words"])
    print("y", y, "=", "2^%d 3^%d 7^%d" % (f[2], f[3], f[7]), "rest", y // (2 ** f[2] * 3 ** f[3] * 7 ** f[7]), "k", r["k"], "a", r["a"], "s1", r["s1"], "ncases1", r["ncases1"], "E", r["E"], "nodes", r["nodes"], "nu", r["nu"], "wrap", r["wrap"], "low classes", sorted(e for e in cl if e < r["a"] + 9))
