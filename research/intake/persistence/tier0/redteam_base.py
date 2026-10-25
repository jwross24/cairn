#!/usr/bin/env python3
"""
redteam_base.py — adversarial tests of the base-parametrized engine on a base's small vertices.

Two protocols on the same vertices (chosen: every vertex with known children and run time < 15 s):
  BLIND   solve every equation with known=[] (no positive controls at all) and score the found children
          against the exhaustive corpus afterwards: the engine must find exactly the corpus children.
  PLANTED add a fake child (right digit product, wrong arithmetic) to the control list: the engine must
          raise (POSITIVE CONTROL LOST).
  MUTANTS six engine defects injected by monkeypatching, each run BLIND: a mutant "escapes" if the found
          set still equals the corpus on every test vertex.

Usage: python3 redteam_base.py <b> <D> [max_secs_per_vertex=15]
"""
import sys, time, json
from collections import Counter, defaultdict
import engine_b as E
from engine_b import Base, solve_equation

def corpus(base, D):
    zf = []
    b = base.b; lim = b ** D
    def rec(i, v):
        if i == base.k:
            if v >= b and 0 not in base.digits(v): zf.append(v)
            return
        p = base.dp[i]; w = v
        while w < lim:                       # every exponent; b | y is excluded by the zero-digit test
            rec(i + 1, w); w *= p
    rec(0, 1)
    return sorted(zf)

def orbit_end(base, y):
    while y >= base.b: y = base.dprod(y)
    return y

def run_vertex(base, s, kids, levels, known_mode, sig=None):
    found = set(); nopen = 0
    for M in base.multisets(s):
        kn = [y for y in kids if Counter(d for d in base.digits(y) if d != 1) == Counter(M)] if known_mode else []
        r = solve_equation(base, s, M, kn, levels)
        if sig is not None: sig.append((M, sorted(r['solutions']), r['descent_sols'], [(L, n, sv, tuple(sorted(cls.items()))) for (L, ps, n, sv, cls, el) in r['levels']]))
        sols = {y for y in r['solutions'] if y >= base.b}
        for (bv, nu, eps, co) in r['open']:
            pt = co.nearest()
            if all(c >= 0 for c in pt) and max(pt) < 200:
                y = 1
                for p, a in zip(base.bounded, bv): y *= p ** a
                for q, v in zip(base.free, pt): y *= q ** v
                dg = base.digits(y)
                if y >= base.b and 0 not in dg and Counter(d for d in dg if d != 1) == Counter(M) and len(dg) % levels[-1] == nu % levels[-1] and y % base.b: sols.add(y)
        found |= sols; nopen += len(r['open'])
    return found, nopen

# ------------------------------------------------------------------ mutants (monkeypatches)
def mutants():
    orig = dict(descend=E.descend, padic=Base.padic_bound, classify=E.classify, nearest=E.FreeCoset.nearest,
                pinning=E.pinning_K, solve=E.Level.solve)
    def m_descent_no_exact():
        d0 = orig['descend']
        def descend(base, co, bv, D, eps, nu, L, M, K, kcap, depth=0):
            st, s2 = d0(base, co, bv, D, eps, nu, L, M, K, kcap, depth)
            return st, set()                      # descent never reports a solution
        E.descend = descend
    def m_padic_short():
        p0 = orig['padic']
        Base.padic_bound = lambda self, M, p, kcap=400: max(0, p0(self, M, p, kcap) - 1)   # bounded exponent range one too small
    def m_classify_no_solution():
        c0 = orig['classify']
        def classify(*a, **k):
            kind, val, K = c0(*a, **k)
            if kind == 'SOLUTION': return 'DEAD', None, K            # a resolved pattern reported dead
            if kind == 'SOLUTION+OPEN': return 'OPEN', None, K
            return kind, val, K
        E.classify = classify
    def m_nearest_off():
        n0 = orig['nearest']
        E.FreeCoset.nearest = lambda self: tuple(x + 1 for x in n0(self))   # exceptional point shifted
    def m_pinning_zero():
        E.pinning_K = lambda base, co, bv, kcap=200: 0                      # no 10-adic information at all
    def m_level_overkill():
        s0 = orig['solve']
        def solve(self, targets):
            t = s0(self, targets)
            if t is not None and sum(targets) % 7 == 3: return None        # 1 in 7 genuine survivors killed
            return t
        E.Level.solve = solve
    def restore():
        E.descend = orig['descend']; Base.padic_bound = orig['padic']; E.classify = orig['classify']
        E.FreeCoset.nearest = orig['nearest']; E.pinning_K = orig['pinning']; E.Level.solve = orig['solve']
    return [('descent-no-exact', m_descent_no_exact), ('padic-bound-short', m_padic_short),
            ('classify-no-solution', m_classify_no_solution), ('nearest-off-by-one', m_nearest_off),
            ('pinning-K-zero', m_pinning_zero), ('level-overkill-1/7', m_level_overkill)], restore

