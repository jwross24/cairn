import sys, json

R96 = (10 ** 96 - 1) // 9
S = 2 ** 6 * 3 ** 27 * 7
bad = 0
n = 0
for ln in open(sys.argv[1]):
    r = json.loads(ln)
    n += 1
    V = sum((d - 1) * 10 ** e for d, e in r["words"])
    prod = 1
    for d, e in r["words"]:
        prod *= d
    ok = (V == r["y"] + r["k"] * R96 - (10 ** r["nu"] - 1) // 9) and prod == S and all(0 <= e < 96 for d, e in r["words"])
    if not ok:
        bad += 1
print("patterns", n, "invalid", bad)
