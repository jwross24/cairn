#!/usr/bin/env python3
"""
Archimedean (Baker-Davenport / de Weger LLL) height bound for the 4 surviving
level-96 patterns of survivors.json (base 10, S-units y' = 2^a 3^b' 7^c').

For every candidate y' of a pattern (n digits, n = nu mod 96, listed digits
(d_j, e_j) at distinct positions E_j = e_j mod 96, all other digits 1) and every
"top-window case" tau (which listed digits sit in the top 96*D digits, and in
which 96-block), the quantity

    Lambda'_tau = beta_tau + alpha_1 x + alpha_2 y - m

(with (b',c') = (b,c) + x u1 + y u2, n = nu + 96 m) is tiny: |Lambda'_tau| < delta'_tau.
The inhomogeneous LLL lemma (de Weger, Algorithms for Diophantine equations,
CWI Tract 65 (1989), Lemma 3.5) then shows that no (x, y) with |x|,|y| <= X
exists, for X as large as ~ delta'^(-1/2).  The lemma is implemented with exact
integer/rational arithmetic (sympy's integral LLL, whose output is re-verified
to be LLL-reduced with exact Fractions).

Run:  python3 lll_bound.py [D] [--control] [--idx i]     (D = 1, 2, 3; default 1; --idx runs one pattern)
"""
import json, sys, time, itertools
from fractions import Fraction
import mpmath as mp
from sympy.polys.matrices import DomainMatrix
from sympy import ZZ

mp.mp.dps = 800            # working precision (digits); C goes up to ~10^350 for D = 2
PREC_SLACK = Fraction(1, 10**100)   # rigorous allowance for the mpmath error in [C*alpha]
RHO = Fraction(1, 2) + PREC_SLACK   # |[C*alpha] - C*alpha| <= RHO (nearest-integer rounding)
L = 96

LOG2, LOG3, LOG7, LOG10, LOG9 = mp.log(2), mp.log(3), mp.log(7), mp.log(10), mp.log(9)
SCALE = L * LOG10            # we divide the linear form by 96 log 10 so that m has coefficient -1


def nint(x):
    """nearest integer to an mpf, as a Python int"""
    return int(mp.nint(x))


def frac_upper(x, k=400):
    """a rational >= the mpf x (x >= 0), within 10^-k"""
    return Fraction(int(mp.floor(x * mp.mpf(10) ** k)) + 1, 10 ** k)


# ----------------------------------------------------------------------------
# exact lattice tools (dimension 3, but written for any n)
# ----------------------------------------------------------------------------
def gram_schmidt(B):
    """B: list of n integer vectors (the basis). returns (Bstar, mu, norms2) exact."""
    n = len(B)
    Bstar, mu = [], [[Fraction(0)] * n for _ in range(n)]
    norms2 = []
    for i in range(n):
        v = [Fraction(t) for t in B[i]]
        for j in range(i):
            mu[i][j] = sum(Fraction(B[i][k]) * Bstar[j][k] for k in range(len(v))) / norms2[j]
            v = [v[k] - mu[i][j] * Bstar[j][k] for k in range(len(v))]
        Bstar.append(v)
        norms2.append(sum(t * t for t in v))
    return Bstar, mu, norms2


def is_lll_reduced(B, delta=Fraction(3, 4)):
    """exact check: size-reduced (|mu_ij| <= 1/2) and Lovasz with the given delta"""
    Bstar, mu, norms2 = gram_schmidt(B)
    n = len(B)
    for i in range(n):
        for j in range(i):
            if abs(mu[i][j]) > Fraction(1, 2):
                return False
    for i in range(1, n):
        if norms2[i] < (delta - mu[i][i - 1] ** 2) * norms2[i - 1]:
            return False
    return True


