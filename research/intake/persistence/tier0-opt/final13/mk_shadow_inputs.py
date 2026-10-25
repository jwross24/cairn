import json, sys, os, collections

D1 = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT)
st = json.load(open(D1 + '/pattern_status.json'))
surv = sorted(fk for fk, v in st.items() if v == 'unrun')
others = collections.Counter(v for v in st.values())
anchors = collections.OrderedDict()
for fk in surv:
    s, M, a, y, nu, eps = fk.split(' ', 5)
    anchors.setdefault((s, M, int(a), int(y)), []).append(fk)
with open(OUT + '/cases.txt', 'x') as fc, open(OUT + '/only.txt', 'x') as fo:
    for (s, M, a, y) in sorted(anchors, key=lambda k: (int(k[0]), k[1], k[2], k[3])):
        fc.write(f'{s} {M} {a} {y} - -\n')
        fo.write(f'{s} {M} {a} {y}\n')
print('status counts', dict(others))
print('survivor full keys', len(surv), 'distinct anchors', len(anchors))
per = collections.Counter(k[0] for k in anchors)
print(dict(per))
