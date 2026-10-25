import json
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0/'
for l in open(T0 + 'trees_mac.jsonl'):
    r = json.loads(l)
    if r['s'] not in (11239424, 1161216):
        continue
    for eq in r['eqs']:
        if eq.get('open') != len(eq.get('exceptional', [])):
            print(r['s'], ''.join(map(str, eq['M'])), json.dumps(eq['open_patterns'])[:600], 'levels', eq['levels'])
