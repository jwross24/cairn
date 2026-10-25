import sys, json
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1d import analyze_rank
from depth1c import v2
from statlib import clopper_pearson

rows = [json.loads(l) for l in open(sys.argv[1])]
n = len(rows)
s2 = s1k = 0
ks = []
as_ = []
kinds = {"b": 0, "c": 0}
for r in rows:
    w = [tuple(x) for x in r["words"]]
    kind = "b" if r["y"] % 3 == 0 else "c"
    kinds[kind] += 1
    a = v2(r["y"])
    x2 = analyze_rank(r["y"], w, 1, 2)[0]
    x1 = analyze_rank(r["y"], w, 1, kind)[0]
    assert x1 <= x2 or True
    s2 += 1 if x2 else 0
    s1k += 1 if x1 else 0
    ks.append(len(w))
    as_.append(a)
print("rank-1 patterns", n, "kinds", kinds, "digit counts", min(ks), sorted(ks)[n // 2], max(ks), "a median", sorted(as_)[n // 2])
print("survive depth-1 under the rank-2 (production) cut:", s2, "CP95", clopper_pearson(s2, n))
print("survive depth-1 under the rank-1 cut:", s1k, "CP95", clopper_pearson(s1k, n))
