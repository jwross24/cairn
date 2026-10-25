import os, sys, json, time
from collections import Counter
from math import comb
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'tier0')); sys.path.insert(0, T0); sys.dont_write_bytecode = True
from tier0v2 import multisets, two_adic_bound
TIER_B = [71663616, 226492416, 1194891264, 169869312, 4182119424, 1792336896, 13884223438848, 2113929216, 1811939328, 11329339392, 4444263936, 3699376128, 1783627776]
out = os.path.join(HERE, 'logs', 'tierb_A.jsonl')
done = set()
if os.path.exists(out):
    for l in open(out): r = json.loads(l); done.add((r['s'], tuple(r['M'])))
def npat(Ms):
    p = 12
    for d, k in Counter(Ms).items(): p *= comb(12 + k - 1, k)
    return p
t0 = time.time(); n = 0
with open(out, 'a') as f:
    import random
    random.seed(20261021)
    for s in TIER_B:
        allm = [tuple(sorted(m)) for m in multisets(s)]
        pick = {max(allm, key=len), min(allm, key=len)}
        for m in sorted(pick, key=lambda m: len(m)):
            if (s, m) in done: continue
            A = two_adic_bound(m); n += 1
            f.write(json.dumps(dict(s=s, M=list(m), k=len(m), npat=npat(m), A=A)) + '\n'); f.flush()
print('done', n, 'in %.0fs' % (time.time() - t0))
