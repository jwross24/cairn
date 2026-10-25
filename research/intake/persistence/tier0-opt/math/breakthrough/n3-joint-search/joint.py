import sys

sys.dont_write_bytecode = True

from math import gcd

import mpmath
from functools import lru_cache
from gmpy2 import mpq, mpz, isqrt


def egcd(a, b):
    x0, y0, x1, y1 = 1, 0, 0, 1
    while b:
        q, a, b = a // b, b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    if a < 0:
        a, x0, y0 = -a, -x0, -y0
    return a, x0, y0


@lru_cache(maxsize=None)
def logs_fixed(Q):
    mpmath.mp.prec = Q + 128
    one = mpmath.mpf(2) ** Q
    return {k: int(mpmath.floor(mpmath.log(k) * one)) for k in (2, 3, 7, 10)}


@lru_cache(maxsize=None)
def log_int_fixed(x, Q):
    mpmath.mp.prec = Q + 128 + 4 * max(1, int(x).bit_length() // 3)
    return int(mpmath.floor(mpmath.log(mpmath.mpf(int(x))) * mpmath.mpf(2) ** Q))


def dlog5(t, K):
    m5 = 5**K
    x4 = {1: 0, 2: 1, 4: 2, 3: 3}[t % 5]
    if K == 1:
        return x4, 4
    g5 = pow(2, 4, m5)
    t5 = pow(t, 4, m5)
    gam = pow(g5, 5 ** (K - 2), m5)
    pw = {pow(gam, d, m5): d for d in range(5)}
    x5 = 0
    for i in range(K - 1):
        cur = t5 * pow(g5, -x5, m5) % m5
        e = pow(cur, 5 ** (K - 2 - i), m5)
        x5 += pw[e] * 5**i
    mod5 = 5 ** (K - 1)
    inv = pow(4, -1, mod5)
    x = x4 + 4 * ((x5 - x4) * inv % mod5)
    return x, 4 * mod5


def dlog2adic(u, m):
    e = 1 if u % 4 == 3 else 0
    mm = 1 << m
    w = (-u) % mm if e else u % mm
    x = 0
    for i in range(m - 2):
        if pow(5, x, 1 << (i + 3)) != w % (1 << (i + 3)):
            x += 1 << i
    return e, x


def kernel_mod_2d(r1, r2, m):
    r1 %= m
    r2 %= m
    if r1 == 0 and r2 == 0:
        return [(1, 0), (0, 1)]
    g1, u, v = egcd(r1, r2)
    r1p, r2p = r1 // g1, r2 // g1
    mp_ = m // gcd(g1, m)
    return [(r2p, -r1p), (u * mp_, v * mp_)]


def solve_system(congs):
    p = (0, 0)
    V = [(1, 0), (0, 1)]
    for r1, r2, rho, m in congs:
        if m == 1:
            continue
        a1 = r1 * V[0][0] + r2 * V[0][1]
        a2 = r1 * V[1][0] + r2 * V[1][1]
        rp = (rho - r1 * p[0] - r2 * p[1]) % m
        g = gcd(gcd(a1, a2), m)
        if rp % g:
            return None
        a1 //= g
        a2 //= g
        rp //= g
        mg = m // g
        if mg == 1:
            continue
        a1 %= mg
        a2 %= mg
        if a1 == 0 and a2 == 0:
            if rp % mg:
                return None
            continue
        g1, u, v = egcd(a1, a2)
        if rp % gcd(g1, mg):
            return None
        gg = gcd(g1, mg)
        g1r, mgr = g1 // gg, mg // gg
        k = (rp // gg) * pow(g1r, -1, mgr) % mgr if mgr > 1 else 0
        s0, t0 = u * k, v * k
        ker = kernel_mod_2d(a1, a2, mg)
        p = (p[0] + s0 * V[0][0] + t0 * V[1][0], p[1] + s0 * V[0][1] + t0 * V[1][1])
        V = [
            (ker[0][0] * V[0][0] + ker[0][1] * V[1][0], ker[0][0] * V[0][1] + ker[0][1] * V[1][1]),
            (ker[1][0] * V[0][0] + ker[1][1] * V[1][0], ker[1][0] * V[0][1] + ker[1][1] * V[1][1]),
        ]
    return p, V


@lru_cache(maxsize=200000)
def tail_lattice(a, Bt, K):
    t_odd = Bt >> a
    m = K - a
    congs = []
    m5 = 5**K
    t5 = Bt % m5 * pow(2, -a, m5) % m5
    x3, mod5 = dlog5(3, K)
    x7, _ = dlog5(7, K)
    xt, _ = dlog5(t5, K)
    congs.append((x3, x7, xt % mod5, mod5))
    if m >= 2:
        e3, y3 = dlog2adic(3, max(m, 3))
        e7, y7 = dlog2adic(7, max(m, 3))
        et, yt = dlog2adic(t_odd % (1 << m) if m >= 3 else t_odd % 8, max(m, 3))
        congs.append((e3, e7, et, 2))
        if m >= 3:
            congs.append((y3, y7, yt, 1 << (m - 2)))
    return solve_system(congs)


def gauss_reduce(U):
    u, v = list(U[0]), list(U[1])
    while True:
        nu = u[0] * u[0] + u[1] * u[1]
        nv = v[0] * v[0] + v[1] * v[1]
        if nu > nv:
            u, v, nu, nv = v, u, nv, nu
        if nu == 0:
            break
        q = (2 * (u[0] * v[0] + u[1] * v[1]) + nu) // (2 * nu)
        if q == 0:
            break
        v = [v[0] - q * u[0], v[1] - q * u[1]]
    return [tuple(u), tuple(v)]


def babai_center(p, U, bmax, cmax):
    det = U[0][0] * U[1][1] - U[0][1] * U[1][0]
    dx, dy = bmax // 2 - p[0], cmax // 2 - p[1]
    s = (dx * U[1][1] - dy * U[1][0])
    t = (U[0][0] * dy - U[0][1] * dx)
    s, t = (2 * s + det) // (2 * det), (2 * t + det) // (2 * det)
    return (p[0] + s * U[0][0] + t * U[1][0], p[1] + s * U[0][1] + t * U[1][1])


def lll_rows(rows, delta=mpq(3, 4)):
    n = len(rows)
    b = [list(map(mpz, r)) for r in rows]
    T = [[mpz(int(i == j)) for j in range(n)] for i in range(n)]

    def dot(u, v):
        return sum(x * y for x, y in zip(u, v))

    def gso():
        bs, mu = [], [[mpq(0)] * n for _ in range(n)]
        for i in range(n):
            v = [mpq(x) for x in b[i]]
            for j in range(i):
                mu[i][j] = dot(b[i], bs[j]) / dot(bs[j], bs[j])
                v = [x - mu[i][j] * y for x, y in zip(v, bs[j])]
            bs.append(v)
        return bs, mu

    bs, mu = gso()
    k = 1
    while k < n:
        for j in range(k - 1, -1, -1):
            x = mu[k][j] + mpq(1, 2)
            q = int(x.numerator // x.denominator)
            if q:
                b[k] = [x - q * y for x, y in zip(b[k], b[j])]
                T[k] = [x - q * y for x, y in zip(T[k], T[j])]
                bs, mu = gso()
        if dot(bs[k], bs[k]) >= (delta - mu[k][k - 1] ** 2) * dot(bs[k - 1], bs[k - 1]):
            k += 1
        else:
            b[k], b[k - 1] = b[k - 1], b[k]
            T[k], T[k - 1] = T[k - 1], T[k]
            bs, mu = gso()
            k = max(k - 1, 1)
    return b, T


def enum_ball(rows, target, R2):
    n = len(rows)
    b = rows
    bs, mu = [], [[mpq(0)] * n for _ in range(n)]
    for i in range(n):
        v = [mpq(x) for x in b[i]]
        for j in range(i):
            mu[i][j] = sum(x * y for x, y in zip(b[i], bs[j])) / sum(y * y for y in bs[j])
            v = [x - mu[i][j] * y for x, y in zip(v, bs[j])]
        bs.append(v)
    nn = [sum(y * y for y in v) for v in bs]
    tau = [sum(mpq(x) * y for x, y in zip(target, bs[i])) / nn[i] for i in range(n)]
    out = []
    z = [0] * n

    def ceil_q(x):
        return -((-x.numerator) // x.denominator)

    def floor_q(x):
        return x.numerator // x.denominator

    def rec(i, rem):
        if i < 0:
            out.append(tuple(z))
            return
        c = tau[i] - sum(mu[j][i] * z[j] for j in range(i + 1, n))
        r2 = rem / nn[i]
        r = mpq(isqrt(r2.numerator * 4 * r2.denominator) + 1, 2 * r2.denominator)
        for zi in range(ceil_q(c - r), floor_q(c + r) + 1):
            d = zi - c
            left = rem - d * d * nn[i]
            if left < 0:
                continue
            z[i] = zi
            rec(i - 1, left)
        z[i] = 0

    rec(n - 1, mpq(R2))
    return out


def window_ln(D, P, a, Q, lg):
    lo = log_int_fixed(D, Q) - P * lg[10] - a * lg[2]
    hi = log_int_fixed(D + 1, Q) - P * lg[10] - a * lg[2]
    return lo, hi


def query_fixed_a(D, P, Bt, K, a, nmin, nmax, stats=None):
    if Bt % 5 == 0:
        return []
    if a < K:
        if Bt % (1 << a) or (Bt >> a) % 2 == 0:
            return []
    elif Bt % (1 << K):
        return []
    Q = int(3.33 * (len(str(nmax)) + P + 8)) + 96
    lg = logs_fixed(Q)
    bmax = (nmax * lg[10] - a * lg[2]) // lg[3] + 2
    cmax = (nmax * lg[10] - a * lg[2]) // lg[7] + 2
    if bmax < 0 or cmax < 0:
        return []
    bmax, cmax = max(bmax, 1), max(cmax, 1)
    tl = tail_lattice(a, Bt, K)
    if tl is None:
        if stats is not None:
            stats["coset_empty"] = stats.get("coset_empty", 0) + 1
        return []
    p, U = tl
    U = gauss_reduce(U)
    p = babai_center(p, U, bmax, cmax)
    lo, hi = window_ln(D, P, a, Q, lg)
    err = bmax + cmax + nmax + P + a + 4
    LO, HI = lo - err, hi + err
    W = HI - LO
    HW = (W + 1) // 2
    Fc = (LO + HI) // 2
    f1 = U[0][0] * lg[3] + U[0][1] * lg[7]
    f2 = U[1][0] * lg[3] + U[1][1] * lg[7]
    F0 = p[0] * lg[3] + p[1] * lg[7]
    Om = bmax * cmax * HW
    a_s = (2 * U[0][0] * cmax * HW, 2 * U[0][1] * bmax * HW, f1 * bmax * cmax)
    a_t = (2 * U[1][0] * cmax * HW, 2 * U[1][1] * bmax * HW, f2 * bmax * cmax)
    a_n = (0, 0, -lg[10] * bmax * cmax)
    X0 = ((2 * p[0] - bmax) * cmax * HW, (2 * p[1] - cmax) * bmax * HW, (F0 - Fc) * bmax * cmax)
    red, T = lll_rows([a_s, a_t, a_n])
    sols = enum_ball(red, [-x for x in X0], 3 * Om * Om * 1)
    if stats is not None:
        stats["enum_points"] = stats.get("enum_points", 0) + len(sols)
    out = []
    for z in sols:
        s = sum(int(z[i]) * int(T[i][0]) for i in range(3))
        t = sum(int(z[i]) * int(T[i][1]) for i in range(3))
        n = sum(int(z[i]) * int(T[i][2]) for i in range(3))
        b = p[0] + s * U[0][0] + t * U[1][0]
        c = p[1] + s * U[0][1] + t * U[1][1]
        F = F0 + s * f1 + t * f2 - n * lg[10]
        if 0 <= b <= bmax and 0 <= c <= cmax and LO <= F <= HI and nmin <= n <= nmax:
            out.append((a, b, c, n))
    return out


def leading_digits(a, b, c, P):
    e = max(a.bit_length(), b.bit_length(), c.bit_length())
    mpmath.mp.dps = int(e * 0.31) + P + 60
    x = a * mpmath.log10(2) + b * mpmath.log10(3) + c * mpmath.log10(7)
    n = int(mpmath.floor(x)) + 1
    fr = x - mpmath.floor(x)
    top = mpmath.mpf(10) ** (fr + P - 1)
    return n, int(mpmath.floor(top)), top - mpmath.floor(top)


def verify_candidate(a, b, c, n, D, P, Bt, K):
    if (pow(2, a, 10**K) * pow(3, b, 10**K) * pow(7, c, 10**K) - Bt) % 10**K:
        return False
    nn, d, frac = leading_digits(a, b, c, P)
    if nn != n:
        return False
    return d == D or frac < mpmath.mpf(10) ** -20 or frac > 1 - mpmath.mpf(10) ** -20


def query(D, P, Bt, K, nmin, nmax, stats=None):
    if Bt % (1 << K) == 0:
        return None
    a = (Bt & -Bt).bit_length() - 1
    return [r for r in query_fixed_a(D, P, Bt, K, a, nmin, nmax, stats) if verify_candidate(*r, D, P, Bt, K)]
