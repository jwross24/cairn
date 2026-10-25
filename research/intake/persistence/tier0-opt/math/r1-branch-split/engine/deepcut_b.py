#!/usr/bin/env python3
"""
deepcut_b.py — Lemma C (full-depth b-adic cut) for a base-b run (see DEEPCUT.md for base 10).

For every open pattern (bounded exps bv, ν, positions e_j in [0, L), anchor y) of a run_base(_mp).py output:
coset = v_y + Λ_L in the free exponents (Λ_L = kernel of the free primes' logs at all level primes of
b^L − 1); every candidate other than the anchor has ≥ (height bound) ≫ L·D digits, so its lowest L·D
digits are R_{LD} + Σ (d_j − 1) b^{e_j + L t_j} for a choice of copies t_j; engine_b.cut_coset imposes the
b-adic congruences (v_p for each base prime p | b, then the unit-group logs) at K = L·D.

Usage: python3 deepcut_b.py <b> <jsonl> [--levels 12,24,48,96] [--depth 2]
"""
import sys, json, math, itertools, time
from collections import Counter, defaultdict
from engine_b import Base, PrimeData, primes_for_level, FreeCoset, cut_coset, solve_equation
from lattice3 import CosetK
from engine_b import _lll

def kernel_lattice(base, levels):
    f = len(base.free); ck = CosetK.full(f); used = set()
    for L in levels:
        ps = primes_for_level(base, L, used); used.update(ps)
        for p in ps:
            pd = PrimeData(base, p, L)
            A = [pd.logs[base.dp.index(q)] for q in base.free]
            ck = ck.intersect_congruence(A, 0, p - 1)
    U = _lll(ck.U) if f > 1 else ck.U
    return [tuple(u) for u in U]

def point_to_y(base, bv, pt):
    y = 1
    for p, a in zip(base.bounded, bv): y *= p ** a
    for q, v in zip(base.free, pt): y *= q ** v
    return y

def deep_cut(base, co0, bv, nu, De, L, depth, maxcases):
    b = base.b
    survivors = [(co0, ())]; stats = []; cases = 0
    for D in range(1, depth + 1):
        K = L * D; RK = base.R(K); new = []
        for co, assigned in survivors:
            fixed = dict(assigned)                                   # digit index j -> copy t (indices, not (d,e): repeated (d,e) pairs are distinct digits)
            free = [j for j in range(len(De)) if j not in fixed]
            for choice in itertools.product((0, 1), repeat=len(free)):
                taken = Counter(De[j][1] for j, c in zip(free, choice) if c)
                if any(cnt > 1 for cnt in taken.values()): continue
                Lv = RK
                for j, t in fixed.items(): Lv += (De[j][0] - 1) * b ** (De[j][1] + L * t)
                for j, c in zip(free, choice):
                    if c: Lv += (De[j][0] - 1) * b ** (De[j][1] + L * (D - 1))
                cases += 1
                if cases > maxcases: return None, None, cases, stats
                co2 = cut_coset(base, co, bv, Lv, K)
                if co2 is None: continue
                new.append((co2, assigned + tuple((j, D - 1) for j, c in zip(free, choice) if c)))
        survivors = new; stats.append(len(new))
        if not survivors: return True, None, cases, stats
    bound = min(co.shortest() for co, _ in survivors)
    f = len(base.free)
    return False, bound / (2 * math.sqrt(f)) * math.log(min(base.free)) / math.log(b), cases, stats

if __name__ == "__main__":
    b = int(sys.argv[1]); path = sys.argv[2]
    levels = tuple(int(x) for x in (sys.argv[sys.argv.index('--levels') + 1] if '--levels' in sys.argv else '12,24,48').split(','))
    depth = int(sys.argv[sys.argv.index('--depth') + 1]) if '--depth' in sys.argv else 2
    base = Base(b); L = levels[-1]; t0 = time.time()
    Lam = kernel_lattice(base, levels)
    print(f"base {b}: Λ_{L} basis {Lam}; shortest {min(math.hypot(*u) for u in Lam):.3e} [{time.time()-t0:.0f}s]", flush=True)
    rows = [json.loads(l) for l in open(path)]
    tot = Counter(); per_vertex = {}
    for r in rows:
        if not r['open']: continue
        s = r['s']; vclosed = True; worst = None
        for eq in r['eqs']:
            if not eq['open']: continue
            M = tuple(eq['M'])
            exc = eq.get('exceptional')
            if exc is None:
                res = solve_equation(base, s, M, eq['brute'], levels)
                exc = []
                for (bv, nu, eps, co) in res['open']:
                    pt = co.nearest(); y = point_to_y(base, bv, pt) if all(c >= 0 for c in pt) and max(pt) < 200 else None
                    exc.append([list(bv), nu, list(eps), y, False])
            for (bv, nu, eps, y, issol) in exc:
                if y is None: tot['NO-ANCHOR'] += 1; vclosed = False; continue
                fct = base.factor(y); assert fct is not None
                assert all(fct[base.dp.index(p)] == a for p, a in zip(base.bounded, bv)), (s, M, bv, y)
                v = tuple(fct[base.dp.index(q)] for q in base.free)
                co0 = FreeCoset(v, Lam)
                De = [(d, e % L) for d, e in zip(sorted(M), eps)]
                closed, bound, cases, stats = deep_cut(base, co0, tuple(bv), nu % L, De, L, depth, 300000)
                if closed is None: tot['BUDGET'] += 1; vclosed = False
                elif closed: tot['CLOSED'] += 1
                else:
                    tot['SURVIVES'] += 1; vclosed = False; worst = bound if worst is None or bound < worst else worst
        per_vertex[s] = (vclosed, worst)
        print(f"s={s:<12} {'CLOSED' if vclosed else f'bound 10^{worst:.1e} digits' if worst else 'open'} [{time.time()-t0:.0f}s]", flush=True)
    print(f"\nbase {b}: patterns {dict(tot)}; vertices with open patterns {len(per_vertex)}, now CLOSED {sum(1 for c, _ in per_vertex.values() if c)}")
