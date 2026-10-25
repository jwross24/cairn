import json, glob, sys
W = '/private/tmp/persist-cport/logs/'
py = {}
for f in glob.glob(W + 'pyref_sandwich_*.jsonl'):
    for l in open(f):
        r = json.loads(l); py[tuple(r['key'])] = r
cr = {}
for l in open(sys.argv[1] if len(sys.argv) > 1 else W + 'c_sandwich.tsv'):
    p = l.rstrip('\n').split('\t')
    s, M, a, y, ri, D, res, cases, st, nn, t = p
    cr.setdefault((s, M, a, y), {}).setdefault(int(ri), {})[int(D)] = (res, int(cases), st, nn, float(t))
bad = 0; n = 0; tp = 0.0; tc_inc = 0.0; tc_cum = 0.0; nn_eq = 0; nn_n = 0; per = []
for k, r in py.items():
    for ri, rep in enumerate(r['reps']):
        cum = 0.0
        for d in rep['depths']:
            D = d['D']; c = cr[k][ri][D]; n += 1
            cum += c[4]
            tp += d['t']; tc_inc += c[4]; tc_cum += cum
            per.append((d['t'], cum, c[4]))
            stats = '[' + ', '.join(map(str, d['stats'])) + ']'
            if d['res'] != c[0] or d['cases'] != c[1]: bad += 1; print('VERDICT', k, ri, D, d['res'], c[0], d['cases'], c[1])
            if d['res'] in ('open', 'CLOSED-sandwich'):
                nn_n += 1
                if d['nn'] == c[3] and stats == c[2]: nn_eq += 1
                else: bad += 1; print('NN/STATS', k, ri, D, d['nn'], c[3], stats, c[2])
print(f"patterns {len(py)}, rep-depth entries compared {n}, mismatches {bad}")
print(f"exact nearest-norm integers + survivor-count lists compared: {nn_n}, equal: {nn_eq}")
print(f"python per-depth call (restarts from depth 1) total {tp:.1f}s; C same-work (cumulative to D) {tc_cum:.3f}s -> {tp / tc_cum:.0f}x; "
      f"C incremental stage only {tc_inc:.3f}s -> {tp / tc_inc:.0f}x")
