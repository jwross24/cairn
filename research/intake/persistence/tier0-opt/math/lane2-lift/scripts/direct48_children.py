import os, sys, json
from math import comb
from collections import Counter
S = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
tot24 = tot48 = 0.0
rows = []
for eq in sorted(os.listdir(S)):
    f = f"{S}/{eq}/parents24.txt"
    if not os.path.exists(f):
        continue
    cfgl = open(f"{S}/{eq}/cfgL24.txt").read().split()
    q = int(cfgl[3]); digits = list(map(int, cfgl[4:4 + q]))
    c24 = c48 = 0.0
    for l in open(f):
        t = l.split(); eps = t[2:2 + q]
        cnt = Counter(zip(digits, eps))
        a = b = 1
        for m in cnt.values():
            a *= m + 1; b *= comb(m + 3, 3)
        c24 += 2 * a; c48 += 4 * b
    rows.append((eq, c24, c48)); tot24 += c24; tot48 += c48
print("sum children 12->24 %.4g, sum direct 12->48 children %.4g, ratio %.3g" % (tot24, tot48, tot48 / tot24))
json.dump(rows, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "direct48.json"), "w"))
