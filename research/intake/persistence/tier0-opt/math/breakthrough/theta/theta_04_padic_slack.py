from math import log, log10, e as E_
from lat import lll, intersect_2d, det2, norm_inf, v_p


def log5_1unit(h, L, extra=6):
    prec = L + extra
    mod = 5 ** prec
    y = (h - 1) % mod
    assert y % 5 == 0
    total = 0
    ym = 1
    m = 1
    while True:
        ym = ym * y
        r = 0
        mm = m
        while mm % 5 == 0:
            mm //= 5
            r += 1
        if m - r >= prec + 2 and m > 5:
            break
        # y^m is divisible by 5^m; divide by 5^r exactly
        if r:
            ymr = ym // 5 ** r
        else:
            ymr = ym
        term = ymr * pow(mm, -1, mod) % mod if ymr else 0
        total = (total + (term if m % 2 else -term)) % mod
        m += 1
    return total, mod


def dlog2_mod5L(x, L):
    N5 = 5 ** (L - 1)
    mod = 5 ** L
    d0 = next(d for d in range(4) if pow(2, d, 5) == x % 5)
    h = x * pow(pow(2, d0, mod), -1, mod) % mod
    g4 = pow(2, 4, mod)
    lh, _ = log5_1unit(h, L)
    lg, _ = log5_1unit(g4, L)
    assert lh % 5 == 0 and lg % 5 == 0
    d1 = (lh // 5) * pow(lg // 5, -1, N5) % N5
    d = d0 + 4 * d1
    assert pow(2, d, mod) == x % mod
    return d


def dlog5_mod2L(w, L):
    t = 0
    mod = 2 ** L
    for i in range(L - 2):
        if (w * pow(pow(5, t, mod), -1, mod)) % 2 ** (i + 3) != 1:
            t += 2 ** i
    assert pow(5, t, mod) == w % mod
    return t


def lattice3_5adic(L):
    d3 = dlog2_mod5L(3, L)
    d7 = dlog2_mod5L(7, L)
    N = 4 * 5 ** (L - 1)
    return lll([(N, 0, 0), (-d3, 1, 0), (-d7, 0, 1)])


def lattice2_10adic(L):
    d3 = dlog2_mod5L(3, L)
    d7 = dlog2_mod5L(7, L)
    t3 = dlog5_mod2L((-3) % 2 ** L, L)
    t7 = dlog5_mod2L((-7) % 2 ** L, L)
    basis = [(1, 0), (0, 1)]
    basis = intersect_2d(basis, d3, d7, 4 * 5 ** (L - 1))
    basis = intersect_2d(basis, 1, 1, 2)
    basis = intersect_2d(basis, t3, t7, 2 ** (L - 2))
    return basis


def verify_lattice3(basis, L):
    mod = 5 ** L
    for a, b, c in basis:
        val = pow(2, a, mod) * pow(3, b, mod) * pow(7, c, mod) % mod
        if val != 1:
            return False
    return True


def verify_lattice2(basis, L):
    for b, c in basis:
        for m in (5 ** L, 2 ** L):
            if pow(3, b, m) * pow(7, c, m) % m != 1:
                return False
    return True


def yu_allowed_valuation(logB):
    t = 3
    CY = (16 * E_) ** (2 * (t + 1)) * t ** 2.5 * log(2 * t) ** 2 * 5 / log(5) ** 2
    return CY * log(3) * log(7) * log(2) * logB


def main():
    rows = []
    for L in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128):
        bas = lattice3_5adic(L)
        ok = verify_lattice3(bas, L)
        lam = min(norm_inf(v) for v in bas)
        rows.append((L, lam))
        print('rank-3 lattice {2^a 3^b 7^c = 1 mod 5^L}: L=%3d verified=%s  lambda_1(sup)=10^%.2f   3*log10(lambda_1)/(L log10 5)=%.3f' % (
            L, ok, log10(lam), 3 * log10(lam) / (L * log10(5))))
    bas = lattice3_5adic(24)
    planted_ok = verify_lattice3([(bas[0][0] + 1, bas[0][1], bas[0][2])], 24)
    print('planted negative (shift a basis vector by one): still satisfies the congruence? %s' % planted_ok)
    print()
    print('true max 5-adic valuation of 2^a 3^b 7^c - 1 over the box sup<=B (largest L with lambda_1(L) <= B) versus the proved-type bound C_Yu*log2*log3*log7*log B:')
    for Be in (3, 6, 12, 24, 48):
        B = 10.0 ** Be
        Lstar = max([L for (L, lam) in rows if lam <= B] + [0])
        allowed = yu_allowed_valuation(log(B))
        print('  B=10^%2d  true L* >= %3d (grid)   proved-type allowance %.3e   slack >= 10^%.1f   (true L*/log B = %.2f)' % (
            Be, Lstar, allowed, log10(allowed / max(Lstar, 1)), Lstar / log(B)))
    print()
    print('10-adic rank-2 lattice {3^b 7^c = 1 mod 10^L} (this is the object whose shortest vector is ~sqrt(det)):')
    for L in (4, 8, 16, 32, 48, 64, 96):
        bas = lattice2_10adic(L)
        ok = verify_lattice2(bas, L)
        lam = min(norm_inf(v) for v in bas)
        print('  L=%3d verified=%s det=10^%.2f lambda_1=10^%.2f   L/log10(lambda_1)=%.3f' % (L, ok, log10(det2(bas)), log10(lam), L / log10(lam)))


if __name__ == '__main__':
    main()
