from itertools import combinations, product
from math import log2

GAMMAS = [9 * w for w in range(1, 9)]


def v2(x):
    return (x & -x).bit_length() - 1


def check_one(n, pos_desc, gam_desc, a_override=0):
    M = 10 ** n + sum(g * 10 ** p for g, p in zip(gam_desc, pos_desc)) - 1
    a = v2(M) + a_override
    ps = list(reversed(pos_desc))
    gs = list(reversed(gam_desc))
    k = len(ps)
    viol = 0
    nontriv = 0
    if a >= 1:
        if ps[0] != 0 or gs[0] % 2 == 0:
            viol += 1
    S = -1
    for m in range(0, k):
        if m >= 1:
            S += gs[m - 1] * 10 ** ps[m - 1]
        if m == 0:
            continue
        nxt = ps[m]
        if nxt <= a:
            if v2(S) < nxt or not (nxt <= log2(80) + ps[m - 1] * log2(10)):
                viol += 1
            if nxt >= 4 * (ps[m - 1] + 1) // 3 and nxt > 3:
                nontriv += 1
        else:
            if v2(S) != a or not (a <= log2(80) + ps[m - 1] * log2(10)):
                viol += 1
    return a, viol, nontriv


def run(nmax, kmax, a_override=0, label=''):
    tested = 0
    with_a = 0
    viol = 0
    nontriv = 0
    maxa = 0
    for k in range(1, kmax + 1):
        for n in range(k + 1, nmax + 1):
            for pos in combinations(range(n - 1, -1, -1), k):
                for gam in product(GAMMAS, repeat=k):
                    a, v, nt = check_one(n, pos, gam, a_override)
                    tested += 1
                    if a >= 1:
                        with_a += 1
                        maxa = max(maxa, a)
                    viol += v
                    nontriv += nt
    print('%s n<=%d k<=%d: %d candidates, %d with a>=1 (max a %d), %d chain steps with a gap larger than the dense case, violations %d' % (
        label, nmax, kmax, tested, with_a, maxa, nontriv, viol))
    return viol


if __name__ == '__main__':
    v = run(14, 3, 0, 'true a')
    w = run(14, 3, 3, 'PLANTED NEGATIVE (a shifted by 3)')
    print('FAILURES:', v, int(w == 0))
