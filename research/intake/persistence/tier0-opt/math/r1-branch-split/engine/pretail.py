import sys, random, json
from collections import Counter
import branchsplit
from tier0v2 import chain_step, two_adic_bound

step = chain_step((12, 24, 48, 96), 0)
pdata, fl = step['pdata'], step['fl']
N = int(sys.argv[1])
out = []
for M in ((2, 2, 2, 2, 2, 4, 4, 4, 7), (2, 2, 2, 2, 2, 2, 2, 8, 8), (4, 4, 4, 7, 8, 8), (2, 2, 2, 3, 3, 5, 5, 6), (3, 4, 5, 5, 6, 6), (2, 3, 3, 4, 5, 5, 6, 9, 9, 9, 9)):
    rng = random.Random(11)
    A = two_adic_bound(M)
    D = tuple(sorted(M))
    rank3 = kept = patterns = zero = 0
    for _ in range(N):
        nu = rng.randrange(12)
        eps = tuple(rng.randrange(12) for _ in D)
        patterns += 1
        logs = []
        z = False
        for pd in pdata:
            y = pd.R[nu]
            for d, e in zip(D, eps):
                y = (y + (d - 1) * pd.pow10[e]) % pd.p
            if y == 0:
                z = True
                break
            logs.append(pd.log(y))
        if z:
            zero += 1
            continue
        v = fl.solve(logs)
        if v is None:
            continue
        for a0, co in fl.split_by_a(v, A):
            rank3 += 1
            if branchsplit.keep(D, a0, nu, eps, co):
                kept += 1
    row = dict(M=M, A=A, samples=patterns, rank3_a_pattern=rank3, kept=kept, ratio=round(rank3 / max(kept, 1), 2))
    print(json.dumps(row), flush=True)
