#!/usr/bin/env python3
"""
wordlift.py — the survivor-WORD lift (TIERB-FINAL.md §4.2a): raise the level, not the depth, but only for the
digits that Lemma C depth 1 left unplaced.

After Lemma C depth 1 at level 96 a surviving word fixes some digits at copy 0 (position e_j < 96) and leaves r
digits with copy t_j ≥ 1.  Lifting the whole representation to level 192 costs 2^(k+1) children (deepcut_lift.py);
lifting the WORD costs 2^(r+1): the fixed digits keep their position, each unplaced digit chooses t_j mod 2, ν
chooses ν or ν + 96.  Each child is cut by the new primes of level 192 (child_coset) and then by Lemma C depth 1 at
K = 192 (window t < 2: an unplaced digit with t ≡ 1 mod 2 is either at t = 1 — now fixed — or at t ≥ 3).  Then
192 → 384 the same way (t mod 4), and so on.  Each level multiplies the lattice index by the new primes AND doubles
the 10-adic window, so the certified lower bound grows by ≈ 10^(27 + 48·m) per doubling, with ≤ 2^(r+1) children.

Exactness: a digit's state is (e, t) with t fixed, or (e, ρ, m) meaning t ≡ ρ (mod m), t ≥ 1.  Lemma C's premise
(every candidate other than the anchor has ≥ ν + K digits) holds as in DEEPCUT.md (bound ≥ 10^27 digits).

Usage: python3 wordlift.py <survivors.txt> <jsonl files...> [--levels 192,384] [--utable utable_U2.txt]
"""
import sys, time, math, itertools
from collections import Counter
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC
import deepcut_lift as DL
import classify_open as C

def R(n): return (10 ** n - 1) // 9

def depth1_words(co0, a, rep):
    """Lemma C depth 1 at level 96 → list of (coset, state) with state[j] = ('F', e, 0) or ('U', e, 0, 1)."""
    nu, De = rep
    out = []
    for choice in itertools.product((0, 1), repeat=len(De)):
        taken = Counter(e for (d, e), c in zip(De, choice) if c)
        if any(v > 1 for v in taken.values()): continue
        L = R(96) + sum((d - 1) * 10 ** e for (d, e), c in zip(De, choice) if c)
        if v2(L) != a or L % 5 == 0: continue
        co = cut_coset(co0, a, L, 96)
        if co is None: continue
        state = tuple(('F', e, 0) if c else ('U', e, 0, 1) for (d, e), c in zip(De, choice))
        out.append((co, state))
    return out

def lift_word(co, a, nu, De, state, Lp, L, pds):
    """lift one word from level Lp to level L = 2 Lp; returns list of (coset, nu1, state1) after the level cut
    AND Lemma C depth 1 at K = L."""
    m = L // 96; mp = Lp // 96                  # copies per level
    unf = [j for j, st in enumerate(state) if st[0] == 'U']
    out = []
    for sn in (0, 1):
        nu1 = nu + Lp * sn
        for bits in itertools.product((0, 1), repeat=len(unf)):
            # new residues mod m
            st1 = list(state)
            for j, b in zip(unf, bits):
                _, e, rho, mm = state[j]; assert mm == mp
                st1[j] = ('U', e, rho + mp * b, m)
            # level-L pattern value (positions mod L): fixed digit at e + 96 t, unplaced at e + 96 (rho mod m)
            V = R(nu1)
            pos = []
            for j, st in enumerate(st1):
                d = De[j][0]
                p = st[1] + 96 * (st[2] if st[0] == 'F' else st[2])
                V += (d - 1) * 10 ** p; pos.append(p)
            # (equal positions mod L are allowed: distinct actual positions can share a residue)
            co1 = DL.child_coset(co, a, V, pds)
            if co1 is None: continue
            # Lemma C depth 1 at K = L: window t < m. Unplaced digit with rho ≥ 1 may sit at t = rho (fix) or t ≥ rho + m.
            cand = [j for j in unf if st1[j][2] >= 1]
            for cbits in itertools.product((0, 1), repeat=len(cand)):
                st2 = list(st1)
                for j, c in zip(cand, cbits):
                    if c: st2[j] = ('F', st1[j][1], st1[j][2])
                Lv = R(L); wpos = []
                for j, st in enumerate(st2):
                    if st[0] == 'F':
                        p = st[1] + 96 * st[2]; Lv += (De[j][0] - 1) * 10 ** p; wpos.append(p)
                if len(set(wpos)) != len(wpos): continue
                if v2(Lv) != a or Lv % 5 == 0: continue
                co2 = cut_coset(co1, a, Lv, L)
                if co2 is None: continue
                out.append((co2, nu1, tuple(st2)))
    return out

