import sys, json
from collections import defaultdict

pairs = [json.loads(l) for l in open("pairs_filtered.jsonl")]
r1 = [(p[0], p[1], p[4]) for p in pairs if (p[2] > 0) + (p[3] > 0) == 1]
done = [ln.split() for ln in open(sys.argv[1])]
ok = [t for t in done if t and t[-1].startswith("T:")]
print("rank-1 pairs", len(r1), "complete lines", len(ok))
b = defaultdict(lambda: [0, 0, 0])
for t, (y, a, k) in zip(ok, r1):
    assert str(y) == t[0] and k == int(t[1])
    T = int(t[-1].split(":")[1])
    b[a][0] += 1
    b[a][1] += 1 if T else 0
    b[a][2] += T
for a in sorted(b):
    print("a", a, "pairs", b[a][0], "anchored", b[a][1], "patterns", b[a][2])
remaining = defaultdict(int)
for (y, a, k) in r1[len(ok):]:
    remaining[a] += 1
print("remaining pairs by a (first 8):", dict(list(sorted(remaining.items()))[:8]), "total remaining", sum(remaining.values()))
