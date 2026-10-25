import json, sys, functools
from collections import Counter
src = open('eqs_timing.py').read()
start = src.index('@functools.lru_cache')
end = src.index('elapsed =')
exec('import functools\nfrom collections import Counter\n' + src[start:end])
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0/'
for l in open(T0 + 'trees_mac.jsonl'):
    r = json.loads(l)
    if r['s'] == 3281116734:
        As = [(''.join(map(str, e['M'])), two_adic_bound(tuple(e['M']))) for e in r['eqs']]
        print('3281116734 equations', len(As), 'max A', max(a for _, a in As), sorted(a for _, a in As))
