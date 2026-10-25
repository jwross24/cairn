import math
import cypari2

pari = cypari2.Pari()
pari.allocatemem(1500000000)

R96 = (10 ** 96 - 1) // 9
DIVS96 = [d for d in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 96) if d > 1]


def factor_r96():
    fa = {}
    for d in DIVS96:
        v = pari.polcyclo(d, 10)
        f = pari.factor(v)
        for i in range(len(f[0])):
            p = int(f[0][i])
            e = int(f[1][i])
            fa[p] = fa.get(p, 0) + e
    prod = 1
    for p, e in fa.items():
        prod *= p ** e
    assert prod == R96
    return sorted(fa.items())


FA = None


def fa():
    global FA
    if FA is None:
        FA = factor_r96()
    return FA


def order_of_two():
    L = 1
    for p, e in fa():
        o = int(pari.znorder(pari.Mod(2, p ** e)))
        L = L * o // math.gcd(L, o)
    return L


def crt_pair(r1, m1, r2, m2):
    g = math.gcd(m1, m2)
    if (r2 - r1) % g:
        return None
    l = m1 // g * m2
    t = ((r2 - r1) // g * pow(m1 // g, -1, m2 // g)) % (m2 // g) if m2 // g > 1 else 0
    return (r1 + m1 * t) % l, l


def dlog2(v):
    r, m = 0, 1
    for p, e in fa():
        q = p ** e
        x = pari.znlog(pari.Mod(v % q, q), pari.Mod(2, q))
        if x.type() != "t_INT":
            return None
        o = int(pari.znorder(pari.Mod(2, q)))
        res = crt_pair(r, m, int(x) % o, o)
        if res is None:
            return None
        r, m = res
    return r, m


from collections import Counter

LOG2_10 = math.log2(10)
_L = None


def L2():
    global _L
    if _L is None:
        _L = order_of_two()
    return _L


def pattern_value(nu, words):
    return (10 ** nu - 1) // 9 + sum((d - 1) * 10 ** e for d, e in words)


def fonga_bound(words):
    cnt = Counter(d for d, e in words)
    q = sum(cnt.values())
    big_b = 1 + 9 * sum((d - 1) * c for d, c in cnt.items())
    if cnt[2] > 0:
        rho = 3
    elif cnt[6] > 0:
        rho = 2
    elif cnt[4] + cnt[8] > 0:
        rho = 1
    else:
        rho = 0
    c = LOG2_10
    cq = c ** q
    return int(rho * cq + (cq - 1) / (c - 1) * math.log2(big_b))


def t7_bound(k, g0):
    r = LOG2_10
    return int(r * (2.723 * r ** (k - 1) + g0 + 1)) + 1


def decide(nu, words, a_bound, ord2=None):
    k = len(words)
    v = pattern_value(nu, words) % R96
    if v % 3 == 0 or v % 7 == 0:
        return {"verdict": "not-rank0"}
    L = ord2 if ord2 is not None else L2()
    sol = dlog2(v)
    if sol is None:
        return {"verdict": "closed by the cut", "reason": "no 2^x = V mod R96"}
    x0, Lm = sol
    if Lm != L:
        return {"verdict": "error", "reason": "order mismatch"}
    if L <= a_bound:
        return {"verdict": "open", "reason": "ord2 not above a-bound", "x0": x0}
    if x0 > a_bound:
        return {"verdict": "closed by the cut", "reason": "x0 above a-bound", "x0": x0}
    if x0 <= 3000:
        s = str(2 ** x0)
        n = len(s)
        got = Counter((int(ch), (n - 1 - i) % 96) for i, ch in enumerate(s) if ch != "1")
        want = Counter((d, e) for d, e in words)
        if n % 96 == nu and got == want:
            return {"verdict": "open", "reason": "2^x0 is a genuine candidate", "x0": x0}
        return {"verdict": "closed by the cut", "reason": "2^x0 has the wrong digits", "x0": x0}
    K = 400
    low = pow(2, x0, 10 ** K)
    ds = str(low).zfill(K)
    nonone = sum(1 for ch in ds if ch != "1")
    if nonone > k:
        return {"verdict": "closed by the cut", "reason": "2^x0 has too many non-1 low digits", "x0": x0}
    return {"verdict": "open", "reason": "low digits compatible", "x0": x0}
