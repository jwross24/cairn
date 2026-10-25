import collections
def load(p):
    return {l.split('\t')[0]: l.rstrip('\n').split('\t') for l in open(p)}
a, b = load('shadow/s480w.tsv'), load('shadow/s480w_neg.tsv')
print('rows', len(a), len(b), 'same keys', set(a) == set(b))
c = collections.Counter()
for k in a:
    c[(a[k][7], b[k][7])] += 1
print(dict(c))
print(open('shadow/s480w_neg.txt').read().strip().splitlines()[-2][:200])
