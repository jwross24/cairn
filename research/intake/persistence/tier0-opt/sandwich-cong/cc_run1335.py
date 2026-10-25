import sys, os, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from congchain import *

mode = sys.argv[1] if len(sys.argv) > 1 else "true"
c96 = (9, 5); c480 = (10, 5)
if mode == "mod2_96": c96 = (8, 5)
if mode == "mod2_480": c480 = (11, 5)
if mode == "mod5_96": c96 = (9, 4)
if mode == "mod2_480m": c480 = (9, 5)
t0 = time.time()
tot = collections.Counter()
bad = []
for line in open(HERE + "runs/base1335.reps"):
    f = line.rstrip("\n").split("\t")
    ci, ri, y, a, nu, n = int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4]), int(f[5])
    pairs = [tuple(int(x) for x in t.split(":")) for t in f[6].split()]
    wrap, nwords, nonappl, alive, nsalive = int(f[7]), int(f[8]), int(f[9]), int(f[10]), int(f[11])
    pe = list(pairs)
    nuT = nu
    if mode == "digit" and pe:
        d, e = pe[0]
        pe[0] = (d + 1 if d < 9 else 2, e)
    if mode == "nu":
        nuT = nu + 1
    w, p96, p480 = predict2(y, a, nu, pairs, pe, nuT, c96, c480, dedup=False)
    tot["reps"] += 1
    tot["w_ok"] += (w == wrap or nwords == 0)
    tot["words_ok"] += (p96 == nwords)
    shadow_rec = alive - nsalive
    tot["alive_ok"] += (p480 == shadow_rec)
    tot["all_ok"] += (p96 == nwords and p480 == shadow_rec)
    tot["nsalive"] += nsalive
    if p96 != nwords or p480 != shadow_rec:
        if len(bad) < 3: bad.append((ci, ri, y, a, nu, wrap, nwords, p96, alive, nsalive, p480))
print(mode, dict(tot), "%.1fs" % (time.time() - t0))
for b in bad: print("BAD", b)
