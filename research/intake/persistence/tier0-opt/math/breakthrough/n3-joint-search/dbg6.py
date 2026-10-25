import sys
sys.dont_write_bytecode = True
from joint import *
bad = 0
for K in (3, 4):
    for Bt in range(0, 10**K):
        if Bt % 5 == 0 or Bt % (1 << K):
            continue
        for a in range(K, 140):
            r = tail_lattice(a, Bt, K)
            if r is None:
                continue
            p, U = r
            det = U[0][0] * U[1][1] - U[0][1] * U[1][0]
            V = gauss_reduce(U)
            d2 = V[0][0] * V[1][1] - V[0][1] * V[1][0]
            if det == 0 or d2 == 0:
                bad += 1
                if bad < 5:
                    print("DEGENERATE", K, Bt, a, p, U, V)
print("bad", bad)
