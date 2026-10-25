#!/usr/bin/env python3
"""
baker_chain.py -- certified (conservative) Baker-type UPPER bound on the number of digits n
of an S-unit whose base-b expansion has k non-1 digits.

Base 10 (original setting, BAKER-CHAIN.md):

    y' = R_n + sum_{j=1}^k (d_j - 1) 10^{E_j},   R_n = (10^n - 1)/9,  d_j in {2,...,9},
    n > E_1 > ... > E_k >= 0,   y' = 2^a 3^b 7^c,
    i.e. 9y' + 1 = 10^n + sum_j c_j 10^{E_j},  c_j = 9(d_j - 1).

    baker_upper_bound(k, a) -> int N with n < N for every such y' (a = given 2-adic exponent;
                               the bound for a >= 1 is valid for every a' <= a).

Base b in {6, 8, 9, 10, 12, ...} (generalisation, RESULT-base-b.md):

    y' = R_n^{(b)} + sum_j (d_j - 1) b^{E_j},  d_j in {2,...,b-1},  y' = prod_{p < b} p^{e_p},
    with e_p <= bounded_exps_max[p] for the primes p | b;  (b-1)y' + 1 = b^n + sum_j c_j b^{E_j},
    c_j = (b-1)(d_j - 1).

    baker_upper_bound_base(b, k, bounded_exps_max) -> int N with n < N.

Method: iterated-gap argument with Matveev's theorem in the explicit form of
Bugeaud-Mignotte-Siksek, Ann. of Math. 163 (2006), Theorem 9.4 (real case, D = 1).
The chain gives n <= Phi(n) with Phi a polynomial in T = 1 + log(sigma n + tau) with
non-negative coefficients; Phi(nu)/nu is decreasing for nu >= e^k (Lemma 5.1 of
BAKER-CHAIN.md), so any integer N >= e^k with Phi(N) < N is a valid bound.  The returned
integer N is CERTIFIED by evaluating Phi(N) in mpmath interval arithmetic (256 bits):
upper(Phi(N)) < N and N > upper(e^k) are asserted, with N represented exactly.

Only mpmath (pure Python) is needed; light CPU (the whole self-test takes a few seconds).
"""

from fractions import Fraction
from mpmath import mp, mpf, log, exp, ceil, floor, iv

mp.dps = 60
iv.prec = 256

# ---------------------------------------------------------------------------
# small number theory helpers
# ---------------------------------------------------------------------------

def primes_below(b):
    return [p for p in range(2, b) if all(p % q for q in range(2, int(p ** 0.5) + 1))]


def vp(p, m):
    v = 0
    while m % p == 0:
        m //= p
        v += 1
    return v


def _rat_up(x, digits=6):
    """Rational upper bound (Fraction) of a positive mpf, rounded up at `digits` decimals."""
    q = 10 ** digits
    return Fraction(int(ceil(x * q)) + 1, q)


# ---------------------------------------------------------------------------
# chain parameters and the function Phi
# ---------------------------------------------------------------------------

class ChainParams:
    """One concrete application of the chain.

    alphas : the alpha's of the TOP form (positive integers); the inner forms use these
             plus N_j (one more log).  Heights A(alpha) = log(alpha) (all >= log 2 > 0.16).
    sigma, tau : Matveev's B = max |b_i| is bounded by sigma*n + tau (Fractions, sigma >= 1).
    b      : the base; U = (b-2)*b bounds the numerators, V = b-1 bounds N_j / b^{n-E_j}.
    """

    def __init__(self, alphas, sigma, tau, b, label=''):
        self.alphas = list(alphas)
        self.t0 = len(self.alphas)
        self.sigma = Fraction(sigma)
        self.tau = Fraction(tau)
        assert self.sigma >= 1 and self.tau >= 0
        self.b = int(b)
        assert self.b >= 3
        self.U = (self.b - 2) * self.b
        self.V = self.b - 1
        self.label = label

    def __repr__(self):
        return (f"ChainParams(alphas={self.alphas}, sigma={float(self.sigma):.4f}, "
                f"tau={float(self.tau):.3f}, b={self.b}, {self.label})")


def C_matveev(t, ctx=mp):
    """C(t) = 1.4 * 30^{t+3} * t^{4.5} (real case of BMS Theorem 9.4). In the mp context a
    factor (1 + 1e-30) is added; in the iv context the interval encloses the exact value."""
    one4 = ctx.mpf('1.4')
    val = one4 * ctx.mpf(30) ** (t + 3) * ctx.mpf(t) ** ctx.mpf('4.5')
    if ctx is mp:
        val = val * (1 + mpf('1e-30'))
    return val


