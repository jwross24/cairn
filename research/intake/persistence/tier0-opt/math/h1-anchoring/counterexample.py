import sys, time, signal
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
from collections import Counter
import tier0 as T
from lattice import Coset
from descent import descend

L = 96
R96 = (10 ** L - 1) // 9
Rn = lambda n: (10 ** n - 1) // 9
ps = T.primes_for_level(L, set())
pdata = [T.PrimeData(p, L) for p in ps]
lam = Coset()
for pd in pdata:
    lam = lam.intersect(pd.l3, pd.l7, 0, pd.p - 1)
print("primes", len(ps), "index", lam.index(), flush=True)
short = min((x * x + y * y) ** 0.5 for x, y in (lam.u1, lam.u2))
print("shortest vector %.3e" % short, flush=True)

def pattern_from(r, nu):
    Z = r - Rn(nu)
    if Z < 0:
        return None
    entries = []
    for i, ch in enumerate(reversed(str(Z))):
        dl = int(ch)
        if dl == 0:
            continue
        if dl == 9:
            entries.append((9, i)); entries.append((2, i))
        else:
            entries.append((dl + 1, i))
    entries.sort()
    return tuple(d for d, _ in entries), tuple(e for _, e in entries)

def value(nu, D, eps):
    return Rn(nu) + sum((d - 1) * 10 ** e for d, e in zip(D, eps))

def tail_ok(Y, K, D, eps):
    tail = str(Y).zfill(K)
    if '0' in tail:
        return False
    want = Counter((d, e % L) for d, e in zip(D, eps))
    have = Counter((int(ch), i % L) for i, ch in enumerate(reversed(tail)) if ch != '1')
    return all(have[k] <= want[k] for k in have)

hits = []
t0 = time.time()
for a in range(0, 4):
    K = T.ten_adic_K(lam, 400, a)
    if a == 0:
        print("ten_adic_K", K, flush=True)
    for B in range(150, 260):
        for C in range(150, 260):
            u = 2 ** a * 3 ** B * 7 ** C
            r = u % R96
            Y = u % (10 ** K)
            for nu in range(0, 96):
                pat = pattern_from(r, nu)
                if pat is None:
                    break
                D, eps = pat
                if not tail_ok(Y, K, D, eps):
                    continue
                hits.append((a, B, C, nu, D, eps))
    print("a", a, "hits so far", len(hits), "elapsed %.0fs" % (time.time() - t0), flush=True)
    if len(hits) >= 3:
        break

print("candidates", len(hits), flush=True)
import json
verified = []
for (a, B, C, nu, D, eps) in hits[:6]:
    V = value(nu, D, eps)
    u = 2 ** a * 3 ** B * 7 ** C
    assert (V - u) % R96 == 0
    co = Coset()
    for pd in pdata:
        y = pd.R[nu % L]
        for d, e in zip(D, eps):
            y = (y + (d - 1) * pd.pow10[e % L]) % pd.p
        assert y != 0
        co = co.intersect(pd.l3, pd.l7, (pd.log(y) - a * pd.l2) % (pd.p - 1), pd.p - 1)
        assert co is not None
    assert co.contains(B, C)
    kind, val = T.classify(co, a, D, nu, eps, L, D, 400)
    K = T.ten_adic_K(co, 400, a)
    rec = {"a": a, "B": B, "C": C, "nu": nu, "q": len(D), "M": list(D), "eps": list(eps), "classify": kind, "K": K,
           "u_digits": len(str(u)), "V_digits": len(str(V)), "k": (V - u) // R96}
    verified.append(rec)
    print(json.dumps(rec), flush=True)
json.dump(verified, open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h1-anchoring/counterexamples.json", "w"))
