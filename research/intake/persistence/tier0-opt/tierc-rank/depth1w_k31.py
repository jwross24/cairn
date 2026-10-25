import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1w import *

CL = {0: [3], 1: [2], 2: [2, 7], 3: [2], 4: [2, 3], 5: [2] * 8, 6: [2] * 6, 7: [2] * 2, 8: [2] * 2 + [3] * 2, 9: [2] + [3] * 3}
words = [(d, e) for e, l in CL.items() for d in l]
y = 3 ** 3 * 7 ** 10
for E in (1, 2, 3):
    s1, wl, nl = s1_weighted(y, words, E)
    print("E", E, "S1", s1, "Wlow", wl, "nonlow", nl, "nodes", wl * nl)
print("measured N_3 = 440640")
