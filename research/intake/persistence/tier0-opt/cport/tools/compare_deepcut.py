import json, glob, sys
W = '/private/tmp/persist-cport/logs/'
py = {}
for f in glob.glob(W + 'pyref_deepcut_*.jsonl'):
    for l in open(f):
        r = json.loads(l)
        py[tuple(r['key'])] = r
cr = {}
for l in open(sys.argv[1] if len(sys.argv) > 1 else W + 'c_deepcut.tsv'):
    s, M, a, y, ri, closed, cases, nn, t = l.rstrip('\n').split('\t')
    cr.setdefault((s, M, a, y), []).append((int(ri), int(closed), int(cases), nn, float(t)))
bad = 0; nrep = 0; tp = 0.0; tc = 0.0; nn_eq = 0; nn_n = 0; tp_pat = 0.0
for k, r in py.items():
    c = cr.get(k, [])
    if len(c) != len(r['reps']):
        # a budget abort stops the C loop early too
        if not any(x['closed'] is None for x in r['reps']): print('REPCOUNT', k, len(c), len(r['reps'])); bad += 1
    tp_pat += r['t']
    for x, (ri, closed, cases, nn, t) in zip(r['reps'], c):
        nrep += 1
        tp += x['t']; tc += t
        if bool(x['closed']) != bool(closed) or x['cases'] != cases: bad += 1; print('VERDICT', k, ri, x['closed'], closed, x['cases'], cases)
        if not closed:
            nn_n += 1
            if x['nn'] == nn: nn_eq += 1
            else: bad += 1; print('NN', k, ri, x['nn'], nn)
print(f"patterns {len(py)}, reps compared {nrep}, mismatches {bad}")
print(f"survivor reps with exact nearest-norm integer compared: {nn_n}, equal: {nn_eq}")
print(f"cut-stage CPU: python {tp:.1f}s, C {tc:.3f}s, ratio {tp / tc:.0f}x (per-rep, excludes rep enumeration)")
print(f"python per-pattern total (rep enumeration + cuts, from pyref): {tp_pat:.1f}s over {len(py)} patterns")
