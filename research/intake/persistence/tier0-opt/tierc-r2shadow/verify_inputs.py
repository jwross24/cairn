import sys

VERTEX = 3416267673274176
R96 = (10 ** 96 - 1) // 9
bad = 0
for p in sys.argv[1:]:
    for ln in open(p):
        t = ln.split()
        y, nu, n = int(t[0]), int(t[1]), int(t[2])
        pairs = [tuple(map(int, x.split(":"))) for x in t[3:]]
        prod = 1
        for d, e in pairs:
            prod *= d
        V = (10 ** nu - 1) // 9 + sum((d - 1) * 10 ** e for d, e in pairs)
        ok = (len(pairs) == n and prod == VERTEX and (V - y) % R96 == 0 and V >= y and all(0 <= e < 96 for d, e in pairs))
        wrap = (V - y) // R96
        print(p, y, n, "product_ok", prod == VERTEX, "wrap", wrap, "ok", ok)
        bad += not ok
sys.exit(1 if bad else 0)
