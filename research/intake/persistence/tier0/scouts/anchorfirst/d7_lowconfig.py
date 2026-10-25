#!/usr/bin/env python3
"""
d7_lowconfig.py — SPRINT-TIERBC D7: the per-anchor depth-1 certificate.

The K = 96 window verdict of a word depends only on the digits placed in the classes e < P := a + 9 (2-adic) and
e < 5 (5-adic) — PAPER §3.6 / sandwich_lite.verify_reduction. For an anchor (y, k, ν, W) all patterns share V = y + kR_96,
so the patterns differ, below P, only in how V's low digits (with carries) are decomposed into digit multisets — a
"low configuration". The verdict of a (low configuration, word) pair is the same for every completion of the high
classes. Hence: if no (low configuration, word) pair survives the window, EVERY pattern of the anchor is closed at
depth 1 — one computation per anchor, independent of the number of patterns (10^9 for the heavy anchors).

This script enumerates the low configurations by the representations DP truncated at position P (carry-out free,
digit budget respected, suffix feasibility relaxed — sound: a superset of the real low parts), tests every word of
every low configuration with the exact reduced cut (cut_small, exact by verify_reduction), and reports
  #patterns (from the hits line), #low configurations, #(low config, word) pairs tested, #surviving pairs.
Usage: python3 d7_lowconfig.py <vertex 0-5> <y> <k> <nu> <W> <count>
"""
import sys, os, json, time, itertools, collections
sys.path.insert(0, '/home/claude/tier0'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anchorlib as AL
from anchorlib import DIG, DIGS
from sandwich_lite import cut_small
from lattice import Coset
from descent import v2
import deepcut as DC, classify_open as C

def fv_layers(V, P, A, B, Cc, W, cvlist, a, mod, maxstates=3_000_000):
    """layered DP over classes p < P: state (carry, used counts, L mod mod) where L = R_96 + Σ fixed values·10^e so far;
    per class choose the multiset cv (consistent with V's digit and carry) and a fixed value (0 or a digit value in cv).
    Returns the set of final L residues (distinct fixed-value vectors collapse by residue) and the state counts."""
    bymass = collections.defaultdict(list)
    for mass, e, cv in cvlist:
        if mass <= W: bymass[mass].append((e, cv))
    base = (10 ** 96 - 1) // 9 % mod
    # relaxed (sound superset): the digit budget is dropped; per class the mass mu = v_p − carry + 10 t ≤ W and the
    # fixed value is 0 or any digit value that can appear in a multiset of mass mu (precomputed per mass)
    vals_by_mass = {}
    for mass, e, cv in cvlist:
        if mass <= W: vals_by_mass.setdefault(mass, set()).update(DIG[d][0] for d, n in zip(DIGS, cv) if n)
    cur = {(0, base)}
    maxw = 0
    for p in range(P):
        new = set(); vp = V[p]; pw = pow(10, p, mod)
        for (kap, Lr) in cur:
            t = 0
            while True:
                mu = vp - kap + 10 * t
                if mu > W: break
                if mu >= 0 and mu in vals_by_mass:
                    for m in {0} | vals_by_mass[mu]:
                        new.add((t, (Lr + m * pw) % mod))
                t += 1
        cur = new; maxw = max(maxw, len(cur))
        if not cur or len(cur) > maxstates: return None, len(cur)
    return cur, maxw

if __name__ == "__main__":
    vi, y, k, nu, Wm, cnt = map(int, sys.argv[1:7])
    verts = [json.loads(l) for l in open('/home/claude/scouts/tierC.txt')]; v = verts[vi]; A, B, Cc = v['a'], v['b'], v['c']
    t0 = time.time(); cvl = AL.count_vectors(A, B, Cc)
    U = y + k * (10 ** 96 - 1) // 9
    dv = AL.vdigits(U, nu); V, qV = dv
    fct = C.factor237(y); a = fct[0]; P = a + 9
    Lam96 = DC.kernel_lattice(); co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
    mod = 5 ** 6 * 2 ** (a + 10)
    fin, maxw = fv_layers(V, P, A, B, Cc, Wm, cvl, a, mod)
    if fin is None: print(f"anchor y={y} k={k} nu={nu}: a={a} P={P}: DP too big ({maxw} states)"); sys.exit()
    res = set(Lr for (_, Lr) in fin)
    surv = 0
    for Lr in res:
        if v2(Lr) != a: continue
        if cut_small(co0, a, Lr) is not None: surv += 1
    print(f"RESULT anchor y={y} k={k} nu={nu}: patterns {cnt}, a={a} P={P}, final states {len(fin)} (max layer {maxw}), distinct window residues {len(res)}, "
          f"surviving {surv} -> {'ALL PATTERNS CLOSED AT DEPTH 1' if surv == 0 else 'survivors exist'} [{time.time()-t0:.0f}s]", flush=True)
