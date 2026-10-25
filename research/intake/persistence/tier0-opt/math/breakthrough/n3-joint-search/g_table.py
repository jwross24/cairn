import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h3-h4")
import h3_fold
for k in (8, 12, 16, 20, 24, 28, 31, 36, 40, 44):
    v = h3_fold.best(k, 1)
    print(k, round(float(v[0]), 2), v[1], flush=True)