def _frac(ctx, fr):
    return ctx.mpf(fr.numerator) / ctx.mpf(fr.denominator)


def phi(params, k, nu, ctx=mp, details=False):
    """Phi(nu): upper bound on n produced by the chain when the unknown digit count is nu
    (so that Matveev's B <= sigma*nu + tau).  ctx = mp (floating, 60 digits) or iv (intervals).

    k = 0 : Phi = K0 / log b
    k >= 1: G_0 = (K0 + log U)/log b ; S_1 = G_0 ;
            G_j = (log U + K1 (S_j log b + log V))/log b ; S_{j+1} = S_j + G_j  (1 <= j <= k-1) ;
            Phi = K1 (S_k log b + log V)/log b
    with K0 = C(t0) PA T, K1 = C(t0+1) PA T, T = 1 + log(sigma nu + tau), PA = prod log(alpha).
    """
    Lb = ctx.log(ctx.mpf(params.b))
    logU = ctx.log(ctx.mpf(params.U))
    logV = ctx.log(ctx.mpf(params.V))
    PA = ctx.mpf(1)
    for al in params.alphas:
        PA = PA * ctx.log(ctx.mpf(al))
    T = 1 + ctx.log(_frac(ctx, params.sigma) * nu + _frac(ctx, params.tau))
    K0 = C_matveev(params.t0, ctx) * PA * T
    K1 = C_matveev(params.t0 + 1, ctx) * PA * T
    info = {'T': T, 'K0': K0, 'K1': K1, 'PA': PA, 'G': [], 'S': []}
    if k == 0:
        Phi = K0 / Lb
        info['G'].append(Phi)
        return (Phi, info) if details else Phi
    G0 = (K0 + logU) / Lb
    info['G'].append(G0)
    S = G0
    info['S'].append(S)
    for j in range(1, k):
        Gj = (logU + K1 * (S * Lb + logV)) / Lb
        info['G'].append(Gj)
        S = S + Gj
        info['S'].append(S)
    Phi = K1 * (S * Lb + logV) / Lb
    info['Phi'] = Phi
    return (Phi, info) if details else Phi


# ---------------------------------------------------------------------------
# solving n <= Phi(n) with an exact certificate
# ---------------------------------------------------------------------------

def _exact_int_at_least(x):
    """An exact Python int N >= 10^x (x an mpf >= 0), of the form m * 10^e with m < 10^7."""
    xf = int(floor(x))
    frac = x - xf
    if xf < 7:
        return int(ceil(mpf(10) ** x)) + 1
    m = int(ceil(mpf(10) ** frac * 10 ** 6)) + 1       # 10^frac < 10, so m < 10^7 + 2
    return m * 10 ** (xf - 6)


def _certify(params, k, N_int):
    """Rigorous check (interval arithmetic) that N_int >= e^k and Phi(N_int) < N_int.
    N_int is passed exactly: as m * 10^e when it has that shape, else as an exact mpf."""
    s = str(N_int)
    stripped = s.rstrip('0')
    e = len(s) - len(stripped)
    m = int(stripped)
    assert m < 2 ** 52, "certificate integer must be m * 10^e with small m"
    N_iv = iv.mpf(m) * iv.mpf(10) ** e             # m exact, 10^e enclosed
    ek = iv.exp(iv.mpf(k))
    if not (N_iv.a > ek.b):
        return False
    P = phi(params, k, N_iv, ctx=iv)
    return bool(P.b < N_iv.a)


def solve_chain(params, k):
    """Returns (N_int, x) where N_int is a certified integer bound (n < N_int) and x = log10 of
    the grid point 10^x <= N_int at which the floating search succeeded."""
    x = max(mpf(k) / log(mpf(10)) + 1, mpf(2))        # 10^x >= 10 e^k
    for _ in range(80):                               # iterate nu <- Phi(nu) upward
        xn = log(phi(params, k, mpf(10) ** x)) / log(mpf(10))
        if xn <= x:
            break
        x = xn
    step = mpf('0.001')
    for _ in range(100000):
        N = mpf(10) ** x
        if N >= exp(mpf(k)) and phi(params, k, N) * (1 + mpf('1e-6')) < N:
            N_int = _exact_int_at_least(x)
            if _certify(params, k, N_int):
                return N_int, x
        x += step
    raise RuntimeError("no certified point found")


