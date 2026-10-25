import sys, random, itertools
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1d import analyze_rank, class_pools
from depth1c import v2

R96 = (10 ** 96 - 1) // 9
rng = random.Random(21)
bad = 0
bad_exist = 0
nz = 0
tot = 0
multi = 0
for trial in range(600):
    k = rng.randrange(3, 10)
    words = []
    for _ in range(k):
        words.append((rng.choice([2, 3, 4, 6, 7, 8, 9]), rng.randrange(0, 16)))
    pools = class_pools(words)
    classes = sorted(pools)
    opts = [[None] + sorted(pools[e]) for e in classes]
    choice = [rng.choice(o) for o in opts]
    T = R96 + sum((d - 1) * 10 ** e for e, d in zip(classes, choice) if d is not None)
    y = T if rng.random() < 0.7 else T + rng.randrange(1, 1000) * 5 ** 5 * 2 ** rng.randrange(10, 14)
    if y % 5 == 0 or y <= 0:
        continue
    a = v2(y)
    top = a + 9
    M = 2 ** (a + 9) * 5 ** 5
    lowc = [i for i, e in enumerate(classes) if e < top]
    cnt = 0
    for combo in itertools.product(*[opts[i] for i in lowc]):
        TT = R96 + sum((d - 1) * 10 ** classes[i] for i, d in zip(lowc, combo) if d is not None)
        if (TT - y) % M == 0:
            cnt += 1
    got = analyze_rank(y, words, 1, 2)[0]
    tot += 1
    nz += 1 if cnt else 0
    multi += 1 if cnt > 1 else 0
    if got != cnt:
        bad += 1
        print("MISMATCH", words, y, cnt, got)
print("trials", tot, "with a surviving case", nz, "with >1 surviving case", multi, "count mismatches", bad)
