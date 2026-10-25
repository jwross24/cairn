import random, json
import branchsplit
rng = random.Random(5)
bad = 0; N = 0
for _ in range(200000):
    n = rng.randrange(1, 60)
    q = rng.randrange(1, min(n, 12) + 1)
    pos = sorted(rng.sample(range(n), q))
    D = [rng.randrange(2, 10) for _ in range(q)]
    digs = [1] * n
    for d, e in zip(D, pos):
        digs[e] = d
    y = int(''.join(str(x) for x in reversed(digs)))
    L = rng.choice((12, 24, 48, 96))
    nu = n % L
    eps = tuple(e % L for e in pos)
    order = sorted(range(q), key=lambda i: (D[i], eps[i]))
    Ds = tuple(D[i] for i in order); es = tuple(eps[i] for i in order)
    t, s = branchsplit.branch_of(Ds, nu, es)
    N += 1
    if t != (y % 3 == 0) or s != (y % 7 == 0):
        bad += 1
print('random patterns', N, 'mismatches', bad)
rows = [json.loads(l) for l in open('../logs/plants_on.jsonl')]
mm = 0
for r in rows:
    y = r['y']; st = str(y); n = len(st)
    pos = [(int(ch), i) for i, ch in enumerate(reversed(st)) if ch != '1']
    pos.sort()
    t, s = branchsplit.branch_of(tuple(d for d, _ in pos), n % 12, tuple(e % 12 for _, e in pos))
    if t != (r['b'] > 0) or s != (r['c'] > 0):
        mm += 1
print('plants', len(rows), 'branch != (b>0, c>0):', mm)
