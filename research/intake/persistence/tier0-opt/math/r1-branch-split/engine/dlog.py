"""Discrete logarithms in (Z/p)^* with the factorization of p-1 cached per prime.
Pohlig–Hellman over the prime-power factors, baby-step giant-step inside each; every result is
verified by re-exponentiation before it is returned."""
from math import gcd, isqrt
import sympy

_FACT = {}

def _bsgs(g, h, p, order):
    """x in [0, order) with g^x ≡ h (mod p); g has multiplicative order `order`."""
    m = isqrt(order) + 1
    table = {}
    cur = 1
    for j in range(m):
        table.setdefault(cur, j)
        cur = cur * g % p
    ginv_m = pow(g, -m, p)
    cur = h
    for i in range(m):
        if cur in table:
            return (i * m + table[cur]) % order
        cur = cur * ginv_m % p
    raise ValueError("no discrete log")

def discrete_log(p, h, g):
    """x with g^x ≡ h (mod p), g a primitive root mod p."""
    n = p - 1
    if p not in _FACT:
        _FACT[p] = sympy.factorint(n)
    fac = _FACT[p]
    h %= p
    residues = []; moduli = []
    for q, e in fac.items():
        qe = q ** e
        gq = pow(g, n // qe, p); hq = pow(h, n // qe, p)   # order qe
        # Pohlig–Hellman lift within q^e
        x = 0
        gamma = pow(gq, q ** (e - 1), p)                   # order q
        for k in range(e):
            hk = pow(hq * pow(gq, -x, p) % p, q ** (e - 1 - k), p)
            dk = _bsgs(gamma, hk, p, q)
            x += dk * q ** k
        residues.append(x); moduli.append(qe)
    # CRT
    x = 0; M = 1
    for r, m in zip(residues, moduli):
        t = ((r - x) * pow(M, -1, m)) % m
        x += M * t; M *= m
    assert pow(g, x, p) == h, (p, h, g)
    return x

if __name__ == "__main__":
    import random
    from sympy import primitive_root
    for p in (11, 13, 37, 101, 9901, 73, 137, 99990001, 17, 5882353, 9999999900000001, 75118313082913):
        g = primitive_root(p)
        for _ in range(20):
            x = random.randrange(0, p - 1); h = pow(g, x, p)
            assert discrete_log(p, h, g) == x
    print("dlog selftest ok")
