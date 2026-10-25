import collections, json
SN = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/kt-audit-l12/shadow-new/'
V13 = {'331776', '11239424', '3779136', '2939328', '69441624', '3281116734', '1161216', '7112448', '13226976', '46294416', '1741824', '1492992', '9483264'}
cases = []
for f in ('inputs/new1_cases.txt', 'inputs/new3_cases.txt'):
    cases += [l.rstrip('\n') for l in open(SN + f) if l.strip()]
rows = {}
for f in ('runs/new1.tsv', 'runs/new3.tsv'):
    for l in open(SN + f):
        c = l.rstrip('\n').split('\t')
        rows[c[0]] = c
print('case lines', len(cases), 'distinct', len(set(cases)), 'verdict rows', len(rows), 'cases without row', len([c for c in cases if c not in rows]))
per = collections.defaultdict(collections.Counter)
for c in set(cases):
    v = c.split()[0]
    per[v][rows[c][7] if c in rows else 'NO-ROW'] += 1
for v in sorted(per, key=int):
    print(v, 'in13' if v in V13 else 'NOT-in-13', dict(per[v]))
cnt = json.load(open(SN + 'inputs/new3_counts.json'))
print({v: cnt.get(v) for v in sorted(V13, key=int)})
d1cases = set(l.strip() for l in open('shadow/cases.txt'))
print('overlap of shadow-new cases with the 4320 survivor anchors', len(d1cases & set(cases)))