# ---------------------------------------------------------------------------
# base 10: the original API
# ---------------------------------------------------------------------------

def params_base10(a):
    """alphas (3, 7, 10) if a = 0 (t0 = 3), (2, 3, 7, 10) if a >= 1 (t0 = 4);
    B = max(a, b+2, c, n, 1) <= 2.1 n + 2 + a  (b < n log10/log3 < 2.096 n)."""
    alphas = [3, 7, 10] if a == 0 else [2, 3, 7, 10]
    return ChainParams(alphas, Fraction(21, 10), 2 + a, 10, label=f'base10,a={a}')


def chain(k, a, n, details=False):
    """Base-10 Phi (kept for backward compatibility)."""
    return phi(params_base10(a), k, mpf(n), ctx=mp, details=details)


def baker_upper_bound(k, a, return_log10=False):
    """Certified: every y' = 2^a' 3^b 7^c (a' = a, or any a' <= a when a >= 1) of the base-10
    form with exactly k non-1 digits has n < N (returned Python int)."""
    assert k >= 0 and a >= 0
    N_int, x = solve_chain(params_base10(a), k)
    return (N_int, x) if return_log10 else N_int


# ---------------------------------------------------------------------------
# base b
# ---------------------------------------------------------------------------

def params_base_b(b, bounded_exps_max):
    """The two admissible choices of alphas for base b (both valid; the caller takes the min).

    P = primes < b, D = primes dividing b (exponents e_p <= a_p := bounded_exps_max[p]),
    F = P \\ D (free exponents, e_p < n log b / log p), D+ = {p in D : a_p >= 1}.
    M := (b-1) y' = prod_{p in P} p^{e_p + v_p(b-1)}  (every prime factor of b-1 is < b).

    option (i)  alphas = P,  exponents e_p + v_p(b-1) (p in F), e_p - n v_p(b) (p in D), -n absorbed.
    option (ii) alphas = F u {b} u D+, exponents e_p + v_p(b-1), -n, e_p.
    In both, |b_i| <= sigma n + tau with sigma = log b/log 2, tau = log(b-1)/log 2 + max a_p
    (for p in F: e_p + v_p(b-1) < (n log b + log(b-1))/log 2; for p in D: |e_p - n v_p(b)|
    <= max(a_p, n v_p(b)) <= n log b/log 2 + a_p; n <= n sigma; and 1 for N_j).
    """
    b = int(b)
    assert b >= 3
    P = primes_below(b)
    D = [p for p in P if b % p == 0]
    for p in D:
        assert p in bounded_exps_max, f"need a bound for the exponent of {p} | {b}"
    F = [p for p in P if b % p != 0]
    Dplus = [p for p in D if bounded_exps_max[p] >= 1]
    amax = max([bounded_exps_max[p] for p in D] + [0])
    sigma = _rat_up(log(mpf(b)) / log(mpf(2)))
    tau = _rat_up(log(mpf(b - 1)) / log(mpf(2))) + amax
    opt1 = ChainParams(P, sigma, tau, b, label=f'base{b} opt(i) alphas={P}')
    opt2 = ChainParams(F + [b] + Dplus, sigma, tau, b, label=f'base{b} opt(ii) alphas={F + [b] + Dplus}')
    return [opt1, opt2]


def baker_upper_bound_base(b, k, bounded_exps_max, return_log10=False, return_choice=False):
    """Certified: every y' = prod_{p<b} p^{e_p} with e_p <= bounded_exps_max[p] for p | b,
    whose base-b expansion is all 1s except exactly k digits d_j in {2,...,b-1}, has n < N."""
    assert k >= 0
    best = None
    for par in params_base_b(b, bounded_exps_max):
        N_int, x = solve_chain(par, k)
        if best is None or N_int < best[0]:
            best = (N_int, x, par)
    out = [best[0]]
    if return_log10:
        out.append(best[1])
    if return_choice:
        out.append(best[2])
    return out[0] if len(out) == 1 else tuple(out)


# ---------------------------------------------------------------------------
# polynomial form and the Pethő–de Weger closed-form cross-check
# ---------------------------------------------------------------------------

