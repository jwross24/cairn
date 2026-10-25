import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
sys.argv = ["x", "8", "70", "12,24,48,96", "/dev/null", "1"]
import run_base_mp as R
for s in (826875, 972405, 455625, 37500, 55125, 23625, 6750, 3402):
    print(s, [len(M) for M in R.base.multisets(s)], R.npat(s))
