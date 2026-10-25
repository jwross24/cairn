import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
import importlib.util
spec = importlib.util.spec_from_file_location('mk', '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport/tools/mk_utable_u2.py')
mk = importlib.util.module_from_spec(spec); spec.loader.exec_module(mk)
from mpmath import mpf, log10
bad = 0
for (k, a) in ((25, 0), (27, 1), (29, 0), (29, 1), (29, 24)):
    refused, n, low = mk.planted_negative(k, a)
    print(f"k={k} a={a}: certified log10 {float(log10(mpf(n))):.4f}; 0.99 of it refused: {refused}")
    bad += not refused
sys.exit(1 if bad else 0)
