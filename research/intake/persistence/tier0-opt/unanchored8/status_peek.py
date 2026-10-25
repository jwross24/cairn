import json, collections
P = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/final13/'
st = json.load(open(P + 'd1/pattern_status.json'))
c = collections.defaultdict(collections.Counter)
for fk, v in st.items():
    s, M, a, y, nu, eps = fk.split(' ', 5)
    if M in ('22222222233667', '2222222222227778', '222222222444777'):
        c[(s, M)][v] += 1
        if v != 'cut1':
            print(fk, v)
print(dict(c))