def lll(B):
    """LLL-reduce the integer basis B (list of vectors) with sympy, verify exactly."""
    n = len(B)
    M = DomainMatrix([[ZZ(int(t)) for t in v] for v in B], (n, len(B[0])), ZZ)
    R = M.lll(delta=Fraction(3, 4))
    Bred = [[int(t) for t in row] for row in R.to_Matrix().tolist()]
    assert is_lll_reduced(Bred), "sympy output is not LLL-reduced (exact check failed)"
    # same lattice? Bred = T B with T integral and |det T| = 1
    from sympy import Matrix
    T = Matrix(Bred) * Matrix(B).inv()
    assert all(t.is_integer for t in T), "reduced basis is not an integer combination of the input"
    assert abs(T.det()) == 1, "transformation not unimodular"
    return Bred


def det3(B):
    from sympy import Matrix
    return int(Matrix(B).det())


def dist_lower_bound(Bred, w):
    """
    de Weger's Lemma 3.5 (sharpened form, same proof): for an LLL-reduced basis
    c_1..c_n of the full-rank lattice Lat and w = sum s_i c_i (real coordinates),
    let i0 be the largest index with s_i0 not an integer (w not in Lat).  Then
        dist(w, Lat)^2 >= min( ||s_i0||^2 * |c_i0*|^2 ,  min_{i > i0} |c_i*|^2 ),
    where ||.|| is the distance to the nearest integer.  (de Weger's printed form
    follows from |c_i*|^2 >= 2^-(i-1) |c_1|^2 for an LLL-reduced basis with
    delta = 3/4.)  Returns (lower bound on dist^2 as a Fraction, i0, ||s_i0||),
    or (0, None, None) if w lies in the lattice.
    """
    from sympy import Matrix, Rational
    n = len(Bred)
    # coordinates s with  w = sum_i s_i c_i   (c_i are the rows of Bred)
    A = Matrix(Bred).T                      # columns = c_i
    s_vec = A.LUsolve(Matrix(w))
    s = [Fraction(int(t.p), int(t.q)) for t in s_vec]
    i0 = None
    for i in range(n - 1, -1, -1):
        if s[i].denominator != 1:
            i0 = i
            break
    if i0 is None:
        return Fraction(0), None, None
    Bstar, mu, norms2 = gram_schmidt(Bred)
    fr = s[i0] - round(s[i0])
    dist_nint2 = fr * fr                     # ||s_i0||^2
    lb = dist_nint2 * norms2[i0]
    for i in range(i0 + 1, n):
        lb = min(lb, norms2[i])
    # classical de Weger bound, for the record
    classical = dist_nint2 * norms2[0] / 2 ** (n - 1)
    assert lb >= classical
    return lb, i0, fr


def cvp_exact(Bred, w):
    """
    exact closest-vector distance in a rank-3 (any rank) lattice given an LLL-reduced
    basis (rows of Bred), by Schnorr-Euchner enumeration in exact rational arithmetic.
    Returns (dist^2 as a Fraction, coefficient vector t of the closest lattice point).
    """
    from sympy import Matrix
    n = len(Bred)
    Bstar, mu, norms2 = gram_schmidt(Bred)
    s_vec = Matrix(Bred).T.LUsolve(Matrix(w))
    s = [Fraction(int(t.p), int(t.q)) for t in s_vec]
    def vec(t):
        return [sum(t[i] * Bred[i][k] for i in range(n)) - w[k] for k in range(len(w))]
    def norm2(v):
        return sum(Fraction(x) * x for x in v)
    # Babai nearest plane as the starting radius
    t = [0] * n
    for i in range(n - 1, -1, -1):
        ci = s[i] - sum(mu[j][i] * (t[j] - s[j]) for j in range(i + 1, n))
        t[i] = round(ci)
    best2 = norm2(vec(t))
    best_t = list(t)
    def width(rem, nn):      # a safe upper bound for sqrt(rem/nn)
        with mp.workdps(60):
            return mp.sqrt(mp.mpf(rem.numerator) / rem.denominator / (mp.mpf(nn.numerator) / nn.denominator)) * (1 + mp.mpf(10) ** -30) + mp.mpf(10) ** -30
    # enumerate (dimension-generic recursion)
    def rec(i, t, rem):
        nonlocal best2, best_t
        # GS coordinate on c_i* of sum_j (t_j - s_j) c_j is  (t_i - s_i) + sum_{j>i} mu[j][i] (t_j - s_j)
        shift = sum(mu[j][i] * (t[j] - s[j]) for j in range(i + 1, n))
        center = s[i] - shift
        wd = width(rem, norms2[i])
        lo = int(mp.floor(mp.mpf(center.numerator) / center.denominator - wd))
        hi = int(mp.ceil(mp.mpf(center.numerator) / center.denominator + wd))
        for ti in range(lo, hi + 1):
            d = ti - center
            used = d * d * norms2[i]
            if used > rem:
                continue
            t[i] = ti
            if i == 0:
                v2 = norm2(vec(t))
                if v2 < best2:
                    best2, best_t = v2, list(t)
            else:
                rec(i - 1, t, rem - used)
        t[i] = 0
    rec(n - 1, [0] * n, best2)
    # consistency: the GS decomposition gives the same value
    assert norm2(vec(best_t)) == best2
    return best2, best_t


