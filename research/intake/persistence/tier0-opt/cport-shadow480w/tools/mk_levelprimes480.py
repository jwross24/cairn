import sys
sys.dont_write_bytecode = True
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0, T0)
from sympy import primitive_root, factorint, isprime
import deepcut_lift as DL
from dlog import discrete_log

src, out = sys.argv[1], sys.argv[2]
ps = DL.new_primes(480, 96)
rows = []
for p in ps:
    assert isprime(p)
    g = primitive_root(p)
    l2 = discrete_log(p, 2 % p, g); l3 = discrete_log(p, 3 % p, g); l7 = discrete_log(p, 7 % p, g)
    f = sorted(factorint(p - 1).items())
    assert pow(g, l2, p) == 2 % p and pow(g, l3, p) == 3 and pow(g, l7, p) == 7 % p
    assert (10 ** 480 - 1) % p == 0 and (10 ** 96 - 1) % p != 0
    prod = 1
    for q, e in f:
        prod *= q ** e
    assert prod == p - 1
    rows.append((p, g, l2, l3, l7, f))
with open(src) as fi, open(out, 'x') as fo:
    fo.write(fi.read())
    fo.write('# level 480 (x5 over 96): new primes of 10^480-1 not dividing 10^96-1; rows tagged B exceed 64 bits\n')
    for (p, g, l2, l3, l7, f) in rows:
        if p.bit_length() > 63:
            fo.write(f"B 480 {p} {g} {l2} {l3} {l7} {len(f)} " + ' '.join(f"{q} {e}" for q, e in f) + '\n')
        else:
            fo.write(f"480 {p} {g} {l2} {l3} {l7} {len(f)} " + ' '.join(f"{q} {e}" for q, e in f) + '\n')
print(len(rows), 'level-480 primes:', [p for p, *_ in rows])
