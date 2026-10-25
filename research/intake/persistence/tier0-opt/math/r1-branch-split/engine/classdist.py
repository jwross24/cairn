import sys, glob, os
from collections import Counter
import branchsplit
from lattice import Coset
from tier0v2 import chain_step
U2 = chain_step((12, 24, 48, 96), 0)['fl'].U2
root = sys.argv[1]
tot = Counter(); kept = Counter()
for d in sorted(glob.glob(root + '/*')):
    M = tuple(int(c) for c in os.path.basename(d).split('_')[1])
    q = len(M)
    for f in glob.glob(d + '/l12_*_?.txt'):
        for line in open(f):
            x = line.split()
            if x[0] != 'OPEN':
                continue
            a, nu = int(x[1]), int(x[2]); eps = tuple(int(t) for t in x[3:3 + q]); b, c = int(x[3 + q]), int(x[4 + q])
            cls = branchsplit.branch_of(M, nu, eps)
            tot[cls] += 1
            if branchsplit.keep(M, a, nu, eps, Coset((b, c), tuple(U2[0]), tuple(U2[1]))):
                kept[cls] += 1
n = sum(tot.values())
for cls in sorted(tot):
    print(cls, tot[cls], round(tot[cls] / n, 4), 'kept', kept[cls], round(kept[cls] / tot[cls], 4))
print('total', n, 'kept', sum(kept.values()), 'ratio', round(n / max(1, sum(kept.values())), 2))
