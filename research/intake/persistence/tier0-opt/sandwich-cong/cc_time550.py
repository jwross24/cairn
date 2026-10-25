import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from congchain import *
from wordspace import load_rep
rec = json.load(open(HERE + "recorded550.json"))
reps = []
for i in sorted(rec):
    y, nu, pairs = load_rep(i); y = int(y)
    reps.append((i, y, factor237(y)[0], nu, pairs))
t0 = time.perf_counter()
tot = 0
for i, y, a, nu, pairs in reps:
    w, n96, n480 = predict(y, a, nu, pairs)
    tot += n480
t1 = time.perf_counter()
print("reps", len(reps), "shadow-alive total", tot, "time %.3f s, %.1f us per rep" % (t1 - t0, (t1 - t0) / len(reps) * 1e6))
