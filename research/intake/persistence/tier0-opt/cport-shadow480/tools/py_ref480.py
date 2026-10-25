import sys
sys.dont_write_bytecode = True
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0, T0)
from collections import Counter
from lattice import Coset
import deepcut as DC, deepcut_lift as DL, classify_open as C
import wordlift as W
import wordlift480 as WL

M_str, a, y = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
primes = [int(x) for x in sys.argv[4].split(',')]
M = tuple(int(ch) for ch in M_str)
pds = [DL.PD(p) for p in primes]
Lam96 = DC.kernel_lattice()
fct = C.factor237(y)
co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
reps = DC.all_representations(M, y)
tot_pass = tot_alive = 0
nnset = set()
best = None
for (nu0, De) in reps:
    words = W.depth1_words(co0, a, (nu0, De))
    if not words:
        continue
    T = WL.trivial_primes(words[0][0], pds)
    rp = ra = 0
    for co, st in words:
        ch, tested, pT = WL.lift_word_f(co, a, nu0, De, st, 96, 480, pds, T)
        rp += pT; ra += len(ch)
        tot_pass += pT
        tot_alive += len(ch)
        for co2, _, _ in ch:
            nnset.add(DC.nearest_norm(co2)[0])
            b = DC.digits_bound(co2)
            if best is None or b < best:
                best = b
    print(f"  rep nu={nu0} words={len(words)} passed_T={rp} alive={ra}")
print('DISTINCT_NN', len(nnset), sorted(nnset)[0] if nnset else None)
print(f"PYREF M={M_str} a={a} y={y} primes={primes} reps={len(reps)} passed_T={tot_pass} alive={tot_alive} bound={'none' if best is None else '%.2f' % best}")