if __name__ == "__main__":
    b = int(sys.argv[1]); D = int(sys.argv[2]); maxs = float(sys.argv[3]) if len(sys.argv) > 3 else 15
    levels = (12, 24, 48)
    base = Base(b); zf = corpus(base, D)
    kids = defaultdict(list)
    for y in zf: kids[base.dprod(y)].append(y)
    verts = sorted({y for y in zf if orbit_end(base, y) != 0} | set(range(1, b)))
    tests = []; baseline = {}
    print(f"base {b}: corpus {len(zf)} zero-free S-units below {b}^{D}; {len(verts)} vertices")
    # pick test vertices: have children, blind run under maxs seconds
    from math import comb
    def npat(s):
        tot = 0
        for M in base.multisets(s):
            p = 12
            for d, k in Counter(M).items(): p *= comb(12 + k - 1, k)
            tot += p
        return tot
    for s in verts:
        if not kids[s] or npat(s) > 3e5: continue
        t = time.time(); sg = []; found, nopen = run_vertex(base, s, kids[s], levels, known_mode=False, sig=sg); dt = time.time() - t
        if dt > maxs: continue
        ok = found == set(kids[s])
        tests.append(s); baseline[s] = sg; print(f"  BLIND s={s}: found {sorted(found)} corpus {sorted(kids[s])} {'OK' if ok else 'MISS'} ({dt:.1f}s)")
        if not ok: print("  *** BLIND SCORING FAILURE (unmutated engine)"); sys.exit(1)
    print(f"{len(tests)} test vertices: {tests}")
    # planted negatives
    planted = 0; planted_tried = 0
    for s in tests[:5]:
        M = base.multisets(s)[0]
        fake = 0
        for d in list(M) + [1, 1]: fake = fake * b + d        # digits of M then "11": right product, wrong number
        if base.factor(fake) is not None: continue
        planted_tried += 1
        try:
            solve_equation(base, s, M, [fake], levels); print(f"  PLANTED s={s} fake={fake}: NOT CAUGHT ***"); sys.exit(1)
        except AssertionError as e:
            planted += 1; print(f"  PLANTED s={s} fake={fake}: caught ({str(e)[:40]})")
    # mutants
    ms, restore = mutants(); score = 0
    for name, apply in ms:
        apply(); caught = None
        try:
            for s in tests:
                sg = []; found, nopen = run_vertex(base, s, kids[s], levels, known_mode=False, sig=sg)
                if found != set(kids[s]): caught = ('found', s, sorted(found)); break
                if sg != baseline[s]: caught = ('counts/solutions differ', s); break
        except AssertionError as e: caught = ('assert', str(e)[:60])
        except Exception as e: caught = ('exception', repr(e)[:60])
        restore()
        print(f"  MUTANT {name:<22} {'CAUGHT ' + str(caught) if caught else 'ESCAPED ***'}")
        score += bool(caught)
    print(f"mutation score {score}/{len(ms)}; planted negatives caught {planted}/{planted_tried}; blind OK on {len(tests)} vertices")
