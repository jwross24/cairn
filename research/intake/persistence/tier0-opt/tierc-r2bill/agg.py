import json, glob
N, S = {}, {}
for f in sorted(glob.glob("tally_*.json")):
    t = json.load(open(f))
    for k, v in t["tested_by_k"].items():
        N[int(k)] = N.get(int(k), 0) + v
    for k, v in t["surv_by_k"].items():
        S[int(k)] = S.get(int(k), 0) + v
tot = sum(N.values())
print("tested", tot, "survivors", sum(S.values()))
for k in sorted(N):
    print(k, N[k], S.get(k, 0), "%.2e" % (S.get(k, 0) / N[k]))
import collections
a = collections.Counter()
for f in glob.glob("surv_*.jsonl"):
    for ln in open(f):
        r = json.loads(ln)
        a[(r["k"], r["a"])] += 1
print(sorted(a.items()))
