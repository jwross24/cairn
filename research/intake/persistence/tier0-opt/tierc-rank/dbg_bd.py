import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from m1lib import *
for a in (0, 1, 5):
    for xe in (20, 100, 300, 500):
        print(a, xe, bd_first_gap(xe, a, 3))
