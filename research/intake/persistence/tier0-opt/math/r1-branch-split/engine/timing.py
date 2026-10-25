import json, sys
from collections import defaultdict
tot = defaultdict(lambda: defaultdict(list))
for s in (14336, 8192, 28672, 10800):
    for m in ('off', 'on'):
        for rep in (1, 2, 3):
            rows = [json.loads(l) for l in open(f'tm_{s}_{m}_{rep}.jsonl')]
            t12 = sum(r['times'].get('lvl12', 0) for r in rows)
            tN = sum(r['times'].get('lvlN', 0) for r in rows)
            tt = sum(r['secs'] for r in rows)
            tot[(s, m)]['t12'].append(t12); tot[(s, m)]['tN'].append(tN); tot[(s, m)]['tot'].append(tt)
for s in (14336, 8192, 28672, 10800):
    f = tot[(s, 'off')]; n = tot[(s, 'on')]
    print(s, 'off: lvl12 %.2f lvlN %.2f total %.2f | on: lvl12 %.2f lvlN %.2f total %.2f | speedup(total,min) %.2f' % (min(f['t12']), min(f['tN']), min(f['tot']), min(n['t12']), min(n['tN']), min(n['tot']), min(f['tot']) / min(n['tot'])))
    print('    reps total off', [round(x, 2) for x in f['tot']], 'on', [round(x, 2) for x in n['tot']])
