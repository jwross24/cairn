#!/usr/bin/env python3
"""
deepcut.py — the full-depth 10-adic cut for anchored open patterns (base 10).

An open pattern at level 96 with exact anchor y (OPEN-PATTERNS.md) has coset (b_y, c_y) + Λ_96, where
Λ_96 = {(Δb, Δc) : 3^Δb 7^Δc ≡ 1 mod p for every prime p | 10^96 − 1, p ≠ 3}.  Any candidate y′ ≠ y
has n ≥ ν + 96 digits (the lattice bound makes n ≥ 10^27), so its lowest 96 digits are determined up
to the choice S of which pattern positions e_j (as integers in [0, 96)) carry their digit at e_j itself
rather than at e_j + 96k:  y′ ≡ L_S := R_96 + Σ_{j∈S} (d_j − 1) 10^{e_j}  (mod 10^96).
Hence v₂(L_S) = a and 3^b 7^c ≡ L_S / 2^a (mod 5^96 and 2^{96−a}): three congruences that cut the coset
(descent.cut_coset with K = 96).  Each surviving sub-coset is refined again at K = 192 by the choice of
which remaining positions sit at e_j + 96, and so on.  Output per pattern: number of cases, survivors,
and the certified height bound (shortest vector of the finest sub-cosets), or CLOSED when no case
survives.  Everything is exact; the only inputs are the anchors from the sweep files.

Usage: python3 deepcut.py <jsonl files...> [--depth 2] [--maxcases 200000]
"""
import sys, json, math, time, itertools
from collections import Counter, defaultdict
from fractions import Fraction
from sympy import primitive_root, factorint, cyclotomic_poly, divisors
from lattice import Coset
from descent import cut_coset, v2
import classify_open as C

LMAX = 96

def level_primes():
    ps = set()
    for d in divisors(LMAX):
        ps |= set(int(p) for p in factorint(int(cyclotomic_poly(d, 10))))
    return sorted(p for p in ps if p not in (2, 3, 5, 7))

def kernel_lattice():
    from dlog import discrete_log
    co = Coset((0, 0), (1, 0), (0, 1))
    for p in level_primes():
        g = primitive_root(p)
        l3 = discrete_log(p, 3 % p, g); l7 = discrete_log(p, 7 % p, g)
        co = co.intersect(l3, l7, 0, p - 1)
        assert co is not None
    return co

def shortest(co):
    return min(math.hypot(*co.u1), math.hypot(*co.u2))

def nearest_norm(co):
    """exact min over coset points of hypot(b, c): Babai on the Lagrange-reduced basis + neighbour search."""
    u1, u2 = co.u1, co.u2; v0 = co.v0; det = u1[0] * u2[1] - u1[1] * u2[0]
    x = round(Fraction(-v0[0] * u2[1] + v0[1] * u2[0], det)); y = round(Fraction(v0[0] * u1[1] - v0[1] * u1[0], det))
    best = None
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            b = v0[0] + (x + dx) * u1[0] + (y + dy) * u2[0]; c = v0[1] + (x + dx) * u1[1] + (y + dy) * u2[1]
            nn = b * b + c * c
            if best is None or nn < best[0]: best = (nn, b, c)
    return best[0], (best[1], best[2])          # squared norm (exact integer)

def digits_bound(co):
    """certified: EVERY point (b, c) of the coset has hypot ≥ the exact nearest point's norm, hence
    max(b, c) ≥ norm/√2 and y = 2^a 3^b 7^c has ≥ max(b,c)·log10(3) digits.  (The old shortest/2 bound
    ignored the coset's own nearest point.)"""
    nn, _ = nearest_norm(co)
    if nn == 0: return -1.0
    return 0.5 * math.log10(nn) - 0.5 * math.log10(2) + math.log10(math.log10(3))   # LOG10 of the digit bound

