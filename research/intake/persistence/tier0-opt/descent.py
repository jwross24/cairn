"""10-adic descent for OPEN patterns.

State: arrangement D, pattern residues (nu, eps) mod L, exponent a, coset C of (b,c), and the
known tail: y ≡ Y (mod 10^K) with K = K(C) (ten_adic_K). The tail's non-1 digits consume entries
of the pattern; the rest (M_high) sit at positions >= K; every other position in [K, n) holds 1.

Lemma (2-adic). 9y = 10^n + Σ_{high} 9(d_j-1)10^{e_j} + (9Y - 10^K). Let t = v2(9Y - 10^K) and
m = min(n, min e_high) >= K. If m > t then v2(RHS) = t, so a = v2(9y) = t; hence a != t forces
m <= t, i.e. the next event (a high digit, or the end of the number) is at a position in [K, t].
Enumerate those finitely many events; each extends the tail, which cuts the coset by the
congruence 2^a 3^b 7^c ≡ Y' (mod 10^{K'}), then recurse. If a == t the lemma is silent (OPEN).
"""
from collections import Counter
from lattice import Coset
from math import gcd

def v2(x):
    return (x & -x).bit_length() - 1

def digit_product_ok(y, M):
    s = str(y)
    return '0' not in s and Counter(ch for ch in s if ch != '1') == Counter(str(d) for d in M)

def factor237(y):
    e = [0, 0, 0]
    for i, p in enumerate((2, 3, 7)):
        while y % p == 0:
            y //= p; e[i] += 1
    return tuple(e) if y == 1 else None

# ---- discrete logs in (Z/5^k)^* (base 3, a primitive root) and (Z/2^k)^* (= <-1> x <5>)
def log3_mod5k(u, k):
    N = 4 * 5 ** (k - 1); mod = 5 ** k
    assert u % 5
    # Pohlig-Hellman: x mod 4 and x mod 5^(k-1)
    g4 = pow(3, 5 ** (k - 1), mod); u4 = pow(u, 5 ** (k - 1), mod)
    x4 = next(i for i in range(4) if pow(g4, i, mod) == u4)
    x5 = 0
    g5 = pow(3, 4, mod); u5 = pow(u, 4, mod)       # order 5^(k-1)
    h = pow(g5, 5 ** (k - 2), mod) if k >= 2 else 1   # order 5
    for i in range(k - 1):
        # determine digit i of x5
        w = pow(u5 * pow(g5, -x5, mod) % mod, 5 ** (k - 2 - i), mod)
        dgt = next(j for j in range(5) if pow(h, j, mod) == w)
        x5 += dgt * 5 ** i
    # CRT: x ≡ x4 (mod 4), x ≡ x5 (mod 5^(k-1))
    m5 = 5 ** (k - 1)
    x = x5
    while x % 4 != x4:
        x += m5
    assert pow(3, x, mod) == u % mod
    return x, N

def log_mod2k(u, k):
    """u odd -> (s, t, 2^(k-2)) with u ≡ (-1)^s 5^t (mod 2^k), k >= 3."""
    mod = 2 ** k
    s = 0 if u % 4 == 1 else 1
    w = (-u) % mod if s else u % mod           # w ≡ 1 mod 4
    t = 0
    for i in range(2, k):
        if (w * pow(pow(5, t, mod), -1, mod)) % (2 ** (i + 1)) != 1:
            t += 2 ** (i - 2)
    assert pow(5, t, mod) == w
    return s, t, 2 ** (k - 2)

def cut_coset(co, a, Yp, Kp):
    """coset of (b,c) in co with 2^a 3^b 7^c ≡ Yp (mod 10^Kp); None if empty."""
    assert Kp >= 3
    Z5 = Yp * pow(pow(2, a, 5 ** Kp), -1, 5 ** Kp) % 5 ** Kp
    l7, N = log3_mod5k(7 % 5 ** Kp, Kp)
    lZ, _ = log3_mod5k(Z5, Kp)
    co = co.intersect(1, l7, lZ, N)                # b + l7*c ≡ lZ (mod 4*5^(Kp-1))
    if co is None: return None
    # 2-adic part: 2^a * (3^b 7^c) ≡ Yp (mod 2^Kp)
    Y2 = Yp % 2 ** Kp
    if Kp <= a:
        return co if Y2 == 0 else None
    if Y2 == 0 or v2(Y2) != a:
        return None
    k2 = Kp - a
    Z2 = (Y2 >> a) % 2 ** k2                        # odd; 3^b 7^c ≡ Z2 (mod 2^k2)
    if k2 == 1:
        return co
    if k2 == 2:
        return co.intersect(1, 1, 0 if Z2 % 4 == 1 else 1, 2)   # 3,7 ≡ -1 mod 4
    s3, t3, _ = log_mod2k(3, k2); s7, t7, _ = log_mod2k(7, k2); sZ, tZ, half = log_mod2k(Z2, k2)
    co = co.intersect(s3, s7, sZ, 2)
    if co is None: return None
    co = co.intersect(t3, t7, tZ, half)
    return co

