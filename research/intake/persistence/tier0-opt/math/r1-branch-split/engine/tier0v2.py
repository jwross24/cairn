#!/usr/bin/env python3
"""
tier0.py — children of a vertex s of the antecedent tree, by modular lifting (BCGN 2021 method).

A child of s is y = 2^a 3^b 7^c whose digit product is s. Fix the multiset M of non-1 digits
(product s) and an arrangement D = (d_1..d_q) of it; then
    y = R_n + sum_j (d_j - 1) 10^{e_j},   e_1 > e_2 > ... > e_q >= 0,  e_1 < n,  R_n = (10^n-1)/9.
Unknowns: n, e_j (free), a (bounded 2-adically), b, c (free).

Method.
  A. 2-adic bound: a = v2(y) is decided by the last few digits; enumerate admissible tails
     divisible by 2^k until none exist -> a <= A.
  B. Level L: for each prime p | 10^L - 1, p not in {2,3,5,7}, y mod p depends only on
     (n mod L, e_j mod L).  y mod p must lie in 2^a <3,7>_p, i.e.
         b*log3 + c*log7 ≡ log(y_p) - a*log2   (mod p-1)       (DLog base a primitive root).
     The congruences over all primes carve a coset of a lattice in (b,c) ∈ Z^2, or nothing.
  C. Lifting: a surviving residue pattern at level L splits into 2^{q+1} patterns at level 2L
     (each exponent residue gains one bit); the inherited coset meets the new primes' congruences.
  D. 10-adic pinning: on a coset, 3^b 7^c mod 10^K is constant for K <= K*(coset); so the last K*
     digits of y are known. Either n <= K* (then y is known exactly: verify) or n > K* (the
     known tail must be digits from {1} ∪ M at positions consistent with the pattern: else dead).
Outcome per (D, a, pattern): DEAD, SOLUTION (exact y), or OPEN (consistent, n > K*, unresolved).
An equation is CLOSED when no OPEN pattern remains at the final level: its children are exactly
the SOLUTIONs found.

Positive control: every known child from the verified zero-free enumeration (<10^4000) must
survive at every level with its true (b,c) in the coset, and be recovered as a SOLUTION.
"""
import sys, time, itertools, os, math, functools
from math import gcd
from collections import Counter, defaultdict
import sympy
from sympy.ntheory import primitive_root
from dlog import discrete_log
from lattice import Coset
from lattice3 import CosetK
from fastlevel import FastLevel, FastLevelGen
FASTLIFT = os.environ.get('NOFASTLIFT') is None
DESCENT_MAX = int(float(os.environ.get('DESCENT_MAX', '1e18')))   # eager descent by default; set e.g. 2000 to defer
from descent import descend
import pydesc
import branchsplit
USE_PYDESC = pydesc.ENABLED
import os
PREFILTER = os.environ.get('NOPREFILTER') is None

# ----------------------------------------------------------------------------- utilities
def v2(x):
    return 0 if x == 0 else (x & -x).bit_length() - 1

def factor237(y):
    e = {2: 0, 3: 0, 7: 0}
    for p in (2, 3, 7):
        while y % p == 0:
            y //= p; e[p] += 1
    return (e[2], e[3], e[7]) if y == 1 else None

