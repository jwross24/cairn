import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'tier0')); sys.path.insert(0, T0); sys.dont_write_bytecode = True
from tier0v2 import multisets
TIER_B = [71663616, 226492416, 1194891264, 169869312, 4182119424, 1792336896, 13884223438848, 2113929216, 1811939328, 11329339392, 4444263936, 3699376128, 1783627776]
tot = 0
for s in TIER_B:
    n = sum(1 for _ in multisets(s)); tot += n; print(s, n)
print('total', tot)
