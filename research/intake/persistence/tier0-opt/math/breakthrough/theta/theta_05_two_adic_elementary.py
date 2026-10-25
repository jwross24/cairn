import sys
from math import log2
from mpmath import mp, mpf, log10

mp.dps = 50
LOG2_80 = log2(80)
LOG2_71 = log2(71)


def consts():
    L = mp.log
    C = lambda t: mpf('1.4') * mpf(30) ** (t + 3) * mpf(t) ** mpf('4.5')
    CY = lambda t: (16 * mp.e) ** (2 * (t + 1)) * mpf(t) ** mpf('2.5') * L(mpf(2 * t)) ** 2 * 5 / L(mpf(5)) ** 2
    return L, C, CY


def elementary_positions(k):
    p = {1: mpf(0)}
    p[2] = mpf(LOG2_71)
    for m in range(2, k):
        p[m + 1] = mpf(LOG2_80) + mpf(3.3219280948873623) * p[m]
    return p


def chain(nu, k, a, m0, pel):
    L, C, CY = consts()
    l10 = L(mpf(10)); l2 = L(mpf(2)); l3 = L(mpf(3)); l7 = L(mpf(7))
    l80 = L(mpf(80)); l9 = L(mpf(9)); l71 = L(mpf(71))
    B = mpf('2.1') * nu + 2 + a
    TA = 1 + L(B)
    TP = L(B)
    K0 = C(4) * l2 * l3 * l7 * l10 * TA
    K1 = C(4) * l3 * l7 * l10 * TA
    Y1 = CY(3) * l3 * l7 * TP
    aterm = a * l2
    s = (K0 + l80) / l10
    X = {1: s}
    for j in range(1, k):
        s = s + (l80 + K1 * (s * l10 + l9 + aterm)) / l10
        X[j + 1] = s
    q = {k: mpf(0)}
    for m in range(2, k + 1):
        j = k + 1 - m
        if m <= m0:
            q[j] = pel[m]
        else:
            q[j] = Y1 * (aterm + q[j + 1] * l10 + l80)
    return X, q


def bound_for_split(k, a, m0, pel, m):
    nu = mpf(10) ** 30
    for _ in range(3000):
        X, q = chain(nu, k, a, m0, pel)
        new = X[m] + q[m]
        if abs(new - nu) < nu * mpf(10) ** -12:
            break
        nu = new
    return nu


def best_split(k, a, m0, pel):
    best = None
    for m in range(1, k + 1):
        v = bound_for_split(k, a, m0, pel, m)
        if best is None or v < best[1]:
            best = (m, v)
    return best


def a_max(m0, pel):
    return mpf(LOG2_80) + mpf(3.3219280948873623) * pel[m0] if m0 > 1 else mpf(6)


def run(k):
    pel = elementary_positions(k)
    print('k=%d: elementary bottom positions p_1..p_6 <= %s ; p_k <= 10^%.2f' % (
        k, [float(pel[i]) for i in range(1, 7)], float(log10(pel[k]))))
    worst = None
    for m0 in range(1, k):
        a = a_max(m0, pel)
        m, v = best_split(k, a, m0, pel)
        lv = float(log10(v))
        if worst is None or lv > worst[0]:
            worst = (lv, m0, float(a), m)
        if m0 <= 6 or m0 % 5 == 0 or m0 == k - 1:
            print('  m0=%2d  a<=%.3g  best split m=%2d  log10 G = %.3f' % (m0, float(a), m, lv))
    print('  WORST CASE over m0 (all a>=1): log10 G = %.3f at m0=%d (a<=%.3g, split %d)' % worst)
    return worst


if __name__ == '__main__':
    ks = [int(x) for x in sys.argv[1:]] or [6, 31, 44]
    for k in ks:
        run(k)
