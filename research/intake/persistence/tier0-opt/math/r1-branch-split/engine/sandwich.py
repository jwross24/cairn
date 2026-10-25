#!/usr/bin/env python3
"""
sandwich.py — close an open level-96 pattern by the Baker–lattice sandwich:
  UPPER: every candidate y′ (k non-1 digits, 2-adic exponent a) has n < G(k, a) digits — the iterated Matveev
         chain (BAKER-CHAIN.md, baker_chain.baker_upper_bound; ordinary proof, not machine-checked);
  LOWER: Lemma C at depth D leaves finitely many sub-cosets p + Λ_D; every point of each has norm ≥ the
         sub-coset's exact nearest point, so every candidate has ≥ (that norm)/√2·log10(3) digits.
If LOWER > UPPER for some D, the pattern has no candidate besides the anchor: CLOSED (sandwich).
Usage: python3 sandwich.py <survivors.txt> <jsonl files...> [--maxdepth 5] [--maxcases 2000000]
"""
import sys, math, time
from collections import Counter
from lattice import Coset
import deepcut as DC
import classify_open as C
from baker_chain import baker_upper_bound

if __name__ == "__main__":
    surv_file = sys.argv[1]; files = [x for x in sys.argv[2:] if x.endswith('.jsonl')]
    maxdepth = int(sys.argv[sys.argv.index('--maxdepth') + 1]) if '--maxdepth' in sys.argv else 5
    maxcases = int(sys.argv[sys.argv.index('--maxcases') + 1]) if '--maxcases' in sys.argv else 2_000_000
    want = set(tuple(l.split()[:4]) for l in open(surv_file) if l.strip())
    t0 = time.time(); Lam = DC.kernel_lattice(); seen = set(); nclosed = nall = 0
    for f in files:
        for (s, M, a, nu, eps, y, sol) in C.entries(f):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            fullkey = key + (nu, None if eps is None else tuple(eps))
            if key not in want or fullkey in seen: continue
            seen.add(fullkey); nall += 1
            k = len(M); U = baker_upper_bound(k, a); logU = math.log10(U)
            fct = C.factor237(y); assert fct is not None and fct[0] == a, ("anchor/a mismatch", s, M, a, y)   # red team 2
            co0 = Coset((fct[1], fct[2]), Lam.u1, Lam.u2)
            reps = DC.all_representations(M, y)
            assert reps, ("no representation", s, M, a, y)
            if nu is not None:
                reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % 96 for e in eps)]
                assert reps, ("recorded pattern not among representations", s, M, a, y, nu, eps)
            verdict = []; allclosed = True
            for (nu0, De) in reps:
                res = None
                for D in range(1, maxdepth + 1):
                    closed, bound, cases, stats = DC.deep_cut(co0, a, (nu0, list(De)), D, maxcases)
                    if closed is None: res = ('BUDGET', D, cases); break
                    if closed: res = ('CLOSED-cut', D, cases); break
                    if bound > logU: res = ('CLOSED-sandwich', D, cases, round(bound, 2), stats); break
                    res = ('open', D, cases, round(bound, 2), stats)
                verdict.append(res)
                if res[0] not in ('CLOSED-cut', 'CLOSED-sandwich'): allclosed = False
            nclosed += allclosed
            print(f"s={s:<8} M={''.join(map(str,M)):<12} a={a} y={y:<11} k={k} log10 U={logU:.1f} reps={len(reps)} -> {'CLOSED' if allclosed else 'OPEN'} {verdict} [{time.time()-t0:.0f}s]", flush=True)
    print(f"\n{nclosed} of {nall} patterns closed by the sandwich")
