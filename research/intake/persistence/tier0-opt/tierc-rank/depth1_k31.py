import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1 import *
from math import comb

CL = {0: [3], 1: [2], 2: [2, 7], 3: [2], 4: [2, 3], 5: [2] * 8, 6: [2] * 6, 7: [2] * 2, 8: [2] * 2 + [3] * 2, 9: [2] + [3] * 3}
words = [(d, e) for e, l in CL.items() for d in l]
y = 3 ** 3 * 7 ** 10
s1 = s1_count(y, words)
g = Counter(words)
for E in (1, 2, 3):
    prod = 1
    for (d, e), c in g.items():
        if e < 9:
            prod *= comb(c + E, E) / (c + 1)
    print("E", E, "S1", s1, "prod", prod, "S1*prod", s1 * prod)
print("measured N_3 = 440640")
