import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
from tier0v2 import two_adic_bound
keys = [l.rstrip('\n') for l in open(sys.argv[1])]
out = {}
for fk in keys:
    s, M, a, y, nu, eps = fk.split(' ')
    A = two_adic_bound(tuple(int(c) for c in M))
    out[fk] = [s, M, A]
json.dump(out, open(sys.argv[2], 'x'), indent=0)
bad = {fk: v for fk, v in out.items() if v[2] >= 64}
print(len(out), 'patterns;', len(bad), 'with A >= 64;', 'equations:', sorted({(v[0], v[1], v[2]) for v in bad.values()}))