def all_representations(M, y):
    """all (nu, eps) with y + k R_96 = R_nu + Σ (d_j − 1) 10^{e_j}, positions in [0,96), 0 ≤ k ≤ 9."""
    from functools import lru_cache
    M = tuple(sorted(M)); out = []
    RL = (10 ** LMAX - 1) // 9
    for k in range(0, 8 * len(M) + 2):          # pattern value = y + k R_96; digit mass ≤ 8|M|·10^95 ⇒ k ≤ 8|M|+1 (red team 4′)
        for nu in range(LMAX):
            target = y + k * RL - (10 ** nu - 1) // 9
            if target < 0: continue
            emax = len(str(target))
            sols = []
            def rec(e, rem_ms, rem, acc):
                if not rem_ms:
                    if rem == 0: sols.append(tuple(acc))
                    return
                if e > emax or e >= LMAX or rem < 0: return
                need = (rem // 10 ** e) % 10
                ms = list(rem_ms); tried = set()
                for kk in range(0, len(ms) + 1):
                    for sub in itertools.combinations(range(len(ms)), kk):
                        ds = tuple(ms[i] for i in sub)
                        if ds in tried: continue
                        tried.add(ds)
                        tot = sum(d - 1 for d in ds)
                        if tot % 10 != need: continue
                        rest = tuple(ms[i] for i in range(len(ms)) if i not in sub)
                        rec(e + 1, rest, rem - tot * 10 ** e, acc + [(d, e) for d in ds])
            rec(0, M, target, [])
            for s in sols: out.append((nu, s))
    return out

def deep_cut(co0, a, rep, depth, maxcases):
    """rep = list of (d, e). Returns (closed, bound_digits, cases, survivors_at_each_depth)."""
    nu, De = rep
    # positions grouped by class; at most one digit of a class can be at the lower copy
    bycls = defaultdict(list)
    for d, e in De: bycls[e].append(d)
    classes = sorted(bycls)
    # stage K: choose for each (d, e) its copy index t ≥ 0 (position e + 96 t); at depth D we fix all
    # copies with t < D and require the rest to be ≥ D; distinct positions ⇒ within a class the t's are distinct.
    survivors = [(co0, ())]        # (coset, assignment so far: tuple of (d,e,t))
    stats = []; cases = 0
    for D in range(1, depth + 1):
        K = LMAX * D; RK = (10 ** K - 1) // 9
        new = []
        for co, assigned in survivors:
            fixed = dict(assigned)                                   # digit index j -> copy t (indices, not (d,e): repeated (d,e) pairs are distinct digits)
            free = [j for j in range(len(De)) if j not in fixed]
            # choices for the free digits: copy D-1 (position e + 96(D-1)) or later
            for choice in itertools.product((0, 1), repeat=len(free)):
                # 1 = sits at copy D-1 now; check distinct positions within a class
                taken = Counter(De[j][1] for j, c in zip(free, choice) if c)
                if any(cnt > 1 for cnt in taken.values()): continue
                L = RK
                for j, t in fixed.items(): L += (De[j][0] - 1) * 10 ** (De[j][1] + LMAX * t)
                for j, c in zip(free, choice):
                    if c: L += (De[j][0] - 1) * 10 ** (De[j][1] + LMAX * (D - 1))
                cases += 1
                if cases > maxcases: return None, None, cases, stats
                if v2(L) != a or L % 5 == 0: continue        # 5 | L impossible for an S-unit (red team 7′)
                co2 = cut_coset(co, a, L, K)
                if co2 is None: continue
                new.append((co2, assigned + tuple((j, D - 1) for j, c in zip(free, choice) if c)))
        survivors = new
        stats.append(len(new))
        if not survivors: return True, None, cases, stats
    bound = min(digits_bound(co) for co, _ in survivors)
    return False, bound, cases, stats

if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if x.endswith('.jsonl')]
    depth = int(sys.argv[sys.argv.index('--depth') + 1]) if '--depth' in sys.argv else 2
    maxcases = int(sys.argv[sys.argv.index('--maxcases') + 1]) if '--maxcases' in sys.argv else 200000
    t0 = time.time(); Lam = kernel_lattice()
    print(f"Λ_96: shortest {shortest(Lam):.3e}, index {Lam.index():.3e}, base bound {digits_bound(Lam):.2e} digits [{time.time()-t0:.0f}s]", flush=True)
    only = None
    if '--only' in sys.argv:
        only = set(tuple(l.split()[:4]) for l in open(sys.argv[sys.argv.index('--only') + 1]) if l.strip())
    seen = set(); per_vertex = defaultdict(list); n_pat = n_closed = n_rep = 0
    for f in args:
        for (s, M, a, nu, eps, y, sol) in C.entries(f):
            key = (s, M, a, y, nu, None if eps is None else tuple(eps))     # full record (red team 2′)
            if key in seen: continue
            if only is not None and (str(s), ''.join(map(str, M)), str(a), str(y)) not in only: continue
            seen.add(key)
            fct = C.factor237(y); assert fct and fct[0] == a, (s, M, a, y, fct)
            co0 = Coset((fct[1], fct[2]), Lam.u1, Lam.u2)
            reps = all_representations(M, y)
            assert reps, ("no representation of the anchor", s, M, a, y)
            if nu is not None:        # the sweep recorded the pattern: keep exactly that one (no fallback; red team 2″)
                reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % LMAX for e in eps)]
                assert reps, ("recorded pattern not among the representations", s, M, a, y, nu, eps)
            n_pat += 1
            worst = None; closed_all = True; tcase = 0
            for rep in reps:
                n_rep += 1
                closed, bound, cases, stats = deep_cut(co0, a, rep, depth, maxcases)
                tcase += cases
                if closed is None: closed_all = False; worst = -1; break      # case budget exceeded
                if not closed:
                    closed_all = False
                    worst = bound if worst is None or bound < worst else worst
            per_vertex[s].append((M, a, y, len(reps), closed_all, worst, tcase))
            n_closed += closed_all
            print(f"s={s:<10} M={''.join(map(str,M)):<12} a={a:<2} y={y:<12} reps={len(reps):<3} cases={tcase:<7} "
                  f"{'CLOSED' if closed_all else ('BUDGET' if worst == -1 else f'bound 10^(10^{worst:.2f}) digits')}", flush=True)
    print(f"\n{n_pat} anchored patterns ({n_rep} representations): {n_closed} CLOSED outright by the deep cut; "
          f"others: bound ≥ 10^(10^{min(w for v in per_vertex.values() for (*_, c, w, t) in v if not c and w and w > 0):.2f}) digits [{time.time()-t0:.0f}s]")
