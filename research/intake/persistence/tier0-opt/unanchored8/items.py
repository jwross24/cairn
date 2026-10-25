import sys, json, math
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/unanchored8')
from uncut import *

T0F = T0 + '/trees_mac.jsonl'
rows = []
for l in open(T0F):
    r = json.loads(l)
    if r['s'] not in (11239424, 1161216):
        continue
    for eq in r['eqs']:
        op = eq['open_patterns']
        ex = eq.get('exceptional', [])
        for i, it in enumerate(op['items']):
            co = Coset(tuple(it['v0']), tuple(it['u1']), tuple(it['u2']))
            nn, b0, c0 = nearest(co)
            norm = math.hypot(*it['u1'])
            adm = b0 >= 0 and c0 >= 0 and max(b0, c0) < norm / 2
            rows.append((r['s'], ''.join(map(str, eq['M'])), i, it['a'], it['nu'], it['eps'], adm, b0, c0, nn))
bad = [x for x in rows if not x[6]]
print('items', len(rows), 'inadmissible', len(bad))
for x in bad:
    s, M, i, a, nu, eps, adm, b0, c0, nn = x
    print(s, M, 'item', i, 'a', a, 'nu', nu, 'eps', eps, 'b0 sign', b0 < 0, 'c0 sign', c0 < 0, 'nearest log10 norm %.3f' % (0.5 * math.log10(nn)), 'log10 digit bound %.3f' % digits_bound_log10(Coset(*[tuple(z) for z in [(0,0),(1,0),(0,1)]])) if False else '')