def reduce_once(alpha1, alpha2, beta, delta_p, X1, X2, C):
    """
    One application of the lemma.  Linear form  Lambda' = beta + alpha1 x + alpha2 y - m,
    hypotheses |x| <= X1, |y| <= X2, |Lambda'| < delta_p (a Fraction upper bound).
    Lattice (rows = basis vectors): (1, 0, [C a1]), (0, 1, [C a2]), (0, 0, C);  w = (0, 0, -[C beta]).
    Returns (success: bool, info dict).
    """
    a1 = nint(C * alpha1)
    a2 = nint(C * alpha2)
    b0 = nint(C * beta)
    B = [[1, 0, a1], [0, 1, a2], [0, 0, C]]
    w = [0, 0, -b0]
    Bred = lll(B)
    lb2, i0, fr = dist_lower_bound(Bred, w)        # de Weger's bound (for the record / cross-check)
    d2, t = cvp_exact(Bred, w)                       # exact distance
    assert d2 >= lb2, "exact CVP distance below de Weger's lower bound: bug"
    Q = Fraction(X1) ** 2 + Fraction(X2) ** 2 + (Fraction(C) * delta_p + (X1 + X2 + 1) * RHO) ** 2
    return d2 > Q, dict(lb2=lb2, d2=d2, Q=Q, i0=i0, fr=fr, C=C, closest=t, deweger_ok=lb2 > Q)


def reduce_search(alpha1, alpha2, beta, delta_p, X):
    """try a few C's for the given X; success if any works"""
    X = int(X)
    for kappa in (10, 5, 20, 3, 7, 14):
        C = (kappa * X) ** 3
        ok, info = reduce_once(alpha1, alpha2, beta, delta_p, X, X, C)
        if ok:
            return True, info
    return False, info


# ----------------------------------------------------------------------------
# pattern -> cases
# ----------------------------------------------------------------------------
def residues(pat):
    nu = pat["nu"]
    return [((d, e), (nu - 1 - e) % L) for (d, e) in pat["digits_positions"]]


def enumerate_cases(pat, D):
    """
    all assignments t_j in {0..D-1} u {'>=D'} with (r_j, t_j) distinct among the
    placed digits (positions E_j must be distinct).  Yields (tau, theta, eps_plus)
    with theta = sum_{placed} 9 (d_j - 1) 10^{-1 - r_j - 96 t_j}  (exact Fraction)
    and eps_plus = sum_{unplaced} 9 (d_j - 1) 10^{-1 - r_j - 96 D}.
    """
    dig = residues(pat)
    k = len(dig)
    for tau in itertools.product(list(range(D)) + [None], repeat=k):
        placed = [(r, t) for ((d, e), r), t in zip(dig, tau) if t is not None]
        if len(set(placed)) != len(placed):
            continue                      # two digits in the same position
        theta, eps = Fraction(0), Fraction(0)
        for ((d, e), r), t in zip(dig, tau):
            if t is not None:
                theta += Fraction(9 * (d - 1), 10 ** (1 + r + L * t))
            else:
                eps += Fraction(9 * (d - 1), 10 ** (1 + r + L * D))
        yield tau, theta, eps


