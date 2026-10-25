#!/usr/bin/env python3
"""
gtable.py — the depth map of the final stage: for each level L, the compatibility group
    G_L := Z² / (Λ_L + K_L),   Λ_L = kernel of (b,c) ↦ 3^b 7^c at the PH-feasible primes of 10^L − 1 (p ∤ 10^96−1 added
    to Λ_96), K_L = {(b,c): 3^b 7^c ≡ 1 (mod 10^L)}.
A wrap-0 shadow survives level L iff its δ lies in Λ_L + K_L (witness.py), so |G_L| (a 2,5-number) is the only thing
a level contributes against shadows; a level with |G_L| = |G_{L'}| for a lower L' kills no shadow L' did not.
Usage: python3 gtable.py L1 L2 ...
"""
import sys, time, math
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC, deepcut_lift as DL
from witness import lattice_sum, kernel_at

if __name__ == "__main__":
    t0 = time.time(); Lam96 = DC.kernel_lattice()
    for L in map(int, sys.argv[1:]):
        try:
            ps = DL.new_primes(L, 96)
        except Exception as e:
            print(f"L={L}: new_primes failed {e}"); continue
        pds = [DL.PD(p) for p in ps]
        Lam = kernel_at(Lam96, pds)
        KL = cut_coset(Coset((0, 0), (1, 0), (0, 1)), 0, 1, L)
        S = lattice_sum([Lam.u1, Lam.u2, KL.u1, KL.u2]); g = Coset((0, 0), *S).index()
        v5 = 0
        while g % 5 ** (v5 + 1) == 0: v5 += 1
        print(f"L={L}: primes {ps}; [Z²:Λ_L] 10^{math.log10(Lam.index()):.1f}; |G_L| = {g} = 2^{v2(g)}·5^{v5}·{g // (2**v2(g) * 5**v5)} [{time.time()-t0:.0f}s]", flush=True)
