#!/usr/bin/env python3
"""
addlift2.py — the additive lift L1 → L2 = 2·L1 for L1 ∈ {12, 24, 48} (X11; generalises addlift.py).

Parent: a level-L1 survivor (ν, {(d_j, e_j)}, e_j < L1) with exponent a and coset C = v + Λ_{L1} (Λ_{L1} = kernel of
3^b7^c at all level-L1 primes).  Children: V' = V + (10^{L1} − 1)·Δ, Δ(S, sn) = Σ_{S}(d_j−1)10^{e_j} + sn·10^ν/9.
Child passes a new prime p iff Δ ≡ (2^a x_p h − V)/(10^{L1} − 1) (mod p) for some h in the image H_p of Λ_{L1}
(necessary conditions, one per prime; the exact verdict is the sequential coset intersection).  Strategy:
  * DP over Z/M for the product M of the new primes with |H_p| ≤ 64 and M ≤ 10^6 (lists candidates);
  * each candidate: hash-set membership for the remaining primes with |H_p| ≤ 10^6, then the exact test.
Self-test (--selftest): real level-96 anchored records reduced mod L1 are genuine level-L1 survivors; compare the
DP child set with brute force over all 2^(q+1) children.
"""
import sys, time, math, itertools, random
from math import lcm
from sympy import primitive_root, n_order, factorint, cyclotomic_poly, divisors
from lattice import Coset
from dlog import discrete_log
import classify_open as C

def level_primes(L):
    ps = set()
    for d in divisors(L): ps |= set(int(p) for p in factorint(int(cyclotomic_poly(d, 10))))
    return sorted(p for p in ps if p not in (2, 3, 5, 7))

class PD:
    def __init__(self, p):
        self.p = p; self.g = primitive_root(p)
        self.l2 = discrete_log(p, 2 % p, self.g); self.l3 = discrete_log(p, 3 % p, self.g); self.l7 = discrete_log(p, 7 % p, self.g)

_cache = {}
def setup(L1):
    if L1 in _cache: return _cache[L1]
    P1 = level_primes(L1); P2 = [p for p in level_primes(2 * L1) if p not in P1]
    PD1 = [PD(p) for p in P1]; PD2 = [PD(p) for p in P2]
    _cache[L1] = (P1, P2, PD1, PD2); return _cache[L1]

def coset(V, a, PD1):
    co = Coset((0, 0), (1, 0), (0, 1))
    for pd in PD1:
        r = V % pd.p
        if r == 0: return None
        co = co.intersect(pd.l3, pd.l7, (discrete_log(pd.p, r, pd.g) - a * pd.l2) % (pd.p - 1), pd.p - 1)
        if co is None: return None
    return co

def image(co, p, cap):
    g1 = pow(3, co.u1[0], p) * pow(7, co.u1[1], p) % p; g2 = pow(3, co.u2[0], p) * pow(7, co.u2[1], p) % p
    order = lcm(n_order(g1, p) if g1 != 1 else 1, n_order(g2, p) if g2 != 1 else 1)
    if order > cap: return None, order
    H = {1}; frontier = [1]
    while frontier:
        x = frontier.pop()
        for g in (g1, g2):
            y = x * g % p
            if y not in H: H.add(y); frontier.append(y)
    assert len(H) == order
    return H, order

def child_passes(co, a, Vp, pds):
    for pd in pds:
        r = Vp % pd.p
        if r == 0: return False
        co = co.intersect(pd.l3, pd.l7, (discrete_log(pd.p, r, pd.g) - a * pd.l2) % (pd.p - 1), pd.p - 1)
        if co is None: return False
    return True

