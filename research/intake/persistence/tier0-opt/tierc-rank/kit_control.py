import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from kitmv import *

Y = mpfr(10) ** 21
lw = lg(mpfr(1 + 5 ** 0.5) / 2) if False else gmpy2.log((1 + gmpy2.sqrt(mpfr(5))) / 2)
l5h = gmpy2.log(gmpy2.sqrt(mpfr(5)))
alphas_fn = lambda rho: None


def ex1(rho, m, L, chi):
    D = 2
    al = [(lw, lw / 2), (l5h, l5h), ((rho - 1) * 0 + lw + 2 * Y * 0, 0)]
    a1 = (rho + 1) * lw
    a2 = (rho + 3) * l5h
    a3 = (rho + 1) * lw + 4 * Y
    return D, a1, a2, a3


def slack_direct(rho, m, L, chi, p):
    D = 2
    a1 = (rho + 1) * lw
    a2 = (rho + 3) * l5h
    a3 = (rho + 1) * lw + 4 * Y
    a = [a1, a2, a3]
    omega = a1 * a2 * a3
    K = m * L * omega
    amin = min(a)
    c1 = max(mpfr(2) ** (mpfr(1) / 3), (chi * m * L) ** (mpfr(2) / 3), gmpy2.sqrt(2 * m * L / amin))
    c2 = (m * L) ** (mpfr(2) / 3)
    c3 = (3 * m * m) ** (mpfr(1) / 3) * L
    R = sum(c * a2 * a3 for c in (c1, c2, c3)) + 1
    S = sum(c * a1 * a3 for c in (c1, c2, c3)) + 1
    T = sum(c * a1 * a2 for c in (c1, c2, c3)) + 1
    N = K * (K + 1) * L / 2
    g = mpfr(1) / 4 - N / (12 * R * S * T)
    b1 = p
    b2 = mpfr(1)
    b3 = p
    logb = lg(((R - 1) * b3 + (T - 1) * b1) / 2) + lg(((S - 1) * b3 + (T - 1) * b2) / 2) - 2 * lg(K) + mpfr(11) / 3
    lhs = (K * L / 2 + L / 2 - mpfr("0.37") * K - 2) * lg(rho)
    rhs = (D + 1) * lg(N) + g * L * (a1 * R + a2 * S + a3 * T) + 2 * D * (K - 1) * logb / 3
    return lhs - rhs, K, c1, c2, c3, logb


p = mpfr("1.74e12")
rho, m, chi = mpfr(10), mpfr(6), mpfr("0.75")
lo, hi = 5, 10 ** 6
while hi - lo > 1:
    mid = (lo + hi) // 2
    s = slack_direct(rho, m, mpfr(mid), chi, p)[0]
    if s > 0:
        hi = mid
    else:
        lo = mid
print("min L for (m=6, rho=10, chi=0.75):", hi)
s, K, c1, c2, c3, logb = slack_direct(rho, m, mpfr(167), chi, p)
print("K/logy", float(K / Y), "c", float(c1), float(c2), float(c3), "logb", float(logb))
print("KL log rho / log y", float(K * 167 * lg(rho) / Y))
