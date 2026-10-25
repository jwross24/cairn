import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import json
from collections import Counter
from famlib import *
from validate import load_recorded

rows = json.load(open(OUT + 'validate_rows.json'))
rec = load_recorded()
rec480 = {}
for line in open(ROOT + 'cport-shadow480w/runs/x4w_480_1335.tsv'):
    t = line.rstrip('\n').split('\t')
    rec480[tuple(t[0].split()[:4])] = (t[6], t[8] if len(t) > 8 else '')

print('recorded 384 verdicts', Counter(v['verdict'] for v in rec.values()))
print('recorded 480 verdicts', Counter(v[0] for v in rec480.values()))
for L in ('96', '192', '384', '480'):
    print(L, 'keys with a wrap-0 shadow word alive:', sum(1 for r in rows if r['alive'][L] > 0), 'of', len(rows))
tab = Counter()
bad = []
for r in rows:
    k = tuple(r['key'])
    v = rec[k]['verdict']
    mine = 'alive' if r['alive']['384'] > 0 else 'dead'
    tab[(v, mine)] += 1
    if (v == 'CLOSED-cut' and mine == 'alive') or (v == 'CLOSED-sandwich' and mine == 'dead'):
        bad.append((k, v, r['alive']))
print('384 cross table', dict(tab))
print('discordant', len(bad))
for b in bad[:20]:
    print(b)
tab = Counter()
bad = []
for r in rows:
    k = tuple(r['key'])
    v = rec480[k][0]
    mine = 'alive' if r['alive']['480'] > 0 else 'dead'
    tab[(v, mine)] += 1
    if (v == 'CLOSED-cut' and mine == 'alive'):
        bad.append((k, v, r['alive']))
print('480 cross table', dict(tab))
print('480 discordant (recorded cut, mine alive)', len(bad), bad[:5])
