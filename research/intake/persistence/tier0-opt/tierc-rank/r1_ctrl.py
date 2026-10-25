import sys, json
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1d import analyze_rank

SRC = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/unified-cert/inputs/patterns-u2.jsonl"
for l in open(SRC):
    p = json.loads(l)
    y = p["y"]
    r = (y % 3 == 0) + (y % 7 == 0)
    if r < 2:
        kind = "b" if y % 3 == 0 else "c"
        print("rank", r, "y", y, "a", p["a"], "b", p["b"], "c", p["c"], "k", p["k"], "M", p["M"])
        for rep in p["reps"]:
            w = [tuple(x) for x in rep["De"]]
            print("  rep nu", rep["nu"], "rank-1 test", analyze_rank(y, w, 1, kind)[0], "rank-2 test", analyze_rank(y, w, 1, 2)[0])
