import json, sys, functools
from collections import Counter

T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
V = [331776, 11239424, 3779136, 2939328, 69441624, 3281116734, 1161216, 7112448, 13226976, 46294416, 1741824, 1492992, 9483264]
SWAP_LVLN = 1792646505
LOG11_BIRTH = 1792551845


@functools.lru_cache(maxsize=None)
def two_adic_bound(M, kcap=200):
    M = Counter(M)
    states = {(0, tuple(sorted(M.elements())), False)}
    for k in range(1, kcap):
        new = set()
        for tail, rem, ended in states:
            choices = {0} if ended else ({0, 1} | set(rem))
            for d in choices:
                t = d * 10 ** (k - 1) + tail
                if t % (2 ** k) == 0:
                    if d == 0:
                        if tail:
                            new.add((t, rem, True))
                    elif d == 1:
                        new.add((t, rem, False))
                    else:
                        r = list(rem)
                        r.remove(d)
                        new.add((t, tuple(r), False))
        if not new:
            return k - 1
        states = new
    return kcap


elapsed = [(4148928, 922), (393216, 1548), (1778112, 1202), (2667168, 1233), (19361664, 2500), (221184, 2176), (3211264, 6398),
           (331776, 3708), (11239424, 6695), (3779136, 5324), (2939328, 5418), (69441624, 8560), (3281116734, 7690), (1161216, 16456),
           (7112448, 18396), (13226976, 12451), (46294416, 16389), (1741824, 14601), (1492992, 15306), (9483264, 19993)]
t = LOG11_BIRTH
win = {}
for s, e in elapsed:
    win[s] = (t, t + e)
    t += e
print('log.11 birth', LOG11_BIRTH, 'last vertex finish', t, 'lvlN swap', SWAP_LVLN)
for s in V:
    a, b = win[s]
    rel = 'AFTER swap' if a >= SWAP_LVLN else ('BEFORE swap' if b <= SWAP_LVLN else 'STRADDLES swap')
    print(s, 'start', a, 'finish', b, rel)

eqs = [json.loads(l) for l in open(T0 + '/trees_mac.jsonl.eqs.jsonl')]
print('eqs.jsonl lines now', len(eqs))
macrows = {}
for l in open(T0 + '/trees_mac.jsonl'):
    r = json.loads(l)
    macrows[r['s']] = r
for s in V:
    idx = [i for i, d in enumerate(eqs) if d['s'] == s]
    hi = [(i, ''.join(map(str, eqs[i]['M'])), two_adic_bound(tuple(eqs[i]['M']))) for i in idx if two_adic_bound(tuple(eqs[i]['M'])) >= 64]
    row = macrows.get(s)
    rowA = [(''.join(map(str, e['M'])), two_adic_bound(tuple(e['M']))) for e in row['eqs'] if two_adic_bound(tuple(e['M'])) >= 64] if row else None
    print(s, 'eqs lines', (min(idx), max(idx), len(idx)) if idx else None, 'A>=64 lines', hi, 'row eqs', len(row['eqs']) if row else None, 'row A>=64', rowA)