def descend(a, D, eps, nu, co, L, M, K, kcap, depth=0, max_depth=12):
    """-> (status, solutions) with status in {'DEAD','OPEN'}; solutions = set of exact y found."""
    mod = 10 ** K
    Y = pow(2, a, mod) * pow(3, co.v0[0], mod) * pow(7, co.v0[1], mod) % mod
    sols = set()
    # exact case n <= K: the number is Y itself
    sY = str(Y)
    if Y >= 10 and '0' not in sY and len(sY) % L == nu % L and digit_product_ok(Y, M):
        f = factor237(Y)
        if f and f[0] == a and co.contains(f[1], f[2]):
            want = Counter((d, e % L) for d, e in zip(D, eps))
            have = Counter((int(ch), i % L) for i, ch in enumerate(reversed(sY)) if ch != '1')
            if have == want:
                sols.add(Y)
    # case n > K: the last K digits of y are the zero-padded tail
    tail = sY.zfill(K)
    if '0' in tail:
        return 'DEAD', sols
    # consume pattern entries by the tail's non-1 digits
    avail = list(zip(D, eps))                      # (digit, residue)
    for i, ch in enumerate(reversed(tail)):
        if ch == '1': continue
        d = int(ch)
        j = next((j for j, (dd, e) in enumerate(avail) if dd == d and e % L == i % L), None)
        if j is None:
            return 'DEAD', sols
        avail.pop(j)
    t = v2(9 * Y - 10 ** K) if 9 * Y != 10 ** K else None
    if t is None:
        return 'OPEN', sols
    if a == t:
        return 'OPEN', sols
    # a != t  =>  next event at position m in [K, t]  (if t < K: no event possible -> DEAD)
    if t < K:
        return 'DEAD', sols
    status = 'DEAD'
    if not avail:
        # the number ends: n in [K+1, t], n ≡ nu (mod L); y = Y + 10^K R_{n-K}
        for n in range(K + 1, t + 1):
            if n % L != nu % L: continue
            y = Y + 10 ** K * (10 ** (n - K) - 1) // 9
            f = factor237(y)
            if f and f[0] == a and co.contains(f[1], f[2]) and digit_product_ok(y, M):
                sols.add(y)
        return status, sols
    for j, (d, e_res) in enumerate(avail):
        for e in range(K, t + 1):
            if e % L != e_res % L: continue
            Yp = Y + 10 ** K * (10 ** (e - K) - 1) // 9 + d * 10 ** e
            Kp = e + 1
            if Kp < 3:
                continue  # cannot happen: K >= 1 and e >= K... keep simple
            co2 = cut_coset(co, a, Yp, Kp)
            if co2 is None: continue
            # new pattern with entry j consumed; recurse with the extended known tail.
            from tier0 import ten_adic_K
            K2 = ten_adic_K(co2, kcap, a)
            assert K2 >= Kp, (K2, Kp)
            D2 = tuple(dd for i2, (dd, _) in enumerate(avail) if i2 != j)
            e2 = tuple(ee for i2, (_, ee) in enumerate(avail) if i2 != j)
            # the tail recorded in the coset must agree with Yp on Kp digits (by construction)
            if depth >= max_depth:
                return 'OPEN', sols
            st, s2 = descend_tail(a, D2, e2, nu, co2, L, M, K2, kcap, depth + 1)
            sols |= s2
            if st == 'OPEN': status = 'OPEN'
    return status, sols

def descend_tail(a, D_rem, e_rem, nu, co, L, M, K, kcap, depth):
    """like descend, but the consumed digits are already removed from (D_rem, e_rem); the tail
    check re-derives consumption from the coset's own tail, so just rebuild full lists."""
    # Rebuild: the coset's tail contains all consumed digits; descend() re-consumes them from a
    # full pattern, so pass the remaining entries plus the consumed ones recovered from the tail.
    mod = 10 ** K
    Y = pow(2, a, mod) * pow(3, co.v0[0], mod) * pow(7, co.v0[1], mod) % mod
    tail = str(Y).zfill(K)
    consumed = [(int(ch), i) for i, ch in enumerate(reversed(tail)) if ch != '1']
    D_full = tuple(d for d, _ in consumed) + tuple(D_rem)
    e_full = tuple(i for _, i in consumed) + tuple(e_rem)
    return descend(a, D_full, e_full, nu, co, L, M, K, kcap, depth)
