#!/usr/bin/env python3
"""
hshadow.py — characterise the level-192 survivor of each level-96 depth-1 word (hypothesis H-shadow, WORDLIFT.md §5).

For every anchored pattern (one representation via the digit DP — this is a measurement, not a verdict) and every
depth-1 word W (fixed digits at copy 0, r unplaced), enumerate the 2^(r+1) level-192 children and record which
survive the new-prime cut and Lemma C depth 1 at K = 192.  Output per word: r, number of surviving children, and
for each survivor its description: ν shift sn ∈ {0,1} and, for each unplaced digit, (d, e, ρ = t mod 2, fixed at
t = 1?).  Also records, for the anchor identity, where each digit actually sits (all t = 0 in the identity
y + wrap·R_96 = R_ν + Σ (d−1)10^{e}; the wrap value w) so the survivor can be compared with the anchor.

Usage: python3 hshadow.py <jsonl> [--max 300] [--kmin 8] [--kmax 16] [--seed 1] > HSHADOW-run.txt
"""
import sys, time, math, itertools, random, json
from collections import Counter
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC, deepcut_lift as DL, classify_open as C
import wordlift as W

def arg(name, default): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

if __name__ == "__main__":
    path = sys.argv[1]; nmax = int(arg('--max', 300)); kmin = int(arg('--kmin', 8)); kmax = int(arg('--kmax', 16))
    random.seed(int(arg('--seed', 1)))
    t0 = time.time()
    pds = [DL.PD(p) for p in DL.new_primes(192, 96)]
    Lam96 = DC.kernel_lattice()
    rows = []; seen = set()
    for (s, M, a, nu, eps, y, sol) in C.entries(path):
        key = (s, M, a, y)
        if key in seen or not (kmin <= len(M) <= kmax) or y < 10 ** 8 or M.count(2) > 8: continue
        seen.add(key); rows.append((s, M, a, y))
    random.shuffle(rows); rows = rows[:nmax]
    print(f"{len(rows)} patterns, k in [{kmin},{kmax}] [{time.time()-t0:.0f}s]", flush=True)
    stats = Counter(); recipes = Counter()
    for (s, M, a, y) in rows:
        r1 = C.exact_identity(M, y)
        if r1 is None: stats['no-rep'] += 1; continue
        nu0, De = r1[0], tuple(zip(sorted(M, reverse=True), r1[1]))
        # wrap value: y + w R_96 = R_nu + Σ (d-1)10^e
        w = (( (10 ** nu0 - 1) // 9 + sum((d - 1) * 10 ** e for d, e in De)) - y) // ((10 ** 96 - 1) // 9)
        fct = C.factor237(y); co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
        words = W.depth1_words(co0, a, (nu0, De))
        stats['patterns'] += 1
        if not words: stats['killed-d1'] += 1; continue
        for co, state in words:
            unf = [j for j, st in enumerate(state) if st[0] == 'U']
            ch = W.lift_word(co, a, nu0, De, state, 96, 192, pds)
            stats['words'] += 1; stats[f'surv={len(ch)}'] += 1
            desc = []
            for co2, nu1, st2 in ch:
                sn = (nu1 - nu0) // 96
                bits = tuple((De[j][0], De[j][1], st2[j][2] if st2[j][0] == 'U' else st2[j][2], 'fixed@1' if st2[j][0] == 'F' else 'free') for j in unf)
                rho_all = tuple(b[2] for b in bits)
                recipe = (sn, 'all-rho=1' if all(x == 1 for x in rho_all) else 'all-rho=0' if all(x == 0 for x in rho_all) else 'mixed',
                          'all-fixed' if all(b[3] == 'fixed@1' for b in bits) else 'none-fixed' if all(b[3] == 'free' for b in bits) else 'some-fixed')
                recipes[recipe] += 1
                desc.append((sn, bits))
            fixed = [(De[j][0], De[j][1]) for j, st in enumerate(state) if st[0] == 'F']
            print(json.dumps({'s': s, 'M': ''.join(map(str, M)), 'a': a, 'y': y, 'nu': nu0, 'wrap': w, 'k': len(M),
                              'fixed': fixed, 'unplaced': [(De[j][0], De[j][1]) for j in unf], 'r': len(unf),
                              'survivors': len(ch), 'desc': desc}), flush=True)
    print(f"\nSTATS {dict(stats)}\nRECIPES {dict(recipes)} [{time.time()-t0:.0f}s]")
