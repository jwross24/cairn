import sys
sys.dont_write_bytecode = True
import math
from math import gcd

ROOT = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/'
DATA = ROOT + 'cport-shadow480w/data/'
OUT = ROOT + 'tierc-family/'


def egcd(a, b):
    x0, y0, x1, y1 = 1, 0, 0, 1
    while b:
        q, a, b = a // b, b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    if a < 0:
        a, x0, y0 = -a, -x0, -y0
    return a, x0, y0


def v2(x):
    return (x & -x).bit_length() - 1


def hnf(rows):
    rows = [list(r) for r in rows]
    while True:
        nz = [r for r in rows if r[0] != 0]
        if len(nz) <= 1:
            break
        nz.sort(key=lambda r: abs(r[0]))
        p = nz[0]
        for r in nz[1:]:
            q = r[0] // p[0]
            r[0] -= q * p[0]
            r[1] -= q * p[1]
    top = [r for r in rows if r[0] != 0]
    g = 0
    for r in rows:
        if r[0] == 0:
            g = gcd(g, r[1])
    assert top and g
    a, b = top[0]
    if a < 0:
        a, b = -a, -b
    return a, b % g, g


class Lat:
    __slots__ = ('a', 'b', 'd')

    def __init__(self, a=1, b=0, d=1):
        self.a, self.b, self.d = a, b, d

    @staticmethod
    def from_rows(rows):
        return Lat(*hnf(rows))

    def rows(self):
        return [(self.a, self.b), (0, self.d)]

    def index(self):
        return self.a * self.d

    def contains(self, x, y):
        if x % self.a:
            return False
        return (y - (x // self.a) * self.b) % self.d == 0

    def plus(self, other):
        return Lat.from_rows(self.rows() + other.rows())

    def cong(self, A, B, m):
        a, b, d = self.a, self.b, self.d
        al = (A * a + B * b) % m
        be = (B * d) % m
        s = gcd(be, m)
        x0 = s // gcd(s, al) if al else 1
        mm = m // s
        if mm == 1:
            y0 = 0
        else:
            y0 = ((-al * x0) // s) * pow(be // s, -1, mm) % mm
        return Lat.from_rows([(x0 * a, x0 * b + y0 * d), (0, mm * d)])


class Coset:
    __slots__ = ('v', 'lat')

    def __init__(self, v, lat):
        self.v, self.lat = v, lat

    def contains(self, p):
        return self.lat.contains(p[0] - self.v[0], p[1] - self.v[1])

    def cong(self, A, B, r, m):
        a, b, d = self.lat.a, self.lat.b, self.lat.d
        v = self.v
        al = (A * a + B * b) % m
        be = (B * d) % m
        rr = (r - A * v[0] - B * v[1]) % m
        g1, u, w = egcd(al, be)
        gm = gcd(g1, m)
        if rr % gm:
            return None
        mm = m // gm
        z = (rr // gm) * pow(g1 // gm, -1, mm) % mm if mm > 1 else 0
        x0, y0 = u * z, w * z
        nv = (v[0] + x0 * a, v[1] + x0 * b + y0 * d)
        return Coset(nv, self.lat.cong(A, B, m))


ZZ = Lat(1, 0, 1)


def log5(z, e):
    M = 5 ** (e + 8)
    t = (z - 1) % M
    res = 0
    tn = 1
    for n in range(1, e + 9):
        tn = tn * t % M
        j = 0
        nn = n
        while nn % 5 == 0:
            nn //= 5
            j += 1
        term = (tn // 5 ** j) * pow(nn, -1, M)
        res += term if n & 1 else -term
    return res % 5 ** e


def _dlog3_5(u, e):
    tab = {1: 0, 3: 1, 4: 2, 2: 3}
    x4 = tab[u % 5]
    if e == 1:
        return x4
    mod = 5 ** e
    z = pow(u, 4, mod)
    num = log5(z, e) // 5
    den = log5(81, e) // 5
    m5 = 5 ** (e - 1)
    x5 = num * pow(den, -1, m5) % m5
    k = ((x4 - x5) * pow(m5, -1, 4)) % 4
    return x5 + m5 * k


def log2a(z, e):
    K = 16
    M = 1 << (e + K)
    t = (z - 1) % M
    res = 0
    tn = 1
    for n in range(1, e // 2 + K):
        tn = tn * t % M
        j = v2(n)
        nn = n >> j
        term = (tn >> j) * pow(nn, -1, M)
        res += term if n & 1 else -term
    return res % (1 << e)


_l5 = {}


def _dlog2(u, e):
    if e <= 2:
        return (0 if u % 4 == 1 else 1), 0
    s = 0 if u % 4 == 1 else 1
    mod = 1 << e
    w = (-u) % mod if s else u % mod
    if e not in _l5:
        _l5[e] = log2a(5, e) >> 2
    t = (log2a(w, e) >> 2) * pow(_l5[e], -1, 1 << (e - 2)) % (1 << (e - 2))
    return s, t


_kc = {}


def exps(e5, e2):
    key = (e5, e2)
    if key not in _kc:
        t5 = dlog3_5(7, e5) if e5 >= 1 else 0
        if e2 >= 3:
            t3 = dlog2(3, e2)[1]
            t7 = dlog2(7, e2)[1]
        else:
            t3 = t7 = 0
        _kc[key] = (t5, t3, t7)
    return _kc[key]


def klat(e2, e5):
    lat = ZZ
    if e5 >= 1:
        t5 = dlog3_5(7, e5)
        lat = lat.cong(1, t5, 4 * 5 ** (e5 - 1))
    if e2 >= 2:
        lat = lat.cong(1, 1, 2)
    if e2 >= 3:
        t3 = dlog2(3, e2)[1]
        t7 = dlog2(7, e2)[1]
        lat = lat.cong(t3, t7, 1 << (e2 - 2))
    return lat


def window_coset(a, W, L):
    if W % (1 << a) or W % 5 == 0:
        return None
    W2 = W >> a
    if W2 % 2 == 0:
        return None
    e2 = L - a
    co = Coset((0, 0), ZZ)
    t5 = dlog3_5(7, L)
    x = dlog3_5(W2 % 5 ** L, L)
    co = co.cong(1, t5, x, 4 * 5 ** (L - 1))
    if co is None:
        return None
    if e2 >= 2:
        s, t = dlog2(W2 % (1 << e2), e2)
        co = co.cong(1, 1, s, 2)
        if co is None:
            return None
        if e2 >= 3:
            t3 = dlog2(3, e2)[1]
            t7 = dlog2(7, e2)[1]
            co = co.cong(t3, t7, t, 1 << (e2 - 2))
    return co


def read_lat96():
    rows = []
    for line in open(DATA + 'lattice96.txt'):
        if line.startswith('#') or not line.strip():
            continue
        t = line.split()
        rows.append((int(t[0]), int(t[2]), int(t[3])))
    return rows


def read_levelprimes(path):
    out = {}
    for line in open(path):
        if line.startswith('#') or not line.strip():
            continue
        t = line.split()
        if t[0] == 'B':
            t = t[1:]
        L = int(t[0])
        out.setdefault(L, []).append((int(t[1]), int(t[4]), int(t[5])))
    return out


def lam_from(prime_rows, base=None):
    lat = ZZ if base is None else base
    for p, l3, l7 in prime_rows:
        lat = lat.cong(l3, l7, p - 1)
    return lat


def build_lambdas():
    lam = {96: lam_from(read_lat96())}
    lp = read_levelprimes(DATA + 'levelprimes480.txt')
    lam[192] = lam_from(lp[192], lam[96])
    lam[384] = lam_from(lp[384], lam[192])
    lam[480] = lam_from(lp[480], lam[96])
    return lam


def factor237(y):
    e = []
    for p in (2, 3, 7):
        c = 0
        while y % p == 0:
            y //= p
            c += 1
        e.append(c)
    return tuple(e) if y == 1 else None


def R(n):
    return (10 ** n - 1) // 9


def reps_wrap0(M, y, lmax=96):
    import itertools
    M = tuple(sorted(M))
    out = []
    for nu in range(lmax):
        target = y - R(nu)
        if target < 0:
            continue
        emax = len(str(target))
        sols = []

        def rec(e, rem_ms, rem, acc):
            if not rem_ms:
                if rem == 0:
                    sols.append(tuple(acc))
                return
            if e > emax or e >= lmax or rem < 0:
                return
            need = (rem // 10 ** e) % 10
            ms = list(rem_ms)
            tried = set()
            for kk in range(0, len(ms) + 1):
                for sub in itertools.combinations(range(len(ms)), kk):
                    ds = tuple(ms[i] for i in sub)
                    if ds in tried:
                        continue
                    tried.add(ds)
                    tot = sum(d - 1 for d in ds)
                    if tot % 10 != need:
                        continue
                    rest = tuple(ms[i] for i in range(len(ms)) if i not in sub)
                    rec(e + 1, rest, rem - tot * 10 ** e, acc + [(d, e) for d in ds])

        rec(0, M, target, [])
        for s in sols:
            out.append((nu, s))
    return out


_memo = {}


def dlog3_5(u, e):
    if u == 7:
        key = ('5', e)
        if key not in _memo:
            _memo[key] = _dlog3_5(7, e)
        return _memo[key]
    return _dlog3_5(u, e)


def dlog2(u, e):
    if u in (3, 7):
        key = ('2', u, e)
        if key not in _memo:
            _memo[key] = _dlog2(u, e)
        return _memo[key]
    return _dlog2(u, e)
