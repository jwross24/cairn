# Lane 2 MEASURE: which characters kill the children of a level-12 survivor, and is the kill additive in the shift bits

All numbers: 228 level-24 equations of the pinned h12 corpus (parents = OPEN level-12 survivors, 2,645,235 parents, 2.718e10 children).
Tool `src/measure.c` = tier0/lvlN.c (md5 841b4b15) plus read-only counters; it evaluates EVERY character independently on a child (no early exit),
with exact enumeration (rho = 1) on 127 equations and Bernoulli child sampling (rho = 3e6/children, fixed seeds) on the rest. Rates are
children-weighted per equation (weight = exact child count from gate.jsonl); intervals are Wilson on the effective sample size
(sampling variance only; equations with rho = 1 contribute none). Raw: logs/measure.jsonl, summary logs/measure_summary.txt, scripts/summarize_measure.py.
The 3 equations with A >= 64 take parents from the unaudited level-12 output; they are reported separately and agree with the rest.

## 1. Exact lattice content (not sampled)  -- scripts/lattice_content.py, lattice_content2.py
All 228 equations share Uold = [[0,900],[9900,0]] (so (b',c') = (b,c) + (9900 t2, 900 t1)), N = 1699830000, and the same 3 new primes
73, 137, 99990001 (their product is 10^12 + 1). The image of Lambda_12 in each group (sympy, exact):

| prime | p-1 | image order | index | allowed residues for a child |
|---|---|---|---|---|
| 73 | 2^3 3^2 | 2 | 36 | 2 of 72 (T and -T) |
| 137 | 2^3 17 | 34 | 4 | 34 of 136 |
| 99990001 | 2^4 3^2 5^4 11 101 | 111100 | 900 | 111,100 of 99,990,000 |
| joint (73,137,99990001) | | 3,777,400 | 259,200 | 3,777,400 of 9.79e11 |

The joint index is 2 x the product 36 x 4 x 900 = 129,600 because the 2-part couples the three primes. By l-part (the cfg components):
2-part joint (73,137,p3; moduli 8,8,16): image 8 of 1024 (survival 1/128); 3-part joint (73,p3; 9,9): 1 of 81; 5-part (p3; 625): 25 of 625;
11 (p3), 17 (137), 101 (p3): the whole group, so they never kill (they only fix the representative t).
128 x 81 x 25 = 259,200. Level-48 primes (17, 5882353, 9999999900000001): Lambda_12 images 4, 48, 900 (joint 24+48 index 3.94e12 = 88 x 259,200 x 172,800);
Lambda_24 (the parent lattice of the level-48 stage): 17: index 8, 5882353: 48, 9999999900000001: 39,600, joint 15,206,400.

## 2. Which characters kill (measured, A < 64, 225 equations, 9.82e9 children; A >= 64 in brackets)

| character | design fail (exact image) | measured fail [95% CI] |
|---|---|---|
| 2-part joint (73,137,p3) | 0.99219 | 0.9924 [0.9923, 0.9924]  ([0.9923, 0.9925]) |
| 3-part joint (73,p3) | 0.98765 | 0.9878 [0.9878, 0.9878]  ([0.9878, 0.9879]) |
| 5-part (p3) | 0.96000 | 0.9602 [0.9601, 0.9602]  ([0.9599, 0.9601]) |
| 11 (p3), 17 (137), 101 (p3) | 0 | 0 in every one of 3.4e8 sampled children |
| prime 73 alone (projection onto 73) | 35/36 = 0.9722 | 0.9723 [0.9723, 0.9724] |
| prime 137 alone | 0.75 | 0.7501 [0.7499, 0.7502] |
| prime 99990001 alone | 0.99889 | 0.9990 [0.9990, 0.9991] |
| all characters (coset test) | 1 - 3.86e-6 | pass 7.5e-6 [6.8e-6, 8.2e-6] (exact 135,155 passing of 2.718e10 over all 228 = 5.0e-6) |

Per-equation spread of the fail rates is small (2-part 0.9860-0.9936, 3-part 0.9775-0.9897, 5-part 0.9514-0.9663). Children whose value is 0 modulo a new
prime (killed before any character): 73: 1.37%, 137: 0.73%, p3: 3e-7.

**Finding 1: the expectation "the 3-part kills at 73 and 99990001, the 2-part kills almost nothing" is false.** The 2-part is the strongest single
character (factor 128 = 1/0.0078 of the 259,200), then the 3-part (81), then the 5-part (25). The three are close to independent
(P(3-part ok | 2-part ok) = 0.0127 vs 0.0123 marginal; P(5-part ok | 2-part ok) = 0.0402 vs 0.0400), so no pair is redundant.
The excess of the measured joint pass rate over 1/259,200 (about 2x) is a parent effect (survivors of level 12 are not random targets); it is not an error in the tool:
on every equation run exactly (rho = 1) the number of coset-passing children equals tail-dead + open + exact of the reference.

Cascade (children-weighted survival after each stage, A < 64): order 2,3,5: 0.0078 -> 9.9e-5 -> 7.5e-6; order 5,3,2: 0.0400 -> 4.9e-4 -> 7.5e-6;
3,5,2: 0.0124 -> 4.9e-4. The tail stage then keeps open+exact = 19,191 of 135,155 coset-passers (14.2%); no EXACT line occurs at level 24.

## 3. Additivity in the shift bits  -- scripts/additivity.py (independent big-integer recomputation)
(i) Identity: child value = parent value + (10^12 - 1) * Delta with Delta = sum_{j lifted} (d_j - 1) 10^{e_j} + sn * 10^nu / 9, exactly as rationals, and the C residues
equal the big-integer residues: 15,074 dumped random children on 7 equations, 0 mismatches of either kind. Modulo each new prime p (10^12 = -1) this is y = y_parent - 2*Delta.
(ii) The kill condition on Delta at a single prime is membership of y_parent - 2 Delta in a coset T*K_p of the image subgroup, so Delta mod p must lie in a set of |K_p| residues:
**73: 2 residues (a pure congruence on Delta; measured at most 2 distinct Delta mod 73 among the passers of any parent), 137: 34 of 137, 99990001: 111,100 of 99,990,001.**
Only the prime 73 is "additive" in the sense of the final stage (HSHADOW.md, trivial image at 193 and 769); at 137 and at 99990001 the allowed set is a union of cosets of a multiplicative subgroup,
not a linear congruence, so a counting DP over Delta mod p exists only for 73 (73 states) and for 73*137 = 10001 states.
(iii) Window/descent (the 10-adic stage): 14.2% of coset-passers survive K = 4 digits; it depends on t only through t mod 5 in each coordinate (25 classes).
