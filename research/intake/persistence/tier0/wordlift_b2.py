#!/usr/bin/env python3
"""
wordlift_b2.py — base-b word lift 96 → 192 → 384 (X18 continued): the 140 base-8 patterns whose level-192 survivors
sit at 10^(10^79) get the second doubling, with the level-384 trivial-image primes as the additive filter.

Same conventions as wordlift_b.py / wordlift.py: state entries ('F', e, t) (fixed digit at position e + 96 t) and
('U', e, rho, m) (unplaced digit at a copy ≡ rho mod m, beyond the current window); copies are counted in units of 96.

Usage: python3 wordlift_b2.py <b> <jsonl> [--keys file] [--max N]
"""
import sys, json, math, time, itertools
from collections import Counter
from engine_b import Base, PrimeData, primes_for_level, FreeCoset, cut_coset
import deepcut_b as DB
from wordlift_b import R, depth1_words, child_coset, trivial_primes

def lift_word_g(base, co, bv, nu, De, state, Lp, L, pds, T):
    b = base.b; m = L // 96; mp = Lp // 96
    unf = [j for j, st in enumerate(state) if st[0] == 'U']
    PT = 1
    for p in T: PT *= p
    out = []; tested = passed = 0
    for sn in (0, 1):
        nu1 = nu + Lp * sn
        for bits in itertools.product((0, 1), repeat=len(unf)):
            tested += 1
            if PT > 1:
                # child value = parent value + (b^Lp − 1)·Δ, Δ = Σ_{moved} (d−1) b^{pos mod Lp} + sn·b^ν/(b−1)
                D = (sum((De[j][0] - 1) * pow(b, state[j][1] + 96 * state[j][2], PT) for j, bb in zip(unf, bits) if bb)
                     + sn * pow(b, nu, PT) * pow(b - 1, -1, PT)) % PT
                if D: continue
            passed += 1
            st1 = list(state)
            for j, bb in zip(unf, bits):
                _, e, rho, mm = state[j]; assert mm == mp
                st1[j] = ('U', e, rho + mp * bb, m)
            V = R(base, nu1) + sum((De[j][0] - 1) * b ** (st[1] + 96 * st[2]) for j, st in enumerate(st1))
            co1 = child_coset(base, co, bv, V, pds)
            if co1 is None: continue
            cand = [j for j in unf if st1[j][2] >= 1]
            for cb in itertools.product((0, 1), repeat=len(cand)):
                st2 = list(st1)
                for j, c in zip(cand, cb):
                    if c: st2[j] = ('F', st1[j][1], st1[j][2])
                Lv = R(base, L); wpos = []
                for j, st in enumerate(st2):
                    if st[0] == 'F':
                        pos = st[1] + 96 * st[2]; Lv += (De[j][0] - 1) * b ** pos; wpos.append(pos)
                if len(set(wpos)) != len(wpos): continue
                co2 = cut_coset(base, co1, bv, Lv, L)
                if co2 is None: continue
                out.append((co2, nu1, tuple(st2)))
    return out, tested, passed

def arg(name, default): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def bound_of(base, alive):
    f = len(base.free)
    return min(math.log10(max(1, sum(c * c for c in co.nearest()))) / 2 - math.log10(f) / 2 + math.log10(math.log(min(base.free)) / math.log(base.b)) for co, _, _ in alive)

if __name__ == "__main__":
    b = int(sys.argv[1]); path = sys.argv[2]; nmax = int(arg('--max', '100000'))
    keys = None
    if '--keys' in sys.argv:
        keys = set(tuple(l.split()[:4]) for l in open(arg('--keys', '')) if l.strip())
    base = Base(b); levels = (12, 24, 48, 96); L = 96; t0 = time.time()
    Lam = DB.kernel_lattice(base, levels); used = set()
    for Lx in levels: used.update(primes_for_level(base, Lx, used))
    ps192 = primes_for_level(base, 192, used); pds192 = [PrimeData(base, p, 192) for p in ps192]; used.update(ps192)
    ps384 = primes_for_level(base, 384, used); pds384 = [PrimeData(base, p, 384) for p in ps384]
    print(f"base {b}: level 192 primes {ps192}; level 384 primes {ps384} [{time.time()-t0:.0f}s]", flush=True)
    n = 0; tot = Counter()
    for r in [json.loads(l) for l in open(path)]:
        if not r.get('open'): continue
        for eq in r['eqs']:
            if not eq.get('open'): continue
            M = tuple(sorted(eq['M']))
            for ex in eq.get('exceptional', []):
                bv, nu, eps, y = ex[0], ex[1], ex[2], ex[3]
                if y is None: continue
                key = (str(r['s']), ''.join(map(str, M)), str(bv), str(y))
                if keys is not None and key not in keys: continue
                if n >= nmax: break
                n += 1
                fct = base.factor(y); v = tuple(fct[base.dp.index(q)] for q in base.free)
                co0 = FreeCoset(v, Lam); De = [(d, e % L) for d, e in zip(M, eps)]
                words = depth1_words(base, co0, tuple(bv), nu % L, De, L)
                if not words: tot['closed-96'] += 1; print(f"{' '.join(key)} k={len(M)}: closed at depth 1"); continue
                T = trivial_primes(base, words[0][0], pds192)
                alive = []
                for co, st in words:
                    ch, _, _ = lift_word_g(base, co, tuple(bv), nu % L, De, st, 96, 192, pds192, T)
                    alive.extend(ch)
                if not alive:
                    tot['closed-192'] += 1; print(f"{' '.join(key)} k={len(M)}: words {len(words)}, closed at 192 [{time.time()-t0:.0f}s]", flush=True); continue
                b192 = bound_of(base, alive)
                T2 = trivial_primes(base, alive[0][0], pds384)
                alive2 = []; tst = pss = 0
                for co, nu1, st in alive:
                    ch, a_, b_ = lift_word_g(base, co, tuple(bv), nu1, De, st, 192, 384, pds384, T2)
                    alive2.extend(ch); tst += a_; pss += b_
                if alive2:
                    tot['alive-384'] += 1
                    print(f"{' '.join(key)} k={len(M)}: words {len(words)}, alive at 192: {len(alive)} (10^(10^{b192:.1f})), trivial primes at 384 {T2}, "
                          f"children {tst} passed {pss}, alive at 384: {len(alive2)} bound 10^(10^{bound_of(base, alive2):.1f}) [{time.time()-t0:.0f}s]", flush=True)
                else:
                    tot['closed-384'] += 1
                    print(f"{' '.join(key)} k={len(M)}: words {len(words)}, alive at 192: {len(alive)} (10^(10^{b192:.1f})), trivial primes at 384 {T2}, "
                          f"children {tst} passed {pss}, CLOSED at 384 [{time.time()-t0:.0f}s]", flush=True)
    print(f"\nbase {b}: {n} patterns: {dict(tot)} [{time.time()-t0:.0f}s]")
