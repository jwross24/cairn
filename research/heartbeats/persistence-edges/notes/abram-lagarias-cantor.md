# Abram & Lagarias: intersections of multiplicative translates of 3-adic Cantor sets

Source: W. Abram, J. C. Lagarias, "Intersections of multiplicative translates of 3-adic Cantor sets",
arXiv:1308.3133, J. Fractal Geometry 1 (2014) no. 4, 349–390. Read: §1 in full, Theorem 1.6, Theorem 1.9,
Proposition 2.2, via pdftotext of the arXiv PDF, 2026-10-29. Absent from cairn; cited by Idowu
arXiv:2610.03789.

## What it does (documented: §1, Theorems 1.6 and 1.9)

- Σ_3 = 3-adic integers with digits in {0, 1}. C(1, M_1, …, M_n) = Σ_3 ∩ M_1^{-1}Σ_3 ∩ … ∩ M_n^{-1}Σ_3.
- **Theorem 1.6:** a terminating algorithm outputs a right-resolving automaton presenting
  C(1, M_1, …, M_n), with at most Π(1 + ⌊M_i/2⌋) vertices, and dim_H = log_3 β for β the Perron
  eigenvalue of its adjacency matrix. Multiplication by M is a right-to-left carry transducer, which is
  why the state count is bounded by the multipliers.
- Motivation is Lagarias's exceptional set E(Z_3) = {λ : 2^n λ omits digit 2 for infinitely many n}.
  Erdős's weak conjecture is "1 ∉ E(Z_3)"; the program bounds dim_H E(Z_3) (≤ 1/2 from Lagarias 2009;
  the sequel, arXiv:1508.05967, Exp. Math. 2017, lowers it to log_3 φ ≈ 0.438).
- **Theorem 1.9:** relaxing powers of 2 to general multipliers fails, since the generalized exceptional
  set has dim_H ≥ (1/2) log_3 2. Any progress must use special properties of the powers.
- §1.6 states the algorithms apply to g-adic numbers for every integer g ≥ 2, so base 10 is covered.
- §1.6 links dimension to digit sparsity: if dim_H C(1, M) → 0 as the number of nonzero digits of M
  grows, Senge–Straus and Stewart would give the exceptional-set conjecture.

## Carry-over to even targets (inferred; nothing run)

1. **Exact tool, wrong kind of conclusion.** In base 10 with digit set D = {1} ∪ M, Theorem 1.6 gives an
   automaton for the 10-adic λ such that λ and rλ both have digits in D, for a rational S-unit r. Two
   children y, y' of one vertex s differ by such an r, so sibling pairs live in C(1, r). The output is a
   dimension, a statement about 10-adic measure, and cannot show that a given integer is absent. That is
   the gap Lagarias states for 1 ∉ E(Z_3), and it is cairn's Wall 1 in different clothes.
2. **Where it could help H9.** The automaton is an exact, finite description of the joint suffix
   constraint on (y, ry). If the H9 suffix search ever tests several children at once, a product-automaton
   presentation replaces level-by-level enumeration with a graph whose cycles are exactly the anchored
   threads. This is a design idea, not a measured gain.
3. Theorem 1.9's lesson transfers: bounds that treat 2^a 3^b 7^c as generic multipliers will not shrink
   to zero; the S-unit structure has to enter.

## Verdict

Saved: dense, low reach, a precise algorithm valid in base 10. No settlement or pruning result for even
targets. Confidence HIGH on the documented statements, MEDIUM on the sibling-pair framing (argued, not
checked against an A_d vertex with several children).
