import sys, collections
tsv, cases = sys.argv[1], sys.argv[2]
want = [l.rstrip('\n') for l in open(cases) if l.strip()]
rows = {}
for l in open(tsv):
    f = l.rstrip('\n').split('\t')
    rows[f[0]] = f
missing = [w for w in want if w not in rows]
extra = [k for k in rows if k not in set(want)]
per = collections.defaultdict(collections.Counter)
minb = {}
for k, f in rows.items():
    v = f[1]
    verdict = f[7]
    per[v][verdict] += 1
    if verdict == 'CLOSED-sandwich' and f[8]:
        b = float(f[8])
        minb[v] = min(minb.get(v, 1e9), b)
tot = collections.Counter()
print('cases', len(want), 'rows', len(rows), 'missing', len(missing), 'extra', len(extra))
for v in sorted(per, key=int):
    tot.update(per[v])
    print(v, dict(per[v]), 'min sandwich bound log10 digits', minb.get(v))
print('total', dict(tot))
