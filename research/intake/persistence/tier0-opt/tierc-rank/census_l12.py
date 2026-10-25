import sys, json
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from common import *

W = {d: d - 1 for d in DIGITS}


def class_dist(cnt, w):
    dist = [dict() for _ in range(cnt + 1)]
    cur = {(0, 0): 1}
    dist = {(0, 0): 1}
    layers = [{0: 1}]
    poly = [[0] * 7 for _ in range(cnt + 1)]
    poly[0][0] = 1
    for e in range(12):
        v = pow(10, e, 7) * w % 7
        new = [[0] * 7 for _ in range(cnt + 1)]
        for c in range(cnt + 1):
            for r in range(7):
                x = poly[c][r]
                if x == 0:
                    continue
                for t in range(cnt - c + 1):
                    new[c + t][(r + t * v) % 7] += x
        poly = new
    return poly[cnt]


def rank_counts(m):
    mass = sum(W[d] * c for d, c in m.items())
    dist = {0: 1}
    for d, cnt in m.items():
        if cnt == 0:
            continue
        cd = class_dist(cnt, W[d])
        nd = {}
        for r0, x0 in dist.items():
            for r1, x1 in enumerate(cd):
                if x1:
                    nd[(r0 + r1) % 7] = nd.get((r0 + r1) % 7, 0) + x0 * x1
        dist = nd
    inv9 = pow(9, -1, 7)
    out = {0: 0, 1: 0, 2: 0}
    for nu in range(12):
        rn = (pow(10, nu, 7) - 1) * inv9 % 7
        for r, x in dist.items():
            y7 = (rn + r) % 7
            y3 = (nu + mass) % 3
            rk = (1 if y3 == 0 else 0) + (1 if y7 == 0 else 0)
            out[rk] += x
    return out


def main():
    ms = multisets()
    tot = {0: 0, 1: 0, 2: 0}
    n12 = 0
    kmax = 0
    for m in ms:
        rc = rank_counts(m)
        n = level_patterns(m)
        assert sum(rc.values()) == n
        n12 += n
        kmax = max(kmax, sum(m.values()))
        for r in tot:
            tot[r] += rc[r]
    res = {"multisets": len(ms), "kmax": kmax, "N12": n12, "rank_counts": tot,
           "rank_share": {r: tot[r] / n12 for r in tot}}
    print(json.dumps(res, default=str))
    exp = {0: 4 / 7, 1: 8 / 21, 2: 1 / 21}
    print("uniform model", exp)


main()