def multisets(s):
    out = []
    def rec(n, mind, cur):
        if n == 1: out.append(tuple(cur)); return
        for d in range(mind, 10):
            if n % d == 0:
                cur.append(d); rec(n // d, d, cur); cur.pop()
    rec(s, 2, [])
    return out

def arrangements(M):
    return sorted(set(itertools.permutations(M)))

# ----------------------------------------------------------------------------- step A
def two_adic_bound(M, kcap=200):
    return _two_adic_bound(tuple(M), kcap)

@functools.lru_cache(maxsize=None)
def _two_adic_bound(M, kcap):
    """largest possible v2(y) over numbers whose non-1 digits form a sub-multiset of M."""
    M = Counter(M)
    # states: (tail value, remaining multiset, ended) with tail ≡ 0 mod 2^k; `ended` means the
    # number has no more digits (so only leading zeros may be prepended): covers short numbers.
    states = {(0, tuple(sorted(M.elements())), False)}
    for k in range(1, kcap):
        new = set()
        for tail, rem, ended in states:
            choices = {0} if ended else ({0, 1} | set(rem))
            for d in choices:
                t = d * 10 ** (k - 1) + tail
                if t % (2 ** k) == 0:
                    if d == 0:
                        if tail: new.add((t, rem, True))   # a number must be positive
                    elif d == 1:
                        new.add((t, rem, False))
                    else:
                        r = list(rem); r.remove(d); new.add((t, tuple(r), False))
        if not new:
            return k - 1
        states = new
    raise RuntimeError("2-adic bound did not terminate")

# ----------------------------------------------------------------------------- primes
class PrimeData:
    def __init__(self, p, L):
        self.p, self.L = p, L
        g = primitive_root(p)
        self.g = g
        self.l2 = discrete_log(p, 2 % p, g)
        self.l3 = discrete_log(p, 3 % p, g)
        self.l7 = discrete_log(p, 7 % p, g)
        assert pow(g, self.l2, p) == 2 % p and pow(g, self.l3, p) == 3 % p and pow(g, self.l7, p) == 7 % p
        self.inv9 = pow(9, -1, p)
        self.pow10 = [pow(10, i, p) for i in range(L)]
        self.R = [(self.pow10[i] - 1) * self.inv9 % p for i in range(L)]
        self.table = None
        if p < 3_000_000:
            tbl = [0] * p
            x = 1
            for i in range(p - 1):
                tbl[x] = i
                x = x * g % p
            self.table = tbl

    def log(self, x):
        if self.table is not None:
            return self.table[x]
        lg = discrete_log(self.p, x, self.g)
        assert pow(self.g, lg, self.p) == x % self.p
        return lg

    def constraint(self, nu, eps, D, a):
        """return (A,B,r,m) for b*A + c*B ≡ r mod m, or None if y ≡ 0 mod p (impossible)."""
        p = self.p
        y = self.R[nu % self.L]
        for d, e in zip(D, eps):
            y = (y + (d - 1) * self.pow10[e % self.L]) % p
        if y == 0:
            return None
        r = (self.log(y) - a * self.l2) % (p - 1)
        return (self.l3, self.l7, r, p - 1)

class Prefilter:
    """Exact membership test  w - a*v2 ∈ H  in G = ∏_p Z/(p-1), decomposed into ℓ-primary parts.
    H = <v3, v7>. For each prime ℓ dividing some p-1, G_ℓ = ∏ Z/ℓ^k and H_ℓ = image of (b,c).
    w ∈ a v2 + H  iff  for every ℓ, w_ℓ - a v2_ℓ ∈ H_ℓ (H is the internal direct sum of its H_ℓ).
    Components whose G_ℓ exceeds `cap` are left out: the test stays a valid necessary condition."""
    def __init__(self, pdatas, cap=3_000_000, three_d=False):
        self.pdatas = pdatas; self.three_d = three_d
        comps = defaultdict(list)       # ℓ -> list of (prime index, ℓ^k)
        for i, pd in enumerate(pdatas):
            for l, k in sympy.factorint(pd.p - 1).items():
                comps[l].append((i, l ** k))
        self.comps = []
        for l, lst in sorted(comps.items()):
            size = 1
            for _, m in lst: size *= m
            if size > cap:
                continue
            v2 = tuple(pdatas[i].l2 % m for i, m in lst)
            v3 = tuple(pdatas[i].l3 % m for i, m in lst)
            v7 = tuple(pdatas[i].l7 % m for i, m in lst)
            mods = tuple(m for _, m in lst)
            H = {tuple(0 for _ in lst)}
            frontier = list(H)
            gens = (v3, v7) if not three_d else (v2, v3, v7)
            while frontier:
                nxt = []
                for h in frontier:
                    for g in gens:
                        t = tuple((x + y) % m for x, y, m in zip(h, g, mods))
                        if t not in H:
                            H.add(t); nxt.append(t)
                frontier = nxt
            self.comps.append((lst, mods, v2, H))
        self.sizes = [(len(H), 1) for (_, _, _, H) in self.comps]

    def admissible(self, logs, a=None):
        """logs[i] = log_{g_i}(y mod p_i); returns True if the level's system may be solvable."""
        for lst, mods, v2, H in self.comps:
            if a is None:
                t = tuple(logs[i] % m for (i, m) in lst)
            else:
                t = tuple((logs[i] - a * v) % m for (i, m), v in zip(lst, v2))
            if t not in H:
                return False
        return True


def primes_for_level(L, exclude):
    ps = sorted(int(p) for p in sympy.factorint(10 ** L - 1) if int(p) not in (2, 3, 5, 7))
    return [p for p in ps if p not in exclude]

_LEVEL_CACHE = {}

def chain_step(levels, idx, gen=None):
    """PrimeData, Prefilter, FastLevel/FastLevelGen of level levels[idx]; they depend only on the level prefix."""
    gen = FASTLIFT if gen is None else gen
    key = (tuple(levels[:idx + 1]), bool(gen))
    r = _LEVEL_CACHE.get(key)
    if r is not None:
        return r
    if idx == 0:
        used = set(); U_in = None
    else:
        prev = chain_step(levels, idx - 1, gen)
        used = set(prev['used']); U_in = prev['U']
    L = levels[idx]
    ps = primes_for_level(L, used)
    pdata = [PrimeData(p, L) for p in ps]
    used.update(ps)
    if idx == 0:
        pf = None; fl = FastLevel(pdata); fg = None; U = fl.U2
    else:
        pf = Prefilter(pdata); fl = None
        fg = FastLevelGen(pdata, U_in) if gen else None
        U = fg.U_new if fg is not None else U_in
    r = dict(ps=ps, pdata=pdata, pf=pf, fl=fl, fg=fg, U=U, used=used)
    _LEVEL_CACHE[key] = r
    return r

# ----------------------------------------------------------------------------- step D
def ten_adic_K(co, kcap, a=0):
    """largest K <= kcap such that 2^a 3^b 7^c mod 10^K is constant on the coset:
    3^β 7^γ ≡ 1 (mod 5^K) and (mod 2^(K-a)) for both basis vectors."""
    K = 0
    for k in range(1, kcap + 1):
        m5 = 5 ** k; m2 = 2 ** max(k - a, 0)
        ok = True
        for (be, ga) in (co.u1, co.u2):
            if pow(3, be, m5) * pow(7, ga, m5) % m5 != 1: ok = False; break
            if m2 > 1 and pow(3, be, m2) * pow(7, ga, m2) % m2 != 1: ok = False; break
        if not ok: break
        K = k
    return K

def classify(co, a, D, nu, eps, L, M, kcap):
    """-> ('DEAD', None) | ('SOLUTION', y) | ('OPEN', K)"""
    K = ten_adic_K(co, kcap, a)
    if K == 0:
        return ('OPEN', 0)
    mod = 10 ** K
    b0, c0 = co.v0
    Y = pow(2, a, mod) * pow(3, b0, mod) * pow(7, c0, mod) % mod
    # case n <= K: y = Y exactly
    sol = None
    if Y > 0:
        s = str(Y)
        n = len(s)
        if n % L == nu % L and '0' not in s:
            nonone = Counter(ch for ch in s if ch != '1')
            if nonone == Counter(str(d) for d in M):
                f = factor237(Y)
                if f is not None and f[0] == a and co.contains(f[1], f[2]):
                    # positions must match the pattern residues
                    pos = {}
                    for i, ch in enumerate(reversed(s)):
                        if ch != '1': pos.setdefault(ch, []).append(i)
                    want = defaultdict(list)
                    for d, e in zip(D, eps): want[str(d)].append(e % L)
                    okp = all(sorted(x % L for x in pos[k]) == sorted(want[k]) for k in want)
                    if okp:
                        sol = Y
    # case n > K: the last K digits of y are the zero-padded Y
    tail = str(Y).zfill(K)
    open_ok = True
    if '0' in tail:
        open_ok = False
    else:
        nonone = Counter(ch for ch in tail if ch != '1')
        Mc = Counter(str(d) for d in M)
        if any(nonone[k] > Mc[k] for k in nonone):
            open_ok = False
        else:
            # digits at positions i < K must appear in the pattern with residue i mod L
            want = Counter((str(d), e % L) for d, e in zip(D, eps))
            have = Counter((ch, i % L) for i, ch in enumerate(reversed(tail)) if ch != '1')
            if any(have[k] > want[k] for k in have):
                open_ok = False
            else:
                # moreover: pattern residues ε_j < K (as residues mod L, if K <= L) must be occupied.
                # Only valid when K <= L: a residue ε < K then forces an actual position < K
                # unless the true e_j ≥ L. So only use it as: for K <= L, every (d, ε) with ε < K
                # must be present in `have` OR e_j >= L (unknowable) -> no constraint. Skip.
                pass
    if sol is not None and not open_ok:
        return ('SOLUTION', sol)
    if sol is not None and open_ok:
        return ('SOLUTION+OPEN', sol)
    if open_ok:
        return ('OPEN', K)
    return ('DEAD', None)

# ----------------------------------------------------------------------------- driver
def canon(D, nu, eps):
    """canonical pattern: residues sorted within each digit group (D is sorted)."""
    groups = defaultdict(list)
    for d, e in zip(D, eps): groups[d].append(e)
    out = []
    for d in D:
        pass
    eps2 = tuple(e for d in sorted(groups) for e in sorted(groups[d]))
    return (nu, eps2)

def pattern_iter(D, L):
    """all multisets of residues per digit group, D sorted."""
    cnt = Counter(D)
    digits = sorted(cnt)
    pools = [list(itertools.combinations_with_replacement(range(L), cnt[d])) for d in digits]
    for combo in itertools.product(*pools):
        yield tuple(e for part in combo for e in part)

def solve_equation(s, D, known, levels=(12, 24, 48, 96), kcap=400, verbose=True, time_budget=None, l12=None, l12_n_in=None, presolved=(), lift_fn=None):
    D = tuple(sorted(D))
    M = D; q = len(D)
    A = two_adic_bound(M)
    t0 = time.time()
    results = {'s': s, 'D': D, 'A': A, 'levels': [], 'solutions': set(presolved), 'open': []}
    # known children with this arrangement
    known_here = []
    for y in known:
        assert y >= 10 and factor237(y) is not None, f"claimed child {y} is not in S"
        st = str(y)
        pos = [(int(ch), i) for i, ch in enumerate(reversed(st)) if ch != '1']
        if tuple(sorted(d for d, _ in pos)) == D:
            a, b, c = factor237(y)
            pos.sort()                          # by digit, then position: matches canonical order
            known_here.append((y, len(st), tuple(e for _, e in pos), a, b, c))
    if verbose:
        print(f"== s={s} D={D} A={A} known children with this arrangement: {[k[0] for k in known_here]}", flush=True)

    # level 1: enumerate all patterns mod L0
    L0 = levels[0]
    primes = {}
    used = set()
    L_prev = None
    survivors = None   # list of (a, nu, eps, coset)
    for idx_L, L in enumerate(levels):
        step = chain_step(levels, idx_L)
        ps = step['ps']
        pdata = step['pdata']
        first = survivors is None
        if survivors is None:
            def gen():
                for nu in range(L):
                    for eps in pattern_iter(D, L):
                        yield (None, nu, eps, None)
            cand = gen()
            n_in = L
            for d, k in Counter(D).items():
                n_in *= math.comb(L + k - 1, k)
        elif lift_fn is not None:
            cand = []; n_in = 0            # the C lift enumerates the children itself
        else:
            seen = set(); cand = []
            for (a, nu, eps, co) in survivors:
                for dn in (0, L_prev):
                    for de in itertools.product((0, L_prev), repeat=q):
                        nu2, eps2 = canon(D, nu + dn, tuple(e + x for e, x in zip(eps, de)))
                        key = (a, nu2, eps2)
                        if key in seen: continue
                        seen.add(key); cand.append((a, nu2, eps2, co))
            cand.sort(key=lambda t: (t[1], t[2], t[0]))
            n_in = len(cand)
        pf = step['pf']
        fl = step['fl']
        if first:
            U_level = fl.U2
            fg = None
        else:
            fg = step['fg']
            if fg is not None: U_level = fg.U_new
        surv = []
        dead_zero = dead_incons = dead_pre = 0
        if (not first) and lift_fn is not None:
            # external (C) lift: returns the filtered children with their cosets
            surv, n_in, stats = lift_fn(L_prev, L, survivors, fg)
            cand = []
            dead_zero, dead_pre = stats.get('zero', 0), stats.get('dead', 0)
        last_key = None; logs = None
        if first and l12 is not None:
            cand = []; surv = l12 if isinstance(l12, pydesc.RawSurv) else list(l12); n_in = l12_n_in or len(surv)
        for (a, nu, eps, co) in cand:
            key = (nu, eps)
            if key != last_key:          # candidates are grouped by pattern; logs shared across a
                last_key = key; logs = []
                for pd in pdata:
                    y = pd.R[nu % pd.L]
                    for d, e in zip(D, eps):
                        y = (y + (d - 1) * pd.pow10[e % pd.L]) % pd.p
                    if y == 0:
                        logs = None; break
                    logs.append(pd.log(y))
            if logs is None:
                dead_zero += 1; continue
            if first:
                v = fl.solve(logs)
                if v is None:
                    dead_pre += 1; continue
                assert fl.verify(v, logs)
                for a0, co in fl.split_by_a(v, A):
                    surv.append((a0, nu, eps, co))
                continue
            if fg is not None:
                co2 = fg.solve(a, co.v0, logs)
                if co2 is None:
                    dead_pre += 1; continue
                surv.append((a, nu, eps, co2)); continue
            if PREFILTER and not pf.admissible(logs, a):
                dead_pre += 1; continue
            ok = True
            for pd, lg in zip(pdata, logs):
                cs = (pd.l3, pd.l7, (lg - a * pd.l2) % (pd.p - 1), pd.p - 1)
                co2 = co.intersect(*cs)
                if co2 is None:
                    dead_incons += 1; ok = False; break
                co = co2
            if ok:
                surv.append((a, nu, eps, co))
        if not isinstance(surv, pydesc.RawSurv) and lift_fn is None:
            surv = branchsplit.filter_list(D, surv, f'py{L}')
        # positive controls
        for (y, n, es, a, b, c) in known_here:
            if y in results['solutions']:
                continue                      # already recovered exactly at an earlier level
            cn = canon(D, n % L, tuple(e % L for e in es))
            hit = [t for t in surv if t[0] == a and (t[1], t[2]) == cn]
            assert hit, f"POSITIVE CONTROL LOST at level {L}: y={y}"
            assert any(t[3].contains(b, c) for t in hit), f"POSITIVE CONTROL coset miss at level {L}: y={y}"
        # classify
        cls = Counter(); sols = set(); open_ = []
        # descent is a resolution step, not a filter: when many patterns survive and a cheaper
        # level remains, lift first (C) and descend the few that come back.
        do_descent = (L == levels[-1]) or (len(surv) <= DESCENT_MAX) or (lift_fn is None)
        c_raw = surv.classify(D, L, kcap, do_descent) if (USE_PYDESC and isinstance(surv, pydesc.RawSurv) and len(surv)) else None
        if c_raw is not None:
            for kind, n_kind in c_raw[0]:
                cls[kind] += n_kind
            sols.update(c_raw[1])
            open_.extend(c_raw[2])
        c_res = pydesc.classify_batch(surv, D, L, kcap, do_descent) if (USE_PYDESC and c_raw is None and len(surv)) else None
        for idx, (a, nu, eps, co) in enumerate(surv if c_raw is None else ()):
            if c_res is not None and c_res[idx][0] != pydesc.CODE_FALLBACK:
                code, csols = c_res[idx]
                kind = pydesc.KIND[code]
                sols.update(csols)
                cls[kind] += 1
                if kind == 'OPEN': open_.append((a, nu, eps, co))
                continue
            kind, val = classify(co, a, D, nu, eps, L, M, kcap)
            if kind.startswith('SOLUTION'): sols.add(val)
            if kind in ('OPEN', 'SOLUTION+OPEN'):
                K = ten_adic_K(co, kcap, a)
                if K >= 1 and do_descent:
                    st, s2 = descend(a, D, eps, nu, co, L, M, K, kcap)
                    sols |= s2
                    kind = 'OPEN' if st == 'OPEN' else 'RESOLVED(descent)'
                else:
                    kind = 'OPEN'
            cls[kind] += 1
            if kind == 'OPEN': open_.append((a, nu, eps, co))
        el = time.time() - t0
        results['levels'].append((L, ps, n_in, len(surv), dict(cls), el))
        results['solutions'] |= sols
        if verbose:
            print(f"   L={L:3d} primes={ps} in={n_in} survived={len(surv)} "
                  f"(dead: y≡0 {dead_zero}, prefilter {dead_pre}, lattice {dead_incons}) -> {dict(cls)}  "
                  f"sols={sorted(sols)}  [{el:.0f}s]", flush=True)
        survivors = open_
        L_prev = L
        if not open_:
            break
        if time_budget and el > time_budget:
            if verbose: print("   time budget exhausted", flush=True)
            break
    results['open'] = survivors
    results['bs'] = {k: list(v) for k, v in branchsplit.COUNTS.items()}
    # solutions must be exactly the known children
    found = {y for y in results['solutions'] if y >= 10}; kn = {k[0] for k in known_here}
    results['closed'] = (not survivors) and found == kn
    results['new_children'] = found - kn
    results['missing_children'] = kn - found
    return results


if __name__ == "__main__":
    s = int(sys.argv[1])
    kn = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 and sys.argv[2] else []
    budget = float(sys.argv[3]) if len(sys.argv) > 3 else None
    allres = []
    for M in multisets(s):
        for D in [tuple(sorted(M))]:
            r = solve_equation(s, D, kn, time_budget=budget)
            allres.append(r)
            print(f"   => {'CLOSED' if r['closed'] else 'OPEN'}; open patterns {len(r['open'])}; "
                  f"new {sorted(r['new_children'])} missing {sorted(r['missing_children'])}", flush=True)
    nc = sum(r['closed'] for r in allres)
    print(f"\nVERTEX s={s}: {nc}/{len(allres)} equations closed; "
          f"children found {sorted(set().union(*(r['solutions'] for r in allres)))}")