def pattern_constants(pat):
    a, b, c, nu = pat["a"], pat["b"], pat["c"], pat["nu"]
    (u11, u12), (u21, u22) = pat["Lam96"]
    L0 = a * LOG2 + b * LOG3 + c * LOG7 + LOG9 - nu * LOG10
    alpha1 = (u11 * LOG3 + u12 * LOG7) / SCALE
    alpha2 = (u21 * LOG3 + u22 * LOG7) / SCALE
    return L0, alpha1, alpha2


def delta_prime(eps_plus, D):
    """
    |Lambda_tau| <= 2 |eps|, eps = sum_{unplaced} 9(d-1)10^{-1-g_j} - 10^{-n},
    |eps| <= eps_plus + 10^{-n}; candidates have n >= 2.6e27 digits (lattice), so
    10^{-n} <= 10^{-(96 D + 10)} is a (very) safe allowance.  Divide by 96 log 10.
    """
    d = 2 * (eps_plus + Fraction(1, 10 ** (L * D + 10)))
    return frac_upper(mp.mpf(d.numerator) / d.denominator / SCALE)


def lattice_geometry(pat):
    """shortest vector of Lam96 (Gauss reduction, exact) and ||U^{-1}||_inf"""
    (u11, u12), (u21, u22) = pat["Lam96"]
    v1, v2 = [u11, u12], [u21, u22]
    def n2(v): return v[0] ** 2 + v[1] ** 2
    while True:
        if n2(v2) < n2(v1):
            v1, v2 = v2, v1
        q = round(Fraction(v1[0] * v2[0] + v1[1] * v2[1], n2(v1)))
        if q == 0:
            break
        v2 = [v2[0] - q * v1[0], v2[1] - q * v1[1]]
    lam1 = mp.sqrt(n2(v1))
    det = u11 * u22 - u12 * u21
    Uinv_inf = Fraction(max(abs(u22) + abs(u21), abs(u12) + abs(u11)), abs(det))
    return lam1, Uinv_inf, abs(det)


