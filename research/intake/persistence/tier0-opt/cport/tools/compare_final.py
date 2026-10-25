import glob, json, re, sys

mode, pyglob, ctxt, ctsv = sys.argv[1:5]
subset = None
if len(sys.argv) > 5:
    subset = set(l.rstrip('\n') for l in open(sys.argv[5]) if l.strip())

py = {}
for f in sorted(g for pat in pyglob.split(',') for g in glob.glob(pat)):
    for l in open(f):
        r = json.loads(l)
        py[r['key']] = r

lines = [l.rstrip('\n') for l in open(ctxt) if l.startswith('s=')]
lines = [re.sub(r' \[\d+s\]$', '', l) for l in lines] if mode == 'sandwich' else lines
rows = {}
order = []
for l in open(ctsv):
    p = l.rstrip('\n').split('\t')
    if p[0] not in rows:
        rows[p[0]] = []
        order.append(p[0])
    rows[p[0]].append(p[1:])
assert len(order) == len(lines), (len(order), len(lines))
cline = dict(zip(order, lines))

bad = 0
n = 0
nrep = 0
nn_n = 0
nn_eq = 0
stats_eq = 0
cases_total = 0
missing = []
for fk, r in py.items():
    if subset is not None and fk not in subset:
        continue
    if fk not in rows:
        missing.append(fk)
        continue
    n += 1
    if r['line'] != cline[fk]:
        bad += 1
        print('LINE', fk, '\n  py:', r['line'], '\n   c:', cline[fk])
    crows = rows[fk]
    if mode == 'deepcut':
        if len(crows) != len(r['reps']):
            bad += 1
            print('REPCOUNT', fk, len(crows), len(r['reps']))
            continue
        for x, c in zip(r['reps'], crows):
            nrep += 1
            ccl, ccases, cnn = int(c[5]), int(c[6]), c[7]
            pcl = -1 if x['closed'] is None else int(bool(x['closed']))
            if pcl != ccl or x['cases'] != ccases:
                bad += 1
                print('VERDICT', fk, x['closed'], ccl, x['cases'], ccases)
            if not x['closed'] and x['closed'] is not None:
                nn_n += 1
                if x['nn'] == cnn:
                    nn_eq += 1
                else:
                    bad += 1
                    print('NN', fk, x['nn'], cnn)
    else:
        cmap = {}
        for c in crows:
            cmap[(int(c[4]), int(c[5]))] = c
        pkeys = set()
        for ri, rep in enumerate(r['reps']):
            for d in rep['depths']:
                pkeys.add((ri, d['D']))
                c = cmap.get((ri, d['D']))
                nrep += 1
                if c is None:
                    bad += 1
                    print('MISSING-ROW', fk, ri, d['D'])
                    continue
                res, ccases, cst, cnn = c[6], int(c[7]), c[8], c[9]
                if res != d['res'] or ccases != d['cases']:
                    bad += 1
                    print('VERDICT', fk, ri, d['D'], d['res'], res, d['cases'], ccases)
                if d['res'] in ('open', 'CLOSED-sandwich'):
                    nn_n += 1
                    pst = '[' + ', '.join(map(str, d['stats'])) + ']'
                    if d['nn'] == cnn and pst == cst:
                        nn_eq += 1
                    else:
                        bad += 1
                        print('NN/STATS', fk, ri, d['D'], d['nn'], cnn, pst, cst)
        extra = set(cmap) - pkeys
        if extra:
            bad += 1
            print('EXTRA-ROWS', fk, sorted(extra))

print(f"{mode}: python records finished {len(py)}, compared {n}, rep(-depth) entries {nrep}, mismatches {bad}; "
      f"python-finished but absent from C output: {len(missing)}")
print(f"exact nearest-norm integers (+ survivor-count lists for sandwich) compared: {nn_n}, equal: {nn_eq}")
print(f"C records without a python reference (not compared): {len(order) - n}")
sys.exit(1 if bad or missing else 0)
