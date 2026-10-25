import sys, os, json, time, math
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
os.chdir("/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
import run_c
import tier0v2
orig = tier0v2.solve_equation
def lv48(*a, **k):
    k["levels"] = (12, 24, 48)
    return orig(*a, **k)
run_c.solve_equation = lv48
s = 124416
M = (2,) * 9 + (3,) * 5
t0 = time.time()
r = run_c.run(s, M, [], ncores=1, workdir="/private/tmp/h1-l48", verbose=True)
print("levels", [(L, n, sv, cls) for (L, ps, n, sv, cls, el) in r["levels"]], "secs", round(time.time() - t0), flush=True)
out = []
for (a, nu, eps, co) in r["open"]:
    out.append({"a": a, "nu": nu, "eps": list(eps), "v0": [str(co.v0[0]), str(co.v0[1])],
                "u1": [str(x) for x in co.u1], "u2": [str(x) for x in co.u2]})
json.dump({"levels": [(L, n, sv, cls) for (L, ps, n, sv, cls, el) in r["levels"]], "open": out},
          open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h1-anchoring/l48_result.json", "w"))
print("open at 48:", len(out), flush=True)
