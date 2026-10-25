from mpmath import mp, mpf, log10

mp.dps = 60


def iterate(theta, C, S1, k):
    s = S1
    for _ in range(k - 1):
        s = s + C * s ** mpf(theta) if theta else s + C
    return s


def closed(theta, C, S1, k):
    t = mpf(theta)
    return (S1 ** (1 - t) + (1 - t) * C * (k - 1)) ** (1 / (1 - t))


def young_const(theta, C, eps):
    t = mpf(theta)
    return (1 - t) * C ** (1 / (1 - t)) * t ** (t / (1 - t)) * eps ** (-t / (1 - t))


def check_closed_form():
    C = mpf(10) ** 16.3
    S1 = mpf(10) ** 14.3
    bad = 0
    for k in (6, 31, 44, 200):
        for th in (0.25, 0.5, 0.75, 0.9):
            a = iterate(th, C, S1, k)
            b = closed(th, C, S1, k)
            ok = a <= b * (1 + mpf(10) ** -30)
            bad += not ok
            print('closed-form k=%3d theta=%.2f  iter=10^%.3f  bound=10^%.3f  ok=%s' % (k, th, float(log10(a)), float(log10(b)), ok))
    return bad


def check_young():
    import random
    random.seed(1)
    bad = 0
    for _ in range(2000):
        th = random.choice([0.25, 0.5, 0.75, 0.9])
        C = mpf(10) ** random.uniform(0, 17)
        eps = mpf(10) ** random.uniform(-6, 1)
        h = mpf(10) ** random.uniform(0, 80)
        lhs = C * h ** mpf(th)
        rhs = eps * h + young_const(th, C, eps)
        if lhs > rhs * (1 + mpf(10) ** -25):
            bad += 1
    print('Young inequality C h^theta <= eps h + c(eps): violations in 2000 random draws =', bad)
    th = mpf(0.75)
    C = mpf(10) ** 16.3
    for eps in (mpf(1) / 44, mpf(1) / 10, mpf(1), mpf(40)):
        print('  theta=0.75 C=10^16.3 eps=%.4f  c(eps)=10^%.2f' % (float(eps), float(log10(young_const(th, C, eps)))))
    return bad


def planted_negative():
    th, C, S1, k = 0.75, mpf(10) ** 16.3, mpf(10) ** 14.3, 44
    a = iterate(th, C, S1, k)
    b = closed(th, C, S1, k)
    broken = b / mpf(10) ** 3
    print('planted negative: bound divided by 10^3 must be violated by the iteration ->', a > broken)
    return not (a > broken)


def needed_Y():
    print('per-gap multiplier needed for S_k <= target, S_{j+1} = (1+Y) S_j, S_1 = 10^14.7 (one-ended)')
    print('two-ended: n <= min_m [S_1 (1+Y)^(m-1) + Z_1 (1+Y)^(k-m)], Z_1 = 10^14.7')
    S1 = mpf(10) ** 14.7
    for k in (31, 44):
        for D, tgt in ((1, 72), (2, 120), (3, 168), (4, 216)):
            one = (mpf(10) ** tgt / S1) ** (mpf(1) / (k - 1)) - 1
            lo, hi = mpf(1), mpf(10) ** 25
            for _ in range(200):
                mid = (lo * hi) ** mpf('0.5')
                val = min(S1 * (1 + mid) ** (m - 1) + S1 * (1 + mid) ** (k - m) for m in range(1, k + 1))
                if val <= mpf(10) ** tgt:
                    lo = mid
                else:
                    hi = mid
            print('k=%d depth D=%d target 10^%d: Y_one <= 10^%.2f   Y_two <= 10^%.2f   deficit vs 10^16.7 (Matveev K1): 10^%.1f one-ended, 10^%.1f two-ended (vs 10^18.2 Yu)' % (
                k, D, tgt, float(log10(one)), float(log10(lo)), 16.7 - float(log10(one)), 18.2 - float(log10(lo))))


if __name__ == '__main__':
    b1 = check_closed_form()
    b2 = check_young()
    b3 = planted_negative()
    needed_Y()
    print('FAILURES:', b1, b2, int(b3))
