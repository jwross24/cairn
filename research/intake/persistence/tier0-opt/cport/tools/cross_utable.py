import sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport/tools')
import mk_utable_prime as M
import h3_fold as F
from mpmath import mpf, log10

pts = [tuple(map(int, p.split(','))) for p in sys.argv[1:]]
bad = 0
for (k, a) in pts:
    t = time.time()
    n, m = M.best_b3(k, a)
    b = float(log10(mpf(n)))
    h, mh = F.best(k, a)
    h = float(h)
    ok = abs(b - h) <= 0.01
    bad += not ok
    print(f"k={k} a={a}: B3 certified log10 {b:.2f} (m={m}); h3_fold {h:.2f} (m={mh}); agree to 0.01: {ok} [{time.time() - t:.0f}s]", flush=True)
sys.exit(1 if bad else 0)
