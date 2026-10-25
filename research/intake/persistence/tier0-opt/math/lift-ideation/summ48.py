import json, sys, statistics as st, collections
rows = [json.loads(l) for l in open(sys.argv[1])]
ref_to = [r for r in rows if r.get('timeout')]
by = collections.defaultdict(dict)
for r in rows:
    if r.get('timeout'): continue
    by[r['dir']][r['variant']] = r
dirs = list(by)
print('dirs with results', len(dirs), 'ref timeouts', len(ref_to))
j = [by[d]['join'] for d in dirs if 'join' in by[d]]
print('join rows', len(j), 'sha_equal all', all(r['sha_equal'] for r in j), 'stats_equal all', all(r['stats_equal'] for r in j), 'rc nonzero', sum(1 for r in j if r['rc'] != [0, 0]))
print('count>=1', sum(1 for r in j if r['count'] >= 1), 'open+exact>=1', sum(1 for r in j if r['ref_counts']['open'] + r['ref_counts']['exact'] >= 1), 'count>=8', sum(1 for r in j if r['count'] >= 8))
big = [r for r in j if r['children'] >= 1e6]
print('equations with >=1e6 children', len(big))
if big:
    sp = [r['speedup'] for r in big if r['speedup']]
    print('speedup median %.2f min %.2f max %.2f' % (st.median(sp), min(sp), max(sp)))
    ns = [r['ns_per_child_ref'] for r in big]
    print('lvlN ns/child median %.1f min %.1f max %.1f' % (st.median(ns), min(ns), max(ns)))
for v in ('M1', 'M1p', 'M2'):
    mr = [by[d][v] for d in dirs if v in by[d]]
    nv = [r for r in mr if r['count'] >= 8]
    print(v, 'rows', len(mr), 'caught', sum(1 for r in mr if r['caught']), '| non-vacuous (count>=8)', len(nv), 'caught', sum(1 for r in nv if r['caught']), 'missed dirs', [(r['dir'], r['count']) for r in nv if not r['caught']][:8])
    lo = [r for r in mr if 1 <= r['count'] < 8]
    print('   count 1..7:', len(lo), 'caught', sum(1 for r in lo if r['caught']))
