import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from m1lib import *
for k, a in ((34, 6), (31, 0), (26, 6)):
    x, m = two_ended_mv(k, a, "b")
    print(k, a, "two-ended rank1 MV", round(float(x), 2), "m", m, "D", depth_needed(x))
