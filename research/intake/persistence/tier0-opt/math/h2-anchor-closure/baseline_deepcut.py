import sys, os, json, time
from collections import Counter
sys.dont_write_bytecode = True
T0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0"
os.chdir(T0)
sys.path.insert(0, T0)
import deepcut as DC
import classify_open as C
from lattice import Coset

out = sys.argv[1]
SKIP = os.environ.get("SKIP")
STRIDE = int(os.environ.get("STRIDE", "1"))
MAXC = int(os.environ.get("MAXCASES", "200000"))
WALL = float(os.environ.get("WALL", "1e9"))
files = sys.argv[2:]
Lam = DC.kernel_lattice()
seen = set()
skipkeys = set()
if SKIP:
    for line in open(SKIP):
        r = json.loads(line)
        skipkeys.add((r["s"], tuple(r["M"]), r["a"], r["y"], r["nu"], None if r["eps"] is None else tuple(r["eps"])))
idx = -1
with open(out, "w") as fo:
    for f in files:
        for (s, M, a, nu, eps, y, sol) in C.entries(f):
            key = (s, M, a, y, nu, None if eps is None else tuple(eps))
            if key in seen:
                continue
            seen.add(key)
            idx += 1
            if key in skipkeys:
                continue
            if idx % STRIDE:
                continue
            fct = C.factor237(y)
            co0 = Coset((fct[1], fct[2]), Lam.u1, Lam.u2)
            reps = DC.all_representations(M, y)
            if nu is not None:
                reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % DC.LMAX for e in eps)]
            rows = []
            t0 = time.time()
            for rep in reps:
                t1 = time.time()
                if t1 - t0 > WALL:
                    rows.append({"nu": rep[0], "de": rep[1], "closed": None, "cases": 0, "surv": None, "t": 0.0, "wall": True})
                    continue
                closed, bound, cases, stats = DC.deep_cut(co0, a, rep, 1, MAXC)
                rows.append({"nu": rep[0], "de": rep[1], "closed": closed, "cases": cases, "surv": (stats[0] if stats else None), "t": time.time() - t1})
            fo.write(json.dumps({"file": os.path.basename(f), "s": s, "M": list(M), "a": a, "y": y, "nu": nu,
                                 "eps": None if eps is None else list(eps), "reps": rows,
                                 "t": time.time() - t0}) + "\n")
            fo.flush()
