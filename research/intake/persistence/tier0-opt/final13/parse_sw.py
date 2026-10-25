import ast, os, re, sys, collections, json
SW = sys.argv[1]
st = json.load(open(sys.argv[2]))
surv = sorted(fk for fk, v in st.items() if v == 'unrun')
order = sorted(surv, key=lambda fk: (len(fk.split()[1]), fk))
per = collections.defaultdict(collections.Counter)
minm = {}
verd = collections.Counter()
unfinished = []
notstarted = []
for n, fk in enumerate(order):
    v = fk.split()[0]
    cf = f'{SW}/{n}.cases'
    if not os.path.exists(cf):
        notstarted.append(fk)
        per[v]['not-run'] += 1
        continue
    assert open(cf).read().strip() == fk
    line = None
    tf = f'{SW}/{n}.txt'
    for l in open(tf):
        if l.startswith('s='):
            line = l.rstrip('\n')
            break
    if line is None:
        unfinished.append(fk)
        per[v]['in-flight-at-stop'] += 1
        continue
    line = re.sub(r'\s*\[\d+s\]\s*$', '', line)
    m = re.match(r'.*log10 U=([0-9.]+) .* -> (\S+) (\[.*\])\s*$', line)
    U = float(m.group(1))
    word = m.group(2)
    reps = ast.literal_eval(m.group(3))
    verd[word] += 1
    allclosed = all(r[0] in ('CLOSED-cut', 'CLOSED-sandwich') for r in reps)
    kind = 'sandwich' if any(r[0] == 'CLOSED-sandwich' for r in reps) else 'cut-only'
    if word == 'CLOSED' and allclosed:
        per[v]['closed-' + kind] += 1
        for r in reps:
            if r[0] == 'CLOSED-sandwich':
                mg = r[3] - U
                minm[v] = min(minm.get(v, 1e9), mg)
    else:
        per[v]['NOT-closed:' + word] += 1
print('verdict words', dict(verd), 'unfinished', len(unfinished), 'not started', len(notstarted))
tot = collections.Counter()
for v in sorted(per, key=int):
    tot.update(per[v])
    print(v, dict(per[v]), 'min(bound-log10U) over sandwich reps', None if v not in minm else round(minm[v], 2))
print('total', dict(tot))
with open(sys.argv[3], 'x') as f:
    for fk in unfinished + notstarted:
        f.write(fk + '\n')
