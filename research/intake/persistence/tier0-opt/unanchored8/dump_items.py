import json, sys
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0/'
for l in open(T0 + 'trees_mac.jsonl'):
    r = json.loads(l)
    if r['s'] not in (11239424, 1161216):
        continue
    for eq in r['eqs']:
        ex = eq.get('exceptional', [])
        print('EQ', r['s'], ''.join(map(str, eq['M'])), 'open', eq.get('open'), 'listed', len(ex), 'keys', sorted(eq))
        op = eq['open_patterns']
        print(' level', op['level'], 'M', op['M'], 'n_items', len(op['items']))
        for e in ex[:2]:
            print(' EX', json.dumps(e)[:300])
        for it in op['items'][:2]:
            print(' IT', json.dumps(it)[:500])
