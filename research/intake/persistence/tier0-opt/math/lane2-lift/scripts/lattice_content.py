import sys
from math import gcd
from sympy import factorint, primitive_root, Matrix, ZZ
from sympy.ntheory import discrete_log
from sympy.matrices.normalforms import hermite_normal_form

U = [(0, 900), (9900, 0)]


def image_size(primes, rows=U, extra_rows=()):
    ns = [p - 1 for p in primes]
    vecs = []
    for (eb, ec) in list(rows) + list(extra_rows):
        v = []
        for p in primes:
            g = primitive_root(p)
            l3 = discrete_log(p, 3, g)
            l7 = discrete_log(p, 7, g)
            v.append((eb * l3 + ec * l7) % (p - 1))
        vecs.append(v)
    r = len(primes)
    M = [list(v) for v in vecs]
    for i, n in enumerate(ns):
        row = [0] * r
        row[i] = n
        M.append(row)
    H = hermite_normal_form(Matrix(M).T)
    det = 1
    for i in range(min(H.shape)):
        det *= abs(int(H[i, i]))
    tot = 1
    for n in ns:
        tot *= n
    return tot // det, tot


if __name__ == "__main__":
    P24 = [73, 137, 99990001]
    P48 = [17, 5882353, 9999999900000001]
    for name, ps in (("24", P24), ("48", P48), ("24+48", P24 + P48)):
        sz, tot = image_size(ps)
        print(name, ps, "image", sz, "group", tot, "index", tot // sz)
