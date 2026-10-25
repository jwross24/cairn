#!/usr/bin/env python3
"""
cvp_small.py -- EXACT closest-vector / shortest-coset-vector computation in rank <= 3
(works for any small rank), with exact rational arithmetic throughout.

    exact_nearest(v, U) -> (point, z, norm2)

Given an integer vector v (length m) and a list U = [u_1, ..., u_d] of d <= m linearly independent
integer vectors (entries may have hundreds of digits), returns the point  point = v + sum_i z_i u_i
(z_i integers) of MINIMAL Euclidean norm in the coset v + ZU, together with z and the exact
integer norm2 = |point|^2.  Ties are broken arbitrarily (any minimiser is returned).

Method: exact LLL (Fractions, delta = 3/4) on U, then exact Fincke-Pohst / Schnorr-Euchner
enumeration of all lattice points x in ZU with |x - t|^2 <= R^2, t := -v, starting from the
Babai nearest-plane radius and shrinking R^2 whenever a better point is found.  The enumeration
ranges are computed with exact integer square roots (math.isqrt), so no floating point enters
the decision; the result is the exact minimum (standard correctness of Fincke-Pohst: every
lattice point inside the final radius is visited because the bounds at each level are exact
over-estimates of the admissible interval).

Also provided (for testing / comparison):
    babai_with_neighbours(v, U)  -> (point, z, norm2): Babai nearest plane on the LLL basis plus
                                    the 3^d neighbour search in {-1,0,1}^d  (NOT exact in general).
    lll_exact(U)                 -> (reduced basis, unimodular transform rows) with Fractions.

Self-test: python3 cvp_small.py  (300 random small cosets in dims 1-3 against brute force, plus
large-entry cosets against Babai-with-neighbours).
"""

from fractions import Fraction
from math import isqrt
import random


# ---------------------------------------------------------------------------
# exact linear algebra helpers
# ---------------------------------------------------------------------------

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def vadd(a, b):
    return [x + y for x, y in zip(a, b)]


def vsub(a, b):
    return [x - y for x, y in zip(a, b)]


def vscale(c, a):
    return [c * x for x in a]


def gram_schmidt(B):
    """Exact GSO of the rows of B (Fractions). Returns (Bstar, mu, Bnorm2) with
    B[i] = Bstar[i] + sum_{j<i} mu[i][j] Bstar[j], Bnorm2[i] = |Bstar[i]|^2."""
    d = len(B)
    Bstar, mu, Bn = [], [[Fraction(0)] * d for _ in range(d)], []
    for i in range(d):
        v = [Fraction(x) for x in B[i]]
        for j in range(i):
            mu[i][j] = Fraction(dot(B[i], Bstar[j])) / Bn[j]
            v = vsub(v, vscale(mu[i][j], Bstar[j]))
        Bstar.append(v)
        Bn.append(dot(v, v))
        assert Bn[i] > 0, "basis vectors must be linearly independent"
    return Bstar, mu, Bn


def lll_exact(U, delta=Fraction(3, 4)):
    """Exact LLL (textbook, Fractions). Returns (B, T): B the reduced basis (integer rows) and T the
    integer unimodular matrix with B = T * U (rows)."""
    d = len(U)
    B = [list(map(int, row)) for row in U]
    T = [[1 if i == j else 0 for j in range(d)] for i in range(d)]
    if d == 0:
        return B, T
    Bstar, mu, Bn = gram_schmidt(B)
    k = 1
    while k < d:
        # size-reduce b_k
        for j in range(k - 1, -1, -1):
            q = round_frac(mu[k][j])
            if q != 0:
                B[k] = vsub(B[k], vscale(q, B[j]))
                T[k] = vsub(T[k], vscale(q, T[j]))
                Bstar, mu, Bn = gram_schmidt(B)
        if Bn[k] >= (delta - mu[k][k - 1] ** 2) * Bn[k - 1]:
            k += 1
        else:
            B[k], B[k - 1] = B[k - 1], B[k]
            T[k], T[k - 1] = T[k - 1], T[k]
            Bstar, mu, Bn = gram_schmidt(B)
            k = max(k - 1, 1)
    # verify T * U == B exactly
    for i in range(d):
        row = [0] * len(U[0])
        for j in range(d):
            row = vadd(row, vscale(T[i][j], list(map(int, U[j]))))
        assert row == B[i]
    return B, T