def chain_poly_coeffs_params(params, k):
    """Coefficients alpha_0..alpha_{k+1} of Phi as a polynomial in T = 1 + log B (all >= 0)."""
    Lb = log(mpf(params.b))
    logU = log(mpf(params.U))
    logV = log(mpf(params.V))
    PA = mpf(1)
    for al in params.alphas:
        PA *= log(mpf(al))
    c0 = C_matveev(params.t0) * PA
    c1 = C_matveev(params.t0 + 1) * PA
    if k == 0:
        return [mpf(0), c0 / Lb]

    def add(p, q):
        r = [mpf(0)] * max(len(p), len(q))
        for i, x in enumerate(p):
            r[i] += x
        for i, x in enumerate(q):
            r[i] += x
        return r

    def shift_mul(p, c):
        return [mpf(0)] + [c * x for x in p]

    S = [logU / Lb, c0 / Lb]
    for j in range(1, k):
        inner = add([x * Lb for x in S], [logV])
        Gj = add([logU / Lb], [x / Lb for x in shift_mul(inner, c1)])
        S = add(S, Gj)
    inner = add([x * Lb for x in S], [logV])
    return [x / Lb for x in shift_mul(inner, c1)]


def chain_poly_coeffs(k, a):
    return chain_poly_coeffs_params(params_base10(a), k)


def closed_form_log10_params(params, k):
    """Pethő–de Weger lemma (Math. Comp. 47 (1986); Lemma 6 of arXiv:2010.11670):
    if x is the largest real solution of x = u + v (log x)^h (u, v >= 0, h >= 1) then
    x < max{2^h (u^{1/h} + v^{1/h} log(h^h v))^h, 2^h (u^{1/h} + 2e^2)^h}.
    With x := e (sigma n + tau), T = log x >= 1 and Phi <= alpha_0 + (sum_{i>=1} alpha_i) T^{k+1}."""
    co = chain_poly_coeffs_params(params, k)
    h = mpf(len(co) - 1)
    alpha0, alpha = co[0], sum(co[1:])
    e = exp(mpf(1))
    sg, ta = _frac(mp, params.sigma), _frac(mp, params.tau)
    u = e * (ta + sg * alpha0)
    v = sg * e * alpha
    x1 = 2 ** h * (u ** (1 / h) + v ** (1 / h) * log(h ** h * v)) ** h
    x2 = 2 ** h * (u ** (1 / h) + 2 * e ** 2) ** h
    x = max(x1, x2)
    return log((x / e - ta) / sg) / log(mpf(10))


def baker_upper_bound_closed_form(k, a):
    return closed_form_log10_params(params_base10(a), k)


# ---------------------------------------------------------------------------
# controls
# ---------------------------------------------------------------------------

def _digits_pattern(y, b):
    """(n, [(c_j, E_j)]) with (b-1) y + 1 = b^n + sum c_j b^{E_j}, c_j = (b-1)(d_j - 1) over the
    non-1 digits d_j of y in base b (digit 0 gives c_j = -(b-1))."""
    digs = []
    m = y
    while m:
        digs.append(m % b)
        m //= b
    n = len(digs)
    pat = [((b - 1) * (d - 1), E) for E, d in enumerate(digs) if d != 1]
    pat.sort(key=lambda t: -t[1])
    return n, pat


