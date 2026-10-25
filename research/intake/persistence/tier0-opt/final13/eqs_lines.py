import json
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
V = [331776, 11239424, 3779136, 2939328, 69441624, 3281116734, 1161216, 7112448, 13226976, 46294416, 1741824, 1492992, 9483264]
eqs = [json.loads(l) for l in open(T0 + '/trees_mac.jsonl.eqs.jsonl')]
print('eqs.jsonl lines', len(eqs))
for s in V:
    idx = [i for i, d in enumerate(eqs) if d['s'] == s]
    print(s, 'n', len(idx), 'min', min(idx) if idx else None, 'max', max(idx) if idx else None)