def additive_lift(L1, nu, De, a, co, dp_cap=10 ** 6, set_cap=10 ** 6):
    P1, P2, PD1, PD2 = setup(L1)
    V = (10 ** nu - 1) // 9 + sum((d - 1) * 10 ** e for d, e in De); q = len(De)
    w = 10 ** L1 - 1
    allowed = {}; orders = {}
    for p in P2:
        H, order = image(co, p, set_cap); orders[p] = order
        if H is None: continue
        x = pow(3, co.v0[0], p) * pow(7, co.v0[1], p) % p; winv = pow(w % p, -1, p)
        allowed[p] = frozenset((pow(2, a, p) * x * h - V) * winv % p for h in H)
    # choose the DP modulus: smallest-|H| primes while M ≤ dp_cap
    dp_primes = []; M = 1
    for p in sorted(allowed, key=lambda p: orders[p]):
        if M * p <= dp_cap: dp_primes.append(p); M *= p
    rest = [p for p in allowed if p not in dp_primes]
    # CRT-combine the allowed sets of the DP primes
    A = set()
    for combo in itertools.product(*[sorted(allowed[p]) for p in dp_primes]):
        x = 0
        for p, r in zip(dp_primes, combo):
            Mi = M // p; x = (x + r * Mi * pow(Mi, -1, p)) % M
        A.add(x)
    terms = [(d - 1) * pow(10, e, M) % M for d, e in De]
    extra = pow(10, nu, M) * pow(9, -1, M) % M
    reach = {0: [0]}
    for i, t in enumerate(terms):
        new = {}
        for r, masks in reach.items():
            new.setdefault(r, []).extend(masks)
            new.setdefault((r + t) % M, []).extend(m | (1 << i) for m in masks)
        reach = new
    cands = []
    for sn in (0, 1):
        for r in A:
            for m in reach.get((r - sn * extra) % M, []): cands.append((m, sn))
    n_dp = len(cands)
    # hash-set filters at the remaining small-image primes
    out = []
    for m, sn in cands:
        ok = True
        for p in rest:
            D = (sum((d - 1) * pow(10, e, p) for i, (d, e) in enumerate(De) if m >> i & 1) + sn * pow(10, nu, p) * pow(9, -1, p)) % p
            if D not in allowed[p]: ok = False; break
        if not ok: continue
        nu1 = nu + L1 * sn
        Vp = (10 ** nu1 - 1) // 9 + sum((d - 1) * 10 ** (e + (L1 if m >> i & 1 else 0)) for i, (d, e) in enumerate(De))
        if child_passes(co, a, Vp, PD2): out.append((m, sn))
    return out, n_dp, dp_primes, rest, [p for p in P2 if p not in allowed]

def brute(L1, nu, De, a, co):
    P1, P2, PD1, PD2 = setup(L1); q = len(De); out = []
    for sn in (0, 1):
        for m in range(1 << q):
            nu1 = nu + L1 * sn
            Vp = (10 ** nu1 - 1) // 9 + sum((d - 1) * 10 ** (e + (L1 if m >> i & 1 else 0)) for i, (d, e) in enumerate(De))
            if child_passes(co, a, Vp, PD2): out.append((m, sn))
    return out

if __name__ == "__main__":
    L1 = int(sys.argv[sys.argv.index('--L1') + 1]) if '--L1' in sys.argv else 24
    nmax = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 20
    random.seed(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1)
    t0 = time.time(); P1, P2, PD1, PD2 = setup(L1)
    print(f"L1={L1}: old primes {P1}; new primes {P2} [{time.time()-t0:.0f}s]", flush=True)
    rows = []; seen = set()
    for (s, M, a, nu, eps, y, sol) in C.entries('/home/claude/night/trees_mac_1250.jsonl'):
        if (s, M, a, y) in seen or not (6 <= len(M) <= 11) or y < 10 ** 7 or M.count(2) > 6: continue
        seen.add((s, M, a, y)); rows.append((s, M, a, y))
    random.shuffle(rows); ok = tested = 0; tot = [0, 0, 0]
    for (s, M, a, y) in rows[:nmax]:
        r1 = C.exact_identity(M, y)
        if r1 is None: continue
        nu96, De96 = r1[0], list(zip(sorted(M, reverse=True), r1[1]))
        nu = nu96 % L1; De = [(d, e % L1) for d, e in De96]
        V = (10 ** nu - 1) // 9 + sum((d - 1) * 10 ** e for d, e in De)
        co = coset(V, a, PD1)
        if co is None: print("not a survivor?!", s, M, y); continue
        tested += 1
        t1 = time.time(); dp, n_dp, dpp, rest, skipped = additive_lift(L1, nu, De, a, co); t_dp = time.time() - t1
        t1 = time.time(); bf = brute(L1, nu, De, a, co); t_bf = time.time() - t1
        same = sorted(dp) == sorted(bf); ok += same
        tot[0] += 2 ** (len(M) + 1); tot[1] += n_dp; tot[2] += len(bf)
        print(f"s={s} k={len(M)} a={a}: children {2**(len(M)+1)}, DP primes {dpp} -> {n_dp} cands, set-filter primes {rest}, exact-only {skipped}; "
              f"DP {len(dp)} brute {len(bf)} {'MATCH' if same else 'MISMATCH'} [dp {t_dp:.1f}s brute {t_bf:.1f}s]", flush=True)
    print(f"\nL1={L1}: {ok}/{tested} match; children {tot[0]}, DP candidates {tot[1]} (1/{tot[0]/max(1,tot[1]):.0f}), survivors {tot[2]} [{time.time()-t0:.0f}s]")
