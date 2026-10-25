import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from uppp import *

for k, a in ((31, 0), (29, 0), (29, 1), (34, 0), (34, 1), (34, 20), (34, 44), (20, 5), (17, 10)):
    d, x = depth_for(k, a)
    print(k, a, round(x, 2), "D", d, "E", exact_e(d, a))
