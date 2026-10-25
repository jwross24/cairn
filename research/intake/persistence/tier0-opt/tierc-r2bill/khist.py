import json, sys
from collections import Counter
c = Counter()
for ln in open(sys.argv[1]):
    r = json.loads(ln)
    c[len(r["words"])] += 1
n = sum(c.values())
for k in sorted(c):
    print(k, c[k], round(c[k] / n, 5))
