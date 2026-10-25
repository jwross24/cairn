#!/usr/bin/env python3
"""
peranchor.py — certify the sandwich lower bound over ALL copy choices x at once (no enumeration of x).

Setting (SANDWICH.md, DEEPCUT.md).  Pattern (nu, {(d_j, e_j)}) with anchor y = 2^a 3^b 7^c, coset
C = (b, c) + Lambda_96.  Every non-anchor candidate y' has >= 10^27 digits, so its lowest m digits are
   y' ≡ R_m + sum_j (d_j - 1) 10^{e_j + 96 t_j}   (mod 10^m),  t_j copies (distinct positions),
and 2^a 3^b 7^c ≡ that (mod 10^m) cuts C to a coset of Lambda^{(m)} := {Δ ∈ Lambda_96 : 3^Δb 7^Δc ≡ 1 mod 5^m, 2^{m-a}}.

Three tools:
  A. extend_exact : the coset of points with 2^a 3^b 7^c ≡ Y (mod 10^{m2}) inside a coset whose units agree
     mod 10^m, by the exact linearisation of Codex T1 (h = m2 - m <= m - a), falling back to descent.cut_coset.
  B. dp_bound     : digit-ordered branch and bound over the digit words (positions in increasing order, branch
     at class positions, prune a node when the exact nearest point of its coset already has norm^2 >= N2).
     With N2 = inf it is an exact enumeration of the union's minimum at a given precision.
  C. cvp_block    : ONE box-constrained CVP certifying min ||(b,c)|| over the union of all digit words in a
     linear range [s, s+h) (h <= s - a) of a coset whose units agree mod 10^s, by LLL + exact Fincke–Pohst on
     the lifted lattice {(z, x) in Z^{2+f} : A z - W x ≡ β (mod 10^h)} with the Boolean box (and the
     "at most one copy per digit / one digit per position" constraints) encoded as an exact quadratic penalty.
  D. dual_bound   : the sub-lattice relaxation Lambda* = Lambda^{(s)} + sum Z v_j (idea 3) — one nearest point.
"""
import sys, math, time, itertools
from collections import Counter, defaultdict
from fractions import Fraction
sys.path.insert(0, '/home/claude/tier0')
import gmpy2
from gmpy2 import mpz, mpq
from lattice import Coset, _kernel_and_particular, _reduce
from descent import cut_coset, v2
import os as _os; _cwd=_os.getcwd(); _os.chdir("/home/claude/tier0")
import deepcut as DC
_os.chdir(_cwd)
from baker_chain import baker_upper_bound

LOG10_3 = math.log10(3)

# ----------------------------------------------------------------------------------------------------------
# A. exact coset extension
# ----------------------------------------------------------------------------------------------------------

def unit_at(co, a, mod):
    """2^a 3^b 7^c mod `mod` at the coset's base point (b, c) = co.v0."""
    return int(gmpy2.powmod(2, a, mod) * gmpy2.powmod(3, co.v0[0], mod) * gmpy2.powmod(7, co.v0[1], mod) % mod)

def gen_unit(u, mod):
    """3^u1 7^u2 mod `mod` (negative exponents = modular inverses)."""
    return int(gmpy2.powmod(3, u[0], mod) * gmpy2.powmod(7, u[1], mod) % mod)

def v5(x):
    n = 0
    while x and x % 5 == 0: x //= 5; n += 1
    return n

def intersect_z(co, Au, Av, r, mod):
    """points v0 + z1 u1 + z2 u2 of the coset with Au z1 + Av z2 ≡ r (mod mod); None if empty."""
    sol = _kernel_and_particular(Au % mod, Av % mod, mod, r % mod)
    if sol is None: return None
    x0, y0, k1, k2 = sol
    u1, u2, v0 = co.u1, co.u2, co.v0
    nv0 = (v0[0] + x0 * u1[0] + y0 * u2[0], v0[1] + x0 * u1[1] + y0 * u2[1])
    nu1 = (k1[0] * u1[0] + k1[1] * u2[0], k1[0] * u1[1] + k1[1] * u2[1])
    nu2 = (k2[0] * u1[0] + k2[1] * u2[0], k2[0] * u1[1] + k2[1] * u2[1])
    nu1, nu2 = _reduce(nu1, nu2)
    return Coset(nv0, nu1, nu2)

