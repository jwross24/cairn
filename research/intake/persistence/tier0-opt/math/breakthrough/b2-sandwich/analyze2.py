import pickle
from common import *
from strings_lib import *
import numpy as np
out = pickle.load(open(os.path.join(HERE, 'analyze.pkl'), 'rb'))
rows = out['rows']; forms = out['forms']
recs = [r for r in pickle.load(open(os.path.join(HERE, 'ref_run.pkl'), 'rb')) if not r.get('budget') and r.get('closed') != 'BUDGET']
tab = []
for (key, rep, k, ent), r in zip(forms, rows):
    Ds = np.array([D for D, s in ent if D >= 4], float); Vs = np.array([s for D, s in ent if D >= 4], float)
    deg = np.polyfit(np.log(Ds), np.log(Vs), 1)[0]
    tab.append((k, round(deg, 2), r['nlow'], r['r_free'], r['ngroups'], r['nclass'], key[1]))
tab.sort()
for t in tab: print(t)
ks = np.array([t[0] for t in tab], float); dg = np.array([t[1] for t in tab])
print('deg vs k linear fit', np.polyfit(ks, dg, 1), 'corr', np.corrcoef(ks, dg)[0, 1])
byk = defaultdict(list)
for t in tab: byk[t[0]].append(t[1])
for k in sorted(byk): print(k, 'deg mean', np.mean(byk[k]), 'max', max(byk[k]))
last = {}
for r in recs: last[(r['key'], r['rep'])] = r
cache = defaultdict(set); total = 0
for r in recs:
    if not r.get('final') or r['closed']: continue
    for ent in r['final']:
        s = frozenset((r['De'][j][1] + LMAX * t, r['De'][j][0]) for j, t in ent[6]); 
        cache[(r['key'][3], r['key'][2], r['D'])].add(s); total += 1
dist = sum(len(v) for v in cache.values())
print('cross-pattern cache: objects', total, 'distinct (anchor,a,D,string)', dist)
Dmax = defaultdict(int)
tot_by = defaultdict(int)
for r in recs:
    if not r.get('final') or r['closed']: continue
    tot_by[(r['key'][3], r['key'][2], r['D'])] += len({frozenset((r['De'][j][1] + LMAX * t, r['De'][j][0]) for j, t in ent[6]) for ent in r['final']})
print('sum of per-rep distinct strings', sum(tot_by.values()), 'cross-rep/pattern distinct', dist)
bnd = []
for r in recs:
    if r.get('bound') and not r['closed']:
        nd = len({frozenset((r['De'][j][1] + LMAX * t, r['De'][j][0]) for j, t in ent[6]) for ent in r['final']})
        bnd.append((r['D'], nd, r['bound']))
B = np.array(bnd, float)
A = np.vstack([B[:, 0], np.log10(B[:, 1]), np.ones(len(B))]).T
c, *_ = np.linalg.lstsq(A, B[:, 2], rcond=None)
print('bound = %.4f*D + %.4f*log10(V) + %.3f' % tuple(c), 'resid max', float(np.abs(A @ c - B[:, 2]).max()))
