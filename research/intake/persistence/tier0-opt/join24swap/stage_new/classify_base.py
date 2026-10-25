#!/usr/bin/env python3
"""
classify_base.py — the open-pattern classifier for any base (see OPEN-PATTERNS.md).
For every open pattern of a run_base.py output: the exceptional coset point y (recorded in
`exceptional`, or recomputed by re-solving the equation when the record lacks it) and whether
y = R_nu + sum (d_j - 1) b^{e_j} holds exactly over the integers with nu, e_j in [0, L_last).

Usage: python3 classify_base.py <b> <jsonl> [levels=12,24,48]
"""
import sys, json
from collections import Counter
from engine_b import Base, solve_equation, brute

from classify_open import exact_identity as _ei
def exact_identity(base, M, y, L):
    return _ei(M, y, L, base.b)

def point_to_y(base, bv, pt):
    y = 1
    for p, a in zip(base.bounded, bv): y *= p ** a
    for qq, v in zip(base.free, pt): y *= qq ** v
    return y

if __name__ == "__main__":
    b = int(sys.argv[1]); path = sys.argv[2]
    levels = tuple(int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "12,24,48").split(','))
    base = Base(b); L = levels[-1]
    rows = [json.loads(l) for l in open(path)]
    tot = Counter(); anchors = Counter(); unanch = []
    for r in rows:
        if not r['open']: continue
        s = r['s']
        for eq in r['eqs']:
            if not eq['open']: continue
            M = tuple(eq['M'])
            exc = eq.get('exceptional')
            if exc is None:
                res = solve_equation(base, s, M, eq['brute'], levels)
                exc = []
                for (bv, nu, eps, co) in res['open']:
                    pt = co.nearest()
                    y = point_to_y(base, bv, pt) if all(c >= 0 for c in pt) and max(pt) < 200 else None
                    exc.append([list(bv), nu, list(eps), y, False])
            for (bv, nu, eps, y, issol) in exc:
                if y is None: tot['NO-SMALL-POINT'] += 1; unanch.append((s, M, bv, nu, eps)); continue
                dg = base.digits(y)
                zf = 0 not in dg
                ident = exact_identity(base, M, y, L)
                if ident is None: tot['NO-EXACT-IDENTITY'] += 1; unanch.append((s, M, bv, nu, eps, y)); continue
                nu2, e2 = ident
                proper = (nu2 == len(dg) and len(set(e2)) == len(e2) and max(e2) < nu2)
                kind = 'SELF' if proper else ('ANCHORED' if zf else 'ANCHORED(zero-digit anchor)')
                tot[kind] += 1; anchors[y] += 1
    print(f"base {b}: {sum(tot.values())} open patterns: {dict(tot)}")
    print("anchors:", [(y, n, ''.join(map(str, base.digits(y)))) for y, n in anchors.most_common(12)])
    for u in unanch: print("  UNANCHORED:", u)
