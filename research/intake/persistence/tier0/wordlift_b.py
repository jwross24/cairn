#!/usr/bin/env python3
"""
wordlift_b.py — the survivor-word lift 96 → 192 for base b (b = 8 first), with the trivial-image primes of the
words' lattice as an additive filter (EXPERIMENTS-X §X9: base 8 has one such prime at level 192, 3457).

Base-b setting (engine_b): digit primes dp, bounded primes (those dividing b) with exponent vector bv, free primes
with exponent vector v ∈ Z^f; Λ_L = kernel of the free primes' logs at the level-L primes; a pattern's coset is
v_y + Λ_L (anchor y). Lemma C depth 1 at K = L (engine_b.cut_coset) gives words; the lift to 2L sends each unplaced
digit to copy t mod 2 and ν to ν + L·{0,1}; children are cut at the new primes (congruence on the free exponents)
and by Lemma C at K = 2L. For a prime p with Λ_word ⊆ Ker_p the cut is Δ ≡ 0 (mod p) with
Δ = Σ_S (d_j − 1)b^{e_j} + sn·b^ν/(b−1)  (V_child = V_shadow + (b^L − 1)·Δ).

Usage: python3 wordlift_b.py <b> <jsonl> [--levels 12,24,48,96] [--max N] [--nofilter]
"""
import sys, json, math, time, itertools
from math import lcm
from collections import Counter
from sympy import n_order
from engine_b import Base, PrimeData, primes_for_level, FreeCoset, cut_coset, _lll
from lattice3 import CosetK
import deepcut_b as DB

def R(base, n): return (base.b ** n - 1) // (base.b - 1)

def depth1_words(base, co0, bv, nu, De, L):
    out = []
    for choice in itertools.product((0, 1), repeat=len(De)):
        taken = Counter(e for (d, e), c in zip(De, choice) if c)
        if any(v > 1 for v in taken.values()): continue
        Lv = R(base, L) + sum((d - 1) * base.b ** e for (d, e), c in zip(De, choice) if c)
        co = cut_coset(base, co0, bv, Lv, L)
        if co is None: continue
        out.append((co, tuple(('F', e, 0) if c else ('U', e, 0, 1) for (d, e), c in zip(De, choice))))
    return out

def child_coset(base, co, bv, V, pds):
    ck = CosetK(co.v, co.U)
    for pd in pds:
        r = V % pd.p
        if r == 0: return None
        lr = pd.log(r)
        for q, a in zip(base.bounded, bv): lr -= a * pd.logs[base.dp.index(q)]
        A = [pd.logs[base.dp.index(q)] for q in base.free]
        ck = ck.intersect_congruence(A, lr % (pd.p - 1), pd.p - 1)
        if ck is None: return None
    return FreeCoset(ck.v0, _lll(ck.U) if len(ck.U) > 1 else ck.U)

def trivial_primes(base, co, pds):
    out = []
    for pd in pds:
        p = pd.p; ok = True
        for u in co.U:
            x = 1
            for i, q in enumerate(base.free): x = x * pow(q, u[i] % (p - 1), p) % p
            if x != 1: ok = False; break
        if ok: out.append(p)
    return out

def lift_word(base, co, bv, nu, De, state, L, pds, T):
    b = base.b; L2 = 2 * L
    unf = [j for j, st in enumerate(state) if st[0] == 'U']
    PT = 1
    for p in T: PT *= p
    out = []; tested = passed = 0
    for sn in (0, 1):
        nu1 = nu + L * sn
        for bits in itertools.product((0, 1), repeat=len(unf)):
            tested += 1
            if PT > 1:
                D = (sum((De[j][0] - 1) * pow(b, De[j][1], PT) for j, bb in zip(unf, bits) if bb) + sn * pow(b, nu, PT) * pow(b - 1, -1, PT)) % PT
                if D: continue
            passed += 1
            st1 = list(state)
            for j, bb in zip(unf, bits): st1[j] = ('U', state[j][1], bb, 2)
            V = R(base, nu1) + sum((De[j][0] - 1) * b ** (st[1] + L * st[2]) for j, st in enumerate(st1))
            co1 = child_coset(base, co, bv, V, pds)
            if co1 is None: continue
            cand = [j for j in unf if st1[j][2] == 1]
            for cb in itertools.product((0, 1), repeat=len(cand)):
                st2 = list(st1)
                for j, c in zip(cand, cb):
                    if c: st2[j] = ('F', st1[j][1], 1)
                Lv = R(base, L2); wpos = []
                for j, st in enumerate(st2):
                    if st[0] == 'F':
                        pos = st[1] + L * st[2]; Lv += (De[j][0] - 1) * b ** pos; wpos.append(pos)
                if len(set(wpos)) != len(wpos): continue
                co2 = cut_coset(base, co1, bv, Lv, L2)
                if co2 is None: continue
                out.append((co2, nu1, tuple(st2)))
    return out, tested, passed

def arg(name, default): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

if __name__ == "__main__":
    b = int(sys.argv[1]); path = sys.argv[2]
    levels = tuple(int(x) for x in arg('--levels', '12,24,48,96').split(','))
    nmax = int(arg('--max', '1000')); nofilter = '--nofilter' in sys.argv; nskip = int(arg('--skip', '0'))
    base = Base(b); L = levels[-1]; t0 = time.time()
    Lam = DB.kernel_lattice(base, levels)
    used = set()
    for Lx in levels: used.update(primes_for_level(base, Lx, used))
    ps = primes_for_level(base, 2 * L, used); pds = [PrimeData(base, p, 2 * L) for p in ps]
    print(f"base {b}: level {2*L} new primes {ps} [{time.time()-t0:.0f}s]", flush=True)
    rows = [json.loads(l) for l in open(path)]
    n = closed = 0; tot_tested = tot_passed = 0
    for r in rows:
        if not r.get('open'): continue
        for eq in r['eqs']:
            if not eq.get('open'): continue
            M = tuple(sorted(eq['M']))
            for ex in eq.get('exceptional', []):
                bv, nu, eps, y = ex[0], ex[1], ex[2], ex[3]
                if y is None: continue
                if n >= nmax: break
                n += 1
                if n <= nskip: continue
                fct = base.factor(y); v = tuple(fct[base.dp.index(q)] for q in base.free)
                co0 = FreeCoset(v, Lam); De = [(d, e % L) for d, e in zip(M, eps)]
                words = depth1_words(base, co0, tuple(bv), nu % L, De, L)
                if not words: print(f"s={r['s']} M={M} y={y}: closed at depth 1 (no words)"); closed += 1; continue
                T = [] if nofilter else trivial_primes(base, words[0][0], pds)
                alive = []
                for co, st in words:
                    ch, tested, passed = lift_word(base, co, tuple(bv), nu % L, De, st, L, pds, T)
                    tot_tested += tested; tot_passed += passed; alive.extend(ch)
                bound = None
                if alive:
                    f = len(base.free)
                    bound = min(math.log10(max(1, sum(c * c for c in co.nearest()))) / 2 - math.log10(f) / 2 + math.log10(math.log(min(base.free)) / math.log(b)) for co, _, _ in alive)
                print(f"s={r['s']} M={''.join(map(str,M))} bv={bv} y={y} k={len(M)}: words {len(words)}, trivial primes {T}, alive at {2*L}: {len(alive)}"
                      f"{'' if bound is None else f', bound 10^(10^{bound:.1f}) digits'} [{time.time()-t0:.0f}s]", flush=True)
                closed += (not alive)
    print(f"\nbase {b}: {n} patterns, {closed} closed outright at level {2*L}; children tested {tot_tested}, passed the filter {tot_passed}")
