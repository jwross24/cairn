import sys, os, json, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from congchain import *
from wordspace import load_rep, words_of

mode = sys.argv[1] if len(sys.argv) > 1 else "true"
c96 = (9, 5); c480 = (10, 5)
if mode == "mod2_96": c96 = (8, 5)
if mode == "mod2_480": c480 = (11, 5)
rec = json.load(open(HERE + "recorded550.json"))
tot = collections.Counter()
t0 = time.time()
bad = []
for i, r in sorted(rec.items()):
    if "wrap" not in r:
        tot["no_rep0_line"] += 1
        continue
    y, nu, pairs = load_rep(i)
    y = int(y)
    a, b, c = factor237(y)
    w, (n96, s96), (n480, s480) = predict(y, a, nu, pairs, c96, c480, want=True)
    ws = words_of(i)
    rs = set(frozenset((pairs[j][0], pairs[j][1]) for j in wd) for wd in ws)
    tot["reps"] += 1
    tot["mask_sets_equal"] += (s96 == rs)
    tot["words_n_ok"] += (n96 == r["words"])
    tot["wrap_ok"] += (w == r["wrap"])
    ok_alive = (n480 == r["alive"] - r["nsalive"])
    tot["alive_ok"] += ok_alive
    tot["alive_sub_words"] += (s480 <= s96)
    tot["all"] += (s96 == rs and ok_alive and w == r["wrap"])
    if not (s96 == rs and ok_alive) and len(bad) < 3:
        bad.append((i, w, r["wrap"], n96, r["words"], n480, r["alive"], r["nsalive"]))
print(mode, dict(tot), "%.1fs" % (time.time() - t0))
for b in bad: print("BAD", b)