def linear_coeffs(co, a, m, h):
    """Codex T1: for a coset whose units agree mod 10^m (lattice ⊆ Lambda^{(m)}) and h <= m - a, the units at
    v0 + z1 u1 + z2 u2 are ≡ y0 + z1 y0 t_u + z2 y0 t_v (mod 10^{m+h}).  Returns (y0 mod 10^{m+h}, Au, Av) with
    Au = y0 t_u / 10^m mod 10^h, Av likewise.  Asserts the valuation hypotheses v5(t) >= m, v2(t) >= m - a."""
    assert 1 <= h <= m - a, (h, m, a)
    mod = 10 ** (m + h)
    y0 = unit_at(co, a, mod)
    coeffs = []
    for u in (co.u1, co.u2):
        t = (gen_unit(u, mod) - 1) % mod
        if t:
            assert v5(t) >= m and v2(t) >= m - a, "units of the coset do not agree mod 10^m"
        coeffs.append(((y0 * t) % mod) // 10 ** m % 10 ** h)
    return y0, coeffs[0], coeffs[1]

def extend_exact(co, a, m, Y, m2, force_cut=False):
    """Sub-coset of `co` (units agree mod 10^m, m >= 0) with 2^a 3^b 7^c ≡ Y (mod 10^{m2}), m2 > m.
    Uses the linearisation in steps of h <= m - a; cut_coset (Pohlig–Hellman) when m - a < 1 or force_cut."""
    if force_cut or m - a < 1 or m < 3:
        return cut_coset(co, a, Y % 10 ** m2, m2)
    while m < m2:
        h = min(m2 - m, m - a)
        y0, Au, Av = linear_coeffs(co, a, m, h)
        if (Y - y0) % 10 ** m: return None          # cannot happen when the node is consistent
        beta = ((Y - y0) % 10 ** (m + h)) // 10 ** m
        co = intersect_z(co, Au, Av, beta, 10 ** h)
        if co is None: return None
        m += h
    return co

def nearest_norm2(co):
    return DC.nearest_norm(co)[0]

def log10_digits(nn):
    """log10 of the certified digit bound: every point has hypot >= sqrt(nn) ⇒ max(b,c) >= sqrt(nn/2) ⇒
    y has >= max(b,c) log10 3 digits."""
    nn = int(nn)
    return 0.5 * (len(str(nn)) - 1 + math.log10(int(str(nn)[:17]) / 10 ** 16)) - 0.5 * math.log10(2) + math.log10(LOG10_3)

def N2_for_digits(log10_G):
    """norm^2 threshold: hypot(b,c) >= sqrt(N2) certifies > G digits  ⇔  log10 bound > log10 G."""
    # need 0.5 log10 N2 - 0.5 log10 2 + log10 log10 3 > log10 G
    e = 2 * (log10_G + 0.5 * math.log10(2) - math.log10(LOG10_3)) + 0.02      # +0.01 digits of slack for the
    ie = int(math.floor(e)); fr = e - ie                                         # 2-decimal log10 G of the table
    return int(math.ceil(10 ** fr * 10 ** 6)) * 10 ** (ie - 6)

# ----------------------------------------------------------------------------------------------------------
# B. digit-ordered branch and bound
# ----------------------------------------------------------------------------------------------------------

class DPStats:
    def __init__(self): self.nodes = 0; self.cuts = 0; self.pruned = 0; self.dead = 0; self.leaves = 0; self.t0 = time.time()
    def __repr__(self): return f"nodes={self.nodes} cuts={self.cuts} pruned={self.pruned} dead={self.dead} leaves={self.leaves} wall={time.time()-self.t0:.1f}s"

def dp_bound(co0, a, De, maxpos, N2=None, first_lin=12, record_level=None, stats=None):
    """Exact min over the union of all digit words on positions [0, maxpos) of the pattern digits De = [(d, e)],
    each digit used at most once, at positions ≡ e (mod 96), at most one per position, all others 1;
    pruning nodes whose coset's nearest norm^2 >= N2 (N2 = None: no pruning = exact enumeration).
    Returns (min_norm2 or None, stats, level_nodes): None means every leaf was pruned or dead (certified
    min >= N2); level_nodes = surviving (coset, Yfix, remaining) at precision record_level (CVP stage input)."""
    st = stats or DPStats()
    level_nodes = []
    best = [None]
    classes = {e % 96 for _, e in De}
    inf = N2 is None

    def next_branch(m):
        p = m
        while p < maxpos and p % 96 not in classes: p += 1
        return p

    def cut(co, mc, Y, m2):
        """co agrees with Y mod 10^mc; return the sub-coset agreeing mod 10^m2 (m2 >= 3)."""
        st.cuts += 1
        if mc >= first_lin and mc - a >= 1:
            return extend_exact(co, a, mc, Y, m2)
        if m2 > a and v2(Y % 10 ** m2) != a: return None
        return cut_coset(co, a, Y, m2)

    def rec(co, mc, mf, Y, remaining):
        # co: coset cut to precision mc (units ≡ Y mod 10^mc); Y has mf >= mc digits fixed
        st.nodes += 1
        if mf >= 3 and mf > mc:
            co = cut(co, mc, Y, mf)
            if co is None: st.dead += 1; return
            mc = mf
            if not inf:
                nn = nearest_norm2(co)
                if nn >= N2: st.pruned += 1; return
        if record_level is not None and mc == record_level:
            level_nodes.append((co, Y, tuple(remaining)))
        if mf >= maxpos:
            st.leaves += 1
            nn = nearest_norm2(co)
            if best[0] is None or nn < best[0]: best[0] = nn
            return
        p = next_branch(mf)
        if record_level is not None and mf < record_level <= p:
            rec(co, mc, record_level, Y + (10 ** record_level - 10 ** mf) // 9, remaining); return
        if p >= maxpos:
            rec(co, mc, maxpos, Y + (10 ** maxpos - 10 ** mf) // 9, remaining); return
        opts = [None]; seen = set()
        for j in remaining:
            if De[j][1] % 96 == p % 96 and De[j][0] not in seen:
                seen.add(De[j][0]); opts.append(j)
        for j in opts:
            Y2 = Y + (10 ** (p + 1) - 10 ** mf) // 9 + ((De[j][0] - 1) * 10 ** p if j is not None else 0)
            rec(co, mc, p + 1, Y2, [i for i in remaining if i != j])

    rec(co0, 0, 0, 0, list(range(len(De))))
    return best[0], st, level_nodes


def dp_bound_from(co, a, s, Y, De_rem, maxpos, N2=None, stats=None):
    """dp_bound started at a node: coset `co` whose units ≡ Y (mod 10^s), remaining digits De_rem, positions
    [s, maxpos) (same branching/pruning rules)."""
    st = stats or DPStats()
    best = [None]
    classes = {e % 96 for _, e in De_rem}
    inf = N2 is None
    def next_branch(m):
        p = m
        while p < maxpos and p % 96 not in classes: p += 1
        return p
    def rec(co, mc, mf, Y, remaining):
        st.nodes += 1
        if mf > mc:
            st.cuts += 1
            co = extend_exact(co, a, mc, Y, mf)
            if co is None: st.dead += 1; return
            mc = mf
            if not inf:
                nn = nearest_norm2(co)
                if nn >= N2: st.pruned += 1; return
        if mf >= maxpos:
            st.leaves += 1
            nn = nearest_norm2(co)
            if best[0] is None or nn < best[0]: best[0] = nn
            return
        p = next_branch(mf)
        if p >= maxpos:
            rec(co, mc, maxpos, Y + (10 ** maxpos - 10 ** mf) // 9, remaining); return
        opts = [None]; seen = set()
        for j in remaining:
            if De_rem[j][1] % 96 == p % 96 and De_rem[j][0] not in seen:
                seen.add(De_rem[j][0]); opts.append(j)
        for j in opts:
            Y2 = Y + (10 ** (p + 1) - 10 ** mf) // 9 + ((De_rem[j][0] - 1) * 10 ** p if j is not None else 0)
            rec(co, mc, p + 1, Y2, [i for i in remaining if i != j])
    rec(co, s, s, Y % 10 ** s, list(range(len(De_rem))))
    return best[0], st, None

# ----------------------------------------------------------------------------------------------------------
# D. dual (sub-lattice) bound, idea 3
# ----------------------------------------------------------------------------------------------------------

def dual_bound(co, a, m, De_remaining, h):
    """Lambda* = Lambda^{(m)} + sum_j Z v_j over the bits in [m, m+h): the union of the sub-cosets lies in the
    single coset {z : A z ≡ β (mod g)}, g = gcd(10^h, all w_j).  Returns (nearest norm^2, log10 g)."""
    h = min(h, m - a)
    y0, Au, Av = linear_coeffs(co, a, m, h)
    g = 10 ** h
    for (d, e) in De_remaining:
        for p in range(m, m + h):
            if p % 96 == e % 96:
                g = math.gcd(g, (d - 1) * 10 ** (p - m))
    T = y0 % 10 ** m + (10 ** (m + h) - 10 ** m) // 9
    beta = ((T - y0) % 10 ** (m + h)) // 10 ** m
    if g == 1: return nearest_norm2(co), 0.0
    co2 = intersect_z(co, Au, Av, beta % g, g)
    if co2 is None: return None, math.log10(g)
    return nearest_norm2(co2), math.log10(g)

# ----------------------------------------------------------------------------------------------------------
# C. box-constrained CVP over a linear range  (idea 1)
# ----------------------------------------------------------------------------------------------------------

def kernel_basis_and_particular(coeffs, M, r):
    """Lattice {v in Z^d : sum c_i v_i ≡ 0 (mod M)} (basis, rows) and a particular v with sum c_i v_i ≡ r,
    by unimodular column operations on [c_1 .. c_d, M]."""
    d = len(coeffs)
    c = [int(x) for x in coeffs] + [int(M)]
    n = d + 1
    U = [[1 if i == j else 0 for j in range(n)] for i in range(n)]      # columns of U are vectors in Z^n
    def colcomb(i, j, a, b, cc, dd):
        # (col_i, col_j) <- (a col_i + b col_j, cc col_i + dd col_j)
        for row in U:
            x, y = row[i], row[j]
            row[i], row[j] = a * x + b * y, cc * x + dd * y
        c[i], c[j] = a * c[i] + b * c[j], cc * c[i] + dd * c[j]
    for i in range(1, n):
        if c[i] == 0: continue
        if c[0] == 0:
            colcomb(0, i, 0, 1, 1, 0); continue
        g, s, t = _egcd_full(c[0], c[i])
        colcomb(0, i, s, t, -c[i] // g, c[0] // g)
    g = c[0]
    assert all(x == 0 for x in c[1:])
    if r % g: return None, None
    basis = [[U[row][col] for row in range(d)] for col in range(1, n)]
    part = [U[row][0] * (r // g) for row in range(d)]
    assert (sum(ci * vi for ci, vi in zip(coeffs, part)) - r) % M == 0
    return basis, part

def _egcd_full(a, b):
    x0, y0, x1, y1 = 1, 0, 0, 1
    while b:
        q, a, b = a // b, b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    if a < 0: a, x0, y0 = -a, -x0, -y0
    return a, x0, y0

def dot(u, v): return sum(a * b for a, b in zip(u, v))

def lll_integral(B, delta_num=99, delta_den=100, carry=None):
    """Cohen Alg. 2.6.7 (integral LLL) on integer row vectors B (list of lists); returns the reduced basis.
    `carry`: optional parallel rows (e.g. the vectors' coordinates in another basis) transformed alongside."""
    B = [[mpz(x) for x in v] for v in B]
    n = len(B)
    C = [list(v) for v in carry] if carry is not None else None
    lam = [[mpz(0)] * n for _ in range(n)]
    d = [mpz(0)] * (n + 1); d[0] = mpz(1)
    d[1] = dot(B[0], B[0])
    def RED(k, l):
        if 2 * abs(lam[k][l]) > d[l + 1]:
            q = (2 * lam[k][l] + d[l + 1]) // (2 * d[l + 1])
            B[k] = [x - q * y for x, y in zip(B[k], B[l])]
            if C is not None: C[k] = [x - q * y for x, y in zip(C[k], C[l])]
            lam[k][l] -= q * d[l + 1]
            for i in range(l): lam[k][i] -= q * lam[l][i]
    def SWAP(k, kmax):
        B[k], B[k - 1] = B[k - 1], B[k]
        if C is not None: C[k], C[k - 1] = C[k - 1], C[k]
        for j in range(k - 1): lam[k][j], lam[k - 1][j] = lam[k - 1][j], lam[k][j]
        L = lam[k][k - 1]
        Bv = (d[k - 1] * d[k + 1] + L * L) // d[k]
        for i in range(k + 1, kmax + 1):
            t = lam[i][k]
            lam[i][k] = (d[k + 1] * lam[i][k - 1] - L * t) // d[k]
            lam[i][k - 1] = (Bv * t + L * lam[i][k]) // d[k + 1]
        d[k] = Bv
    k = 1; kmax = 0
    while k < n:
        if k > kmax:
            kmax = k
            for j in range(k + 1):
                u = dot(B[k], B[j])
                for i in range(j): u = (d[i + 1] * u - lam[k][i] * lam[j][i]) // d[i]
                if j < k: lam[k][j] = u
                else:
                    d[k + 1] = u
                    assert u > 0, "dependent vectors"
        RED(k, k - 1)
        if delta_den * d[k + 1] * d[k - 1] < delta_num * d[k] * d[k] - delta_den * lam[k][k - 1] ** 2:
            SWAP(k, kmax); k = max(1, k - 1)
        else:
            for l in range(k - 2, -1, -1): RED(k, l)
            k += 1
    out = [[int(x) for x in v] for v in B]
    return (out, C) if carry is not None else out

def gram_schmidt_q(B):
    """exact GS: returns (mu, Bstar_norm2, Bstar) with mpq entries."""
    n = len(B); m = len(B[0])
    Bq = [[mpq(x) for x in v] for v in B]
    Bs = []; mu = [[mpq(0)] * n for _ in range(n)]; Bn = []
    for i in range(n):
        v = list(Bq[i])
        for j in range(i):
            mu[i][j] = sum(a * b for a, b in zip(Bq[i], Bs[j])) / Bn[j]
            v = [a - mu[i][j] * b for a, b in zip(v, Bs[j])]
        Bs.append(v); Bn.append(sum(a * a for a in v))
    return mu, Bn, Bs

def cvp_enumerate(B, target, R2, shrink=False, max_nodes=10 ** 7):
    """Exact Schnorr–Euchner enumeration of lattice points sum c_i B_i within squared distance R2 of target.
    Returns (best_dist2 or None, coeffs, nodes, complete).  shrink=True: closest-vector mode (radius shrinks to
    the best found); shrink=False: fixed radius (certification: None ⇒ no lattice point within R2)."""
    n = len(B)
    mu, Bn, Bs = gram_schmidt_q(B)
    tq = [mpq(x) for x in target]
    tau = [sum(a * b for a, b in zip(tq, Bs[j])) / Bn[j] for j in range(n)]
    tperp2 = sum(a * a for a in tq) - sum(tau[j] * tau[j] * Bn[j] for j in range(n))   # ||t_perp||^2 >= 0
    assert tperp2 >= 0
    R2 = mpq(R2) - tperp2                      # enumerate the in-span distance
    if R2 < 0: return None, None, 0, True
    c = [0] * n; pd = [mpq(0)] * (n + 1)
    best = [None, None]; nodes = 0
    def center(i):
        s = tau[i]
        for j in range(i + 1, n): s -= c[j] * mu[j][i]
        return s
    def candidates(i, ci, rem2):
        if rem2 < 0: return []
        w = int(gmpy2.isqrt(int(rem2 / Bn[i]))) + 1
        fl = ci.numerator // ci.denominator
        xs = [x for x in range(fl - w, fl + w + 2) if (x - ci) * (x - ci) * Bn[i] <= rem2]
        xs.sort(key=lambda x: abs(x - ci))
        return xs
    ci = center(n - 1)
    stack = [(ci, candidates(n - 1, ci, R2))]
    while stack:
        i = n - len(stack)
        ci, cands = stack[-1]
        if not cands: stack.pop(); continue
        x = cands.pop(0); nodes += 1
        if nodes > max_nodes: return best[0], best[1], nodes, False
        d2 = (x - ci) * (x - ci) * Bn[i]
        if pd[i + 1] + d2 > R2: cands.clear(); continue
        c[i] = x; pd[i] = pd[i + 1] + d2
        if i == 0:
            if best[0] is None or pd[0] < best[0]:
                best[0] = pd[0]; best[1] = list(c)
                if shrink: R2 = pd[0]
            continue
        cj = center(i - 1)
        stack.append((cj, candidates(i - 1, cj, R2 - pd[i])))
    return (best[0] + tperp2 if best[0] is not None else None), best[1], nodes, True

def cvp_block(co, a, s, Yfix, h, De_rem, N2, exact_groups=True, verbose=False, shrink=False):
    """One box-constrained CVP certifying min ||(b,c)||^2 over the union of ALL digit words on positions
    [s, s+h) (h <= s - a) inside the coset `co` (units ≡ Yfix mod 10^s), remaining digits De_rem = [(d, e)].
    Returns dict(min2=..., certified=bool, nodes, dim, f, G, lll_time, enum_time, point=(b,c) or None)."""
    t0 = time.time()
    h = min(h, s - a)
    y0, Au, Av = linear_coeffs(co, a, s, h)
    assert (y0 - Yfix) % 10 ** s == 0
    T = Yfix % 10 ** s + (10 ** (s + h) - 10 ** s) // 9
    beta = ((T - y0) % 10 ** (s + h)) // 10 ** s
    # Boolean variables: one per (digit index, position in [s, s+h) of its class)
    vars_ = []
    for j, (d, e) in enumerate(De_rem):
        for p in range(s, s + h):
            if p % 96 == e % 96: vars_.append((j, p, (d - 1) * 10 ** (p - s)))
    f = len(vars_)
    groups = []
    if exact_groups:
        byj = defaultdict(list); byp = defaultdict(list)
        for idx, (j, p, w) in enumerate(vars_): byj[j].append(idx); byp[p].append(idx)
        groups = [g for g in list(byj.values()) + list(byp.values()) if len(g) >= 2]
    G = len(groups)
    coeffs = [Au, Av] + [-w for (_, _, w) in vars_]
    M = 10 ** h
    basis, part = kernel_basis_and_particular(coeffs, M, beta)
    if basis is None:
        return dict(min2=None, certified=True, nodes=0, dim=2 + f, f=f, G=G, empty=True)
    lam = gmpy2.isqrt(N2) + 1
    u1, u2, v0 = co.u1, co.u2, co.v0
    def embed(v):
        z1, z2 = v[0], v[1]; x = v[2:]
        out = [2 * (z1 * u1[0] + z2 * u2[0]), 2 * (z1 * u1[1] + z2 * u2[1])]
        out += [2 * lam * xj for xj in x]
        out += [2 * lam * sum(x[i] for i in g) for g in groups]
        return out
    EB = [embed(v) for v in basis]
    Ep = embed(part)
    target = [-2 * v0[0] - Ep[0], -2 * v0[1] - Ep[1]] + [lam - Ep[2 + i] for i in range(f + G)]
    R2 = 4 * N2 + lam * lam * (f + G)
    t1 = time.time()
    EB, basis = lll_integral(EB, carry=basis)
    assert all(embed(v) == w for v, w in zip(basis, EB)), "LLL carry inconsistent"   # same lattice, exactly
    t2 = time.time()
    dist2, coeffs_best, nodes, complete = cvp_enumerate(EB, target, R2, shrink=shrink)
    t3 = time.time()
    res = dict(min2=None, certified=complete, nodes=nodes, dim=2 + f, f=f, G=G, lll_time=t2 - t1, enum_time=t3 - t2,
               setup_time=t1 - t0, point=None, empty=False)
    if dist2 is not None:
        # recover the lattice point: y = sum c_i basis_i in Z^{2+f}; P = part + y
        y = [sum(cc * b[i] for cc, b in zip(coeffs_best, basis)) for i in range(2 + f)]
        P = [p + yy for p, yy in zip(part, y)]
        x = P[2:]
        ok = all(xj in (0, 1) for xj in x) and all(sum(x[i] for i in g) <= 1 for g in groups)
        b = v0[0] + P[0] * u1[0] + P[1] * u2[0]; c = v0[1] + P[0] * u1[1] + P[1] * u2[1]
        n2 = b * b + c * c
        assert ok, "enumeration returned a non-box point (penalty too small?)"
        assert 4 * n2 + lam * lam * (f + G) == dist2
        # end-to-end check: the unit at (b, c) has the claimed digits in [s, s+h)
        Yw = T + sum(w for (j, p, w), xj in zip(vars_, x) if xj) * 10 ** s
        assert unit_at(Coset((b, c), u1, u2), a, 10 ** (s + h)) == Yw % 10 ** (s + h), "found point is not a union point"
        res.update(min2=n2, point=(b, c), word=[(vars_[i][0], vars_[i][1]) for i in range(f) if x[i]])
    return res
