"""2-D integer lattice cosets  v0 + Z*u1 + Z*u2  and intersection with a linear congruence.

A coset represents the set of (b, c) in Z^2 satisfying every congruence imposed so far.
intersect(coset, A, B, r, m) returns the coset of solutions of  A*b + B*c ≡ r (mod m)
inside the given coset, or None if there is no solution.
"""
from math import gcd


def _egcd(a, b):
    """return (g, x, y) with a*x + b*y = g = gcd(a,b), g >= 0"""
    x0, y0, x1, y1 = 1, 0, 0, 1
    while b:
        q, a, b = a // b, b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    if a < 0:
        a, x0, y0 = -a, -x0, -y0
    return a, x0, y0


def _kernel_and_particular(A, B, m, r):
    """Solutions (x,y) in Z^2 of A x + B y ≡ r (mod m).
    Returns (x0, y0, k1, k2) with the solution set = (x0,y0) + Z k1 + Z k2, or None."""
    g1, u, v = _egcd(A, B)              # u A + v B = g1
    C = -m
    g2, s, t = _egcd(g1, C)             # s g1 + t C = g2 = gcd(A, B, m)
    if g2 == 0:
        return (0, 0, (1, 0), (0, 1)) if r == 0 else None
    if r % g2:
        return None
    # kernel of [A B C]: (B/g1, -A/g1, 0) and (-u C/g2, -v C/g2, g1/g2)
    if g1 == 0:
        k1, k2 = (1, 0), (0, 1)          # A = B = 0: everything is in the kernel (r ≡ 0 handled)
    else:
        k1 = (B // g1, -A // g1)
        k2 = (-u * C // g2, -v * C // g2)
    # particular: A x0 + B y0 + C t0 = r  with  x0 = u s r/g2, y0 = v s r/g2, t0 = t r/g2
    f = r // g2
    x0, y0 = u * s * f, v * s * f
    assert (A * x0 + B * y0 - r) % m == 0
    return x0, y0, k1, k2


def _reduce(u1, u2):
    """Lagrange-Gauss reduction of a 2-D basis (keeps the lattice, shrinks the entries)."""
    def dot(a, b): return a[0] * b[0] + a[1] * b[1]
    while True:
        if dot(u1, u1) > dot(u2, u2):
            u1, u2 = u2, u1
        n = dot(u1, u1)
        if n == 0:
            return u1, u2
        q = round(dot(u1, u2) / n)
        if q == 0:
            return u1, u2
        u2 = (u2[0] - q * u1[0], u2[1] - q * u1[1])


class Coset:
    __slots__ = ("v0", "u1", "u2")

    def __init__(self, v0=(0, 0), u1=(1, 0), u2=(0, 1)):
        self.v0, self.u1, self.u2 = v0, u1, u2

    def index(self):
        return abs(self.u1[0] * self.u2[1] - self.u1[1] * self.u2[0])

    def contains(self, b, c):
        d = self.u1[0] * self.u2[1] - self.u1[1] * self.u2[0]
        if d == 0:
            raise ValueError("degenerate")
        db, dc = b - self.v0[0], c - self.v0[1]
        x_num = db * self.u2[1] - dc * self.u2[0]
        y_num = -db * self.u1[1] + dc * self.u1[0]
        return x_num % d == 0 and y_num % d == 0

    def intersect(self, A, B, r, m):
        """new coset of points (b,c) in self with A b + B c ≡ r (mod m); None if empty."""
        v0, u1, u2 = self.v0, self.u1, self.u2
        # (b,c) = v0 + x u1 + y u2  ->  A' x + B' y ≡ r' (mod m)
        A2 = (A * u1[0] + B * u1[1]) % m
        B2 = (A * u2[0] + B * u2[1]) % m
        r2 = (r - A * v0[0] - B * v0[1]) % m
        sol = _kernel_and_particular(A2, B2, m, r2)
        if sol is None:
            return None
        x0, y0, k1, k2 = sol
        nv0 = (v0[0] + x0 * u1[0] + y0 * u2[0], v0[1] + x0 * u1[1] + y0 * u2[1])
        nu1 = (k1[0] * u1[0] + k1[1] * u2[0], k1[0] * u1[1] + k1[1] * u2[1])
        nu2 = (k2[0] * u1[0] + k2[1] * u2[0], k2[0] * u1[1] + k2[1] * u2[1])
        nu1, nu2 = _reduce(nu1, nu2)
        return Coset(nv0, nu1, nu2)


def _selftest():
    import random
    rng = random.Random(1)
    for _ in range(300):
        cs = [(rng.randrange(0, 60), rng.randrange(0, 60), rng.randrange(0, 60), rng.randrange(2, 60))
              for _ in range(rng.randrange(1, 4))]
        co = Coset()
        for A, B, r, m in cs:
            co = co.intersect(A, B, r, m)
            if co is None:
                break
        M = 1
        for A, B, r, m in cs:
            M = M * m // gcd(M, m)
        brute = {(b, c) for b in range(M) for c in range(M)
                 if all((A * b + B * c - r) % m == 0 for A, B, r, m in cs)} if M <= 400 else None
        if brute is None:
            continue
        if co is None:
            assert not brute, (cs, brute)
        else:
            got = {(b % M, c % M) for b in range(M) for c in range(M) if co.contains(b, c)}
            assert got == brute, (cs, len(got), len(brute))
    print("lattice selftest ok")


if __name__ == "__main__":
    _selftest()
