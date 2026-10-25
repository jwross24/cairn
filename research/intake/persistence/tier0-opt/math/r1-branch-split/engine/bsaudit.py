import sys, json
from collections import Counter
from fractions import Fraction
import bsgate, branchsplit

stats = Counter(); bad = []
for line in open(sys.argv[1]):
    d = json.loads(line)
    L = int(d['tag'][1:])
    M = tuple(d['M'])
    item = dict(a=d['a'], nu=d['nu'], eps=d['eps'], v0=d['v0'], u1=d['u1'], u2=d['u2'])
    verdict, cls = bsgate.indep_impossible(M, item, L)
    ab, ac = bsgate.anchor(item)
    need_b0, need_c0 = not cls[0], not cls[1]
    forb = (need_b0 and ab > 0) or (need_c0 and ac > 0)
    stats[(d['tag'], verdict)] += 1
    stats[('anchor', 'needs-forbidden-factor' if forb else 'compatible')] += 1
    stats[('class', cls)] += 1
    if verdict != 'inconsistent':
        bad.append(d)
print(json.dumps({str(k): v for k, v in sorted(stats.items(), key=str)}))
print('NOT-INCONSISTENT', len(bad))
if bad:
    print(bad[:3])
