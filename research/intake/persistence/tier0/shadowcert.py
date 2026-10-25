#!/usr/bin/env python3
"""
shadowcert.py — the final stage with the shadow certificate (HSHADOW.md): no per-word children enumeration.

Per pattern (anchored, level 96, exponent a), with the depth-1 words W (fixed digits at copy 0, r unplaced):
  (1) Λ'_a := Λ_96 ∩ {3^b 7^c ≡ 1 (mod 5^96 · 2^(96−a))} is the lattice of every word's sub-coset.  Check that
      Λ'_a ⊆ Ker_p for the level-192 primes p ∈ T := {193, 769} (basis vectors map to 1 mod p).  Then for any word,
      a level-192 child (S ⊆ unplaced, ν-shift sn) passes the cut at p ∈ T iff V_child ≡ V_shadow (mod p), i.e.
      Δ(S, sn) := Σ_{j∈S} (d_j − 1)10^{e_j} + sn·10^ν/9 ≡ 0 (mod 193·769).
  (2) DP over Z/(193·769) across ALL k digits: list every (S, sn) ≠ (∅, 0) with Δ ≡ 0.  Usually none.  Each candidate
      is tested at the five remaining level-192 primes for every word with S ⊆ unplaced(W) (exact child_coset).
      If none survives: every word has exactly one level-192 child — its shadow (ν, all unplaced digits at even copies).
  (3) For each word, the shadow's level-192 coset is cut by the level-384 primes (child_coset at V_shadow) and, if it
      passes, by Lemma C depth 1 at K = 384 (window: unplaced digits are at copies ≡ 0 mod 2 — copy 2 is in the
      window, so each may be fixed at t = 2 or pushed to t ≥ 4).  Survivors get the exact nearest-point bound and
      the sandwich against U″.
  Verdict per pattern: CLOSED-cut / CLOSED-sandwich / open, as sandwich.py.

Usage: python3 shadowcert.py <survivors.txt> <jsonl...> [--utable utable_U2.txt] [--first]
"""
import sys, time, math, itertools
from collections import Counter
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC, deepcut_lift as DL, classify_open as C, wordlift as W

T = (193, 769); PT = 193 * 769

def dp_zero(terms, extra):
    """all subsets S (bitmasks) with Σ_S terms ≡ 0 (mod PT), S ≠ ∅, and all S with Σ_S ≡ −extra: counting DP over Z/PT
    (one int per residue per layer, k·PT work) followed by backtracking from the target residues — output-sensitive,
    no mask lists, so it scales to k ≈ 30 (2^31 subsets) as long as the number of solutions is small."""
    k = len(terms); t = [x % PT for x in terms]
    layers = [[0] * PT]; layers[0][0] = 1
    for i in range(k):
        prev = layers[-1]; cur = prev[:]; ti = t[i]
        for r in range(PT):
            if prev[r]: cur[(r + ti) % PT] += prev[r]
        layers.append(cur)
    def back(target):
        out = []
        def rec(i, r, mask):
            if i == 0:
                if r == 0: out.append(mask)
                return
            if layers[i - 1][r]: rec(i - 1, r, mask)                              # digit i-1 not in S
            r2 = (r - t[i - 1]) % PT
            if layers[i - 1][r2]: rec(i - 1, r2, mask | (1 << (i - 1)))           # digit i-1 in S
        rec(k, target % PT, 0)
        return out
    z0 = [m for m in back(0) if m]
    z1 = back((-extra) % PT)
    return z0, z1

def dp_zero_masks(terms, extra):
    """reference implementation with explicit mask lists (small k only)."""
    reach = [None] * PT; reach[0] = [0]
    for i, t in enumerate(terms):
        t %= PT; new = [None] * PT
        for r in range(PT):
            if reach[r] is None: continue
            if new[r] is None: new[r] = []
            new[r].extend(reach[r])
            r2 = (r + t) % PT
            if new[r2] is None: new[r2] = []
            new[r2].extend(m | (1 << i) for m in reach[r])
        reach = new
    return [m for m in (reach[0] or []) if m], list(reach[(-extra) % PT] or [])

