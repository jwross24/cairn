"""k-dimensional integer lattice cosets  v0 + Z^k·U  (rows of U are basis vectors),
intersection with one linear congruence  A·x ≡ r (mod m), and intersection with one exact
linear equation  A·x = t  (which drops the rank by one).  Used with k = 3 for (a, b, c).

The congruence/equation is handled by a unimodular change of basis: find unimodular W with
A·W = (g, 0, ..., 0), g = gcd(A).  In the new coordinates y the condition is on y_1 alone.
"""
from math import gcd


def _egcd(a, b):
    x0, y0, x1, y1 = 1, 0, 0, 1
    while b:
        q, a, b = a // b, b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    if a < 0:
        a, x0, y0 = -a, -x0, -y0
    return a, x0, y0


def _unimodular_clear(A):
    """return (g, W) with W a k×k unimodular matrix (list of columns) such that A·W = (g,0,..,0)."""
    k = len(A)
    A = list(A)
    W = [[1 if i == j else 0 for i in range(k)] for j in range(k)]   # W[j] = column j
    # Euclid between column 0 and column j, j = 1..k-1
    for j in range(1, k):
        a, b = A[0], A[j]
        if b == 0:
            continue
        g, x, y = _egcd(a, b)             # x a + y b = g
        # new col0 = x*c0 + y*cj ; new colj = (-b/g)*c0 + (a/g)*cj   (det = x a/g + y b/g = 1)
        c0, cj = W[0], W[j]
        n0 = [x * c0[i] + y * cj[i] for i in range(k)]
        nj = [(-b // g) * c0[i] + (a // g) * cj[i] for i in range(k)]
        W[0], W[j] = n0, nj
        A[0], A[j] = g, 0
    g = A[0]
    if g < 0:
        g = -g; W[0] = [-v for v in W[0]]
    return g, W


def _matvec_cols(W, y):
    k = len(y)
    return [sum(W[j][i] * y[j] for j in range(k)) for i in range(k)]


def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _lll(B, delta=0.99):
    """integer LLL on a list of basis vectors (small dimension; exact rationals via fractions)."""
    from fractions import Fraction
    B = [list(b) for b in B]
    n = len(B)
    def gso():
        Bs = []; mu = [[Fraction(0)] * n for _ in range(n)]
        for i in range(n):
            v = [Fraction(x) for x in B[i]]
            for j in range(i):
                mu[i][j] = Fraction(_dot(B[i], Bs[j])) / _dot(Bs[j], Bs[j]) if _dot(Bs[j], Bs[j]) else Fraction(0)
                v = [a - mu[i][j] * b for a, b in zip(v, Bs[j])]
            Bs.append(v)
        return Bs, mu
    Bs, mu = gso()
    k = 1
    while k < n:
        for j in range(k - 1, -1, -1):
            q = round(mu[k][j])
            if q:
                B[k] = [a - q * b for a, b in zip(B[k], B[j])]
                Bs, mu = gso()
        if _dot(Bs[k], Bs[k]) >= (delta - mu[k][k - 1] ** 2) * _dot(Bs[k - 1], Bs[k - 1]):
            k += 1
        else:
            B[k], B[k - 1] = B[k - 1], B[k]
            Bs, mu = gso()
            k = max(k - 1, 1)
    return [tuple(b) for b in B]


class CosetK:
    __slots__ = ("v0", "U")

    def __init__(self, v0, U):
        self.v0 = tuple(v0); self.U = [tuple(u) for u in U]

    @classmethod
    def full(cls, k):
        return cls([0] * k, [[1 if i == j else 0 for i in range(k)] for j in range(k)])

    def dim(self):
        return len(self.U)

    def point(self, y):
        """v0 + Σ y_j U_j"""
        k = len(self.v0)
        return tuple(self.v0[i] + sum(y[j] * self.U[j][i] for j in range(len(self.U))) for i in range(k))

    def intersect_congruence(self, A, r, m, reduce=False):
        """{x in coset : A·x ≡ r (mod m)}, or None."""
        d = len(self.U)
        A2 = [sum(A[i] * self.U[j][i] for i in range(len(A))) % m for j in range(d)]
        r2 = (r - _dot(A, self.v0)) % m
        g, W = _unimodular_clear(A2)                 # A2·W = (g,0,..)
        dd = gcd(g, m)
        if r2 % dd:
            return None
        # y1 solves g*y1 ≡ r2 (mod m)  ->  (g/dd) y1 ≡ r2/dd (mod m/dd)
        mm = m // dd
        y1 = (r2 // dd) * pow((g // dd) % mm, -1, mm) % mm if mm > 1 else 0
        # new basis in y-coords: (mm,0,..), (0,1,0..), ...
        ybasis = [[mm] + [0] * (d - 1)] + [[1 if i == j else 0 for i in range(d)] for j in range(1, d)]
        newU = [self.point(_matvec_cols(W, yb))[i] for yb in ybasis for i in ()]  # placeholder
        newU = []
        for yb in ybasis:
            xv = _matvec_cols(W, yb)
            newU.append(tuple(sum(xv[j] * self.U[j][i] for j in range(d)) for i in range(len(self.v0))))
        xpart = _matvec_cols(W, [y1] + [0] * (d - 1))
        newv0 = self.point(xpart)
        if reduce: newU = _lll(newU)
        return CosetK(newv0, newU)

    def intersect_equation(self, A, t, reduce=False):
        """{x in coset : A·x = t} exactly; rank drops by one; None if empty."""
        d = len(self.U)
        A2 = [sum(A[i] * self.U[j][i] for i in range(len(A))) for j in range(d)]
        t2 = t - _dot(A, self.v0)
        g, W = _unimodular_clear(A2)
        if g == 0:
            return self if t2 == 0 else None
        if t2 % g:
            return None
        y1 = t2 // g
        newv0 = self.point(_matvec_cols(W, [y1] + [0] * (d - 1)))
        newU = []
        for j in range(1, d):
            yb = [1 if i == j else 0 for i in range(d)]
            xv = _matvec_cols(W, yb)
            newU.append(tuple(sum(xv[jj] * self.U[jj][i] for jj in range(d)) for i in range(len(self.v0))))
        if len(newU) > 1:
            if reduce: newU = _lll(newU)
        return CosetK(newv0, newU)

    def contains(self, x):
        """solve x - v0 = Σ y_j U_j over Z (small dim: exact rational solve + integrality)."""
        from fractions import Fraction
        d = len(self.U); k = len(self.v0)
        rhs = [x[i] - self.v0[i] for i in range(k)]
        # least squares via Gram system (basis independent)
        G = [[Fraction(_dot(self.U[i], self.U[j])) for j in range(d)] for i in range(d)]
        b = [Fraction(_dot(self.U[i], rhs)) for i in range(d)]
        # Gaussian elimination
        M = [G[i] + [b[i]] for i in range(d)]
        for c in range(d):
            piv = next(i for i in range(c, d) if M[i][c] != 0)
            M[c], M[piv] = M[piv], M[c]
            M[c] = [v / M[c][c] for v in M[c]]
            for i in range(d):
                if i != c and M[i][c] != 0:
                    M[i] = [vi - M[i][c] * vc for vi, vc in zip(M[i], M[c])]
        y = [M[i][d] for i in range(d)]
        if any(v.denominator != 1 for v in y):
            return False
        return self.point([int(v) for v in y]) == tuple(x)


def _selftest():
    import random, itertools
    rng = random.Random(7)
    for _ in range(200):
        k = 3
        cs = [([rng.randrange(0, 40) for _ in range(k)], rng.randrange(0, 40), rng.randrange(2, 40))
              for _ in range(rng.randrange(1, 4))]
        co = CosetK.full(k)
        for A, r, m in cs:
            co = co.intersect_congruence(A, r, m)
            if co is None: break
        M = 1
        for A, r, m in cs: M = M * m // gcd(M, m)
        if M > 60: continue
        brute = {x for x in itertools.product(range(M), repeat=k) if all((_dot(A, x) - r) % m == 0 for A, r, m in cs)}
        if co is None:
            assert not brute
        else:
            got = {x for x in itertools.product(range(M), repeat=k) if co.contains(x)}
            assert got == brute, (cs, len(got), len(brute))
            # plane intersection a = a0
            a0 = rng.randrange(0, M)
            co2 = co.intersect_equation([1, 0, 0], a0)
            exp = {x for x in brute if x[0] == a0}
            # points of co2 inside the box, modulo M in b,c: compare membership
            if co2 is None:
                assert not exp
            else:
                got2 = {x for x in itertools.product(range(M), repeat=k) if x[0] == a0 and co2.contains(x)}
                assert got2 == exp, (cs, a0, got2, exp)
    print("lattice3 selftest ok")


if __name__ == "__main__":
    _selftest()