def round_frac(x):
    """Nearest integer to a Fraction (ties toward +inf; any consistent choice is fine)."""
    return (2 * x.numerator + x.denominator) // (2 * x.denominator)


def floor_frac(x):
    return x.numerator // x.denominator


def ceil_frac(x):
    return -((-x.numerator) // x.denominator)


def sqrt_upper(r):
    """A rational >= sqrt(r) for a non-negative Fraction r (exact integer sqrt)."""
    assert r >= 0
    p, q = r.numerator, r.denominator
    # sqrt(p/q) = sqrt(p q)/q <= (isqrt(p q) + 1)/q
    return Fraction(isqrt(p * q) + 1, q)


# ---------------------------------------------------------------------------
# Babai + enumeration
# ---------------------------------------------------------------------------

def _coords(t, Bstar, Bn):
    """tau_i = <t, b_i*> / |b_i*|^2."""
    return [Fraction(dot(t, Bstar[i])) / Bn[i] for i in range(len(Bstar))]


def _babai(tau, mu, d):
    """Nearest-plane coefficients x (integers) for target with GSO coordinates tau."""
    x = [0] * d
    for i in range(d - 1, -1, -1):
        c = tau[i] - sum(x[j] * mu[j][i] for j in range(i + 1, d))
        x[i] = round_frac(c)
    return x


def _lattice_point(x, B):
    m = len(B[0])
    p = [0] * m
    for i, xi in enumerate(x):
        if xi:
            p = vadd(p, vscale(xi, B[i]))
    return p


def closest_vector(t, B):
    """Exact CVP: lattice point of ZB (B integer rows, independent) closest to the integer target t.
    Returns (x, point, dist2) with point = sum x_i B[i]."""
    d = len(B)
    if d == 0:
        return [], [0] * len(t), dot(t, t)
    Bstar, mu, Bn = gram_schmidt(B)
    tau = _coords(t, Bstar, Bn)
    # initial radius from Babai
    xb = _babai(tau, mu, d)
    pb = _lattice_point(xb, B)
    best = [xb, pb, dot(vsub(pb, t), vsub(pb, t))]
    R2 = [Fraction(best[2])]
    x = [0] * d

    def rec(i, partial):
        # choose x_i with (x_i - c_i)^2 Bn[i] + partial <= R2
        c = tau[i] - sum(x[j] * mu[j][i] for j in range(i + 1, d))
        rem = R2[0] - partial
        if rem < 0:
            return
        w = sqrt_upper(rem / Bn[i])
        lo, hi = ceil_frac(c - w), floor_frac(c + w)
        # Schnorr–Euchner order: start at the centre and zig-zag outward
        centre = round_frac(c)
        order = [centre]
        step = 1
        while centre - step >= lo or centre + step <= hi:
            if centre + step <= hi:
                order.append(centre + step)
            if centre - step >= lo:
                order.append(centre - step)
            step += 1
        for xi in order:
            if xi < lo or xi > hi:
                continue
            x[i] = xi
            contrib = (xi - c) ** 2 * Bn[i]
            if partial + contrib > R2[0]:
                continue
            if i == 0:
                p = _lattice_point(x, B)
                dd = dot(vsub(p, t), vsub(p, t))
                if dd < best[2]:
                    best[0], best[1], best[2] = list(x), p, dd
                    R2[0] = Fraction(dd)
            else:
                rec(i - 1, partial + contrib)
        x[i] = 0

    rec(d - 1, Fraction(0))
    return best[0], best[1], best[2]


def exact_nearest(v, U):
    """Minimal-norm point of the coset v + ZU, exactly. Returns (point, z, norm2) with
    point = v + sum z_i U[i], z integers, norm2 = |point|^2 (int)."""
    v = list(map(int, v))
    U = [list(map(int, row)) for row in U]
    d = len(U)
    if d == 0:
        return v, [], dot(v, v)
    assert all(len(row) == len(v) for row in U)
    B, T = lll_exact(U)
    t = [-x for x in v]
    x, p, dist2 = closest_vector(t, B)
    # point = v + p  where p = sum x_i B_i = sum_i x_i sum_j T_ij U_j  =>  z_j = sum_i x_i T_ij
    z = [sum(x[i] * T[i][j] for i in range(d)) for j in range(d)]
    point = vadd(v, p)
    # exact re-verification
    chk = list(v)
    for j in range(d):
        chk = vadd(chk, vscale(z[j], U[j]))
    assert chk == point
    assert dot(point, point) == dist2
    return point, z, dist2


def babai_with_neighbours(v, U):
    """Babai nearest plane on the LLL-reduced basis plus the {-1,0,1}^d neighbour search.
    Returns (point, z, norm2). Not exact in general."""
    import itertools
    v = list(map(int, v))
    U = [list(map(int, row)) for row in U]
    d = len(U)
    B, T = lll_exact(U)
    Bstar, mu, Bn = gram_schmidt(B)
    t = [-x for x in v]
    tau = _coords(t, Bstar, Bn)
    xb = _babai(tau, mu, d)
    best = None
    for delta in itertools.product((-1, 0, 1), repeat=d):
        x = [xb[i] + delta[i] for i in range(d)]
        p = vadd(v, _lattice_point(x, B))
        nn = dot(p, p)
        if best is None or nn < best[2]:
            z = [sum(x[i] * T[i][j] for i in range(d)) for j in range(d)]
            best = (p, z, nn)
    return best


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def _brute_force_min(v, U, box):
    import itertools
    d = len(U)
    best = None
    for z in itertools.product(range(-box, box + 1), repeat=d):
        p = list(v)
        for j in range(d):
            p = vadd(p, vscale(z[j], U[j]))
        nn = dot(p, p)
        if best is None or nn < best:
            best = nn
    return best


def _det_exact(U):
    """Exact determinant of a square integer matrix (Fraction Gaussian elimination)."""
    A = [[Fraction(x) for x in row] for row in U]
    d = len(A)
    det = Fraction(1)
    for c in range(d):
        piv = next((r for r in range(c, d) if A[r][c] != 0), None)
        if piv is None:
            return 0
        if piv != c:
            A[c], A[piv] = A[piv], A[c]
            det = -det
        det *= A[c][c]
        for r in range(c + 1, d):
            f = A[r][c] / A[c][c]
            if f:
                A[r] = [A[r][j] - f * A[c][j] for j in range(d)]
    return det


def _random_unimodular(d, rng, size=3, rounds=6):
    T = [[1 if i == j else 0 for j in range(d)] for i in range(d)]
    for _ in range(rounds):
        i, j = rng.randrange(d), rng.randrange(d)
        if i != j:
            c = rng.randint(-size, size)
            T[i] = vadd(T[i], vscale(c, T[j]))
    return T


def self_test(n_small=300, seed=1, verbose=True):
    import numpy as np
    rng = random.Random(seed)
    # --- Test 1: random small bases, brute force over a provably sufficient box ---------------
    ok = 0
    for trial in range(n_small):
        d = 1 + trial % 3
        m = d + (trial // 3) % 2          # sometimes embed in a higher-dimensional ambient space
        while True:
            U = [[rng.randint(-6, 6) for _ in range(m)] for _ in range(d)]
            v = [rng.randint(-25, 25) for _ in range(m)]
            if np.linalg.matrix_rank(np.array(U, dtype=float)) < d:
                continue
            # box: any z with |v + zU|^2 <= |v|^2 has |zU| <= 2|v|, so |z|_inf <= 2|v|/sigma_min;
            # a 10% margin covers the floating-point sigma_min.  Skip near-singular bases (box > 40).
            smin = np.linalg.svd(np.array(U, dtype=float), compute_uv=False).min()
            box = int(1.1 * 2 * np.sqrt(dot(v, v)) / smin) + 2
            if box <= (40 if d < 3 else 22):
                break
        point, z, n2 = exact_nearest(v, U)
        bf = _brute_force_min(v, U, box)
        assert n2 == bf, (v, U, n2, bf)
        assert n2 <= dot(v, v)
        ok += 1
    if verbose:
        print(f"test 1: {ok}/{n_small} random small cosets (dims 1-3, ambient dims up to 4) agree with brute force")
    # --- Test 2: known answer: lattice = diag(s) Z^d given by a skewed unimodular basis -------
    ok = 0
    for trial in range(200):
        d = 1 + trial % 3
        s = [rng.randint(1, 50) for _ in range(d)]
        Tm = _random_unimodular(d, rng, size=4, rounds=10)
        U = [[Tm[i][j] * s[j] for j in range(d)] for i in range(d)]      # rows: sum_j T_ij s_j e_j
        v = [rng.randint(-10 ** 6, 10 ** 6) for _ in range(d)]
        point, z, n2 = exact_nearest(v, U)
        # exact answer: per coordinate the residue of v_j mod s_j closest to 0
        exp = 0
        for j in range(d):
            r = v[j] % s[j]
            exp += min(r, s[j] - r) ** 2
        assert n2 == exp, (v, U, n2, exp)
        ok += 1
    if verbose:
        print(f"test 2: {ok}/200 skewed-diagonal lattices (dims 1-3) match the closed-form minimum")
    # --- Test 3: large entries vs Babai + neighbours -------------------------------------------
    ok = 0
    for trial in range(30):
        d = 1 + trial % 3
        digits = 300 + 100 * (trial % 5)
        U = [[rng.randint(-10 ** digits, 10 ** digits) for _ in range(d)] for _ in range(d)]
        if _det_exact(U) == 0:
            continue
        v = [rng.randint(-10 ** (digits + 2), 10 ** (digits + 2)) for _ in range(d)]
        point, z, n2 = exact_nearest(v, U)
        pb, zb, nb = babai_with_neighbours(v, U)
        assert n2 <= nb
        ok += 1
    if verbose:
        print(f"test 3: {ok} large-entry cosets (300-700 digit entries, dims 1-3): exact minimum <= Babai+neighbours in all cases")
    # --- Test 4: a case where Babai + neighbours is NOT optimal (sanity that test 3 is non-trivial)
    # Construct a 3-dim example by searching random small lattices.
    found = None
    plain_sub = 0
    for trial in range(3000):
        d = 3
        U = [[rng.randint(-60, 60) for _ in range(d)] for _ in range(d)]
        if _det_exact(U) == 0:
            continue
        v = [rng.randint(-5000, 5000) for _ in range(d)]
        point, z, n2 = exact_nearest(v, U)
        pb, zb, nb = babai_with_neighbours(v, U)
        # plain Babai (no neighbours) for comparison
        B, T = lll_exact(U)
        Bstar, mu, Bn = gram_schmidt(B)
        xb = _babai(_coords([-x for x in v], Bstar, Bn), mu, d)
        pp = vadd(v, _lattice_point(xb, B))
        if dot(pp, pp) > n2:
            plain_sub += 1
        if n2 < nb and found is None:
            found = (v, U, n2, nb)
    if verbose:
        print(f"test 4: in 3000 random 3-dim cosets plain Babai was suboptimal {plain_sub} times;", end=' ')
        if found:
            print(f"Babai+neighbours suboptimal example: v={found[0]}, U={found[1]}, exact {found[2]} < {found[3]}")
        else:
            print("Babai+neighbours was never suboptimal in this sample (so test 3 only shows '<=')")
    return True


if __name__ == '__main__':
    import time
    t0 = time.time()
    self_test()
    print(f"all tests passed in {time.time() - t0:.1f} s")
