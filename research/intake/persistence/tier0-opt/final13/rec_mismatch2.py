import json
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0/'
for l in open(T0 + 'trees_mac.jsonl'):
    r = json.loads(l)
    if r['s'] not in (11239424, 1161216):
        continue
    print('row', r['s'], 'open', r['open'], 'row-level exceptional', len(r.get('exceptional', [])), 'sols', r.get('sols'))
    for eq in r['eqs']:
        ex = eq.get('exceptional', [])
        if eq.get('open') != len(ex):
            print('  M', ''.join(map(str, eq['M'])), 'open', eq.get('open'), 'listed', len(ex), 'bounds', eq.get('bounds'), 'keys', [k for k in eq if k not in ('M',)])
