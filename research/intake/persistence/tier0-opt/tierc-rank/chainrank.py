import gmpy2
from gmpy2 import mpfr

gmpy2.get_context().precision = 320

LN10 = gmpy2.log(mpfr(10))


def matveev_c(t):
    return mpfr("1.4") * mpfr(30) ** (t + 3) * mpfr(t) ** mpfr("4.5")


def alphas_for(a, rank, which="b"):
    base = [] if a == 0 else [2]
    if rank == 2:
        return base + [3, 7, 10]
    if rank == 1:
        return base + ([3, 10] if which == "b" else [7, 10])
    return base + [10]


def phi(alphas, k, nu, c_override=None, sigma=mpfr("2.1"), tau=mpfr(2), a=0):
    t0 = len(alphas)
    lb = LN10
    logu = gmpy2.log(mpfr(80))
    logv = gmpy2.log(mpfr(9))
    pa = mpfr(1)
    for al in alphas:
        pa *= gmpy2.log(mpfr(al))
    tt = 1 + gmpy2.log(sigma * nu + tau + a)
    if c_override is None:
        k0 = matveev_c(t0) * pa * tt
        k1 = matveev_c(t0 + 1) * pa * tt
    else:
        k0, k1 = c_override(pa, tt, nu)
    if k == 0:
        return k0 / lb
    s = (k0 + logu) / lb
    for _ in range(1, k):
        g = (logu + k1 * (s * lb + logv)) / lb
        s = s + g
    return k1 * (s * lb + logv) / lb


def log10_bound(alphas, k, a=0, c_override=None):
    ten = mpfr(10)
    x = max(mpfr(k) / LN10 + 1, mpfr(2))
    for _ in range(200):
        xn = gmpy2.log10(phi(alphas, k, ten ** x, c_override, a=a))
        if xn <= x:
            break
        x = xn
    step = mpfr("0.001")
    for _ in range(200000):
        n = ten ** x
        if n >= gmpy2.exp(mpfr(k)) and phi(alphas, k, n, c_override, a=a) * (1 + mpfr("1e-6")) < n:
            return x
        x += step
    raise RuntimeError("no fixed point")


def cy(t):
    e = gmpy2.exp(mpfr(1))
    return (16 * e) ** (2 * (t + 1)) * mpfr(t) ** mpfr("2.5") * gmpy2.log(mpfr(2 * t)) ** 2 * 5 / gmpy2.log(mpfr(5)) ** 2


def prodlog(xs):
    p = mpfr(1)
    for x in xs:
        p *= gmpy2.log(mpfr(x))
    return p


def two_ended_spec(a, rank, which="b"):
    if rank == 2:
        top = ([2] if a else []) + [3, 7, 10]
        inner = [3, 7, 10]
        yu = [3, 7]
    elif rank == 1:
        p = 3 if which == "b" else 7
        top = ([2] if a else []) + [p, 10]
        inner = [p, 10]
        yu = [p]
    else:
        raise ValueError("rank 0 has no two-ended chain")
    return top, inner, yu


def chain2(nu, k, a, m, spec):
    top, inner, yu = spec
    l10 = LN10
    l2 = gmpy2.log(mpfr(2))
    l80 = gmpy2.log(mpfr(80))
    l9 = gmpy2.log(mpfr(9))
    l71 = gmpy2.log(mpfr(71))
    b = mpfr("2.1") * nu + 2
    ta = 1 + gmpy2.log(b)
    tp = gmpy2.log(b)
    k0 = matveev_c(len(top)) * prodlog(top) * ta
    k1 = matveev_c(len(inner) + 1) * prodlog(inner) * ta
    y1 = cy(len(yu) + 1) * prodlog(yu) * tp
    aterm = a * l2
    s = (k0 + l80) / l10
    xs = {1: s}
    for j in range(1, k):
        s = s + (l80 + k1 * (s * l10 + l9 + aterm)) / l10
        xs[j + 1] = s
    q = {}
    if a >= 1:
        cur = y1 * (aterm + l71)
        q[k] = mpfr(0)
        if k - 1 >= 1:
            q[k - 1] = cur
        for j in range(k - 2, 0, -1):
            cur = y1 * (aterm + cur * l10 + l80)
            q[j] = cur
    else:
        cur = y1 * (aterm + 1)
        q[k] = cur
        for j in range(k - 1, 0, -1):
            cur = y1 * (aterm + cur * l10 + l80)
            q[j] = cur
    return xs, q


def two_ended_log10(k, a, rank, which="b"):
    spec = two_ended_spec(a, rank, which)
    best = None
    for m in range(1, k + 1):
        nu = mpfr(10) ** 30
        ok = False
        for _ in range(3000):
            xs, q = chain2(nu, k, a, m, spec)
            new = xs[m] + q[m]
            if abs(new - nu) < nu * mpfr(10) ** -12:
                ok = True
                break
            nu = new
        if not ok:
            continue
        if best is None or nu < best[1]:
            best = (m, nu)
    return gmpy2.log10(best[1]), best[0]


def chain2_k1(nu, k, a, m, spec, k1_of_nu):
    top, inner, yu = spec
    l10 = LN10
    l2 = gmpy2.log(mpfr(2))
    l80 = gmpy2.log(mpfr(80))
    l9 = gmpy2.log(mpfr(9))
    l71 = gmpy2.log(mpfr(71))
    b = mpfr("2.1") * nu + 2
    ta = 1 + gmpy2.log(b)
    tp = gmpy2.log(b)
    k0 = matveev_c(len(top)) * prodlog(top) * ta
    k1 = k1_of_nu(nu)
    y1 = cy(len(yu) + 1) * prodlog(yu) * tp
    aterm = a * l2
    s = (k0 + l80) / l10
    xs = {1: s}
    for j in range(1, k):
        s = s + (l80 + k1 * (s * l10 + l9 + aterm)) / l10
        xs[j + 1] = s
    q = {}
    if a >= 1:
        cur = y1 * (aterm + l71)
        q[k] = mpfr(0)
        if k - 1 >= 1:
            q[k - 1] = cur
        for j in range(k - 2, 0, -1):
            cur = y1 * (aterm + cur * l10 + l80)
            q[j] = cur
    else:
        cur = y1 * (aterm + 1)
        q[k] = cur
        for j in range(k - 1, 0, -1):
            cur = y1 * (aterm + cur * l10 + l80)
            q[j] = cur
    return xs, q


def two_ended_k1_log10(k, a, rank, which, k1_of_nu):
    spec = two_ended_spec(a, rank, which)
    best = None
    for m in range(1, k + 1):
        nu = mpfr(10) ** 30
        ok = False
        for _ in range(3000):
            xs, q = chain2_k1(nu, k, a, m, spec, k1_of_nu)
            new = xs[m] + q[m]
            if abs(new - nu) < nu * mpfr(10) ** -12:
                ok = True
                break
            nu = new
        if not ok:
            continue
        if best is None or nu < best[1]:
            best = (m, nu)
    return gmpy2.log10(best[1]), best[0]
