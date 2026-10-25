import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
from famlib import *
for L in (96, 192, 384, 480):
    K = klat(L, L)
    phi = (1 << (L - 1)) * 4 * 5 ** (L - 1)
    print(L, 'index of kernel * 2 == phi(10^L):', K.index() * 2 == phi)
lam = build_lambdas()
for L in (96, 192, 384, 480):
    c2, c5 = {96: (9, 5), 192: (9, 5), 384: (13, 5), 480: (10, 5)}[L]
    Km = klat(c2, c5)
    ok = all(Km.contains(x, y) for (x, y) in lam[L].rows())
    print(L, 'Lambda_L inside kernel mod 2^%d 5^%d:' % (c2, c5), ok, 'index equal:', lam[L].plus(klat(L, L)).index() == Km.index())
