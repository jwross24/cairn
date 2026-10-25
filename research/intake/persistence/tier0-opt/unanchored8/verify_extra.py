import sys, glob, itertools
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/unanchored8')
from uncut import *

rows = [r for r in load_items({1161216, 11239424}) if not r['adm']]
print('exhaustive subsets (no position pruning): count with v2(L)=a and 5 not dividing L')
for r in rows:
    De = rep_from_record(r['M'], r['nu'], r['eps'])[1]
    n = 0
    for choice in itertools.product((0, 1), repeat=len(De)):
        L = (10 ** 96 - 1) // 9 + sum((De[j][0] - 1) * 10 ** De[j][1] for j, c in enumerate(choice) if c)
        if v2(L) == r['a'] and L % 5:
            n += 1
    print(r['s'], ''.join(map(str, r['M'])), 'a', r['a'], 'subsets', 2 ** len(De), 'with v2(L)=a:', n)

D1 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/final13/d1/'
ref = {}
for f in glob.glob(D1 + 'deepcut_*.tsv'):
    for l in open(f):
        p = l.rstrip('\n').split('\t')
        ref.setdefault(p[0], []).append((int(p[5]), p[6], p[7]))
mine = {}
for l in open('control_anchored.tsv'):
    p = l.rstrip('\n').split('\t')
    key = p[0].split(' ')
    k = f'{key[0]} {key[1]} {key[2]} {p[4]} - -' if False else None
    mine.setdefault((p[1], p[2], p[3]), []).append((int(p[5]), p[6], p[7]))
for (s, M, a), v in mine.items():
    cands = [(k, rv) for k, rv in ref.items() if k.split(' ')[:3] == [s, M, a]]
    ok = [k for k, rv in cands if rv == v]
    print('control', s, M, a, 'reps', len(v), 'per-rep (closed, cases) equal to the final13 depth-1 rows of key:', ok)
