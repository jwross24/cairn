import gmpy2
from gmpy2 import mpfr
import kitmv
from chainrank import LN10, matveev_c, prodlog, alphas_for


def k1_mv(xexp, which="b"):
    nm = mpfr(10) ** mpfr(xexp)
    p = 3 if which == "b" else 7
    lp = gmpy2.log(mpfr(p))
    hs = nm * LN10 + 1
    alphas = [(LN10, LN10), (hs, hs), (lp, lp)]
    bsz = (nm, mpfr(1), mpfr("2.1") * nm + 2)
    res = kitmv.bound(1, alphas, bsz)
    return res[0] / hs, res


def k0_matveev(x, a, which="b"):
    top = alphas_for(a, 1, which)
    tt = 1 + gmpy2.log(mpfr("2.1") * mpfr(10) ** x + 2 + a)
    return matveev_c(len(top)) * prodlog(top) * tt


def chain_from_k(k0, k1, k):
    lb = LN10
    logu = gmpy2.log(mpfr(80))
    logv = gmpy2.log(mpfr(9))
    if k == 0:
        return k0 / lb
    s = (k0 + logu) / lb
    for _ in range(1, k):
        s = s + (logu + k1 * (s * lb + logv)) / lb
    return k1 * (s * lb + logv) / lb


def mv_log10(k, a, which="b", grid=(100, 200, 300, 400, 500, 600, 700, 800)):
    tab = {}
    for xe in grid:
        tab[xe] = k1_mv(xe, which)[0]
    xs = sorted(tab)

    def k1_at(x):
        if x <= xs[0]:
            return tab[xs[0]]
        if x >= xs[-1]:
            return tab[xs[-1]]
        for i in range(len(xs) - 1):
            if xs[i] <= x <= xs[i + 1]:
                t = (x - xs[i]) / (xs[i + 1] - xs[i])
                return tab[xs[i]] * (1 - t) + tab[xs[i + 1]] * t

    x = mpfr(grid[0])
    for _ in range(300):
        xn = gmpy2.log10(chain_from_k(k0_matveev(x, a, which), k1_at(float(x)), k))
        if xn <= x:
            break
        x = xn
    for _ in range(200000):
        if chain_from_k(k0_matveev(x, a, which), k1_at(float(x)), k) * (1 + mpfr("1e-6")) < mpfr(10) ** x:
            return x, k0_matveev(x, a, which), k1_at(float(x))
        x += mpfr("0.01")
    raise RuntimeError("no fixed point")