def positive_control(b, exps, bounded_exps_max=None, verbose=True):
    """Check the chain's inequalities on the genuine S-unit y = prod p^{e_p} (base b).

    If every base-b digit of y is in {1,...,b-1} (the theorem's domain) the exact statements of
    Lemmas 3.1-3.2 / Prop. 4.1 are asserted.  If y contains digit 0 (outside the domain) only the
    absolute-value variants are asserted: the identity, non-vanishing (numerators are == -1 mod b-1),
    |numerator| <= U b^{E_{j+1}} + 1, N_j >= 1 with A(N_j) = max(log N_j, 0.16), and the Matveev
    inequalities themselves.  Returns 'in-domain' or 'abs-variant'."""
    y = 1
    for p, e in exps.items():
        y *= p ** e
    M = (b - 1) * y
    n, pat = _digits_pattern(y, b)
    k = len(pat)
    E = [Ej for _, Ej in pat]
    in_domain = all(c >= 0 for c, _ in pat)
    assert M + 1 == b ** n + sum(c * b ** Ej for c, Ej in pat)
    assert all(E[i] > E[i + 1] for i in range(k - 1)) and (k == 0 or (n > E[0] and E[-1] >= 0))
    if bounded_exps_max is None:
        bounded_exps_max = {p: exps.get(p, 0) for p in primes_below(b) if b % p == 0}
    results = []
    plist = params_base_b(b, bounded_exps_max) if b != 10 else [params_base10(exps.get(2, 0))]
    for par in plist:
        # Matveev's B for this y (exact) must be <= sigma n + tau
        Bexact = max([n, 1] + [abs(exps.get(p, 0) + vp(p, b - 1) - n * vp(p, b)) for p in par.alphas if p < b]
                     + [exps.get(p, 0) for p in par.alphas if p < b])
        assert Bexact <= par.sigma * n + par.tau
        T = 1 + log(mpf(Bexact))
        PA = mpf(1)
        for al in par.alphas:
            PA *= log(mpf(al))
        K0 = C_matveev(par.t0) * PA * T
        K1 = C_matveev(par.t0 + 1) * PA * T
        Lb = log(mpf(b))
        U, V = par.U, par.V

        def mlog(fr):
            return log(mpf(fr.numerator)) - log(mpf(fr.denominator))

        Lam0 = Fraction(M, b ** n) - 1
        assert Lam0 != 0
        if k >= 1:
            g0 = n - E[0]
            assert abs(Lam0) <= Fraction(U, b ** g0) + (0 if in_domain else Fraction(1, b ** n))
            assert mlog(abs(Lam0)) > -K0
            if in_domain:
                assert Lam0 > 0 and g0 <= (K0 + log(mpf(U))) / Lb
        else:
            assert Lam0 == -Fraction(1, b ** n) and n * Lb < K0
        for j in range(1, k + 1):
            Ej = E[j - 1]
            Nj = b ** (n - Ej) + sum(pat[i][0] * b ** (pat[i][1] - Ej) for i in range(j))
            assert Nj * b ** Ej + sum(pat[i][0] * b ** pat[i][1] for i in range(j, k)) == M + 1
            assert Nj >= 1
            if in_domain:
                assert b ** (n - Ej) <= Nj <= V * b ** (n - Ej)
            A_N = max(log(mpf(Nj)), mpf('0.16'))
            Lam = Fraction(M, Nj * b ** Ej) - 1
            assert Lam != 0
            num = Lam * Nj * b ** Ej
            assert num.denominator == 1 and (num.numerator + 1) % (b - 1) == 0   # == -1 mod (b-1)
            assert mlog(abs(Lam)) > -K1 * A_N                                     # Matveev
            if j < k:
                gj = Ej - E[j]
                assert abs(num) <= U * b ** E[j] + 1
                if in_domain:
                    assert Lam > 0 and abs(Lam) <= Fraction(U, Nj * b ** gj)
                    assert gj <= (log(mpf(U)) + K1 * log(mpf(Nj))) / Lb
            else:
                assert Lam == -Fraction(1, M + 1)
                if in_domain:
                    assert n * Lb < K1 * log(mpf(Nj)) or Ej == 0
        results.append(par.label)
    tag = 'in-domain' if in_domain else 'abs-variant'
    if verbose:
        print(f"positive control base {b}, y = {' '.join(f'{p}^{e}' for p, e in exps.items())}: "
              f"n = {n} digits, k = {k} non-1 digits [{tag}]: all checked inequalities hold "
              f"({len(results)} parameter choice(s))")
    return tag


# ---------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------

def table_base10(ks=range(0, 33), avals=(0, 1, 40)):
    rows = []
    for k in ks:
        row = [k]
        for a in avals:
            N, x = baker_upper_bound(k, a, return_log10=True)
            row.append(float(log(mpf(N)) / log(mpf(10))))
        rows.append(row)
    return rows


BASE_SETTINGS = {
    6: {2: 2, 3: 2},
    8: {2: 2},
    9: {3: 2},
    10: {2: 40, 5: 0},
    12: {2: 2, 3: 2},
}


def table_bases(ks=range(0, 17), settings=BASE_SETTINGS):
    out = {}
    for b, bex in settings.items():
        col = []
        for k in ks:
            N, x, par = baker_upper_bound_base(b, k, bex, return_log10=True, return_choice=True)
            col.append((k, float(log(mpf(N)) / log(mpf(10))), par.label))
        out[b] = col
    return out


