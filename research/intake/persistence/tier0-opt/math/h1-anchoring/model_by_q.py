import json, sys
from collections import defaultdict
D = json.load(open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h1-anchoring/density.json"))
rho = {int(L): int(v["index"]) / int(v["phi"]) for L, v in D.items()}
prev = {12: None, 24: 12, 48: 24, 96: 48}
acc = defaultdict(lambda: [0, 0, 0.0])
for f in sys.argv[1:]:
    for line in open(f):
        r = json.loads(line)
        for eq in r.get("eqs", []):
            M, lv = (eq["M"], eq["levels"]) if isinstance(eq, dict) else (eq[0], eq[3])
            for L, nin, nout, *_ in lv:
                ratio = rho[L] if prev[L] is None else rho[L] / rho[prev[L]]
                k = (L, min(len(M), 10))
                acc[k][0] += nin
                acc[k][1] += nout
                acc[k][2] += nin * ratio
for k in sorted(acc):
    nin, nout, pred = acc[k]
    if pred > 20:
        print(f"L={k[0]} q={'10+' if k[1] == 10 else k[1]} in={nin} obs={nout} pred={pred:.4g} obs/pred={nout / pred:.3f}")
