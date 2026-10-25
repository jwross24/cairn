from fractions import Fraction
from math import gcd, isqrt


def lll(basis, delta=Fraction(3, 4)):
    b = [list(map(int, v)) for v in basis]
    n = len(b)

    def dot(u, v):
        return sum(x * y for x, y in zip(u, v))

    def gso():
        bs = []
        mu = [[Fraction(0)] * n for _ in range(n)]
        for i in range(n):
            v = [Fraction(x) for x in b[i]]
            for j in range(i):
                mu[i][j] = dot(b[i], bs[j]) / dot(bs[j], bs[j])
                v = [x - mu[i][j] * y for x, y in zip(v, bs[j])]
            bs.append(v)
        return bs, mu

    bs, mu = gso()
    k = 1
    while k < n:
        for j in range(k - 1, -1, -1):
            q = round(mu[k][j])
            if q:
                b[k] = [x - q * y for x, y in zip(b[k], b[j])]
                bs, mu = gso()
        if dot(bs[k], bs[k]) >= (delta - mu[k][k - 1] ** 2) * dot(bs[k - 1], bs[k - 1]):
            k += 1
        else:
            b[k], b[k - 1] = b[k - 1], b[k]
            bs, mu = gso()
            k = max(k - 1, 1)
    return b


def egcd(a, b):
    x0, y0, x1, y1 = 1, 0, 0, 1
    while b:
        q, a, b = a // b, b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    if a < 0:
        a, x0, y0 = -a, -x0, -y0
    return a, x0, y0


def kernel_mod_2d(r1, r2, m):
    g1, u, v = egcd(r1 % m if r1 % m else 0, r2 % m if r2 % m else 0) if (r1 % m or r2 % m) else (0, 0, 0)
    if g1 == 0:
        return [(1, 0), (0, 1)]
    r1p, r2p = (r1 % m) // g1, (r2 % m) // g1
    mp_ = m // gcd(g1, m)
    return [(r2p, -r1p), (u * mp_, v * mp_)]


def intersect_2d(basis, A, B, m):
    r1 = (A * basis[0][0] + B * basis[0][1]) % m
    r2 = (A * basis[1][0] + B * basis[1][1]) % m
    ker = kernel_mod_2d(r1, r2, m)
    nb = []
    for (s, t) in ker:
        nb.append((s * basis[0][0] + t * basis[1][0], s * basis[0][1] + t * basis[1][1]))
    return lll(nb)


def det2(b):
    return abs(b[0][0] * b[1][1] - b[0][1] * b[1][0])


def norm_inf(v):
    return max(abs(x) for x in v)


def v_p(x, p):
    if x == 0:
        return 10 ** 9
    c = 0
    while x % p == 0:
        x //= p
        c += 1
    return c
