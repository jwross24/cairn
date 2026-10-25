import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import json
from collections import Counter
from famlib import *

rows = json.load(open(OUT + 'validate_rows.json'))
rec480 = {}
for line in open(ROOT + 'cport-shadow480w/runs/x4w_480_1335.tsv'):
    t = line.rstrip('\n').split('\t')
    rec480[tuple(t[0].split()[:4])] = (t[7], t[8])
print(Counter(v[0] for v in rec480.values()))
tab = Counter()
bad = []
for r in rows:
    k = tuple(r['key'])
    v = rec480[k][0]
    mine = 'alive' if r['alive']['480'] > 0 else 'dead'
    tab[(v, mine)] += 1
    if v == 'CLOSED-cut' and mine == 'alive':
        bad.append(k)
print('480 cross', dict(tab), 'discordant', len(bad))
tab = Counter()
for r in rows:
    k = tuple(r['key'])
    tab[(rec480[k][0], 'alive384' if r['alive']['384'] else 'dead384')] += 1
print(dict(tab))
