import sys, os
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
import export_cfg
from math import comb

A_MAX = int(sys.argv[1])
export_cfg.two_adic_bound = lambda M: A_MAX

def multisets(a2, b3, c7):
    out = []
    for m7 in range(c7 + 1):
        if m7 != c7:
            continue
        for m8 in range(a2 // 3 + 1):
            for m4 in range((a2 - 3 * m8) // 2 + 1):
                for m6 in range(min(b3, a2 - 3 * m8 - 2 * m4) + 1):
                    m2 = a2 - 3 * m8 - 2 * m4 - m6
                    if m2 < 0:
                        continue
                    for m9 in range((b3 - m6) // 2 + 1):
                        m3 = b3 - m6 - 2 * m9
                        if m3 < 0:
                            continue
                        out.append({2: m2, 3: m3, 4: m4, 6: m6, 7: m7, 8: m8, 9: m9})
    return out

ms = multisets(6, 27, 1)
print("multisets", len(ms))
tot = 0
with open("multisets_tierc.txt", "w") as f:
    for m in ms:
        n = 12
        for d, c in m.items():
            n *= comb(11 + c, c)
        tot += n
        f.write("%d %s\n" % (n, " ".join(str(m[d]) for d in (2, 3, 4, 6, 7, 8, 9))))
print("total patterns", tot)
M0 = []
for d in (2, 3, 4, 6, 7, 8, 9):
    M0 += [d] * ms[0][d]
export_cfg.export(tuple(M0), "cfg_tierc.txt")
print("cfg written, M0", M0)