if __name__ == "__main__":
    surv_file = sys.argv[1]; files = [x for x in sys.argv[2:] if x.endswith('.jsonl')]
    levels = [int(x) for x in (sys.argv[sys.argv.index('--levels') + 1] if '--levels' in sys.argv else '192,384').split(',')]
    ut = sys.argv[sys.argv.index('--utable') + 1] if '--utable' in sys.argv else None
    U = {}
    if ut:
        for l in open(ut):
            k, a, v = l.split(); U[(int(k), int(a))] = math.log10(float(v))
    want = set(tuple(l.split()[:4]) for l in open(surv_file) if l.strip())
    t0 = time.time(); PDS = {}; Lp = 96
    for L in levels:
        ps = DL.new_primes(L, Lp); PDS[L] = (Lp, [DL.PD(p) for p in ps]); print(f"level {L}: new primes {ps}", flush=True); Lp = L
    Lam96 = DC.kernel_lattice(); seen = set(); n_all = n_closed = 0; tot_children = 0
    for f in files:
        for (s, M, a, nu, eps, y, sol) in C.entries(f):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            if key not in want or key in seen: continue
            seen.add(key); n_all += 1; k = len(M)
            fct = C.factor237(y); co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
            if '--first' in sys.argv:                      # cost measurement only: ONE representation (digit DP), not all
                r1 = C.exact_identity(M, y)
                reps = [(r1[0], tuple(zip(sorted(M, reverse=True), r1[1])))] if r1 else DC.all_representations(M, y)
            else:
                reps = DC.all_representations(M, y)
            if nu is not None:
                reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % 96 for e in eps)]
            assert reps
            logU = U.get((k, min(a, 1) if a <= 1 else (a if (k, a) in U else 1)))
            if logU is None and U: logU = max(v for (kk, aa), v in U.items() if kk == k)
            worst = None; nwords = 0; alive_total = 0; log = []
            for (nu0, De) in reps:
                words = depth1_words(co0, a, (nu0, De))
                nwords += len(words)
                alive = [(co, nu0, st) for co, st in words]
                rs = [sum(1 for st in w[2] if st[0] == 'U') for w in alive]
                log.append(('d1', len(alive), 'r', max(rs) if rs else None))
                for L in levels:
                    Lp, pds = PDS[L]; nxt = []
                    for (co, nuw, st) in alive:
                        ch = lift_word(co, a, nuw, De, st, Lp, L, pds); tot_children += len(ch); nxt.extend(ch)
                    alive = nxt; log.append((L, len(alive)))
                    if not alive: break
                if alive:
                    b = min(DC.digits_bound(co) for co, _, _ in alive)
                    alive_total += len(alive)
                    worst = b if worst is None or b < worst else worst
            closed = alive_total == 0 or (logU is not None and worst > logU)
            n_closed += closed
            print(f"s={s:<8} M={''.join(map(str,M)):<12} a={a} y={y:<11} k={k} words={nwords} {log} -> "
                  f"{'CLOSED-cut' if alive_total == 0 else ('CLOSED-sandwich' if closed else 'open')}"
                  f"{'' if worst is None else f' bound 10^(10^{worst:.1f})'}{'' if logU is None else f' U″ 10^{logU:.1f}'} [{time.time()-t0:.0f}s]", flush=True)
    print(f"\n{n_closed} of {n_all} closed by the word lift to {levels}; {tot_children} children in all [{time.time()-t0:.0f}s]")