# ----------------------------------------------------------------------------
# main driver per pattern
# ----------------------------------------------------------------------------
def run_pattern(pat, D, log):
    a, b, c, nu = pat["a"], pat["b"], pat["c"], pat["nu"]
    L0, alpha1, alpha2 = pattern_constants(pat)
    lam1, Uinv_inf, det = lattice_geometry(pat)
    dig = residues(pat)
    emax = max(e for (d, e) in pat["digits_positions"])
    rmin = min(r for _, r in dig)
    log(f"\n=== pattern s={pat['s']} M={pat['M']} a={a} y={pat['y']}=2^{a}3^{b}7^{c} nu={nu} "
        f"digits={pat['digits_positions']}")
    log(f"  residues r_j=(nu-1-e_j) mod 96: {[(de, r) for de, r in dig]};  min r_j = {rmin} "
        f"(guaranteed leading 1s); parent's W = 95-(emax-nu) = {95 - (emax - nu)}")
    log(f"  Lam96: lambda_1 = {mp.nstr(lam1, 6)}, det = {det:.4e}, ||U^-1||_inf = {float(Uinv_inf):.4e}")
    cases = list(enumerate_cases(pat, D))
    log(f"  D = {D}: {len(cases)} top-window cases")
    t0 = time.time()
    Xmin, worst = None, None
    exps = [Fraction(k, 2) for k in range(0, 1000)]   # X = 10^(k/2)
    cur = None                                          # current index into exps (running min)
    per_case = []
    verified_at = {}
    dw_ok = {}
    for ci, (tau, theta, eps_plus) in enumerate(cases):
        beta = (L0 - mp.log(1 + mp.mpf(theta.numerator) / theta.denominator)) / SCALE
        dp = delta_prime(eps_plus, D)
        if cur is None:
            # first case: search upward from a modest X
            k, last_ok, misses = 20, None, 0
            while misses < 3:
                X = int(mp.floor(mp.mpf(10) ** exps[k]))
                ok, info = reduce_search(alpha1, alpha2, beta, dp, X)
                if ok:
                    last_ok, misses, info_ok = k, 0, info
                else:
                    misses += 1
                k += 1
            cur = last_ok
            info = info_ok
            assert cur is not None, "reduction failed even at X = 10^10"
        else:
            while True:
                X = int(mp.floor(mp.mpf(10) ** exps[cur]))
                ok, info = reduce_search(alpha1, alpha2, beta, dp, X)
                if ok:
                    break
                # a failure at X is often a fluke (one unusually close lattice point at this scale);
                # success at any larger X certifies the case at X as well (the conclusion is monotone)
                for up in (1, 2, 3, 4):
                    Xu = int(mp.floor(mp.mpf(10) ** exps[cur + up]))
                    ok, info = reduce_search(alpha1, alpha2, beta, dp, Xu)
                    if ok:
                        break
                if ok:
                    break
                cur -= 1
                assert cur >= 0
        dw_ok[ci] = info["deweger_ok"]
        X = int(mp.floor(mp.mpf(10) ** exps[cur]))
        per_case.append((tau, float(exps[cur]), dp))
        verified_at[ci] = cur
        if worst is None or exps[cur] < worst[1]:
            worst = (tau, exps[cur], dp)
        if ci % 500 == 0:
            log(f"    case {ci}/{len(cases)}: running X = 10^{float(exps[cur])}  ({time.time() - t0:.0f}s)")
    X = int(mp.floor(mp.mpf(10) ** exps[cur]))
    # X works for every case (the running minimum was re-verified for each case at or below it);
    # but cases before the last decrease were verified at a larger X, which implies success at X?
    # NOT automatically (the lemma is monotone in X for fixed C, but we re-choose C).  Re-verify all.
    t1 = time.time()
    # Every case ci was certified at X_ci = 10^exps[verified_at[ci]] >= 10^exps[cur] (cur never increases).
    # The lemma's conclusion ("no solution with |x|,|y| <= X_ci") is monotone in X, so every case is
    # certified at X = 10^exps[cur] even though the test itself (for a fixed C) is not monotone.
    assert all(verified_at[ci] >= cur for ci in range(len(cases)))
    n_dw_fail = sum(1 for ci in range(len(cases)) if not dw_ok[ci])
    log(f"  all {len(cases)} cases certified at X >= 10^{float(exps[cur])} (exact CVP distance); "
        f"{len(cases) - n_dw_fail} of them already by de Weger's printed lower bound at their own X")
    Xp1 = int(mp.floor(mp.mpf(10) ** exps[cur + 1]))
    # X+1: largest exponent at which some case failed (the search's stopping point); report
    Bcert = (Fraction(X + 1) / Uinv_inf) - max(b, c)
    digits_cert = 1 + int(mp.floor(mp.mpf(Bcert.numerator) / Bcert.denominator * mp.log10(3)))
    log(f"  reduction succeeds for ALL cases at X = 10^{float(exps[cur])} (= {X:.3e}); "
        f"fails for at least one case at X = 10^{float(exps[cur+1])}")
    log(f"  worst case tau = {worst[0]} (delta' = {float(worst[2]):.3e})")
    log(f"  => every candidate has max(|x|,|y|) > X, hence max(b',c') >= (X+1)/||U^-1||_inf - max(b,c)")
    log(f"  B_cert = {float(Bcert):.4e}  (max(b',c') >= B_cert);  digits >= {digits_cert:.4e}  "
        f"(n >= 1 + B_cert*log10 3)")
    log(f"  time: search {t1 - t0:.1f}s")
    return dict(s=pat["s"], M=pat["M"], a=a, nu=nu, D=D, cases=len(cases), rmin=rmin,
                W_parent=95 - (emax - nu), log10X=float(exps[cur]), log10X_fail=float(exps[cur + 1]),
                Bcert=float(Bcert), digits=float(digits_cert), worst_tau=worst[0],
                worst_delta=float(worst[2]), Uinv_inf=float(Uinv_inf), lam1=float(lam1))


