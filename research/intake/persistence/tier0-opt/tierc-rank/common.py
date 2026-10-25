from math import comb

VERTEX = (6, 27, 1)
S = 2 ** 6 * 3 ** 27 * 7
DIGITS = (2, 3, 4, 6, 7, 8, 9)
EXPS = {2: (1, 0, 0), 3: (0, 1, 0), 4: (2, 0, 0), 6: (1, 1, 0), 7: (0, 0, 1), 8: (3, 0, 0), 9: (0, 2, 0)}


def multisets(vertex=VERTEX):
    a, b, c = vertex
    out = []
    for n7 in range(c + 1):
        for n9 in range(b // 2 + 1):
            for n6 in range(min(a, b - 2 * n9) + 1):
                n3 = b - 2 * n9 - n6
                if n3 < 0:
                    continue
                ra = a - n6
                for n8 in range(ra // 3 + 1):
                    for n4 in range((ra - 3 * n8) // 2 + 1):
                        n2 = ra - 3 * n8 - 2 * n4
                        if n7 != c:
                            continue
                        out.append({2: n2, 3: n3, 4: n4, 6: n6, 7: n7, 8: n8, 9: n9})
    return out


def level_patterns(m, level=12):
    t = level
    r = t
    for d, cnt in m.items():
        r *= comb(t - 1 + cnt, cnt)
    return r
