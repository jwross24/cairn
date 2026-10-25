#!/usr/bin/env python3
"""
d1_ladder.py — SPRINT-TIERBC D1: the exact accident ladder of one Tier-C anchor (y, k, ν, W) at level 192.

For every pattern of the anchor (anchorlib.representations), every depth-1 word (copy choices of the classes e < a+9
that pass the K = 96 window; exact cut, descent.cut_coset), and every level-192 child (S ⊆ unplaced digits to odd
copies, ν-shift sn): count the children with Δ ≡ −k/9 (mod 148417) by a multiset subset-sum DP, compare with the
prediction (#children)/148417, then test every candidate exactly at the seven level-192 primes, the K = 192 window,
and the level-384 lift (wordlift.lift_word), reporting survivors at each rung.

Usage: python3 d1_ladder.py <vertex index 0-5> <y> <k> <nu> <W> [--maxpat N]
"""
import sys, os, json, time, itertools, math
from collections import Counter
sys.path.insert(0, '/home/claude/tier0'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anchorlib as AL
from sandwich_lite import cut_small
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC, deepcut_lift as DL, classify_open as C, wordlift as W

PT = 193 * 769

def count_children(terms, target):
    """terms: list of (value mod PT, multiplicity); number of distinct children (j_i copies of term i to odd copies,
    0 ≤ j_i ≤ m_i) with Σ j_i t_i ≡ target, plus a backtracking enumerator."""
    layers = [[0] * PT]; layers[0][0] = 1
    for (t, m) in terms:
        prev = layers[-1]; cur = [0] * PT
        for r in range(PT):
            if prev[r]:
                w = prev[r]
                for j in range(m + 1): cur[(r + j * t) % PT] += w
        layers.append(cur)
    n = layers[-1][target % PT]
    def back(cap):
        out = []
        def rec(i, r, acc):
            if len(out) >= cap: return
            if i == 0:
                if r == 0: out.append(tuple(acc))
                return
            t, m = terms[i - 1]
            for j in range(m + 1):
                r2 = (r - j * t) % PT
                if layers[i - 1][r2]: rec(i - 1, r2, [j] + acc)
        rec(len(terms), target % PT, []); return out
    return n, back

if __name__ == "__main__":
    vi, y, k, nu, Wm = map(int, sys.argv[1:6]); maxpat = int(sys.argv[sys.argv.index('--maxpat') + 1]) if '--maxpat' in sys.argv else 10 ** 9
    verts = [json.loads(l) for l in open('/home/claude/scouts/tierC.txt')]; v = verts[vi]; A, B, Cc = v['a'], v['b'], v['c']
    t0 = time.time()
    cvl = AL.count_vectors(A, B, Cc)
    U = y + k * W.R(96)
    cnt, reps = AL.representations(U, nu, A, B, Cc, Wm, cvl, cap=maxpat)
    print(f"anchor y={y} k={k} nu={nu} W={Wm}: {cnt} patterns (enumerated {len(reps)}) [{time.time()-t0:.0f}s]", flush=True)
    fct = C.factor237(y); a = fct[0]
    pds192 = [DL.PD(p) for p in DL.new_primes(192, 96)]; pds384 = [DL.PD(p) for p in DL.new_primes(384, 192)]
    Lam96 = DC.kernel_lattice(); co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
    tgt = (-k * pow(9, -1, PT)) % PT
    tot = Counter(); exp_children = 0.0
    for pi, (M, De) in enumerate(reps):
        De = list(De)
        bycls = {}
        for j, (d, e) in enumerate(De): bycls.setdefault(e, []).append(j)
        low = sorted(e for e in bycls if e < a + 9)
        choice_lists = [[None] + sorted(set(De[j][0] for j in bycls[e])) for e in low]
        words = []
        for ch in itertools.product(*choice_lists):
            fixed = []
            for e, dv in zip(low, ch):
                if dv is not None:
                    j = next(j for j in bycls[e] if De[j][0] == dv); fixed.append(j)
            L = W.R(96) + sum((De[j][0] - 1) * 10 ** De[j][1] for j in fixed)
            if v2(L) != a or L % 5 == 0: continue
            if cut_small(co0, a, L % (5 ** 6 * 2 ** (a + 10))) is None: continue      # reduced verdict (exact by verify_reduction)
            co = cut_coset(co0, a, L, 96)
            if co is None: continue
            words.append((co, fixed))
        tot['patterns'] += 1; tot['words'] += len(words)
        for co, fixed in words:
            unpl = [j for j in range(len(De)) if j not in fixed]
            tm = Counter(((De[j][0] - 1) * pow(10, De[j][1], PT) % PT, De[j][0], De[j][1]) for j in unpl)
            terms = [(t, m) for (t, d, e), m in tm.items()]
            nchild = 2
            for _, m in terms: nchild *= (m + 1)
            exp_children += nchild / PT
            tot['children'] += nchild
            n_hit = 0; cands = []
            for sn in (0, 1):
                target = (tgt - sn * pow(10, nu, PT) * pow(9, -1, PT)) % PT
                n, back = count_children(terms, target); n_hit += n
                if n: cands += [(sn, c) for c in back(5000)]
            tot['hit148417'] += n_hit
            # exact tests on the candidates
            keys = [(t, d, e) for (t, d, e), m in tm.items()]
            for sn, js in cands:
                nu1 = nu + 96 * sn
                # child value: fixed digits at copy 0; unplaced: j_i of each term class at odd copy (1), the rest even (0)
                Vc = W.R(nu1) + sum((De[j][0] - 1) * 10 ** De[j][1] for j in fixed)
                moved = []
                for (t, d, e), j_ in zip(keys, js):
                    m = tm[(t, d, e)]
                    Vc += j_ * (d - 1) * 10 ** (e + 96) + (m - j_) * (d - 1) * 10 ** e
                    moved += [(d, e)] * j_
                co1 = DL.child_coset(co, a, Vc, pds192)
                if co1 is None: continue
                tot['pass7primes'] += 1
                # K = 192 window: each moved digit (odd copy) is in copy 1 (< 192) or beyond; fixed digits at copy 0
                alive192 = []
                for cb in itertools.product((0, 1), repeat=len(moved)):
                    Lv = W.R(192) + sum((De[j][0] - 1) * 10 ** De[j][1] for j in fixed); pos = set()
                    ok = True
                    for (d, e), c_ in zip(moved, cb):
                        if c_:
                            if e + 96 in pos: ok = False; break
                            pos.add(e + 96); Lv += (d - 1) * 10 ** (e + 96)
                    if not ok or v2(Lv) != a or Lv % 5 == 0: continue
                    co2 = cut_coset(co1, a, Lv, 192)
                    if co2 is not None: alive192.append((co2, cb))
                if alive192: tot['passwindow192'] += 1
                # level 384: state for lift_word — fixed digits ('F', e, 0 or 1), unplaced ('U', e, rho, 2)
                for co2, cb in alive192:
                    st = []
                    mv = iter(zip(moved, cb))
                    for j in range(len(De)):
                        d, e = De[j]
                        if j in fixed: st.append(('F', e, 0))
                        else: st.append(None)
                    # assign unplaced entries: for each term class, j_ moved (odd) and m-j_ even; moved ones fixed at copy 1 if cb says so
                    counters = {key: [tm[key], 0] for key in keys}
                    mv_list = list(zip(moved, cb)); mvi = 0
                    for j in range(len(De)):
                        if st[j] is not None: continue
                        d, e = De[j]; t = (d - 1) * pow(10, e, PT) % PT; key = (t, d, e)
                        j_ = js[keys.index(key)]; used = counters[key][1]; counters[key][1] += 1
                        if used < j_:
                            fixc = mv_list[mvi][1]; mvi += 1
                            st[j] = ('F', e, 1) if fixc else ('U', e, 1, 2)
                        else: st[j] = ('U', e, 0, 2)
                    ch3 = W.lift_word(co2, a, nu1, De, tuple(st), 192, 384, pds384)
                    tot['alive384'] += len(ch3)
        if (pi + 1) % 50 == 0: print(f"  {pi+1} patterns: {dict(tot)} expected hits {exp_children:.2f} [{time.time()-t0:.0f}s]", flush=True)
    print(f"RESULT anchor y={y} k={k} nu={nu}: {dict(tot)}; expected hits at 148417 = {exp_children:.2f} [{time.time()-t0:.0f}s]")
