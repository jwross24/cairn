import json, sys
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0/'
want = {1161216, 11239424}
for fn in ('runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl'):
    for l in open(T0 + fn):
        r = json.loads(l)
        if r['s'] not in {331776, 11239424, 3779136, 2939328, 69441624, 3281116734, 1161216, 7112448, 13226976, 46294416, 1741824, 1492992, 9483264}:
            continue
        listed = sum(len(eq.get('exceptional', [])) for eq in r.get('eqs', []) if isinstance(eq, dict)) + len(r.get('exceptional', []))
        print(fn, r['s'], 'open', r.get('open'), 'listed', listed, 'closed', r.get('closed'), 'eqs', len(r.get('eqs', [])))
