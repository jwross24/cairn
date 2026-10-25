import json, sys, statistics as st, collections
rows = [json.loads(l) for l in open(sys.argv[1])]
by = collections.defaultdict(dict); to = [r for r in rows if r.get('timeout')]
for r in rows:
    if r.get('timeout'): continue
    by[r['dir']][r['variant']] = r
print('equations', len(by), 'ref timeouts', len(to))
for v in ('gpu', 'join'):
    rr = [by[d][v] for d in by if v in by[d]]
    print(v, 'n', len(rr), 'sha_equal', sum(r['sha_equal'] for r in rr), 'stats_equal', sum(r['stats_equal'] for r in rr), 'rc!=0', sum(1 for r in rr if r['rc'] != [0, 0]))
    big = [r for r in rr if r['children'] >= 5e6]
    sp = [r['speedup'] for r in big if r['speedup']]
    if sp: print('  children>=5e6: %d  cpu speedup vs lvlN median %.1f min %.1f max %.1f' % (len(big), st.median(sp), min(sp), max(sp)))
    if v == 'gpu' and big:
        kr = [r['children'] / (r['extra']['gpu_us'] * 1e-6) for r in big]; print('  kernel children/s median %.3g min %.3g max %.3g' % (st.median(kr), min(kr), max(kr)))
        print('  cand fraction median %.2e; cpu_cand_us/cand median %.0f ns' % (st.median(r['extra']['gcand'] / r['children'] for r in big), st.median(r['extra']['cpu_cand_us'] * 1e3 / max(r['extra']['gcand'], 1) for r in big)))
        print('  wall speedup median %.1f' % st.median(r['wall_ref'] / r['wall_j'] for r in big))
        print('  ns/child lvlN median %.1f' % st.median(r['ns_per_child_ref'] for r in big))
both = [d for d in by if 'gpu' in by[d] and 'join' in by[d] and by[d]['gpu']['children'] >= 5e6]
if both:
    print('gpu vs join (cpu s): median ratio join/gpu %.2f  (n=%d), by wall %.2f' % (st.median(by[d]['join']['cpu_j'] / by[d]['gpu']['cpu_j'] for d in both), len(both), st.median(by[d]['join']['wall_j'] / by[d]['gpu']['wall_j'] for d in both)))
mr = [by[d]['gpuM'] for d in by if 'gpuM' in by[d]]; nv = [r for r in mr if r['count'] >= 8]
print('gpuM rows', len(mr), 'caught', sum(r['caught'] for r in mr), 'non-vacuous', len(nv), 'caught', sum(r['caught'] for r in nv), 'missed', [(r['dir'], r['count']) for r in nv if not r['caught']][:5])
bad = [(d, v) for d in by for v, r in by[d].items() if v in ('gpu', 'join') and not (r['sha_equal'] and r['stats_equal'])]
print('mismatches', bad[:6])
