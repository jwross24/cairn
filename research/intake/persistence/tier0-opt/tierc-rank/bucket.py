import sys
from collections import defaultdict
b = defaultdict(lambda: [0, 0, 0])
for ln in open(sys.argv[1]):
    t = ln.split()
    if not t or t[-1].startswith("OVERFLOW"):
        continue
    d = len(t[0])
    T = int(t[-1].split(":")[1])
    b[d][0] += 1
    b[d][1] += 1 if T else 0
    b[d][2] += T
for d in sorted(b):
    print("digits", d, "pairs", b[d][0], "anchored", b[d][1], "patterns", b[d][2])
