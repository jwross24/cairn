import sys, json, random
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1c import analyze, v2

SRC = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/unified-cert/inputs/patterns-u2.jsonl"
pats = [json.loads(l) for l in open(SRC)]
ok = 0
tot_reps = 0
surv_reps = 0
aerr = 0
for p in pats:
    y = p["y"]
    if v2(y) != p["a"]:
        aerr += 1
    any_s = False
    for rep in p["reps"]:
        words = [tuple(w) for w in rep["De"]]
        s1 = analyze(y, words, 1)[0]
        tot_reps += 1
        if s1 > 0:
            any_s = True
            surv_reps += 1
    ok += 1 if any_s else 0
print("recorded depth-1 survivors:", len(pats), "patterns; mine report survivor:", ok, "; reps", tot_reps, "surviving reps", surv_reps, "; v2(y)!=a:", aerr)
rng = random.Random(4)
trials = 0
dead = 0
for p in pats:
    y = p["y"]
    for rep in p["reps"]:
        words = [tuple(w) for w in rep["De"]]
        for _ in range(20):
            w2 = list(words)
            i = rng.randrange(len(w2))
            d, e = w2[i]
            a = v2(y)
            if rng.random() < 0.5:
                w2[i] = (d, (e + rng.randrange(1, 8)) % 96)
            else:
                w2[i] = (rng.choice([x for x in (2, 3, 4, 6, 7, 8, 9) if x != d]), e)
            trials += 1
            if analyze(y, w2, 1)[0] == 0:
                dead += 1
print("perturbed copies (one digit moved or changed):", trials, "closed at depth 1:", dead)
