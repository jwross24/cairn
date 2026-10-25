import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import json
from collections import Counter
from famlib import *
from validate import load_recorded

rows = json.load(open(OUT + 'validate_rows.json'))
rec = load_recorded()
c = Counter()
for r in rows:
    k = tuple(r['key'])
    pure = rec[k]['reps'] == r['nreps']
    sd = r['alive']['384'] == 0 and r['nreps'] > 0
    c[(pure, sd, rec[k]['verdict'])] += 1
print({str(k): v for k, v in sorted(c.items(), key=str)})
rows2 = json.load(open(OUT + 'validate2_rows.json'))
rec2 = {}
for line in open(ROOT + 'final13/shadow/s480w.tsv'):
    t = line.rstrip('\n').split('\t')
    rec2[tuple(t[0].split()[:4])] = (int(t[5]), t[7])
c2 = Counter()
for r in rows2:
    k = tuple(r['key'])
    pure = rec2[k][0] == r['nreps']
    sd = r['alive']['480'] == 0 and r['nreps'] > 0
    c2[(pure, sd, rec2[k][1])] += 1
print({str(k): v for k, v in sorted(c2.items(), key=str)})
