import json, sys, statistics as st, collections, math
import numpy as np
rows = [json.loads(l) for l in open(sys.argv[1])]
by = collections.defaultdict(dict)
for r in rows:
    if r.get('timeout'): continue
    by[r['dir']][r['variant']] = r
print('equations', len(by), 'timeouts', sum(1 for r in rows if r.get('timeout')))
for v in ('join', 'way3', 'fp'):
    rr = [by[d][v] for d in by if v in by[d]]
    print(v, 'n', len(rr), 'sha_equal', sum(r['sha_equal'] for r in rr), 'stats_equal', sum(r['stats_equal'] for r in rr))
# way3 vs join
both = [d for d in by if 'join' in by[d] and 'way3' in by[d] and by[d]['join']['children'] >= 1e6]
if both:
    rat = []; cr = []
    for d in both:
        j = by[d]['join']['extra']; w = by[d]['way3']['extra']
        mj = j['probes'] + j['built']; mw = w['probes'] + w['built'] + w['pairadds']
        rat.append(mw / mj); cr.append(by[d]['way3']['cpu_j'] / by[d]['join']['cpu_j'])
        same_c = j['cands'] == w['cands']
        if not same_c: print('  cands differ', d, j['cands'], w['cands'])
    print('way3/join meet-ops (probes+built+pairadds vs probes+built): median %.3f min %.3f max %.3f (n=%d)' % (st.median(rat), min(rat), max(rat), len(both)))
    print('way3/join cpu seconds: median %.3f min %.3f max %.3f' % (st.median(cr), min(cr), max(cr)))
    xs = np.log([by[d]['join']['children'] / by[d]['join']['parents'] for d in both])
    for nm, f in (('2-way meet ops/parent', lambda d: (by[d]['join']['extra']['probes'] + by[d]['join']['extra']['built']) / by[d]['join']['parents']),
                  ('3-way meet ops/parent', lambda d: (by[d]['way3']['extra']['probes'] + by[d]['way3']['extra']['built'] + by[d]['way3']['extra']['pairadds']) / by[d]['join']['parents']),
                  ('2-way total ops/parent (incl cands)', lambda d: (by[d]['join']['extra']['probes'] + by[d]['join']['extra']['built'] + by[d]['join']['extra']['cands']) / by[d]['join']['parents']),
                  ('3-way total ops/parent (incl cands)', lambda d: (by[d]['way3']['extra']['probes'] + by[d]['way3']['extra']['built'] + by[d]['way3']['extra']['pairadds'] + by[d]['way3']['extra']['cands']) / by[d]['join']['parents'])):
        ys = np.log([f(d) for d in both]); sl = np.polyfit(xs, ys, 1)[0]
        print('  slope d log(%s)/d log(C per parent) = %.3f  [C range %.0f..%.0f]' % (nm, sl, math.exp(xs.min()), math.exp(xs.max())))
fp = [by[d]['fp'] for d in by if 'fp' in by[d]]
if fp:
    tot_par = sum(r['parents'] for r in fp)
    print('FP: parents', tot_par, 'C>=1024 parents', sum(r['extra']['fp_par_big'] for r in fp), 'decided dead (all)', sum(r['extra']['fp_dead_all'] for r in fp), 'decided dead (C>=1024)', sum(r['extra']['fp_dead_big'] for r in fp), 'rank0 parents', sum(r['extra']['fp_rank0'] for r in fp))
    ch_small = sum(r['extra']['fp_ch_small'] for r in fp); ch_all = sum(r['extra']['fp_ch_all'] for r in fp)
    print('FP: children in parents with C<=64: %d of %d (%.4f%%)' % (ch_small, ch_all, 100 * ch_small / max(ch_all, 1)))
    eq = [r for r in fp if r['extra']['fp_dead_all'] > 0]; print('FP: equations where any parent was decided dead:', len(eq), 'of', len(fp))
m4 = [by[d]['fpM4'] for d in by if 'fpM4' in by[d]]
nv = [r for r in m4 if r['count'] >= 8]
print('FP mutant4 rows', len(m4), 'caught', sum(r['caught'] for r in m4), 'non-vacuous', len(nv), 'caught', sum(r['caught'] for r in nv))
bad = [(d, v) for d in by for v, r in by[d].items() if v in ('join', 'way3', 'fp') and not (r['sha_equal'] and r['stats_equal'])]
print('mismatch', bad[:5])
