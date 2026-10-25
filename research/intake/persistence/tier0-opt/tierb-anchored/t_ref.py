import sys, time, os
sys.dont_write_bytecode = True
T0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0"
sys.path.insert(0, T0)
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC, classify_open as C
t = time.time()
Lam96 = DC.kernel_lattice()
print("kernel", time.time() - t, Lam96.u1, Lam96.u2)
y = 2**4 * 3**5
fct = C.factor237(y)
co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
R96 = (10**96 - 1) // 9
t = time.time()
n = 0
for dgt in range(20):
    L = R96 + 10**dgt
    if v2(L) != 4 or L % 5 == 0: continue
    r = cut_coset(co0, 4, L, 96); n += 1
print(n, "calls", time.time() - t)
