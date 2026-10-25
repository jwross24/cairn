import sys
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
from collections import defaultdict
from tier0v2 import multisets

def dp(x):
    p = 1
    for ch in str(x):
        p *= int(ch)
    return p

def orbit_end(x):
    while x >= 10:
        x = dp(x)
    return x

def vertices(path):
    rows = [l.split() for l in open(path) if l.startswith('ZF')]
    S = [2 ** int(a) * 3 ** int(b) * 7 ** int(c) for _, d, a, b, c, p in rows]
    assert len(S) == len(set(S))
    tree_of = {}
    for y in S:
        if y >= 10:
            e = orbit_end(y)
            if e in (2, 4, 6, 8):
                tree_of[y] = e
    for r in (2, 4, 6, 8):
        tree_of[r] = r
    V = sorted(tree_of)
    K = {s: max((len(M) for M in (tuple(sorted(M)) for M in multisets(s))), default=0) for s in V}
    return len(S), tree_of, K

new = vertices(sys.argv[1])
old = vertices(sys.argv[2])
print('corpus sizes new/old', new[0], old[0])
print('vertices new/old', len(new[2]), len(old[2]))
print('vertex set identical', set(new[2]) == set(old[2]))
print('k_max identical per vertex', new[2] == old[2])
print('new vertices', sorted(set(new[2]) - set(old[2])))
print('max k_max overall new/old', max(new[2].values()), max(old[2].values()))
print('max k_max per tree new', {t: max(k for s, k in new[2].items() if new[1][s] == t) for t in (2, 4, 6, 8)})
print('max k_max per tree old', {t: max(k for s, k in old[2].items() if old[1][s] == t) for t in (2, 4, 6, 8)})
print('vertices with k_max > 44:', [s for s, k in new[2].items() if k > 44])
print('top k_max vertices new', sorted(((k, s) for s, k in new[2].items()), reverse=True)[:9])
