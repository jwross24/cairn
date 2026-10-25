#!/usr/bin/env python3
"""wordlift480.py — the word lift to a ×f level (96 → 480, f = 5) with the trivial-image primes as an additive filter
(EXPERIMENTS-X.md X4/X6). Children: unplaced digits choose t mod f (f choices), ν shifts by Lp·{0..f−1}: f^(r+1).
A child survives the trivial-image primes T iff Δ′ ≡ 0 (mod ∏T), Δ′ = Σ_S (d_j−1)10^{e_j}(10^{Lp s_j}−1)/(10^{Lp}−1) + sn·10^ν/9
(exact: V_child = V_shadow + (10^{Lp} − 1)·Δ′ and the image of the word lattice at p ∈ T is trivial — lemma X5).
Only children with Δ′ ≡ 0 get the exact coset cut at all new primes and the Lemma C window at K = L."""
import sys, time, math, itertools
from collections import Counter
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC, deepcut_lift as DL, classify_open as C
import wordlift as W
from math import lcm
from sympy import n_order

def R(n): return (10 ** n - 1) // 9

def trivial_primes(co, pds):
    out = []
    for pd in pds:
        p = pd.p
        g1 = pow(3, co.u1[0], p) * pow(7, co.u1[1], p) % p; g2 = pow(3, co.u2[0], p) * pow(7, co.u2[1], p) % p
        if g1 == 1 and g2 == 1: out.append(p)
    return out

def lift_word_f(co, a, nu, De, state, Lp, L, pds, T):
    f = L // Lp; m = L // 96; mp = Lp // 96
    unf = [j for j, st in enumerate(state) if st[0] == 'U']
    PT = 1
    for p in T: PT *= p
    base = (pow(10, Lp, PT) - 1) % PT
    geo = [(pow(10, Lp * s, PT) - 1) * pow(base, -1, PT) % PT if s else 0 for s in range(f)]   # (10^{Lp s} − 1)/(10^{Lp} − 1) mod PT
    nuterm = pow(10, nu, PT) * pow(9, -1, PT) % PT
    out = []; tested = 0; passed_T = 0
    for sn in range(f):
        nu1 = nu + Lp * sn
        for shifts in itertools.product(range(f), repeat=len(unf)):
            tested += 1
            # additive filter at the trivial-image primes: Δ′ ≡ 0 mod PT
            Dp = (sum((De[j][0] - 1) * pow(10, De[j][1] + 96 * state[j][2], PT) * geo[s] for j, s in zip(unf, shifts)) + sn * nuterm * (geo[1] if sn else 0)) % PT if sn <= 1 else None
            if sn > 1:   # ν-shift by s copies: R_{ν+Lp s} − R_ν = 10^ν (10^{Lp s} − 1)/9 = 10^ν/9 · (10^{Lp}−1)·geo[s]
                Dp = (sum((De[j][0] - 1) * pow(10, De[j][1] + 96 * state[j][2], PT) * geo[s] for j, s in zip(unf, shifts)) + nuterm * geo[sn]) % PT
            if Dp != 0: continue
            passed_T += 1
            st1 = list(state)
            for j, s in zip(unf, shifts):
                _, e, rho, mm = state[j]; assert mm == mp
                st1[j] = ('U', e, rho + mp * s, m)
            V = R(nu1)
            for j, st in enumerate(st1):
                V += (De[j][0] - 1) * 10 ** (st[1] + 96 * st[2])
            co1 = DL.child_coset(co, a, V, pds)
            if co1 is None: continue
            cand = [j for j in unf if st1[j][2] >= 1]
            for cbits in itertools.product((0, 1), repeat=len(cand)):
                st2 = list(st1)
                for j, c in zip(cand, cbits):
                    if c: st2[j] = ('F', st1[j][1], st1[j][2])
                Lv = R(L); wpos = []
                for j, st in enumerate(st2):
                    if st[0] == 'F':
                        pos = st[1] + 96 * st[2]; Lv += (De[j][0] - 1) * 10 ** pos; wpos.append(pos)
                if len(set(wpos)) != len(wpos): continue
                if v2(Lv) != a or Lv % 5 == 0: continue
                co2 = cut_coset(co1, a, Lv, L)
                if co2 is None: continue
                out.append((co2, nu1, tuple(st2)))
    return out, tested, passed_T

if __name__ == "__main__":
    surv_file = sys.argv[1]; files = [x for x in sys.argv[2:] if x.endswith('.jsonl')]
    L = int(sys.argv[sys.argv.index('--level') + 1]) if '--level' in sys.argv else 480
    ut = sys.argv[sys.argv.index('--utable') + 1] if '--utable' in sys.argv else None
    U = {}
    if ut:
        for l in open(ut):
            k, a, v = l.split(); U[(int(k), int(a))] = math.log10(float(v))
    want = set(tuple(l.split()[:4]) for l in open(surv_file) if l.strip())
    t0 = time.time()
    ps = DL.new_primes(L, 96); pds = [DL.PD(p) for p in ps]; print(f"level {L}: {len(ps)} new primes [{time.time()-t0:.0f}s]", flush=True)
    Lam96 = DC.kernel_lattice(); seen = set(); n_all = n_closed = 0; tot_tested = tot_T = 0
    for f_ in files:
        for (s, M, a, nu, eps, y, sol) in C.entries(f_):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            if key not in want or key in seen: continue
            seen.add(key); n_all += 1; k = len(M)
            fct = C.factor237(y); co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
            if '--first' in sys.argv:
                r1 = C.exact_identity(M, y); reps = [(r1[0], tuple(zip(sorted(M, reverse=True), r1[1])))] if r1 else DC.all_representations(M, y)
            else:
                reps = DC.all_representations(M, y)
                if nu is not None:
                    reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % 96 for e in eps)]
            logU = max((v for (kk, aa), v in U.items() if kk == k), default=None)
            worst = None; alive_total = 0; log = []
            for (nu0, De) in reps:
                words = W.depth1_words(co0, a, (nu0, De))
                if not words: log.append('d1:0'); continue
                T = trivial_primes(words[0][0], pds)
                alive = []
                for co, st in words:
                    ch, tested, pT = lift_word_f(co, a, nu0, De, st, 96, L, pds, T)
                    tot_tested += tested; tot_T += pT; alive.extend(ch)
                log.append((len(words), 'T', len(T), 'alive', len(alive)))
                if alive:
                    b = min(DC.digits_bound(co) for co, _, _ in alive); alive_total += len(alive)
                    worst = b if worst is None or b < worst else worst
            closed = alive_total == 0 or (logU is not None and worst > logU)
            n_closed += closed
            print(f"s={s:<8} M={''.join(map(str,M)):<12} a={a} y={y:<11} k={k} {log} -> {'CLOSED-cut' if alive_total == 0 else ('CLOSED-sandwich' if closed else 'open')}"
                  f"{'' if worst is None else f' bound 10^(10^{worst:.1f})'}{'' if logU is None else f' U″ 10^{logU:.1f}'} [{time.time()-t0:.0f}s]", flush=True)
    print(f"\n{n_closed} of {n_all} closed by the word lift 96→{L}; children tested {tot_tested}, passed the trivial-prime congruence {tot_T} [{time.time()-t0:.0f}s]")