if __name__ == "__main__":
    surv_file = sys.argv[1]; files = [x for x in sys.argv[2:] if x.endswith('.jsonl')]
    ut = sys.argv[sys.argv.index('--utable') + 1] if '--utable' in sys.argv else None
    U = {}
    if ut:
        for l in open(ut):
            k, a, v = l.split(); U[(int(k), int(a))] = math.log10(float(v))
    want = set(tuple(l.split()[:4]) for l in open(surv_file) if l.strip())
    t0 = time.time()
    pds192 = [DL.PD(p) for p in DL.new_primes(192, 96)]; pds384 = [DL.PD(p) for p in DL.new_primes(384, 192)]
    pT = [pd for pd in pds192 if pd.p in T]; pRest = [pd for pd in pds192 if pd.p not in T]
    Lam96 = DC.kernel_lattice(); seen = set(); n_all = n_closed = 0; tot = Counter()
    for f in files:
        for (s, M, a, nu, eps, y, sol) in C.entries(f):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            if key not in want or key in seen: continue
            seen.add(key); n_all += 1; k = len(M)
            fct = C.factor237(y); co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
            if '--first' in sys.argv:
                r1 = C.exact_identity(M, y)
                reps = [(r1[0], tuple(zip(sorted(M, reverse=True), r1[1])))] if r1 else DC.all_representations(M, y)
            else:
                reps = DC.all_representations(M, y)
                if nu is not None:
                    reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % 96 for e in eps)]
            logU = max((v for (kk, aa), v in U.items() if kk == k), default=None)
            closed_all = True; worst = None; log = []
            for (nu0, De) in reps:
                words = W.depth1_words(co0, a, (nu0, De))
                if not words: log.append('d1:0'); continue
                # (1) the lattice of the words' sub-cosets is the same for all words: check its image at T is trivial
                lat = words[0][0]
                for co, _ in words[1:]: assert (co.u1, co.u2) == (lat.u1, lat.u2) or True   # bases may differ by unimodular change; check the image on each word instead
                triv = all(pow(3, co.u1[0], p) * pow(7, co.u1[1], p) % p == 1 and pow(3, co.u2[0], p) * pow(7, co.u2[1], p) % p == 1
                           for co, _ in words for p in T)
                assert triv, "word lattice image at 193/769 not trivial: certificate does not apply"
                # (2) per-word target: the child (S, sn) passes 193 and 769 iff Δ(S, sn) ≡ τ_W (mod 148417), where
                #     τ_W = (2^a 3^{w_b} 7^{w_c} − V)/(10^96 − 1) for the word's coset base point w (lemma: the image is
                #     trivial, so the cut is a single congruence). τ_W = 0 iff the shadow passes (G2: not always).
                terms = [(d - 1) * 10 ** e for d, e in De]; V = W.R(nu0) + sum(terms)
                winv = pow((10 ** 96 - 1) % PT, -1, PT)
                taus = {}
                for co, state in words:
                    x = pow(2, a, PT) * pow(3, co.v0[0], PT) * pow(7, co.v0[1], PT) % PT
                    taus[id(co)] = (x - V) * winv % PT
                alive = []; n_cand = 0; n_extra = 0
                for co, state in words:
                    tau = taus[id(co)]
                    z0, z1 = dp_zero(terms, (tau - 0) % PT) if False else (None, None)
                    # subsets with Δ ≡ τ: reuse dp_zero's machinery with shifted targets
                    k_ = len(terms); t_ = [x % PT for x in terms]
                    layers = [[0] * PT]; layers[0][0] = 1
                    for i in range(k_):
                        prev = layers[-1]; cur = prev[:]; ti = t_[i]
                        for r in range(PT):
                            if prev[r]: cur[(r + ti) % PT] += prev[r]
                        layers.append(cur)
                    def back(target):
                        out = []
                        def rec(i, r, mask):
                            if i == 0:
                                if r == 0: out.append(mask)
                                return
                            if layers[i - 1][r]: rec(i - 1, r, mask)
                            r2 = (r - t_[i - 1]) % PT
                            if layers[i - 1][r2]: rec(i - 1, r2, mask | (1 << (i - 1)))
                        rec(k_, target % PT, 0); return out
                    extra = 10 ** nu0 * pow(9, -1, PT) % PT
                    cands = [(m, 0) for m in back(tau)] + [(m, 1) for m in back((tau - extra) % PT)]
                    unpl = {j for j, st in enumerate(state) if st[0] == 'U'}
                    cands = [(m, sn) for (m, sn) in cands if all((m >> j & 1) == 0 or j in unpl for j in range(k))]
                    n_cand += len(cands)
                    # exact level-192 children of this word: each candidate through all seven primes and the K = 192 window
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
                            if (m, sn) != (0, 0): n_extra += 1
                    # (3) level 384 per branch (G1): the general word lift with the branch's own value
                    for co2, nu1, st2 in children:
                        ch3 = W.lift_word(co2, a, nu1, De, st2, 192, 384, pds384)
                        alive.extend(co3 for co3, _, _ in ch3)
                log.append((len(words), n_cand, n_extra, len(alive)))
                if alive:
                    b = min(DC.digits_bound(co) for co in alive)
                    worst = b if worst is None or b < worst else worst
                    if logU is None or b <= logU: closed_all = False
            verdict = 'BUDGET' if worst == -1 else ('CLOSED-cut' if worst is None else ('CLOSED-sandwich' if closed_all else 'open'))
            tot[verdict] += 1; n_closed += verdict.startswith('CLOSED')
            print(f"s={s:<8} M={''.join(map(str,M)):<12} a={a} y={y:<11} k={k} {log} -> {verdict}"
                  f"{'' if worst in (None, -1) else f' bound 10^(10^{worst:.1f}) U″ 10^{logU:.1f}'} [{time.time()-t0:.0f}s]", flush=True)
    print(f"\n{n_closed} of {n_all} closed by the shadow certificate: {dict(tot)} [{time.time()-t0:.0f}s]")
