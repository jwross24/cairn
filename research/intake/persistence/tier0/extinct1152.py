#!/usr/bin/env python3
"""
extinct1152.py — X20/P2: the ×3 step 384 → 1152 on the sandwich survivors (prediction P2 of EXPERIMENTS-X §X20).  Do the CLOSED-sandwich survivors of the shadow certificate (level 384) die at
level 768 by the prime cuts and the K = 768 window alone — i.e. without the Baker/Yu sandwich?

Pipeline = shadowcert.py v2 (words at 96, τ-target DP at 192, exact children, per-branch 384) but the level-384
survivors are kept with their states and lifted once more, 384 → 768, with the PH-feasible level-768 primes
    257, 15361, 434689, 453377, 859393, 33649448872371457   (new_primes(768, 384); 492 s to factor, so hard-coded)
through wordlift.lift_word (prime cut on every child's own value, then Lemma C depth 1 at K = 768).
Per pattern: level-384 survivors (cosets, with the digits bound), per prime whether each survivor's lattice has
trivial image (additive kill: only Δ ≡ τ children pass) and level-768 survivors with their bound.

Usage: python3 extinct.py <keys.txt> <jsonl> [--utable utable_U2.txt]
"""
import sys, time, math, itertools
from collections import Counter
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC, deepcut_lift as DL, classify_open as C, wordlift as W

T = (193, 769); PT = 193 * 769
P1152 = [19, 3169, 8929, 13249, 52579, 98641, 333667, 1067329, 999999000001, 577, 317752351489, 1153, 23041]
import wordlift480 as W480

def subsets_with_target(terms, target):
    k = len(terms); t = [x % PT for x in terms]
    layers = [[0] * PT]; layers[0][0] = 1
    for i in range(k):
        prev = layers[-1]; cur = prev[:]; ti = t[i]
        for r in range(PT):
            if prev[r]: cur[(r + ti) % PT] += prev[r]
        layers.append(cur)
    out = []
    def rec(i, r, mask):
        if i == 0:
            if r == 0: out.append(mask)
            return
        if layers[i - 1][r]: rec(i - 1, r, mask)
        r2 = (r - t[i - 1]) % PT
        if layers[i - 1][r2]: rec(i - 1, r2, mask | (1 << (i - 1)))
    rec(k, target % PT, 0); return out

def trivial(co, p):
    return all(pow(3, u[0] % (p - 1), p) * pow(7, u[1] % (p - 1), p) % p == 1 for u in (co.u1, co.u2))

