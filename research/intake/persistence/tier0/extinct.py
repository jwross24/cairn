#!/usr/bin/env python3
"""
extinct.py — X20: cut to extinction.  Do the CLOSED-sandwich survivors of the shadow certificate (level 384) die at
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
P768 = [257, 15361, 434689, 453377, 859393, 33649448872371457]

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

if __name__ == "__main__":
    keyf, jf = sys.argv[1], sys.argv[2]
    want = set(tuple(l.split()[:4]) for l in open(keyf) if l.strip())
    t0 = time.time()
    pds192 = [DL.PD(p) for p in DL.new_primes(192, 96)]; pds384 = [DL.PD(p) for p in DL.new_primes(384, 192)]
    pds768 = [DL.PD(p) for p in P768]
    print(f"primes ready: 192 {[pd.p for pd in pds192]} 384 {[pd.p for pd in pds384]} 768 {P768} [{time.time()-t0:.0f}s]", flush=True)
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
        triv = {p: sum(trivial(co, p) for co, _, _, _ in surv384) for p in P768}
        surv768 = []; n_unpl = []
        for co3, nu3, st3, De in surv384:
            n_unpl.append(sum(1 for st in st3 if st[0] == 'U'))
            surv768.extend(W.lift_word(co3, a, nu3, De, st3, 384, 768, pds768))
        b768 = min(DC.digits_bound(co) for co, _, _ in surv768) if surv768 else None
        print(f"{' '.join(key)} k={k}: surv384={len(surv384)} (unplaced {sorted(Counter(n_unpl).items())}) bound 10^(10^{b384:.1f}); "
              f"trivial-image counts at 768 primes {triv}; surv768={len(surv768)}"
              f"{'' if b768 is None else f' bound 10^(10^{b768:.1f})'} -> {'EXTINCT' if not surv768 else 'alive'} [{time.time()-t0:.0f}s]", flush=True)
