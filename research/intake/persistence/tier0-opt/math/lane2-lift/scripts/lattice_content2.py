import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lattice_content import image_size
from sympy import n_order, factorint
from math import lcm
UN = [(0, 673200), (-49995000, 316800)]
P48 = [17, 5882353, 9999999900000001]
for p in P48:
    o = lcm(*[n_order(pow(3, u0, p) * pow(7, u1, p) % p, p) for (u0, u1) in UN])
    print(p, "image order of Lambda_24", o, "index", (p - 1) // o, "p-1 =", factorint(p - 1))
sz, tot = image_size(P48, rows=UN)
print("joint level-48 primes: image", sz, "group", tot, "index", tot // sz)
