import sys, json
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
from fractions import Fraction
from collections import Counter
import classify_open as C

M = (2,) * 9 + (3,) * 5
d = json.load(open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h1-anchoring/l48_result.json"))
print("levels", d["levels"])
anch = acc = 0
rows = []
for o in d["open"]:
    v0 = (int(o["v0"][0]), int(o["v0"][1])); u1 = tuple(int(x) for x in o["u1"]); u2 = tuple(int(x) for x in o["u2"])
    det = u1[0] * u2[1] - u1[1] * u2[0]
    x = round(Fraction(-v0[0] * u2[1] + v0[1] * u2[0], det)); y = round(Fraction(v0[0] * u1[1] - v0[1] * u1[0], det))
    best = None
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            b = v0[0] + (x + dx) * u1[0] + (y + dy) * u2[0]; c = v0[1] + (x + dx) * u1[1] + (y + dy) * u2[1]
            n = b * b + c * c
            if best is None or n < best[0]: best = (n, b, c)
    _, b, c = best
    a = o["a"]
    if b >= 0 and c >= 0 and max(b, c) < 400:
        yv = 2 ** a * 3 ** b * 7 ** c
        ident = C.exact_identity(M, yv) is not None
        rows.append((a, b, c, ident))
        if ident: anch += 1
        else: acc += 1
    else:
        rows.append((a, b, c, None)); acc += 1
print("level-48 open patterns:", len(d["open"]), "anchored(exact identity):", anch, "accident/no small anchor:", acc)
print(Counter((r[3]) for r in rows))
for r in rows[:15]: print(r)
