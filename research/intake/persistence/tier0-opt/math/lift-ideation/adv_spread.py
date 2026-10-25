import json, glob, os, statistics as st, collections, math
HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in glob.glob(os.path.join(HERE, '..', 'tierb-lift', 'logs', 'h12_*.jsonl')):
    for l in open(f):
        r = json.loads(l)
        if r.get('npat', 0) >= 1e7 and 'lift24' in r and r['lift24']['children'] > 0:
            rows.append(r)
print('multisets with npat>=1e7 and a level-24 lift:', len(rows))
byk = collections.defaultdict(list)
for r in rows:
    r['cpp'] = r['lift24']['children'] / r['npat']
    r['spp'] = r['l12_n'] / r['npat']
    r['n2'] = sum(1 for d in r['M'] if d == 2) / len(r['M'])
    byk[r['k']].append(r)
print('k n  median(children/pattern)  max  max/median | median(l12 surv/pattern) max max/median | argmax multiset')
for k in sorted(byk):
    v = byk[k]
    if len(v) < 3: continue
    m = st.median(r['cpp'] for r in v); mx = max(v, key=lambda r: r['cpp'])
    ms = st.median(r['spp'] for r in v); mxs = max(v, key=lambda r: r['spp'])
    print(k, len(v), '%.3g %.3g x%.1f | %.3g %.3g x%.1f | %s %s' % (m, mx['cpp'], mx['cpp'] / m, ms, mxs['spp'], mxs['spp'] / ms, mx['s'], ''.join(map(str, mx['M']))))
print('correlation of fraction-of-2s with children/pattern after removing k trend (log-residual):')
import numpy as np
ks = np.array([r['k'] for r in rows], float); y = np.log(np.array([r['cpp'] for r in rows])); A = np.vstack([ks, np.ones_like(ks)]).T
coef = np.linalg.lstsq(A, y, rcond=None)[0]; res = y - A @ coef
f2 = np.array([r['n2'] for r in rows]); print('trend slope per digit x%.3f' % math.exp(coef[0]), 'corr(resid, frac2)=%.3f' % np.corrcoef(res, f2)[0, 1], 'resid sd %.2f max %.2f (x%.1f)' % (res.std(), res.max(), math.exp(res.max())))
top = sorted(range(len(rows)), key=lambda i: -res[i])[:5]
for i in top: print('  top residual x%.1f' % math.exp(res[i]), rows[i]['s'], ''.join(map(str, rows[i]['M'])), 'k', rows[i]['k'])