# ----------------------------------------------------------------------------
# control: a genuine S-unit treated as a candidate of a (fake, small) lattice coset
# ----------------------------------------------------------------------------
def control(log, D=1):
    log("\n=== CONTROL: genuine S-unit y'' = 2^a 3^b'' 7^c'' as a candidate of its own pattern")
    a, bpp, cpp = 3, 401, 141            # ~ 300 digits
    ypp = 2 ** a * 3 ** bpp * 7 ** cpp
    s = str(ypp)
    n = len(s)
    nu = n % L
    # the pattern of its own digits: every non-1 digit, with its residue
    digits_positions = []
    actual_pos = []
    for pos, ch in enumerate(reversed(s)):
        if ch != '1':
            digits_positions.append((int(ch), pos % L))
            actual_pos.append(pos)
    # fake small lattice and an anchor so that (x, y) = (2, -3)
    u1, u2 = (5, 3), (2, -7)
    x0, y0 = 2, -3
    b = bpp - (x0 * u1[0] + y0 * u2[0])
    c = cpp - (x0 * u1[1] + y0 * u2[1])
    m0 = (n - nu) // L
    pat = dict(a=a, b=b, c=c, nu=nu, digits_positions=digits_positions, Lam96=[list(u1), list(u2)])
    log(f"  y'' = 2^{a} 3^{bpp} 7^{cpp}, n = {n} digits, nu = n mod 96 = {nu}, {len(digits_positions)} non-1 digits; "
        f"fake lattice u1={u1}, u2={u2}, anchor (b,c)=({b},{c}), (x,y,m) = ({x0},{y0},{m0})")
    # the actual top-window case tau: t_j = (n-1-E_j) // 96 if < D else None
    dig = residues(pat)
    tau, theta, eps_plus = [], Fraction(0), Fraction(0)
    for ((d, e), r), E in zip(dig, actual_pos):
        g = n - 1 - E
        assert g % L == r
        t = g // L
        if t < D:
            tau.append(t)
            theta += Fraction(9 * (d - 1), 10 ** (1 + r + L * t))
        else:
            tau.append(None)
            eps_plus += Fraction(9 * (d - 1), 10 ** (1 + r + L * D))
    placed = sum(1 for t in tau if t is not None)
    log(f"  D = {D}: {placed} digits in the top {96*D} positions, {len(tau)-placed} below")
    # (i) exact identity 9 y''/10^n = 1 + theta + eps,  -10^-n <= eps <= eps_plus
    eps = Fraction(9 * ypp, 10 ** n) - 1 - theta
    log(f"  eps = 9y''/10^n - 1 - theta = {float(eps):.6e};  eps_plus = {float(eps_plus):.6e};  "
        f"-10^-n <= eps <= eps_plus: {-Fraction(1, 10**n) <= eps <= eps_plus}")
    # (ii) |Lambda_tau| = |log(9y''/10^n) - log(1+theta)| <= 2|eps|
    Lam = mp.log(mp.mpf(9) * ypp) - n * LOG10 - mp.log(1 + mp.mpf(theta.numerator) / theta.denominator)
    two_eps = mp.mpf(2 * abs(eps).numerator) / abs(eps).denominator
    log(f"  |Lambda_tau| = {mp.nstr(abs(Lam), 8)} <= 2|eps| = {mp.nstr(two_eps, 8)}: {abs(Lam) <= two_eps}")
    # (iii) the linear form in (x, y, m) with the pattern's constants equals Lambda_tau / (96 log 10)
    L0, alpha1, alpha2 = pattern_constants(pat)
    beta = (L0 - mp.log(1 + mp.mpf(theta.numerator) / theta.denominator)) / SCALE
    Lp = beta + alpha1 * x0 + alpha2 * y0 - m0
    dp = delta_prime(eps_plus, D)       # NB: uses the 10^-(96D+10) allowance for 10^-n: n = 300 > 106 ok for D=1
    log(f"  Lambda' = beta + a1 x + a2 y - m = {mp.nstr(Lp, 8)};  Lambda/(96 log10) = {mp.nstr(Lam / SCALE, 8)};  "
        f"agree: {abs(Lp - Lam / SCALE) < mp.mpf(10)**(-700)};  delta' = {float(dp):.3e};  |Lambda'| < delta': {abs(Lp) < mp.mpf(dp.numerator)/dp.denominator}")
    # (iv) the lemma's vector inequality holds for the genuine solution, and the reduction FAILS
    X = 3
    for kappa in (3, 5, 10, 30):
        C = (kappa * X) ** 3
        a1, a2, b0 = nint(C * alpha1), nint(C * alpha2), nint(C * beta)
        last = x0 * a1 + y0 * a2 - m0 * C + b0
        norm2 = x0 ** 2 + y0 ** 2 + last ** 2
        Q = Fraction(X) ** 2 + Fraction(X) ** 2 + (Fraction(C) * dp + (2 * X + 1) * RHO) ** 2
        ok, info = reduce_once(alpha1, alpha2, beta, dp, X, X, C)
        log(f"  C={C}: |v-w|^2 = {norm2} <= Q = {float(Q):.3f}: {norm2 <= Q};  dist_lb^2 = {float(info['lb2']):.3f};  "
            f"lemma certifies 'no solution': {ok} (must be False)")
        assert norm2 <= Q and not ok
    # (v) negative control: perturb one placed digit (so the number is not a candidate) -> reduction may succeed
    theta2 = theta + Fraction(9, 10 ** (1 + 5))       # pretend an extra 2 at gap 5 (a different number)
    beta2 = (L0 - mp.log(1 + mp.mpf(theta2.numerator) / theta2.denominator)) / SCALE
    ok2, info2 = reduce_search(alpha1, alpha2, beta2, dp, 10 ** 6)
    log(f"  perturbed theta (no genuine solution): reduction at X = 10^6 certifies: {ok2}")
    return dict(n=n, nu=nu, placed=placed, eps=float(eps), eps_plus=float(eps_plus), Lam=float(abs(Lam)),
                Lp=float(abs(Lp)), dp=float(dp), perturbed_ok=ok2)


def main():
    D = 1
    do_control = False
    only = None
    args = sys.argv[1:]
    while args:
        arg = args.pop(0)
        if arg == "--control":
            do_control = True
        elif arg == "--idx":            # run a single pattern (index into survivors.json)
            only = int(args.pop(0))
        else:
            D = int(arg)
    lines = []
    def log(s):
        print(s, flush=True)
        lines.append(s)
    pats = json.load(open("/home/claude/scouts/survivors.json"))
    results = []
    if do_control:
        results.append(("control", control(log)))
    for i, pat in enumerate(pats):
        if pat["closed_at_96"] or (only is not None and i != only):
            continue
        results.append(("pattern", run_pattern(pat, D, log)))
    suffix = f"D{D}" + (f"-idx{only}" if only is not None else "")
    with open(f"/home/claude/scouts/lll/run-{suffix}.log", "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(f"/home/claude/scouts/lll/results-{suffix}.json", "w") as f:
        json.dump(results, f, indent=1, default=str)


if __name__ == "__main__":
    main()
