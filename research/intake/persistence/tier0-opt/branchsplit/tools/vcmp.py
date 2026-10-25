import sys, json
from collections import Counter
prod = [json.loads(l) for l in open(sys.argv[1])]
cand = [json.loads(l) for l in open(sys.argv[2])]
assert len(prod) == len(cand) and [p['M'] for p in prod] == [c['M'] for c in cand]
same = Counter(); changed = Counter(); bad = []
tot = Counter()
for p, c in zip(prod, cand):
    for k in ('s', 'M', 'npat', 'open', 'sols', 'bounds', 'exceptional'):
        if p[k] == c[k]:
            same[k] += 1
        else:
            bad.append((p['M'], k))
    po, co = p['open_patterns'], c['open_patterns']
    if po['items'] == co['items'] and po['M'] == co['M']:
        same['open_patterns.items+M'] += 1
    else:
        bad.append((p['M'], 'open_patterns.items'))
    if po['level'] == co['level']:
        same['open_patterns.level'] += 1
    elif not po['items']:
        changed['open_patterns.level (items empty)'] += 1
    else:
        bad.append((p['M'], 'open_patterns.level'))
    for k in sorted(set(p['c_stats']) | set(c['c_stats'])):
        if p['c_stats'].get(k) == c['c_stats'].get(k):
            same['c_stats.' + k] += 1
        elif k == 'open' and c['c_stats']['open'] + c['bsdrop'] == p['c_stats']['open']:
            changed['c_stats.open'] += 1
        else:
            bad.append((p['M'], 'c_stats.' + k))
    pl, cl = p['levels'], c['levels']
    if [x[0] for x in pl] == [x[0] for x in cl]:
        same['levels.L-list'] += 1
    else:
        changed['levels.L-list'] += 1
    for a in pl:
        b = next((x for x in cl if x[0] == a[0]), None)
        L = a[0]
        if b is None:
            changed[f'levels[{L}] absent in candidate'] += 1
            tot[f'prod_surv{L}'] += a[2]; tot[f'prod_in{L}'] += a[1]
            continue
        tot[f'prod_surv{L}'] += a[2]; tot[f'cand_surv{L}'] += b[2]; tot[f'prod_in{L}'] += a[1]; tot[f'cand_in{L}'] += b[1]
        for i, nm in ((1, 'n_in'), (2, 'survived'), (3, 'classes')):
            if a[i] == b[i]:
                same[f'levels.{nm}'] += 1
            else:
                changed[f'levels.{nm}'] += 1
print(json.dumps(dict(equations=len(prod), identical_fields=dict(same), changed_fields=dict(changed), totals=dict(tot), bad=bad)))
sys.exit(1 if bad else 0)