def lift_f(co, a, nu, De, state, Lp, L, pds, T, target):
    """wordlift480.lift_word_f with the additive filter Δ′ ≡ target (mod ∏T) (target = 0 for a wrap-0 shadow descendant,
    −w/9 for wrap w; here computed from the coset base point, which is exact)."""
    f = L // Lp; m = L // 96; mp = Lp // 96
    unf = [j for j, st in enumerate(state) if st[0] == 'U']
    PT = 1
    for p in T: PT *= p
    base = (pow(10, Lp, PT) - 1) % PT
    geo = [(pow(10, Lp * s, PT) - 1) * pow(base, -1, PT) % PT if s else 0 for s in range(f)]
    nuterm = pow(10, nu, PT) * pow(9, -1, PT) % PT
    out = []; tested = 0; passed_T = 0
    for sn in range(f):
        nu1 = nu + Lp * sn
        for shifts in itertools.product(range(f), repeat=len(unf)):
            tested += 1
            Dp = (sum((De[j][0] - 1) * pow(10, De[j][1] + 96 * state[j][2], PT) * geo[s] for j, s in zip(unf, shifts)) + nuterm * geo[sn]) % PT
            if Dp != target % PT: continue
            passed_T += 1
            st1 = list(state)
            for j, s in zip(unf, shifts):
                _, e, rho, mm = state[j]; assert mm == mp
                st1[j] = ('U', e, rho + mp * s, m)
            V = W.R(nu1)
            for j, st in enumerate(st1):
                V += (De[j][0] - 1) * 10 ** (st[1] + 96 * st[2])
            co1 = DL.child_coset(co, a, V, pds)
            if co1 is None: continue
            cand = [j for j in unf if st1[j][2] >= 1]
            for cbits in itertools.product((0, 1), repeat=len(cand)):
                st2 = list(st1)
                for j, c in zip(cand, cbits):
                    if c: st2[j] = ('F', st1[j][1], st1[j][2])
                Lv = W.R(L); wpos = []
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
    keyf, jf = sys.argv[1], sys.argv[2]
    want = set(tuple(l.split()[:4]) for l in open(keyf) if l.strip())
    t0 = time.time()
    pds192 = [DL.PD(p) for p in DL.new_primes(192, 96)]; pds384 = [DL.PD(p) for p in DL.new_primes(384, 192)]
    pds1152 = [DL.PD(p) for p in P1152]
    print(f"primes ready: 192 {[pd.p for pd in pds192]} 384 {[pd.p for pd in pds384]} 1152 {P1152} [{time.time()-t0:.0f}s]", flush=True)
    Lam96 = DC.kernel_lattice(); seen = set(); winv = pow((10 ** 96 - 1) % PT, -1, PT)
    for (s, M, a, nu, eps, y, sol) in C.entries(jf):
        key = (str(s), ''.join(map(str, M)), str(a), str(y))
        if key not in want or key in seen: continue
        seen.add(key); k = len(M)
        fct = C.factor237(y); co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
        reps = DC.all_representations(M, y)
        if nu is not None:
            reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % 96 for e in eps)]
        surv384 = []
        for (nu0, De) in reps:
            words = W.depth1_words(co0, a, (nu0, De))
            if not words: continue
            assert all(trivial(co, p) for co, _ in words for p in T)
            terms = [(d - 1) * 10 ** e for d, e in De]; V = W.R(nu0) + sum(terms)
            extra = 10 ** nu0 * pow(9, -1, PT) % PT
            for co, state in words:
                x = pow(2, a, PT) * pow(3, co.v0[0], PT) * pow(7, co.v0[1], PT) % PT
                tau = (x - V) * winv % PT
                cands = [(m, 0) for m in subsets_with_target(terms, tau)] + [(m, 1) for m in subsets_with_target(terms, (tau - extra) % PT)]
                unpl = {j for j, st in enumerate(state) if st[0] == 'U'}
                cands = [(m, sn) for (m, sn) in cands if all((m >> j & 1) == 0 or j in unpl for j in range(k))]
                children = []
                for (m, sn) in cands:
                    st1 = list(state)
                    for j in unpl: st1[j] = ('U', state[j][1], (m >> j) & 1, 2)
                    nu1 = nu0 + 96 * sn
                    Vc = W.R(nu1) + sum((De[j][0] - 1) * 10 ** (st[1] + 96 * st[2]) for j, st in enumerate(st1))
                    co1 = DL.child_coset(co, a, Vc, pds192)
                    if co1 is None: continue
                    cand_f = [j for j in unpl if st1[j][2] == 1]
                    for cb in itertools.product((0, 1), repeat=len(cand_f)):
                        st2 = list(st1)
                        for j, c_ in zip(cand_f, cb):
                            if c_: st2[j] = ('F', st1[j][1], 1)
                        Lv = W.R(192); wpos = []
                        for j, st in enumerate(st2):
                            if st[0] == 'F':
                                pos = st[1] + 96 * st[2]; Lv += (De[j][0] - 1) * 10 ** pos; wpos.append(pos)
                        if len(set(wpos)) != len(wpos): continue
                        if v2(Lv) != a or Lv % 5 == 0: continue
                        co2 = cut_coset(co1, a, Lv, 192)
                        if co2 is None: continue
                        children.append((co2, nu1, tuple(st2)))
                for co2, nu1, st2 in children:
                    for co3, nu3, st3 in W.lift_word(co2, a, nu1, De, st2, 192, 384, pds384):
                        surv384.append((co3, nu3, st3, De))
        if not surv384:
            print(f"{' '.join(key)} k={k}: CLOSED-cut at 384 (nothing to extinguish) [{time.time()-t0:.0f}s]", flush=True); continue
        b384 = min(DC.digits_bound(co) for co, _, _, _ in surv384)
        surv1152 = []; info = []
        for co3, nu3, st3, De in surv384:
            T = [p for p in P1152 if trivial(co3, p)]
            PTT = 1
            for p in T: PTT *= p
            V3 = W.R(nu3) + sum((De[j][0] - 1) * 10 ** (st[1] + 96 * st[2]) for j, st in enumerate(st3) if st[0] == 'F') \
                 + sum((De[j][0] - 1) * 10 ** (st[1] + 96 * st[2]) for j, st in enumerate(st3) if st[0] == 'U')
            x = pow(2, a, PTT) * pow(3, co3.v0[0], PTT) * pow(7, co3.v0[1], PTT) % PTT
            tau = (x - V3) * pow((10 ** 384 - 1) % PTT, -1, PTT) % PTT
            ch, tested, passed = lift_f(co3, a, nu3, De, st3, 384, 1152, pds1152, T, tau)
            info.append((len(T), tau, tested, passed, len(ch)))
            surv1152.extend(ch)
        b1152 = min(DC.digits_bound(co) for co, _, _ in surv1152) if surv1152 else None
        print(f"{' '.join(key)} k={k}: surv384={len(surv384)} bound 10^(10^{b384:.1f}); per survivor (|T|, τ, tested, passed T, alive) {info}; "
              f"surv1152={len(surv1152)}{'' if b1152 is None else f' bound 10^(10^{b1152:.1f})'} -> {'CLOSED-cut at 1152' if not surv1152 else 'sandwich at 1152'} [{time.time()-t0:.0f}s]", flush=True)
