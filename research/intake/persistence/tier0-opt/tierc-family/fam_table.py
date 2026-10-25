import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import json
from collections import Counter, defaultdict
from famlib import *
from validate import load_recorded

rows = json.load(open(OUT + 'validate_rows.json'))
rows2 = json.load(open(OUT + 'validate2_rows.json'))
rec384 = load_recorded()
rec480 = {}
for line in open(ROOT + 'cport-shadow480w/runs/x4w_480_1335.tsv'):
    t = line.rstrip('\n').split('\t')
    rec480[tuple(t[0].split()[:4])] = t[7]
rec480b = {}
for line in open(ROOT + 'final13/shadow/s480w.tsv'):
    t = line.rstrip('\n').split('\t')
    rec480b[tuple(t[0].split()[:4])] = t[7]


def verdict(rs, L):
    if any(r['nreps'] == 0 for r in rs):
        return 'UNDECIDED'
    return 'ALIVE' if any(r['alive'][str(L)] > 0 for r in rs) else 'KILL'


def table(rows, recd, L, name):
    res = {}
    for gran, f in (('key', lambda k: k), ('(s,M,a)', lambda k: k[:3]), ('(s,M)', lambda k: k[:2]), ('s', lambda k: k[:1])):
        fam = defaultdict(list)
        for r in rows:
            fam[f(tuple(r['key']))].append(r)
        c = Counter()
        bad = 0
        for fk, rs in fam.items():
            v = verdict(rs, L)
            rec_surv = any(recd[tuple(r['key'])] != 'CLOSED-cut' for r in rs)
            c[v] += 1
            if v == 'KILL' and rec_surv:
                bad += 1
        res[gran] = (len(fam), dict(c), bad)
    print(name, 'level', L, res)


for L in (96, 192, 384, 480):
    table(rows, {k: v['verdict'] for k, v in rec384.items()}, L, '1335 vs recorded-384')
for L in (480,):
    table(rows, rec480, L, '1335 vs recorded-480')
    table(rows2, rec480b, L, '4320 vs recorded-480')

tot_low = sum(r['profiles'] for r in rows)
tot_words = sum(r['profiles'] * 1 for r in rows)
print('mult>1 keys', sum(1 for r in rows if r['mult'] > r['nreps']), 'of', len(rows))
by_k = defaultdict(list)
for r in rows:
    if r['nreps']:
        by_k[r['k']].append(r['mult'] / r['nreps'])
print({k: round(sum(v) / len(v), 3) for k, v in sorted(by_k.items())})
