import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/lane2-lift")
import cfgparse
c = cfgparse.parse(sys.argv[1])
print("primes", [(p["p"], p["fac"]) for p in c["primes"]])
for i, k in enumerate(c["comps"]):
    keys = {e[0] for e in k["ent"]}
    print("comp", i, "cidx", k["cidx"], "cmod", k["cmod"], "hs", k["hs"], "sample", sorted(keys)[:6])
    if 625 in k["cmod"]:
        j = k["cmod"].index(625)
        vals = sorted({key[j] for key in keys})
        print(" coord(625) distinct values", len(vals), "all mult of 25:", all(v % 25 == 0 for v in vals), "key[j] mod 625 values", vals[:30])
        print(" key+1 in image count:", sum(1 for key in keys if tuple(x + (1 if t == j else 0) for t, x in enumerate(key)) in keys))
print("N", c["N"], "Uold", c["Uold"], "lins", c["lins"])
