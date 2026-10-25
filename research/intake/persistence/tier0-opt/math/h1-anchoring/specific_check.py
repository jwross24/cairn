import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
import classify_open as C
L = 96
R = (10 ** L - 1) // 9
Rn = lambda n: (10 ** n - 1) // 9
withpos = ok = bad = 0
ks = {}
badrows = []
seen = set()
for f in sys.argv[1:]:
    for (s, M, a, nu, eps, y, sol) in C.entries(f):
        if nu is None:
            continue
        key = (s, M, a, nu, tuple(eps), y)
        if key in seen:
            continue
        seen.add(key)
        Md = sorted(M, reverse=True)
        V = Rn(nu) + sum((d - 1) * 10 ** e for d, e in zip(M, eps))
        withpos += 1
        if (V - y) % R == 0 and V >= y:
            ok += 1
            k = (V - y) // R
            ks[k] = ks.get(k, 0) + 1
        else:
            bad += 1
            badrows.append(key)
print("rows with recorded (nu, eps):", withpos, "specific identity ok:", ok, "fail:", bad)
print("k distribution:", dict(sorted(ks.items())))
for b in badrows[:10]:
    print("FAIL", b)
