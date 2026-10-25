import sys
sys.dont_write_bytecode = True
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0, T0)
from sympy import primitive_root, factorint
import deepcut_lift as DL
from dlog import discrete_log

out = sys.argv[1]
rows = []
for L, Lp in ((192, 96), (384, 192)):
    ps = DL.new_primes(L, Lp)
    for p in ps:
        g = primitive_root(p)
        l2 = discrete_log(p, 2 % p, g); l3 = discrete_log(p, 3 % p, g); l7 = discrete_log(p, 7 % p, g)
        f = factorint(p - 1)
        assert pow(g, l2, p) == 2 % p and pow(g, l3, p) == 3 and pow(g, l7, p) == 7 % p
        assert (10 ** L - 1) % p == 0 and (10 ** Lp - 1) % p != 0
        rows.append((L, p, g, l2, l3, l7, sorted(f.items())))
with open(out, 'x') as fo:
    fo.write('# level p g log_g(2) log_g(3) log_g(7) nfac [q e]...   (new primes of 10^L-1 not dividing 10^(L/2)-1; tier0/deepcut_lift.new_primes)\n')
    for (L, p, g, l2, l3, l7, f) in rows:
        fo.write(f"{L} {p} {g} {l2} {l3} {l7} {len(f)} " + ' '.join(f"{q} {e}" for q, e in f) + '\n')
print(len(rows), 'primes')
