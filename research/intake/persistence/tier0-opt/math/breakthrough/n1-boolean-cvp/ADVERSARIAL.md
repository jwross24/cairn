# N1: where the Boolean-lattice sandwich breaks

Labels as in THEOREMS.md. MEASURED cites a run in NOTES.md.

1. The lower half is not linearizable (PROVEN-ON-PAPER, THEOREMS.md Proposition 1.2). Two free digits at positions p, q leave
   a second difference of 5-adic valuation exactly p + q, so no system affine in the Boolean variables is exact beyond
   precision 2 s when the free variables start at position s. Enumeration of blocks 0..E-1 cannot be replaced by lattice
   reduction in this formulation; D_eff = 2E is a ceiling. MEASURED: with E = 1 at D = 3 (K = 288 > 2 s = 192) the relaxed
   system has so many spurious solutions that the enumeration did not finish in 50,000,000 nodes (the exact system: 5).
   Routes around it that I priced and rejected (HEURISTIC): quadratic monomials as extra Boolean variables cost about
   log10 g digits of certificate budget each and number m^2/2 against a gain of 96 digits per block; recursion on precision gains
   nothing because information about positions beyond 2 s only enters through enumerated bases; shifting the reference
   point is the base enumeration itself.

2. The remaining enumeration is exponential in the number of occupied residue classes r and the depth E, not in q. One block
   has F = prod_e (1 + v_e) fillings (v_e = distinct digit values left in class e): F = 5184 for Tier C (r = 10), and 3^30 for a
   pattern whose 31 digits sit in 30 classes. Depth-E bases: N_E <= F^E trivially, N_E = 4.4e5 (E = 3) and 3.4e7 (E = 4) for Tier C.
   MEASURED growth of N_E in q at fixed skeleton (q = 31, 36, 40, 44): N_3 = 4.4e5, 6.2e5, 1.4e6, 1.9e6; N_4 = 3.4e7, 7.0e7,
   3.4e8, 5.9e8; N_5 = 1.7e9, 5.2e9, 4.9e10, 1.1e11.

3. A single multiplier needs information slack. Existence is a counting statement (THEOREMS.md section 3); MEASURED: at k = 31
   E = 3 the slack is +25 to +46 and 66 of 66 bases certify, with one LLL; at k = 44 the z-part alone uses 372 of the 384
   digits of modulus at E = 4 (slack -56) and 0 of 16 bases certify within 200 branch-and-bound nodes, while E = 5 (slack +115)
   certifies 6 of 6. Odd D is wasted: D = 7 needs E = 4, the same as D = 8. The grid at E = 3 shows certificates down to slack
   -50 (62 coordinates) and none at -53 and below (92 coordinates). Branching on a position group buys log10 g (about 1.7)
   digits for a factor of types + 1, so recovering 56 digits costs about 3^33, worse than enumerating one more block.

4. LLL quality: the certificate is the output of LLL on a lattice of dimension m + 3. MEASURED: LLL alone suffices wherever
   the certificate exists in the grid (BKZ-20 changed no verdict, only the time). Where slack is within a few tens of digits of the
   threshold, a larger block size or an exact enumeration of the L1 body would be needed and was not tried.

5. a > 0: the 2-adic modulus exponent is K - a and exact linearization needs K <= 2 s - a. For even D this forces E = D/2 + 1 or a
   relaxed system (sound; the prototype re-verifies every candidate exactly). a up to 3 occurs in the 43; the b3 two-ended case has
   a up to 40 (loses 40 digits of the modulus, about 40 digits of slack, at Tier C that is the whole margin at E = 3).

6. Genuinely open patterns: if a real S-unit sits inside the disc, the certificate refuses and the exact mode returns the sub-coset.
   MEASURED: 12 genuine S-units with their own digits placed as patterns (m up to 338): the Theorem 1 congruence holds for the
   genuine (z, x) in 12 of 12, and the certificate is never granted at its radius. Nothing in the method closes a pattern
   whose sub-cosets reach into the disc; only more depth or a smaller U can.

7. Non-rigorous float step: the exact-minimum mode enumerates with doubles after exact rational Gram-Schmidt, radius inflated by
   1e-7, every leaf verified by exact modular exponentiation. A missed lattice point would raise the reported minimum; the
   differential test (145 rows, all equal) is the only evidence it does not. The certificate mode, which is the one that closes
   patterns, is exact integer arithmetic and its soundness is Theorem 3.

8. Structural assumptions that fail outside this program: rank-2 exponent lattice and the two primes 2 and 5 in the modulus; the
   base-8 variant has a 3-dimensional lattice and one base prime, so the Theorem 1 coefficients and the saturation count change
   (not examined). The pivot step needs a coefficient that is a unit modulo 10; saturation guarantees it for the L96 coset and it
   never raised in any run. The conclusions use U from b3 REPORT, which assumes Bugeaud-Kaneko's printed constant (Yu not read).

9. What the lane does NOT show: that the vertex is closed, or that anything is PROVEN. All 440,640 depth-3 bases of ONE pattern
   (the multiset of codex-deep-attempt.md) are certified at D = 6 with log10 U = 281.51 (NOTES.md section 6), conditional on Lemma C,
   on Theorem U with the two-ended values of the b3 REPORT (Bugeaud-Kaneko constant taken from a page image, Yu not read), and on
   the pattern/representation list. The vertex's other anchors and representations, its census, and the machine check are open.
   The same machinery gives no closure at k = 44 at any feasible cost (item 3).
