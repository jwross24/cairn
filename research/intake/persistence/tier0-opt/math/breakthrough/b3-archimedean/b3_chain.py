import sys
from mpmath import mp, mpf, iv

def consts(ctx, a):
    L = ctx.log
    one = ctx.mpf(1)
    C = lambda t: ctx.mpf('1.4') * ctx.mpf(30) ** (t + 3) * ctx.mpf(t) ** ctx.mpf('4.5')
    CY = lambda t: (16 * ctx.e) ** (2 * (t + 1)) * ctx.mpf(t) ** ctx.mpf('2.5') * L(ctx.mpf(2 * t)) ** 2 * 5 / L(ctx.mpf(5)) ** 2
    return L, C, CY

def chain(ctx, nu, k, a, m, fold=True):
    L, C, CY = consts(ctx, a)
    l10 = L(ctx.mpf(10)); l2 = L(ctx.mpf(2)); l3 = L(ctx.mpf(3)); l7 = L(ctx.mpf(7))
    l80 = L(ctx.mpf(80)); l9 = L(ctx.mpf(9)); l71 = L(ctx.mpf(71))
    B = ctx.mpf('2.1') * nu + 2
    TA = 1 + L(B)
    TP = L(B)
    if a == 0:
        K0 = C(3) * l3 * l7 * l10 * TA
    else:
        K0 = C(4) * l2 * l3 * l7 * l10 * TA
    K1 = C(4) * l3 * l7 * l10 * TA if fold else (C(5) * l2 * l3 * l7 * l10 * TA if a else C(4) * l3 * l7 * l10 * TA)
    Y1 = CY(3) * l3 * l7 * TP
    aterm = a * l2
    s = (K0 + l80) / l10
    X = {1: s}
    for j in range(1, k):
        s = s + (l80 + K1 * (s * l10 + l9 + aterm)) / l10
        X[j + 1] = s
    q = {}
    if a >= 1:
        cur = Y1 * (aterm + l71)
        q[k] = ctx.mpf(0)
        q[k - 1] = cur
        for j in range(k - 2, 0, -1):
            cur = Y1 * (aterm + cur * l10 + l80)
            q[j] = cur
    else:
        cur = Y1 * (aterm + ctx.mpf(1))
        q[k] = cur
        for j in range(k - 1, 0, -1):
            cur = Y1 * (aterm + cur * l10 + l80)
            q[j] = cur
    return X, q, K0, K1, Y1

def bound(k, a, m):
    mp.dps = 50
    nu = mpf(10) ** 30
    for _ in range(2000):
        X, q, *_ = chain(mp, nu, k, a, m)
        new = X[m] + q[m]
        if abs(new - nu) < nu * mpf(10) ** -12:
            break
        nu = new
    return nu

def bound_oneside(k, a):
    mp.dps = 50
    nu = mpf(10) ** 30
    for _ in range(2000):
        X, q, K0, K1, Y1 = chain(mp, nu, k, a, k)
        l10 = mp.log(10)
        new = X[k] * (1) 
        new = new + 0
        if abs(new - nu) < nu * mpf(10) ** -12:
            break
        nu = new
    return nu

if __name__ == '__main__':
    from mpmath import log10
    for a in (0, 40):
        for k in (6, 8, 31, 44):
            best = None
            for m in range(1, k + 1):
                if a >= 1 and m == k:
                    pass
                try:
                    v = bound(k, a, m)
                except Exception as e:
                    continue
                if best is None or v < best[1]:
                    best = (m, v)
            X, q, K0, K1, Y1 = chain(mp, best[1], k, a, best[0])
            print('a=%d k=%d best m=%d log10 G=%.3f  log10K0=%.2f K1=%.2f Y1=%.2f' % (a, k, best[0], float(log10(best[1])), float(log10(K0)), float(log10(K1)), float(log10(Y1))))
