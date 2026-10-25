import math, os
from math import gcd

B = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/"
SH = B + "tierc-r2shadow/data/"


def egcd(a, b):
    x0, x1, y0, y1 = 1, 0, 0, 1
    aa, bb = a, b
    while bb:
        q = aa // bb
        aa, bb = bb, aa - q * bb
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    if aa < 0:
        aa, x0, y0 = -aa, -x0, -y0
    return aa, x0, y0


def kernel_cond(basis, A, Bc, m):
    (u1b, u1c), (u2b, u2c) = basis
    al = A * u1b + Bc * u1c
    be = A * u2b + Bc * u2c
    g0, s, t = egcd(al, be)
    if g0 == 0:
        return basis
    mm = m // gcd(g0, m)
    vs = [(mm * s, mm * t), (be // g0, -al // g0)]
    return [(x * u1b + y * u2b, x * u1c + y * u2c) for (x, y) in vs]


def det(basis):
    (a, b), (c, d) = basis
    return abs(a * d - b * c)


def load_lam96():
    basis = [(1, 0), (0, 1)]
    n = 0
    for line in open(SH + "lattice96.txt"):
        if line[0] == "#" or not line.strip():
            continue
        t = line.split()
        p, l3, l7 = int(t[0]), int(t[2]), int(t[3])
        basis = kernel_cond(basis, l3, l7, p - 1)
        n += 1
    return basis, n


def load_lam_eff(basis96):
    basis = basis96
    n = 0
    for line in open(SH + "levelprimes480.txt"):
        if line[0] == "#" or not line.strip():
            continue
        t = line.split()
        if t[0] == "B":
            L, p, l3, l7 = int(t[1]), int(t[2]), int(t[5]), int(t[6])
        else:
            L, p, l3, l7 = int(t[0]), int(t[1]), int(t[4]), int(t[5])
        if L != 480:
            continue
        basis = kernel_cond(basis, l3, l7, p - 1)
        n += 1
    return basis, n


def hnf2(gens):
    p = q = d = 0
    for (x, y) in gens:
        if x == 0:
            d = gcd(d, y)
            continue
        if p == 0:
            if x < 0:
                x, y = -x, -y
            p, q = x, y
            continue
        g, s, t = egcd(x, p)
        np_, nq = s * x + t * p, s * y + t * q
        d = gcd(d, (p // g) * y - (x // g) * q)
        p, q = np_, nq
    if d:
        q %= d
    return p, q, d


def lat_member(h, v):
    p, q, d = h
    x, y = v
    if p == 0:
        if x != 0:
            return False
        return (y % d == 0) if d else y == 0
    if x % p:
        return False
    c = x // p
    r = y - c * q
    return (r % d == 0) if d else r == 0


def dlog2(u, M):
    mod = 1 << M
    u %= mod
    s = 1 if (u & 3) == 3 else 0
    if s:
        u = (-u) % mod
    e = 0
    cur = 1
    for i in range(M - 2):
        if (cur - u) % (1 << (i + 3)) != 0:
            e |= 1 << i
            cur = cur * pow(5, 1 << i, mod) % mod
    assert cur == u
    return s, e


def img(mod, v):
    return pow(3, v[0], mod) * pow(7, v[1], mod) % mod


def order_mod5(g, M):
    mod = 5 ** M
    N = 4 * 5 ** (M - 1)
    o = N
    for q in (2, 5):
        while o % q == 0 and pow(g, o // q, mod) == 1:
            o //= q
    return o


def closure(gens, mod):
    seen = {1}
    frontier = [1]
    while frontier:
        nxt = []
        for x in frontier:
            for g in gens:
                y = x * g % mod
                if y not in seen:
                    seen.add(y)
                    nxt.append(y)
        frontier = nxt
        if len(seen) > 5_000_000:
            raise RuntimeError("closure too large")
    return seen


class Window:
    def __init__(self, basis, M=480):
        self.basis = basis
        self.M = M
        m2 = 1 << M
        im2 = [img(m2, v) for v in basis]
        dl = [dlog2(g, M) for g in im2]
        mod_e = 1 << (M - 2)
        self.h2 = hnf2(dl + [(2, 0), (0, mod_e)])
        c = 3
        while not lat_member(self.h2, (0, 1 << (c - 2))):
            c += 1
        self.c2 = c
        mc = 1 << c
        self.A2 = closure([g % mc for g in im2], mc)
        m5 = 5 ** M
        im5 = [img(m5, v) for v in basis]
        ords = [order_mod5(g, M) for g in im5]
        Hs = 1
        for o in ords:
            Hs = Hs * o // gcd(Hs, o)
        self.Hs = Hs
        w = 0
        x = Hs
        while x % 5 == 0:
            x //= 5
            w += 1
        self.t5 = max(M - w, 1)
        mt = 5 ** self.t5
        self.A5 = closure([g % mt for g in im5], mt)

    def full_member2(self, u):
        s, e = dlog2(u, self.M)
        return lat_member(self.h2, (s, e))

    def full_member5(self, u):
        return pow(u % (5 ** self.M), self.Hs, 5 ** self.M) == 1
