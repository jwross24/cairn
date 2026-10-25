#!/usr/bin/env python3
"""
deepcut_lift.py — lift surviving level-96 patterns through levels 192 and 384 (PH-feasible primes only;
a subset of a level's primes is a valid weaker level) and apply Lemma C at each level.

Usage: python3 deepcut_lift.py <survivors.txt> <jsonl files...> [--levels 192,384] [--depth 1]
survivors.txt lines: s M a y
"""
import sys, itertools, time, math
from collections import Counter
from sympy import primitive_root, factorint, cyclotomic_poly, divisors
from lattice import Coset
from descent import cut_coset, v2
from dlog import discrete_log
import deepcut as DC
import classify_open as C

def new_primes(L, L_prev, cap_digits=40, ph_cap=10 ** 8):
    out = []
    for d in divisors(L):
        if L_prev % d == 0: continue
        v = int(cyclotomic_poly(d, 10))
        f = factorint(v, limit=10 ** 7) if v > 10 ** 40 else factorint(v)
        for p in f:
            p = int(p)
            if len(str(p)) > cap_digits or p in (2, 3, 5, 7): continue
            if p > 10 ** 12 and max(factorint(p - 1, limit=10 ** 7)) > ph_cap: continue
            out.append(p)
    return sorted(out)

class PD:
    def __init__(self, p):
        self.p = p; self.g = primitive_root(p)
        self.l2 = discrete_log(p, 2 % p, self.g); self.l3 = discrete_log(p, 3 % p, self.g); self.l7 = discrete_log(p, 7 % p, self.g)

def child_coset(co, a, V, pds):
    for pd in pds:
        r = V % pd.p
        if r == 0: return None
        lr = discrete_log(pd.p, r, pd.g)
        co = co.intersect(pd.l3, pd.l7, (lr - a * pd.l2) % (pd.p - 1), pd.p - 1)
        if co is None: return None
    return co

if __name__ == "__main__":
    surv_file = sys.argv[1]; files = [x for x in sys.argv[2:] if x.endswith('.jsonl')]
    levels = [int(x) for x in (sys.argv[sys.argv.index('--levels') + 1] if '--levels' in sys.argv else '192,384').split(',')]
    depth = int(sys.argv[sys.argv.index('--depth') + 1]) if '--depth' in sys.argv else 1
    want = set(tuple(l.split()[:4]) for l in open(surv_file) if l.strip())
    t0 = time.time()
    PDS = {}; Lp = 96
    for L in levels:
        ps = new_primes(L, Lp); PDS[L] = (Lp, [PD(p) for p in ps]); print(f"level {L}: new primes {ps}", flush=True); Lp = L
    Lam96 = DC.kernel_lattice(); seen = set(); n_closed = 0; n_all = 0
    for f in files:
        for (s, M, a, nu, eps, y, sol) in C.entries(f):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            if key not in want or key in seen: continue
            seen.add(key); n_all += 1
            fct = C.factor237(y); co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
            reps = DC.all_representations(M, y)
            if nu is not None:
                reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % 96 for e in eps)] or reps
            # alive patterns: list of (L, nu, De, coset)
            alive = [(96, nu0, list(De), co0) for (nu0, De) in reps]
            log = []
            for L in levels:
                Lp, pds = PDS[L]; nxt = []
                for (Lc, nu0, De, co) in alive:
                    assert Lc == Lp
                    q = len(De); m = L // Lp                       # lift factor (2 for 96->192, 3 for 96->288, ...)
                    for sn in range(m):
                        for shifts in itertools.product(range(m), repeat=q):
                            nu1 = nu0 + Lp * sn; De1 = [(d, e + Lp * sh) for (d, e), sh in zip(De, shifts)]
                            V = (10 ** nu1 - 1) // 9 + sum((d - 1) * 10 ** e for d, e in De1)
                            co1 = child_coset(co, a, V, pds)
                            if co1 is None: continue
                            DC.LMAX = L
                            closed, bound, cases, stats = DC.deep_cut(co1, a, (nu1, De1), depth, 2_000_000)
                            DC.LMAX = 96
                            if closed: continue
                            nxt.append((L, nu1, De1, co1 if closed is not None else co1))
                log.append((L, len(alive), len(nxt)))
                alive = nxt
                if not alive: break
            closed_all = not alive
            n_closed += closed_all
            bound = None if closed_all else min(DC.digits_bound(co) for (_, _, _, co) in alive)
            print(f"s={s:<8} M={''.join(map(str,M)):<12} a={a} y={y:<11} reps={len(reps)} lift {log} -> {'CLOSED' if closed_all else f'{len(alive)} alive, bound 10^(10^{bound:.2f})'} [{time.time()-t0:.0f}s]", flush=True)
    print(f"\n{n_closed} of {n_all} survivors closed by lifting to {levels} + Lemma C")
