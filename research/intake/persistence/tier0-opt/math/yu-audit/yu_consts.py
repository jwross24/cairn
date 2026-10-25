import sys

sys.dont_write_bytecode = True
from mpmath import mp, mpf, log, exp, factorial

mp.dps = 50
E = exp(mpf(1))
LOG5 = log(mpf(5))


def c2_theorem3(n, d=2):
    # Yu 2007 (1.7), case III: p = 5 = 1 mod 4, e_p = f_p = 1; c2 = 394(p-1)/(p-2), a2 = 8, kappa = 0, q = 2.
    # d = 2 means K = Q(i), required by (1.5) because ord_2(5 - 1) = 2.
    p = mpf(5)
    c2 = 394 * (p - 1) / (p - 2)
    a2 = mpf(8)
    qu = mpf(4) if d == 2 else mpf(2)
    return (
        c2
        * (a2 * 1) ** n
        * mpf(n + 1) ** (n + 1)
        / factorial(n - 1)
        * p
        / qu
        * mpf(d) ** (n + 2)
        / LOG5**3
        * log(max(mpf(d), E))
        * max(log(E**4 * (n + 1) * d), mpf(1), LOG5)
    )


def c1_theorem1(n, d=2):
    p = mpf(5)
    c1 = mpf(1473)
    a1 = 8 * (p - 1) / (p - 2)
    qu = mpf(4) if d == 2 else mpf(2)
    return (
        c1
        * a1**n
        * mpf(n) ** n
        * mpf(n + 1) ** (n + 1)
        / factorial(n)
        * p
        / qu
        * (mpf(d) / LOG5) ** (n + 2)
        * log(max(mpf(d), E))
        * max(log(E**4 * (n + 1) * d), mpf(1), LOG5)
    )


def bk(n):
    return (16 * E) ** (2 * (n + 1)) * mpf(n) ** mpf("2.5") * log(mpf(2 * n)) ** 2 * 5 / LOG5**2


def yu190(n, base=10):
    return (base * E) ** (2 * (n + 1)) * mpf(n) ** mpf("2.5") * log(mpf(2 * n)) * log(mpf(2)) * 5 / LOG5**2


def thm3(n):
    return (n + 1) * c2_theorem3(n)


def thm1(n):
    return (n + 1) * c1_theorem1(n)


KAPPA2 = 4 * E**2


def _t13_common(n, delta):
    # Yu 2013 (1.9)/(1.10) shared factors for K = Q (d = 1), p = 5, e_p = f_p = 1: q^u = 2, log* d = 1.
    p = mpf(5)
    brace = max(p / (delta * LOG5 ** (n + 1)), E**n / mpf(n) ** n)
    top = max(log(E**4 * (n + 1)), mpf(1), LOG5)
    return brace, top


def c1_2013(n, delta=1):
    # case III.2 (p >= 5, e_p = 1, d = 1): c1 = 1790, a^(1) = 8(p-1)/(p-2)
    p = mpf(5)
    brace, top = _t13_common(n, delta)
    return 1790 * (8 * (p - 1) / (p - 2)) ** n * mpf(n) ** n * mpf(n + 1) ** (n + 1) / factorial(n) / (2 * LOG5) * brace * top


def c2_2013(n, delta=1):
    # case III.2: c2 = 557(p-1)/(p-2), a^(2) = 8, kappa = 0
    p = mpf(5)
    brace, top = _t13_common(n, delta)
    return 557 * (p - 1) / (p - 2) * 8**n * mpf(n + 1) ** (n + 1) / factorial(n - 1) / (2 * LOG5**3) * brace * top


def g2_2013(n):
    a0 = 2 + log(mpf(7))
    return (n + 1) * (a0 * n + mpf("3.32") + log(mpf(n + 1)))


def omega1():
    return log(mpf(2)) * log(mpf(3)) / log(mpf(6))


def thm1_2013(n):
    return (n + 1) * c1_2013(n)


def g2(n):
    a0 = 1 + log(mpf(8))
    a1 = mpf("2.4")
    a2 = mpf("6.44")
    return (n + 1) * (a0 * n + a1 + log(a0 * n + a2) + log(mpf(n + 1)) + log(mpf(2)) + LOG5)


def omega(d=2):
    return 1 / (d * log(mpf(3 * d)) ** 3)


if __name__ == "__main__":
    from mpmath import log10

    for n in (2, 3, 4):
        print(
            n,
            "BK %.2f yu190(16) %.2f yu190(10) %.2f thm3 %.2f thm1 %.2f c2(no n+1) %.2f G2 %.2f"
            % (log10(bk(n)), log10(yu190(n, 16)), log10(yu190(n, 10)), log10(thm3(n)), log10(thm1(n)), log10(c2_theorem3(n)), g2(n)),
        )
    print("omega(2)", omega(2), "1/(kappa2*d)", 1 / (KAPPA2 * 2))
    for n in (1, 2, 3, 4):
        print(n, "2013: C1* %.2f  C1 %.2f  C2 %.2f  C2* %.2f  G2 %.2f" % (log10(thm1_2013(n)), log10(c1_2013(n)), log10(c2_2013(n)), log10((n + 1) * c2_2013(n)), g2_2013(n)))
