import json, collections
P = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/final13/'
st = json.load(open(P + 'd1/pattern_status.json'))
ver = {}
for l in open(P + 'shadow/s480w.tsv'):
    p = l.rstrip('\n').split('\t')
    ver.setdefault(p[0], []).append(p[1:9])
out = collections.defaultdict(list)
for fk, v in st.items():
    s, M, a, y, nu, eps = fk.split(' ', 5)
    if s in ('1161216', '11239424'):
        out[(s, len(M), v)].append((M, a, y))
for k in sorted(out):
    print(k, len(out[k]), out[k][:2])
print(list(ver.items())[:2])