if __name__ == '__main__':
    print("Matveev constants C(t) = 1.4*30^(t+3)*t^4.5:")
    for t in (3, 4, 5, 6):
        print(f"  C({t}) = {mp.nstr(C_matveev(t), 6)}")
    print()
    print("BASE 10: log10 N for the certified integer N = baker_upper_bound(k, a)  (n < N)")
    print("   [PdW] = closed-form Pethő–de Weger cross-check (weaker, must be >= the bound)")
    print(" k    a=0    [PdW]     a=1    [PdW]     a=40   [PdW]")
    for row in table_base10():
        k = row[0]
        pdw = [float(baker_upper_bound_closed_form(k, a)) for a in (0, 1, 40)]
        assert all(pdw[i] >= row[i + 1] for i in range(3))
        print(f"{k:2d}  {row[1]:8.3f} {pdw[0]:8.3f}  {row[2]:8.3f} {pdw[1]:8.3f}  {row[3]:8.3f} {pdw[2]:8.3f}")
    print()
    for k, a in ((0, 0), (1, 3), (6, 0), (8, 1), (31, 40)):
        nn = mpf(10) ** 150
        co = chain_poly_coeffs(k, a)
        T = 1 + log(mpf('2.1') * nn + 2 + a)
        assert abs(sum(c * T ** i for i, c in enumerate(co)) / chain(k, a, nn) - 1) < mpf('1e-40')
    print("polynomial-in-T form of Phi agrees with the recursion (checked).")
    N, x = baker_upper_bound(6, 0, return_log10=True)
    Phi, info = chain(6, 0, N, details=True)
    print(f"k=6, a=0: certified N = {str(N)[:8]}...e{len(str(N))-1} (log10 N = {mp.nstr(log(mpf(N))/log(mpf(10)), 7)}), "
          f"T = {mp.nstr(info['T'],6)}, K0 = {mp.nstr(info['K0'],5)}, K1 = {mp.nstr(info['K1'],5)}")
    print("  gap bounds log10 G_j:", [mp.nstr(log(g) / log(mpf(10)), 5) for g in info['G']])
    print("  Phi(N)/N =", mp.nstr(Phi / mpf(N), 6))
    print()
    print("BASES 6, 8, 9, 10, 12: log10 N for N = baker_upper_bound_base(b, k, bounded_exps_max)")
    print("  bounded exponents:", BASE_SETTINGS)
    tb = table_bases()
    print(" k   " + "  ".join(f"b={b:<2d}    " for b in tb))
    for i, k in enumerate(range(0, 17)):
        print(f"{k:2d}  " + "  ".join(f"{tb[b][i][1]:9.3f}" for b in tb))
    print("  choice of alphas used (k = 8):", {b: tb[b][8][2] for b in tb})
    # base-10 consistency: the generic function must not be far from the base-10 table
    N10a, _ = baker_upper_bound(8, 40, return_log10=True)
    print(f"  base-10 cross-check at k = 8: specific API log10 = {float(log(mpf(N10a))/log(mpf(10))):.3f}, "
          f"generic = {tb[10][8][1]:.3f}")
    print()
    # controls
    positive_control(10, {3: 13, 7: 2})          # 78121827, in-domain, k = 6
    positive_control(10, {2: 1, 3: 14, 7: 3})    # 3281116734, in-domain, k = 7
    positive_control(10, {2: 3, 3: 401, 7: 141}) # 312 digits, contains 0s -> abs-variant
    positive_control(10, {3: 60, 7: 20})         # 46 digits, contains 0s -> abs-variant
    for b in (6, 8, 9, 12):
        # find small in-domain examples (no digit 0, at least one non-1 digit) and one large one
        found = 0
        P = primes_below(b)
        import itertools
        for es in itertools.product(range(0, 7), repeat=len(P)):
            y = 1
            for p, e in zip(P, es):
                y *= p ** e
            if y < b ** 3:
                continue
            n, pat = _digits_pattern(y, b)
            if all(c >= 0 for c, _ in pat) and 1 <= len(pat):
                positive_control(b, dict(zip(P, es)))
                found += 1
                if found >= 2:
                    break
        big = {p: 23 + 7 * i for i, p in enumerate(P)}
        positive_control(b, big)
    print()
    for a in (0, 40):
        N0, x0 = baker_upper_bound(0, a, return_log10=True)
        print(f"k = 0, a = {a} (repunit S-unit): n < 10^{float(log(mpf(N0))/log(mpf(10))):.3f}")
