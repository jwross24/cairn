import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from congchain import *
from wordspace import load_rep
for i in ("t347", "t348"):
    y, nu, pairs = load_rep(i); y = int(y)
    a, b, c = factor237(y)
    print(i, predict(y, a, nu, pairs))
