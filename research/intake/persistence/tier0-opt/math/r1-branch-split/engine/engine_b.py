#!/usr/bin/env python3
"""
engine_b.py — the antecedent-tree child enumeration, parametrized by the base b.

Setting. Digits 2..b-1 factor over the "digit primes" P. A child y of a vertex s is a product of
digit primes with digit product s, not divisible by b (else its last digit is 0). Base primes
(p | b) have bounded exponents (tail enumeration); the remaining digit primes are free and
their exponents form a lattice coset after the residue filters. Everything else is the base-10
method with 10 -> b: residue patterns modulo primes of b^L - 1, ℓ-component tables, CRT
representatives, b-adic pinning, descent with v_p for each base prime.

Validation: brute force over all y of each equation's shape up to NMAX base-b digits.
"""
import sys, itertools, math, time
from collections import Counter, defaultdict
from math import gcd, comb
import sympy
from sympy import primitive_root, factorint
from lattice3 import CosetK, _egcd
from lattice3 import _lll as _lll_float
from fractions import Fraction as _Fr
def _lll(B): return _lll_float(B, _Fr(99, 100))     # exact delta: a float delta overflows on the huge entries of high levels

# ----------------------------------------------------------------------------- base data
class Base:
    def __init__(self, b):
        self.b = b
        self.dp = [p for p in range(2, b) if sympy.isprime(p)]                  # digit primes
        self.bp = {p: 0 for p in self.dp if b % p == 0}                          # base primes -> v_p(b)
        for p in self.bp:
            t = b
            while t % p == 0: t //= p; self.bp[p] += 1
        self.free = [p for p in self.dp if p not in self.bp]
        self.bounded = [p for p in self.dp if p in self.bp]
        self.k = len(self.dp)
    def digits(self, n):
        out = []
        while n: out.append(n % self.b); n //= self.b
        return out[::-1]
    def dprod(self, n):
        r = 1
        for d in self.digits(n): r *= d
        return r
    def R(self, n):
        return (self.b ** n - 1) // (self.b - 1)
    def factor(self, y):
        """exponent vector over dp, or None if y has another prime factor."""
        e = []
        for p in self.dp:
            c = 0
            while y % p == 0: y //= p; c += 1
            e.append(c)
        return tuple(e) if y == 1 else None
    def multisets(self, s):
        out = []
        def rec(n, mind, cur):
            if n == 1: out.append(tuple(cur)); return
            for d in range(mind, self.b):
                if n % d == 0:
                    cur.append(d); rec(n // d, d, cur); cur.pop()
        rec(s, 2, [])
        return out
    def padic_bound(self, M, p, kcap=400):
        """max v_p(y) over numbers whose non-1 digits form a sub-multiset of M (base b)."""
        e = self.bp[p]; b = self.b
        states = {(0, tuple(sorted(M)), False)}
        for k in range(1, kcap):
            new = set(); mod = p ** (k * e)
            for tail, rem, ended in states:
                choices = {0} if ended else ({0, 1} | set(rem))
                for d in choices:
                    t = d * b ** (k - 1) + tail
                    if t % mod == 0:
                        if d == 0:
                            if tail: new.add((t, rem, True))
                        elif d == 1: new.add((t, rem, False))
                        else:
                            r = list(rem); r.remove(d); new.add((t, tuple(r), False))
            if not new:
                return k * e - 1
            states = new
        raise RuntimeError("p-adic bound did not terminate")
    def admissible_bounded(self, M):
        """tuples of bounded exponents (one per base prime, in self.bounded order) with b ∤ y."""
        bounds = [self.padic_bound(M, p) for p in self.bounded]
        out = []
        for t in itertools.product(*[range(B + 1) for B in bounds]):
            if any(t[i] < self.bp[p] for i, p in enumerate(self.bounded)):
                out.append(t)
        return out, bounds

# ----------------------------------------------------------------------------- level primes
PRIME_CAP = 10 ** 30          # level primes above this (or with a non-smooth p-1) are skipped: a subset of
PH_CAP = 10 ** 8              # the level primes is still a valid (weaker) level
def primes_for_level(base, L, exclude):
    from sympy import cyclotomic_poly, divisors
    ps = set()
    for d in divisors(L):                       # b^L - 1 = prod_{d|L} Phi_d(b): factor the cyclotomic parts
        v = int(cyclotomic_poly(d, base.b))
        f = factorint(v, limit=10 ** 6) if v > 10 ** 40 else factorint(v)
        for p in f:
            p = int(p)
            if p > PRIME_CAP: continue
            if p > 10 ** 12 and max(factorint(p - 1)) > PH_CAP: continue
            ps.add(p)
    ps = sorted(p for p in ps if p not in base.dp)
    return [p for p in ps if p not in exclude]

class PrimeData:
    def __init__(self, base, p, L):
        self.p, self.L = p, L
        g = primitive_root(p); self.g = g
        from dlog import discrete_log
        self.logs = [discrete_log(p, q % p, g) for q in base.dp]
        for q, lg in zip(base.dp, self.logs): assert pow(g, lg, p) == q % p
        self.powb = [pow(base.b, i, p) for i in range(L)]
        inv = pow(base.b - 1, -1, p)
        self.R = [(self.powb[i] - 1) * inv % p for i in range(L)]
        self.table = None
        if p < 3_000_000:
            tbl = [0] * p; x = 1
            for i in range(p - 1):
                tbl[x] = i; x = x * g % p
            self.table = tbl
    def log(self, x):
        if self.table is not None: return self.table[x]
        from dlog import discrete_log
        return discrete_log(self.p, x, self.g)

# ----------------------------------------------------------------------------- level algebra (k generators)
class Level:
    """Pattern-independent algebra for one level: generators = the digit primes' logs (first
    level, over Z^k) or, for a lift, the parent lattice basis images (over Z^dim)."""
    def __init__(self, pdatas, gens_per_prime, dim, cap=5_000_000):
        self.pdatas = pdatas; self.dim = dim; self.lattice_only = False
        self.gens = gens_per_prime     # list over primes of tuples of length dim (mod p-1)
        comps = defaultdict(list)
        for i, pd in enumerate(pdatas):
            for l, k in factorint(pd.p - 1).items(): comps[l].append((i, l ** k))
        self.comps = []; self.linear = []
        for l, lst in sorted(comps.items()):
            mods = tuple(m for _, m in lst)
            gl = [tuple(self.gens[i][j] % m for i, m in lst) for j in range(dim)]
            Nl = 1
            for m in mods: Nl = Nl * m // gcd(Nl, m)
            if len(lst) == 1 and mods[0] > 1_000_000:
                self.linear.append((lst[0][0], mods[0], [g[0] for g in gl], Nl)); continue
            zero = tuple(0 for _ in lst)
            H = {zero: tuple(0 for _ in range(dim))}; frontier = [zero]; toobig = False
            while frontier and not toobig:
                nxt = []
                for h in frontier:
                    x = H[h]
                    for gi, g in enumerate(gl):
                        t = tuple((u + v) % m for u, v, m in zip(h, g, mods))
                        if t not in H:
                            e = list(x); e[gi] += 1; H[t] = tuple(e); nxt.append(t)
                    if len(H) > cap: toobig = True; break
                frontier = nxt
            if toobig:
                self.lattice_only = True; continue      # this level is solved by lattice intersections (slow path)
            self.comps.append((lst, mods, H, Nl))
        N = 1
        for _, _, _, Nl in self.comps: N = N * Nl // gcd(N, Nl)
        for _, _, _, Nl in self.linear: N = N * Nl // gcd(N, Nl)
        self.N = N
        def crt(Nl):
            q = N // Nl
            return (q * pow(q % Nl, -1, Nl) if Nl > 1 else 0) % N
        self.crt = [crt(Nl) for _, _, _, Nl in self.comps]
        self.crt_lin = [crt(Nl) for _, _, _, Nl in self.linear]
        ck = CosetK.full(dim)
        for pd, g in zip(pdatas, self.gens):
            ck = ck.intersect_congruence(list(g), 0, pd.p - 1)
        self.kernel = [tuple(u) for u in _lll(ck.U)]      # basis of the kernel lattice in Z^dim

    def solve(self, targets):
        """targets[i] ≡ Σ_j t_j gens[i][j] (mod p_i - 1); returns t ∈ Z^dim or None."""
        if self.lattice_only:
            ck = CosetK.full(self.dim)
            for pd, g, w in zip(self.pdatas, self.gens, targets):
                ck = ck.intersect_congruence(list(g), w % (pd.p - 1), pd.p - 1)
                if ck is None: return None
            return tuple(ck.v0)
        t = [0] * self.dim
        for (lst, mods, H, Nl), c in zip(self.comps, self.crt):
            key = tuple(targets[i] % m for (i, m) in lst)
            x = H.get(key)
            if x is None: return None
            for j in range(self.dim): t[j] += c * x[j]
        for (i, m, g, Nl), c in zip(self.linear, self.crt_lin):
            key = targets[i] % m
            # solve Σ t_j g_j ≡ key (mod m): reduce to a two-term egcd chain
            gg, coeffs = g[0], [1] + [0] * (self.dim - 1)
            for j in range(1, self.dim):
                if g[j] == 0: continue
                g2, x, y = _egcd(gg, g[j]); coeffs = [x * cf for cf in coeffs]; coeffs[j] = y; gg = g2
            d = gcd(gg, m)
            if key % d: return None
            mm = m // d; s_ = (key // d) * pow((gg // d) % mm, -1, mm) % mm if mm > 1 else 0
            for j in range(self.dim): t[j] += c * coeffs[j] * s_
        for pd, g, w in zip(self.pdatas, self.gens, targets):
            assert (sum(tj * gj for tj, gj in zip(t, g)) - w) % (pd.p - 1) == 0
        return tuple(t)

# ----------------------------------------------------------------------------- cosets in the free exponents
class FreeCoset:
    """v + Λ in Z^f (f = number of free primes), Λ given by a basis list (rank f)."""
    __slots__ = ("v", "U")
    def __init__(self, v, U): self.v = tuple(v); self.U = [tuple(u) for u in U]
    def contains(self, x):
        from fractions import Fraction
        f = len(self.v); d = len(self.U)
        rhs = [x[i] - self.v[i] for i in range(f)]
        G = [[Fraction(sum(a * b for a, b in zip(self.U[i], self.U[j]))) for j in range(d)] for i in range(d)]
        bb = [Fraction(sum(a * r for a, r in zip(self.U[i], rhs))) for i in range(d)]
        M = [G[i] + [bb[i]] for i in range(d)]
        for c in range(d):
            piv = next((i for i in range(c, d) if M[i][c] != 0), None)
            if piv is None: return False
            M[c], M[piv] = M[piv], M[c]; M[c] = [v / M[c][c] for v in M[c]]
            for i in range(d):
                if i != c and M[i][c] != 0: M[i] = [vi - M[i][c] * vc for vi, vc in zip(M[i], M[c])]
        y = [M[i][d] for i in range(d)]
        if any(v.denominator != 1 for v in y): return False
        pt = tuple(self.v[i] + sum(int(y[j]) * self.U[j][i] for j in range(d)) for i in range(f))
        return pt == tuple(x)
    def shortest(self):
        return min(math.sqrt(sum(c * c for c in u)) for u in self.U)
    def nearest(self):
        """the coset point nearest the origin (exact rational Babai + neighbour search)."""
        from fractions import Fraction
        f = len(self.v); d = len(self.U)
        G = [[Fraction(sum(a * b for a, b in zip(self.U[i], self.U[j]))) for j in range(d)] for i in range(d)]
        bb = [Fraction(-sum(a * r for a, r in zip(self.U[i], self.v))) for i in range(d)]
        M = [G[i] + [bb[i]] for i in range(d)]
        for c in range(d):
            piv = next(i for i in range(c, d) if M[i][c] != 0)
            M[c], M[piv] = M[piv], M[c]; M[c] = [v / M[c][c] for v in M[c]]
            for i in range(d):
                if i != c and M[i][c] != 0: M[i] = [vi - M[i][c] * vc for vi, vc in zip(M[i], M[c])]
        y0 = [round(M[i][d]) for i in range(d)]
        best = None
        for delta in itertools.product((-1, 0, 1), repeat=d):
            yv = [y0[i] + delta[i] for i in range(d)]
            pt = tuple(self.v[k] + sum(yv[j] * self.U[j][k] for j in range(d)) for k in range(f))
            nn = sum(c * c for c in pt)
            if best is None or nn < best[0]: best = (nn, pt)
        return best[1]

# ----------------------------------------------------------------------------- b-adic tools
def unit_group_log(base, p, j, x):
    """discrete log of x in (Z/p^j)^*: returns (coords, moduli) with x ≡ Π gen_i^{coord_i}.
    odd p: cyclic, generator = primitive_root(p^j). p = 2: <-1> x <5>."""
    m = p ** j
    if p == 2:
        if j <= 1: return (), ()
        if j == 2: return ((0 if x % 4 == 1 else 1),), (2,)
        s = 0 if x % 4 == 1 else 1
        w = (-x) % m if s else x % m
        t = 0
        for i in range(2, j):
            if (w * pow(pow(5, t, m), -1, m)) % (2 ** (i + 1)) != 1: t += 2 ** (i - 2)
        assert pow(5, t, m) == w
        return (s, t), (2, 2 ** (j - 2))
    g = primitive_root(m); order = (p - 1) * p ** (j - 1)
    # Pohlig–Hellman on the cyclic group
    fac = factorint(order); x %= m; res = []; mods = []
    for q, e in fac.items():
        qe = q ** e; gq = pow(g, order // qe, m); hq = pow(x, order // qe, m); xq = 0
        gamma = pow(gq, q ** (e - 1), m)
        for k in range(e):
            hk = pow(hq * pow(gq, -xq, m) % m, q ** (e - 1 - k), m)
            dk = next(i for i in range(q) if pow(gamma, i, m) == hk)
            xq += dk * q ** k
        res.append(xq); mods.append(qe)
    X = 0; MM = 1
    for r, mo in zip(res, mods):
        t = ((r - X) * pow(MM, -1, mo)) % mo; X += MM * t; MM *= mo
    assert pow(g, X, m) == x % m
    return (X,), (order,)

def cut_coset(base, co, bounded_vals, Yp, Kp):
    """FreeCoset of points with Π bounded^a Π free^v ≡ Yp (mod b^Kp); None if empty."""
    f = len(base.free)
    ck = CosetK(co.v, co.U)
    for p, e in base.bp.items():
        j = Kp * e; m = p ** j
        a = bounded_vals[base.bounded.index(p)]
        Y = Yp % m
        if j <= a:
            if Y != 0: return None
            continue
        if Y % (p ** a) or (Y // p ** a) % p == 0: return None
        jj = j - a
        if jj == 0: continue
        mm = p ** jj
        Z = (Y // p ** a) % mm
        for p2, a2 in zip(base.bounded, bounded_vals):          # divide out the other bounded primes
            if p2 != p: Z = Z * pow(pow(p2, a2, mm), -1, mm) % mm
        # now Π free^v ≡ Z (mod p^jj)
        coordsZ, mods = unit_group_log(base, p, jj, Z)
        if not mods: continue
        gen_logs = [unit_group_log(base, p, jj, q % p ** jj)[0] for q in base.free]
        for ci, mo in enumerate(mods):
            A = [gl[ci] for gl in gen_logs]
            ck = ck.intersect_congruence(A, coordsZ[ci], mo)
            if ck is None: return None
    return FreeCoset(ck.v0, _lll(ck.U) if len(ck.U) > 1 else ck.U)

def pinning_K(base, co, bounded_vals, kcap=200):
    """largest K with Π free^γ ≡ 1 (mod p^(K e_p - a_p)) for each base prime, on the basis."""
    K = 0
    for k in range(1, kcap + 1):
        ok = True
        for p, e in base.bp.items():
            a = bounded_vals[base.bounded.index(p)]; j = k * e - a
            if j <= 0: continue
            m = p ** j
            for u in co.U:
                if math.prod(pow(q, ui, m) for q, ui in zip(base.free, u)) % m != 1: ok = False; break
            if not ok: break
        if not ok: break
        K = k
    return K

def value_mod(base, co, bounded_vals, K):
    m = base.b ** K
    Y = 1
    for p, a in zip(base.bounded, bounded_vals): Y = Y * pow(p, a, m) % m
    for q, v in zip(base.free, co.v): Y = Y * pow(q, v, m) % m
    return Y

def tail_digits(base, Y, K):
    d = []
    for _ in range(K): d.append(Y % base.b); Y //= base.b
    return d   # position 0 first

# ----------------------------------------------------------------------------- classification + descent
def classify(base, co, bounded_vals, D, nu, eps, L, M, kcap):
    K = pinning_K(base, co, bounded_vals, kcap)
    if K == 0: return 'OPEN', None, 0
    Y = value_mod(base, co, bounded_vals, K)
    sol = None
    if Y >= base.b:
        dg = base.digits(Y); n = len(dg)
        if n % L == nu % L and 0 not in dg and Counter(d for d in dg if d != 1) == Counter(M):
            fct = base.factor(Y)
            if fct is not None and all(fct[base.dp.index(p)] == a for p, a in zip(base.bounded, bounded_vals)):
                free_e = tuple(fct[base.dp.index(q)] for q in base.free)
                if co.contains(free_e):
                    want = Counter((d, e % L) for d, e in zip(D, eps))
                    have = Counter((d, i % L) for i, d in enumerate(reversed(dg)) if d != 1)
                    if have == want: sol = Y
    tail = tail_digits(base, Y, K)
    open_ok = 0 not in tail
    if open_ok:
        have = Counter((d, i % L) for i, d in enumerate(tail) if d != 1)
        want = Counter((d, e % L) for d, e in zip(D, eps))
        if any(have[k] > want[k] for k in have): open_ok = False
    if sol is not None and not open_ok: return 'SOLUTION', sol, K
    if sol is not None: return 'SOLUTION+OPEN', sol, K
    return ('OPEN' if open_ok else 'DEAD'), None, K

def vp(x, p):
    c = 0
    while x % p == 0: x //= p; c += 1
    return c

def descend(base, co, bounded_vals, D, eps, nu, L, M, K, kcap, depth=0):
    """-> (status, solutions)"""
    b = base.b
    Y = value_mod(base, co, bounded_vals, K)
    sols = set()
    if Y >= b:
        dg = base.digits(Y)
        if 0 not in dg and len(dg) % L == nu % L and Counter(d for d in dg if d != 1) == Counter(M):
            fct = base.factor(Y)
            if fct is not None and all(fct[base.dp.index(p)] == a for p, a in zip(base.bounded, bounded_vals)):
                if co.contains(tuple(fct[base.dp.index(q)] for q in base.free)):
                    want = Counter((d, e % L) for d, e in zip(D, eps)); have = Counter((d, i % L) for i, d in enumerate(reversed(dg)) if d != 1)
                    if have == want: sols.add(Y)
    tail = tail_digits(base, Y, K)
    if 0 in tail: return 'DEAD', sols
    avail = list(zip(D, eps))
    for i, d in enumerate(tail):
        if d == 1: continue
        j = next((j for j, (dd, e) in enumerate(avail) if dd == d and e % L == i % L), None)
        if j is None: return 'DEAD', sols
        avail.pop(j)
    # valuation lemma for each base prime: (b-1)y = b^n + Σ_high (b-1)(d-1) b^e + ((b-1)Y - b^K)
    best_t = None
    for p, e in base.bp.items():
        Z = (b - 1) * Y - b ** K
        if Z == 0: continue
        t = vp(Z, p); a = bounded_vals[base.bounded.index(p)]
        if a != t:
            win = t // e
            best_t = win if best_t is None else min(best_t, win)
    if best_t is None: return 'OPEN', sols
    if best_t < K: return 'DEAD', sols
    status = 'DEAD'
    if not avail:
        for n in range(K + 1, best_t + 1):
            if n % L != nu % L: continue
            y = Y + b ** K * base.R(n - K)
            fct = base.factor(y)
            if fct is not None and all(fct[base.dp.index(p)] == a for p, a in zip(base.bounded, bounded_vals)) \
               and co.contains(tuple(fct[base.dp.index(q)] for q in base.free)) and Counter(d for d in base.digits(y) if d != 1) == Counter(M) and 0 not in base.digits(y):
                sols.add(y)
        return status, sols
    if depth > 12: return 'OPEN', sols
    for j, (d, e_res) in enumerate(avail):
        for pos in range(K, best_t + 1):
            if pos % L != e_res % L: continue
            Yp = Y + b ** K * base.R(pos - K) + d * b ** pos
            Kp = pos + 1
            co2 = cut_coset(base, co, bounded_vals, Yp, Kp)
            if co2 is None: continue
            K2 = pinning_K(base, co2, bounded_vals, kcap)
            assert K2 >= Kp
            D2 = tuple(dd for i2, (dd, _) in enumerate(avail) if i2 != j); e2 = tuple(ee for i2, (_, ee) in enumerate(avail) if i2 != j)
            # rebuild full lists from the new tail
            Y2 = value_mod(base, co2, bounded_vals, K2); tail2 = tail_digits(base, Y2, K2)
            consumed = [(dd, i) for i, dd in enumerate(tail2) if dd != 1]
            Dfull = tuple(dd for dd, _ in consumed) + D2; efull = tuple(i for _, i in consumed) + e2
            st, s2 = descend(base, co2, bounded_vals, Dfull, efull, nu, L, M, K2, kcap, depth + 1)
            sols |= s2
            if st == 'OPEN': status = 'OPEN'
    return status, sols

# ----------------------------------------------------------------------------- patterns
def canon(D, nu, eps):
    groups = defaultdict(list)
    for d, e in zip(D, eps): groups[d].append(e)
    return (nu, tuple(e for d in sorted(groups) for e in sorted(groups[d])))

def pattern_iter(D, L):
    cnt = Counter(D); digits = sorted(cnt)
    pools = [list(itertools.combinations_with_replacement(range(L), cnt[d])) for d in digits]
    for combo in itertools.product(*pools):
        yield tuple(e for part in combo for e in part)

# ----------------------------------------------------------------------------- the solver
def solve_equation(base, s, M, known, levels, kcap=200, verbose=False, time_budget=None, resume=None):
    """resume = dict(levels_done=(...), survivors=[(bv, nu, eps, FreeCoset)], lattice_free=[...], solutions=set())
    continues the lift from the recorded open set instead of enumerating the first level."""
    M = tuple(sorted(M)); D = M; q = len(D)
    bounded_tuples, bounds = base.admissible_bounded(M)
    f = len(base.free); kdim = base.k
    known_here = []
    for y in known:
        dg = base.digits(y)
        if Counter(d for d in dg if d != 1) == Counter(M):
            fct = base.factor(y); pos = sorted((d, i) for i, d in enumerate(reversed(dg)) if d != 1)
            assert fct is not None, f"POSITIVE CONTROL INVALID: {y} is not a product of the digit primes"
            known_here.append((y, len(dg), tuple(e for _, e in pos), fct))
    results = {'s': s, 'M': M, 'bounds': bounds, 'levels': [], 'solutions': set(), 'open': [], 'descent_sols': 0}
    used = set(); survivors = None; L_prev = None; t0 = time.time()
    lattice_free = None     # basis of the free-exponent lattice at the current level (fixed per level)
    if resume is not None:
        for L0 in resume['levels_done']: used.update(primes_for_level(base, L0, used))
        survivors = list(resume['survivors']); L_prev = resume['levels_done'][-1]
        lattice_free = [tuple(u) for u in resume['lattice_free']]
        results['solutions'] |= set(resume.get('solutions', ()))
        levels = tuple(L for L in levels if L > L_prev)
    for L in levels:
        ps = primes_for_level(base, L, used); used.update(ps)
        pdata = [PrimeData(base, p, L) for p in ps]
        first = survivors is None
        if first:
            lev = Level(pdata, [tuple(pd.logs) for pd in pdata], kdim)
            # free sublattice: kernel ∩ {bounded coords = 0}
            ck = CosetK((0,) * kdim, lev.kernel)
            for p in base.bounded:
                idx = base.dp.index(p); A = [1 if i == idx else 0 for i in range(kdim)]
                ck = ck.intersect_equation(A, 0)
            free_idx = [base.dp.index(q) for q in base.free]
            lattice_free = [tuple(u[i] for i in free_idx) for u in ck.U]
            if len(lattice_free) > 1: lattice_free = [tuple(u) for u in _lll(lattice_free)]
            cand = ((nu, eps) for nu in range(L) for eps in pattern_iter(D, L))
            n_in = L
            for d, k in Counter(D).items(): n_in *= comb(L + k - 1, k)
        else:
            # lift level: generators = images of the free lattice basis
            gens = []
            for pd in pdata:
                gl = [pd.logs[base.dp.index(q)] for q in base.free]
                gens.append(tuple(sum(u[i] * gl[i] for i in range(f)) % (pd.p - 1) for u in lattice_free))
            lev = Level(pdata, gens, len(lattice_free))
            new_lattice = [tuple(sum(t[i] * lattice_free[i][k2] for i in range(len(lattice_free))) for k2 in range(f)) for t in lev.kernel]
            if len(new_lattice) > 1: new_lattice = [tuple(u) for u in _lll(new_lattice)]
            def _lift_children(survivors=survivors, L_prev=L_prev):
                seen = set()
                for (bv, nu, eps, co) in survivors:
                    for dn in (0, L_prev):
                        for de in itertools.product((0, L_prev), repeat=q):
                            key = (bv,) + canon(D, nu + dn, tuple(e + x for e, x in zip(eps, de)))
                            if key in seen: continue
                            seen.add(key); yield (bv, key[1], key[2], co)
            cand = _lift_children(); n_in = 0
        # streaming: every survivor is classified (and descended) as soon as it is produced; only the
        # OPEN ones are kept.  Memory is O(#open), not O(#patterns x #bounded tuples).
        ctrl_keys = {}
        for (y, n, es, fct) in known_here:
            if y in results['solutions']: continue
            bvy = tuple(fct[base.dp.index(p)] for p in base.bounded); fe = tuple(fct[base.dp.index(qq)] for qq in base.free)
            ctrl_keys.setdefault((bvy,) + canon(D, n % L, tuple(e % L for e in es)), []).append((y, fe))
        ctrl_hit = {y: [False, False] for (y, n, es, fct) in known_here if y not in results['solutions']}
        nsurv = 0; dead = 0; cls = Counter(); sols = set(); open_ = []
        def _consume(bv, nu, eps, co):
            nonlocal nsurv
            nsurv += 1
            for (y, fe) in ctrl_keys.get((bv, nu, eps), ()):
                ctrl_hit[y][0] = True
                if co.contains(fe): ctrl_hit[y][1] = True
            kind, val, K = classify(base, co, bv, D, nu, eps, L, M, kcap)
            if kind.startswith('SOLUTION'): sols.add(val)
            if kind in ('OPEN', 'SOLUTION+OPEN'):
                if K >= 1:
                    st, s2 = descend(base, co, bv, D, eps, nu, L, M, K, kcap)
                    sols.update(s2); kind = 'OPEN' if st == 'OPEN' else 'RESOLVED(descent)'
                    results['descent_sols'] += len(s2)
                else: kind = 'OPEN'
            cls[kind] += 1
            if kind == 'OPEN': open_.append((bv, nu, eps, co))
        for item in cand:
            if first: nu, eps = item
            else: bv, nu, eps, co = item; n_in += 1
            logs = []
            for pd in pdata:
                y = pd.R[nu % L]
                for d, e in zip(D, eps): y = (y + (d - 1) * pd.powb[e % L]) % pd.p
                if y == 0: logs = None; break
                logs.append(pd.log(y))
            if logs is None: dead += 1; continue
            if first:
                t = lev.solve(logs)
                if t is None: dead += 1; continue
                # split by bounded exponents: points of t + kernel with those coordinates
                for bv in bounded_tuples:
                    ck = CosetK(t, lev.kernel)
                    ok = True
                    for p, a in zip(base.bounded, bv):
                        idx = base.dp.index(p); A = [1 if i == idx else 0 for i in range(kdim)]
                        ck = ck.intersect_equation(A, a)
                        if ck is None: ok = False; break
                    if not ok: continue
                    free_idx = [base.dp.index(qq) for qq in base.free]
                    v = tuple(ck.v0[i] for i in free_idx)
                    _consume(bv, nu, eps, FreeCoset(v, lattice_free))
            else:
                targets = []
                for pd, lg in zip(pdata, logs):
                    w = lg
                    for p, a in zip(base.bounded, bv): w -= a * pd.logs[base.dp.index(p)]
                    for qq, vv in zip(base.free, co.v): w -= vv * pd.logs[base.dp.index(qq)]
                    targets.append(w % (pd.p - 1))
                t = lev.solve(targets)
                if t is None: dead += 1; continue
                v = tuple(co.v[k2] + sum(t[i] * lattice_free[i][k2] for i in range(len(lattice_free))) for k2 in range(f))
                _consume(bv, nu, eps, FreeCoset(v, new_lattice))
        if not first: lattice_free = new_lattice
        # positive controls (checked during the stream)
        for y, (found_pat, found_pt) in ctrl_hit.items():
            assert found_pat, f"POSITIVE CONTROL LOST at level {L}: y={y}"
            assert found_pt, f"POSITIVE CONTROL coset miss at level {L}: y={y}"
        results['levels'].append((L, ps, n_in, nsurv, dict(cls), round(time.time() - t0, 1)))
        results['solutions'] |= sols
        if verbose: print(f"   L={L} primes={ps} in={n_in} surv={len(surv)} -> {dict(cls)} sols={sorted(sols)} [{time.time()-t0:.0f}s]", flush=True)
        survivors = open_; L_prev = L
        if not open_: break
        if time_budget and time.time() - t0 > time_budget: break
    results['open'] = survivors
    results['lattice_free'] = lattice_free
    found = {y for y in results['solutions'] if y >= base.b}
    results['closed'] = (not survivors) and found == {k[0] for k in known_here}
    results['bound_digits'] = None
    if survivors:
        sh = min(co.shortest() for (_, _, _, co) in survivors)
        results['bound_digits'] = sh / (2 * math.sqrt(len(base.free))) * math.log(min(base.free)) / math.log(base.b)
    return results

# ----------------------------------------------------------------------------- brute force oracle
def brute(base, M, nmax):
    q = len(M); out = set()
    for n in range(q, nmax + 1):
        R = base.R(n)
        for es in itertools.combinations(range(n), q):
            for arr in set(itertools.permutations(M)):
                y = R + sum((d - 1) * base.b ** e for d, e in zip(arr, es[::-1]))
                if y >= base.b and base.factor(y) is not None and y % base.b:
                    out.add(y)
    return out

if __name__ == "__main__":
    b = int(sys.argv[1]); s = int(sys.argv[2]); levels = tuple(int(x) for x in sys.argv[3].split(',')) if len(sys.argv) > 3 else (12, 24)
    base = Base(b)
    # known children: brute force to 14 digits as the oracle
    for M in base.multisets(s):
        kn = sorted(brute(base, M, 14))
        r = solve_equation(base, s, M, kn, levels, verbose=True)
        print(f"base {b} s={s} M={M}: {'CLOSED' if r['closed'] else 'OPEN('+str(len(r['open']))+')'} sols={sorted(r['solutions'])} brute(<=14 digits)={kn} bounds={r['bounds']}")
