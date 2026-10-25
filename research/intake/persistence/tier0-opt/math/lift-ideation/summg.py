import json, sys, statistics as st, collections
rows = [json.loads(l) for l in open(sys.argv[1])]
minch = float(sys.argv[2]) if len(sys.argv) > 2 else 1e6
by = collections.defaultdict(dict)
for r in rows:
    if r.get('timeout'): continue
    by[r['dir']][r['variant']] = r
g = [by[d]['gpu'] for d in by if 'gpu' in by[d]]
print('equations', len(g), 'sha_equal all', all(r['sha_equal'] for r in g), 'stats_equal all', all(r['stats_equal'] for r in g), 'rc', sorted(set(map(str, (r['rc'] for r in g)))))
big = [r for r in g if r['children'] >= minch]
print('equations with >= %g children: %d' % (minch, len(big)))
if big:
    sp = [r['speedup'] for r in big]; print('cpu speedup vs lvlN (rusage, includes host work) median %.2f min %.2f max %.2f' % (st.median(sp), min(sp), max(sp)))
    wsp = [r['wall_ref'] / r['wall_j'] for r in big if r['wall_j']]; print('wall speedup median %.2f min %.2f max %.2f' % (st.median(wsp), min(wsp), max(wsp)))
    kr = [r['children'] / (r['extra']['gpu_us'] * 1e-6) for r in big if r['extra'].get('gpu_us')]
    print('kernel children/s median %.3e min %.3e max %.3e' % (st.median(kr), min(kr), max(kr)))
    fr = [r['extra']['gcand'] / r['children'] for r in big]; print('candidate fraction median %.2e' % st.median(fr))
    for r in sorted(big, key=lambda r: r['children'])[-4:]:
        print(r['dir'], 'children %.3e' % r['children'], 'ref cpu %.2f' % r['cpu_ref'], 'gpuprog cpu %.2f wall %.2f' % (r['cpu_j'], r['wall_j']), {k: r['extra'][k] for k in ('gpu_us', 'cpu_cand_us', 'prep_us', 'total_us', 'gcand')})
mr = [by[d]['gpuM'] for d in by if 'gpuM' in by[d]]
nv = [r for r in mr if r['count'] >= 8]
print('gpuM mutant rows', len(mr), 'caught', sum(r['caught'] for r in mr), 'non-vacuous', len(nv), 'caught', sum(r['caught'] for r in nv), 'missed', [(r['dir'], r['count']) for r in nv if not r['caught']][:6])
