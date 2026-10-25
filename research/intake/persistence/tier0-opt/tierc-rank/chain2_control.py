import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from chainrank import *

rec = {(31, 0): 281.50, (31, 1): 279.23, (31, 40): 280.06, (44, 0): 402.11, (44, 1): 393.93, (44, 40): 394.75}
worst = 0
for (k, a), v in rec.items():
    x, m = two_ended_log10(k, a, 2)
    d = float(x) - v
    worst = max(worst, abs(d))
    print(k, a, round(float(x), 3), v, "m", m)
print("max abs diff", worst)
