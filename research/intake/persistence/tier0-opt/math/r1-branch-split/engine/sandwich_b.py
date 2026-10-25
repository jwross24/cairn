#!/usr/bin/env python3
"""
sandwich_b.py — the Baker–lattice sandwich for a base-b run (see SANDWICH.md for base 10).

Input: a lift_open.py output (patterns lifted to L = levels[-1] with their exceptional points).  For every
open pattern: coset = v_y + Λ_L (free exponents), Lemma C at depth D (deepcut_b.deep_cut, K = L·D) leaves
sub-cosets; the certified lower bound on any candidate's digit count is the EXACT nearest point
(cvp_small.exact_nearest) of each sub-coset: digits ≥ ‖p‖/√f · log_b(min free prime).  Upper bound:
baker_chain.baker_upper_bound_base(b, k, {p: max exponent}).  lower > upper ⇒ CLOSED (sandwich).

Usage: python3 sandwich_b.py <b> <lifted.jsonl> <out.jsonl> --levels 12,24,48,96,192,384 [--maxdepth 5]
"""
import sys, json, math, time, itertools, os
from collections import Counter
from engine_b import Base, FreeCoset, cut_coset
import deepcut_b as DC
from cvp_small import exact_nearest
from baker_chain import baker_upper_bound_base

def arg(name, default): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def lower_bound_log10(base, subcosets):
    f = len(base.free); best = None
    for co in subcosets:
        pt, z, nn = exact_nearest(co.v, co.U)
        if best is None or nn < best: best = nn
    if best == 0: return -1.0
    return 0.5 * math.log10(best) - 0.5 * math.log10(f) + math.log10(math.log(min(base.free)) / math.log(base.b))

def deep_cut_subcosets(base, co0, bv, nu, De, L, depth, maxcases):
    """like deepcut_b.deep_cut but returns the surviving sub-cosets."""
    b = base.b; survivors = [(co0, ())]; cases = 0; stats = []
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
                if cases > maxcases: return None, cases, stats
                co2 = cut_coset(base, co, bv, Lv, K)
                if co2 is None: continue
                new.append((co2, assigned + tuple((j, D - 1) for j, c in zip(free, choice) if c)))
        survivors = new; stats.append(len(new))
        if not survivors: return [], cases, stats
    return [co for co, _ in survivors], cases, stats

if __name__ == "__main__":
    b = int(sys.argv[1]); inp = sys.argv[2]; outp = sys.argv[3]
    levels = tuple(int(x) for x in arg('--levels', '12,24,48,96,192,384').split(','))
    maxdepth = int(arg('--maxdepth', '5')); maxcases = int(arg('--maxcases', '3000000'))
    base = Base(b); L = levels[-1]; t0 = time.time()
    Lam = DC.kernel_lattice(base, levels)
    amax = {p: 0 for p in base.bounded}
    rows = [json.loads(l) for l in open(inp)]
    done = set()
    if os.path.exists(outp):
        for l in open(outp): done.add(json.loads(l)['s'])
    out = open(outp, 'a'); summary = Counter()
    for r in rows:
        if r['s'] in done: continue
        if not r['open']:
            out.write(json.dumps(r) + '\n'); out.flush(); summary['CLOSED'] += 1; continue
        s = r['s']; vclosed = True; notes = []
        for eq in r['eqs']:
            if not eq['open']: continue
            M = tuple(sorted(eq['M'])); k = len(M)
            for ex in eq['exceptional']:
                bv, nu, eps, y = ex[0], ex[1], ex[2], ex[3]
                if len(ex) > 5 and str(ex[5]).startswith('CLOSED'): continue
                if y is None: vclosed = False; notes.append((M, 'no-anchor')); continue
                U = baker_upper_bound_base(b, k, {p: max(a, 1) for p, a in zip(base.bounded, bv)}); logU = math.log10(U)
                fct = base.factor(y); v = tuple(fct[base.dp.index(q)] for q in base.free)
                co0 = FreeCoset(v, Lam); De = [(d, e % L) for d, e in zip(M, eps)]
                res = None
                for D in range(1, maxdepth + 1):
                    subs, cases, stats = deep_cut_subcosets(base, co0, tuple(bv), nu % L, De, L, D, maxcases)
                    if subs is None: res = ('BUDGET', D, cases); break
                    if not subs: res = ('CLOSED-cut', D, cases); break
                    lb = lower_bound_log10(base, subs)
                    if lb > logU: res = ('CLOSED-sandwich', D, cases, round(lb, 2), round(logU, 2), stats); break
                    res = ('open', D, cases, round(lb, 2), round(logU, 2), stats)
                notes.append((M, bv, nu, y, res))
                if res[0] not in ('CLOSED-cut', 'CLOSED-sandwich'): vclosed = False
        r2 = dict(r); r2['status'] = 'CLOSED' if vclosed else r['status']; r2['sandwich'] = [str(n) for n in notes]
        out.write(json.dumps(r2) + '\n'); out.flush()
        summary['CLOSED' if vclosed else 'open'] += 1
        print(f"s={s:<10} {'CLOSED' if vclosed else 'OPEN'} {[n[-1] if len(n) == 5 else n for n in notes]} [{time.time()-t0:.0f}s]", flush=True)
    print("SUMMARY", dict(summary))
