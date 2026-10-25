import pickle, statistics
from common import *
from strings_lib import count_feasible, count_objects, groups, class_ways, enum_low
import numpy as np

recs = [r for r in pickle.load(open(os.path.join(HERE, 'ref_run.pkl'), 'rb')) if not r.get('budget') and r.get('closed') != 'BUDGET']
bud = [r for r in pickle.load(open(os.path.join(HERE, 'ref_run.pkl'), 'rb')) if r.get('budget')]
diff = {(x['key'], x['rep'], x['D']): x for x in pickle.load(open(os.path.join(HERE, 'differential.pkl'), 'rb'))}
pats = {(p['key'], p['nu']): p for p in load_patterns()}
out = {}

series = defaultdict(dict)
for r in recs: series[(r['key'], r['rep'])][r['D']] = r
rows = []
for (key, rep), dd in series.items():
    anyr = next(iter(dd.values()))
    De = anyr['De']; k = anyr['k']; a = anyr['a']; y = int(key[3])
    if dd.get(1, {}).get('closed'): continue
    surv = [dd[D]['stats'][-1] for D in sorted(dd) if dd[D].get('stats')]
    strs = [diff[(key, rep, D)]['nleaf'] for D in sorted(dd) if (key, rep, D) in diff]
    g = groups(De); w = a + 9
    free_classes = [e for e in g if e >= w]
    r_occ = sum(len(g[e]) for e in free_classes)
    ngroups = sum(len(g[e]) for e in g)
    nlow = sum(sum(g[e].values()) for e in g if e < w)
    rows.append(dict(key=key, rep=rep, k=k, a=a, surv=surv, strs=strs, nclass=len(g), ngroups=ngroups, r_free=r_occ, nlow=nlow, raw2k=2 ** k))
out['rows'] = rows

ratios = []
for r in rows:
    s = r['surv']
    for i in range(1, len(s)):
        ratios.append((r['k'], i + 1, s[i] / s[i - 1], r['strs'][i] / r['strs'][i - 1] if len(r['strs']) > i else None))
out['ratios'] = ratios
for b in bud:
    pass

sym = [(r['surv'][-1], r['strs'][-1]) for r in rows if r['strs'] and len(r['strs']) == len(r['surv'])]
out['sym'] = sym

def fit(xs, ys):
    A = np.vstack([xs, np.ones(len(xs))]).T
    c, res, *_ = np.linalg.lstsq(A, ys, rcond=None)
    pred = A @ c
    ss = float(((np.array(ys) - pred) ** 2).sum()); st = float(((np.array(ys) - np.mean(ys)) ** 2).sum())
    return c.tolist(), 1 - ss / st if st else None

R2 = [(k, d, math.log10(x)) for k, d, x, _ in ratios if x > 0]
ks = [x[0] for x in R2]; ds = [x[1] for x in R2]; ls = [x[2] for x in R2]
out['fit_ratio_vs_k_lin'] = fit(ks, ls)
out['fit_ratio_vs_logk'] = fit([math.log10(k) for k in ks], ls)
out['fit_ratio_vs_depth'] = fit(ds, ls)

forms = []
for r in rows:
    p = pats[(r['key'], None)] if (r['key'], None) in pats else [v for kk, v in pats.items() if kk[0] == r['key']][0]
    De = series[(r['key'], r['rep'])][1]['De']
    a = r['a']; y = int(r['key'][3])
    ent = []
    for D in range(1, 9):
        s, nlow = count_feasible(De, y, a, D)
        ent.append((D, s))
    forms.append((r['key'], r['rep'], r['k'], ent))
out['forms'] = forms
pickle.dump(out, open(os.path.join(HERE, 'analyze.pkl'), 'wb'))

print('rows', len(rows))
print('sym obj/str final', [(a, b) for a, b in sym][:50])
print('ratio fits (log10 ratio): lin k', out['fit_ratio_vs_k_lin'], 'log k', out['fit_ratio_vs_logk'], 'depth', out['fit_ratio_vs_depth'])
byk = defaultdict(list)
for k, d, x, xs in ratios: byk[k].append(x)
for k in sorted(byk): print('k', k, 'n', len(byk[k]), 'median ratio obj', statistics.median(byk[k]), 'max', max(byk[k]))
byk2 = defaultdict(list)
for k, d, x, xs in ratios:
    if xs: byk2[k].append(xs)
for k in sorted(byk2): print('k', k, 'median ratio strings', statistics.median(byk2[k]), 'max', max(byk2[k]))
for f in forms[:60]:
    print(f[0][1], f[1], f[2], [f'{s:.3g}' for _, s in f[3]])
