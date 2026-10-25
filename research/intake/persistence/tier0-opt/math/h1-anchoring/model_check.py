import json, math, sys
from collections import Counter, defaultdict
from math import comb
D = json.load(open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h1-anchoring/density.json"))
rho = {int(L): int(v["index"]) / int(v["phi"]) for L, v in D.items()}
print({L: f"{r:.3e}" for L, r in rho.items()})

def npat(M, L):
    c = Counter(M)
    n = L
    for d, m in c.items():
        n *= comb(L + m - 1, m)
    return n

obs = defaultdict(lambda: [0, 0, 0.0])
rows = []
for f in sys.argv[1:]:
    for line in open(f):
        r = json.loads(line)
        for eq in r.get("eqs", []):
            if isinstance(eq, dict):
                M, lv = eq["M"], eq["levels"]
            else:
                M, lv = eq[0], eq[3]
            for ent in lv:
                L, nin, nout = ent[0], ent[1], ent[2]
                obs[L][0] += nin
                obs[L][1] += nout
                prev = {12: None, 24: 12, 48: 24, 96: 48}[L]
                ratio = rho[L] if prev is None else rho[L] / rho[prev]
                obs[L][2] += nin * ratio
for L in sorted(obs):
    nin, nout, pred = obs[L]
    print(f"L={L} inputs={nin} observed_survivors={nout} predicted_random={pred:.4g} obs/pred={nout / pred if pred else float('nan'):.3g}")

tot = 0.0
perq = defaultdict(float)
seen = set()
for f in sys.argv[1:]:
    for line in open(f):
        r = json.loads(line)
        for eq in r.get("eqs", []):
            M = tuple(eq["M"] if isinstance(eq, dict) else eq[0])
            key = (r["s"], M)
            if key in seen:
                continue
            seen.add(key)
            mu = npat(M, 96) * rho[96]
            tot += mu
            perq[len(M)] += mu
print("equations", len(seen), "sum mu96", f"{tot:.4g}")
for q in sorted(perq):
    print(q, f"{perq[q]:.3e}")
