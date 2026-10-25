import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import time, json
from collections import Counter
from famlib import *
from validate import pattern_family_alive, LEVELS

cases = []
for line in open(ROOT + 'final13/shadow/cases.txt'):
    t = line.split()
    cases.append((t[0], tuple(int(ch) for ch in t[1]), int(t[2]), int(t[3])))
rec = {}
for line in open(ROOT + 'final13/shadow/s480w.tsv'):
    t = line.rstrip('\n').split('\t')
    rec[tuple(t[0].split()[:4])] = (t[7], t[9])
t0 = time.time()
rows = []
for (s, M, a, y) in cases:
    t1 = time.time()
    reps = reps_wrap0(M, y)
    tot = {L: 0 for L in LEVELS}
    for nu, De in reps:
        r, ns, mu = pattern_family_alive(a, y, nu, De)
        for L in LEVELS:
            tot[L] += r[L]
    rows.append(dict(key=(s, ''.join(map(str, M)), str(a), str(y)), k=len(M), a=a, nreps=len(reps), alive=tot, sec=time.time() - t1))
    if len(rows) % 500 == 0:
        print(len(rows), round(time.time() - t0), flush=True)
json.dump(rows, open(OUT + 'validate2_rows.json', 'w'))
tab = Counter()
bad = []
for r in rows:
    k = tuple(r['key'])
    v = rec[k][0]
    mine = 'alive' if r['alive'][480] > 0 else ('dead' if r['nreps'] else 'nowrap0')
    tab[(v, mine)] += 1
    if v == 'CLOSED-sandwich' and mine == 'dead':
        bad.append(k)
print('s480w 480 cross', dict(tab))
print('recorded survivor but shadow dead:', bad[:10], len(bad))
print('seconds', round(time.time() - t0, 1))
