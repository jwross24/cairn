#!/usr/bin/env python3
"""
deepcut192.py — level-192 lift + deep cut for the patterns that survive the level-96 deep cut.

A level-96 pattern (ν, {(d_j, e_j)}) with coset C lifts to the level-192 patterns (ν + 96s, {(d_j, e_j + 96 s_j)}),
s, s_j ∈ {0, 1}; each child's coset is C cut by the congruences at the new primes of 10^192 − 1 (those of
Φ_64(10) and Φ_192(10); the 59-digit prime factor of Φ_192(10) is NOT used — using a subset of the level
primes is valid, only weaker).  Each child with a nonempty coset gets the deep cut at K = 192·D.
Positions are integers in [0, 192) and the copies sit at e + 192t.  The anchor y (< 10^96) is never a
candidate (all other coset points have ≥ 10^27 digits, as before).

Usage: python3 deepcut192.py <survivors.txt> <jsonl files...> [--depth 2]
       survivors.txt lines: s M a y   (as printed by deepcut.py)
"""
import sys, itertools, time, math
from collections import Counter
from sympy import primitive_root, factorint, cyclotomic_poly
from lattice import Coset
from descent import cut_coset, v2
from dlog import discrete_log
import deepcut as DC
import classify_open as C

NEW_PRIMES = []
for d in (64, 192):
    for p in factorint(int(cyclotomic_poly(d, 10)), limit=10 ** 6):
        if len(str(p)) < 40: NEW_PRIMES.append(int(p))
NEW_PRIMES.sort()

class PD:
    def __init__(self, p):
        self.p = p; self.g = primitive_root(p)
        self.l3 = discrete_log(p, 3 % p, self.g); self.l7 = discrete_log(p, 7 % p, self.g)
        self.l2 = discrete_log(p, 2 % p, self.g)
        assert pow(self.g, self.l3, p) == 3 % p and pow(self.g, self.l7, p) == 7 % p

def child_coset(co, a, V, pds):
    """points (b,c) of co with 2^a 3^b 7^c ≡ V (mod p) for the new primes."""
    for pd in pds:
        r = V % pd.p
        if r == 0: return None
        lr = discrete_log(pd.p, r, pd.g)
        co = co.intersect(pd.l3, pd.l7, (lr - a * pd.l2) % (pd.p - 1), pd.p - 1)
        if co is None: return None
    return co

if __name__ == "__main__":
    surv_file = sys.argv[1]
    files = [x for x in sys.argv[2:] if x.endswith('.jsonl')]
    depth = int(sys.argv[sys.argv.index('--depth') + 1]) if '--depth' in sys.argv else 2
    want = set(tuple(l.split()[:4]) for l in open(surv_file) if l.strip())
    t0 = time.time()
    pds = [PD(p) for p in NEW_PRIMES]
    print(f"new primes at level 192 (used): {NEW_PRIMES} [{time.time()-t0:.0f}s]", flush=True)
    Lam96 = DC.kernel_lattice()
    seen = set(); results = []
    for f in files:
        for (s, M, a, nu, eps, y, sol) in C.entries(f):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            if key not in want or key in seen: continue
            seen.add(key)
            fct = C.factor237(y); co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
            reps = DC.all_representations(M, y)
            if nu is not None:
                reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % 96 for e in eps)] or reps
            DC.LMAX = 192
            pat_closed = True; worst = None; nchild = nalive = ncases = 0
            for (nu0, De) in reps:
                q = len(De)
                for sn in (0, 1):
                    for shifts in itertools.product((0, 1), repeat=q):
                        nu1 = nu0 + 96 * sn
                        De1 = tuple((d, e + 96 * sh) for (d, e), sh in zip(De, shifts))
                        V = (10 ** nu1 - 1) // 9 + sum((d - 1) * 10 ** e for d, e in De1)
                        co = child_coset(co0, a, V, pds)
                        nchild += 1
                        if co is None: continue
                        nalive += 1
                        closed, bound, cases, stats = DC.deep_cut(co, a, (nu1, list(De1)), depth, 2_000_000)
                        ncases += cases
                        if closed is None: pat_closed = False; worst = -1; continue
                        if not closed:
                            pat_closed = False; worst = bound if (worst is None or bound < worst) else worst
            DC.LMAX = 96
            results.append((s, M, a, y, pat_closed, worst))
            print(f"s={s:<8} M={''.join(map(str,M)):<12} a={a} y={y:<10} reps={len(reps)} children={nchild} alive-at-192={nalive} cases={ncases} "
                  f"{'CLOSED at level 192' if pat_closed else ('BUDGET' if worst == -1 else f'bound 10^{worst:.1e} digits')} [{time.time()-t0:.0f}s]", flush=True)
    print(f"\n{sum(1 for r in results if r[4])} of {len(results)} survivors closed at level 192")
