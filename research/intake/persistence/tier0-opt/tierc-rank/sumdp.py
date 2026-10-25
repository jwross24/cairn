import sys
tot = 0
pairs = 0
anch = 0
mx = 0
for ln in open(sys.argv[1]):
    t = ln.split()
    T = int(t[-1].split(":")[1]) if not t[-1].startswith("OVERFLOW") else -1
    pairs += 1
    if T:
        anch += 1
        tot += T
        mx = max(mx, T)
print("pairs", pairs, "anchored", anch, "patterns", tot, "max", mx)
