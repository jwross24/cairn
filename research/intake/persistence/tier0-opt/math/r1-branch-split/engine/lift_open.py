#!/usr/bin/env python3
"""
lift_open.py — continue a finished base-b run from its recorded open patterns: lift them to higher levels
(no re-enumeration of the first level) and apply the full-depth b-adic cut (Lemma C), writing a new jsonl.

Each open pattern's coset is reconstructed from its recorded exceptional point y (the Babai-nearest
coset point): coset = v_y + Λ_L in the free exponents, a superset of the engine's coset (conservative).
Positive controls: the equation's known children (eq['brute']) must still be found.

Usage: python3 lift_open.py <b> <in.jsonl> <out.jsonl> --levels 12,24,48,96 --to 192,384 [--depth 1] [--ncores N]
"""
import sys, json, math, time, os
from collections import Counter
from multiprocessing import Pool
from engine_b import Base, solve_equation, FreeCoset
import deepcut_b as DC

def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

b = int(sys.argv[1]); inp = sys.argv[2]; outp = sys.argv[3]
levels = tuple(int(x) for x in arg('--levels', '12,24,48,96').split(','))
to = tuple(int(x) for x in arg('--to', '192,384').split(','))
depth = int(arg('--depth', '1')); ncores = int(arg('--ncores', '1'))
base = Base(b)
LAM = {}

def lam(levs):
    if levs not in LAM: LAM[levs] = DC.kernel_lattice(base, levs)
    return LAM[levs]

def process(r):
    if not r['open']: return r
    s = r['s']; t0 = time.time(); L0 = levels[-1]; Lam0 = lam(levels); Lfin = (levels + to)[-1]; Lamf = lam(levels + to)
    found = set(r['found']); nopen = 0; bounds = []; incomplete = False; neweqs = []
    for eq in r['eqs']:
        if not eq['open'] or 'exceptional' not in eq: neweqs.append(eq); continue
        M = tuple(eq['M']); surv = []
        for (bv, nu, eps, y, issol) in eq['exceptional']:
            if y is None: incomplete = True; continue
            fct = base.factor(y); v = tuple(fct[base.dp.index(q)] for q in base.free)
            surv.append((tuple(bv), nu, tuple(eps), FreeCoset(v, Lam0)))
        res = dict(levels_done=levels, survivors=surv, lattice_free=Lam0, solutions=set(eq['sols']))
        try:
            rr = solve_equation(base, s, M, eq['brute'], levels + to, resume=res)
        except AssertionError as e:
            neweqs.append(dict(eq, lift_error=str(e))); incomplete = True; continue
        sols = {y for y in rr['solutions'] if y >= b}
        exc = []; eq_open = 0; eq_bounds = []
        for (bv, nu, eps, co) in rr['open']:
            pt = co.nearest(); y = None; issol = False
            if all(c >= 0 for c in pt) and max(pt) < 200:
                y = DC.point_to_y(base, bv, pt); dg = base.digits(y)
                if y >= b and 0 not in dg and Counter(d for d in dg if d != 1) == Counter(M) and len(dg) % Lfin == nu % Lfin and y % b: sols.add(y); issol = True
            # Lemma C on this pattern
            if y is not None:
                De = [(d, e % Lfin) for d, e in zip(sorted(M), eps)]
                fct = base.factor(y); vv = tuple(fct[base.dp.index(q)] for q in base.free)
                closed, bound, cases, stats = DC.deep_cut(base, FreeCoset(vv, Lamf), tuple(bv), nu % Lfin, De, Lfin, depth, 200000)
                if closed: exc.append([list(bv), nu, list(eps), y, issol, 'CLOSED-by-cut']); continue
                if closed is None: bound = rr['bound_digits']
                eq_bounds.append(bound); exc.append([list(bv), nu, list(eps), y, issol, f'bound {bound:.3e}'])
            else:
                exc.append([list(bv), nu, list(eps), None, False, 'no-small-point']); eq_bounds.append(rr['bound_digits'] or 0)
            eq_open += 1
        found |= sols; nopen += eq_open
        if eq_bounds: bounds.append(min(eq_bounds))
        neweqs.append(dict(M=list(M), open=eq_open, sols=sorted(sols), brute=eq['brute'], exceptional=exc,
                           levels=eq['levels'] + [(L, n, sv, cls) for (L, ps, n, sv, cls, el) in rr['levels']], descent_sols=rr['descent_sols']))
        if set(eq['brute']) - sols: incomplete = True
    st = 'INCOMPLETE' if incomplete else ('CLOSED' if nopen == 0 else f"CLOSED BELOW 10^{min(bounds):.1e} DIGITS")
    out = dict(r); out.update(found=sorted(found), open=nopen, status=st, secs=r['secs'] + round(time.time() - t0), eqs=neweqs, lifted_to=list(to))
    return out

if __name__ == "__main__":
    rows = [json.loads(l) for l in open(inp)]
    done = set()
    if os.path.exists(outp):
        for l in open(outp): done.add(json.loads(l)['s'])
    todo = [r for r in rows if r['s'] not in done]
    lam(levels); lam(levels + to)
    summary = Counter()
    with open(outp, 'a') as out:
        it = Pool(ncores).imap_unordered(process, todo) if ncores > 1 else map(process, todo)
        for rec in it:
            out.write(json.dumps(rec) + '\n'); out.flush()
            summary['CLOSED' if rec['status'] == 'CLOSED' else ('closed-below' if 'BELOW' in rec['status'] else rec['status'])] += 1
            print(f"  s={rec['s']} {rec['status']}; children {rec['found']} known {rec['known']} open {rec['open']}", file=sys.stderr, flush=True)
    print("SUMMARY", dict(summary), file=sys.stderr)
