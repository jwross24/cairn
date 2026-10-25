# X2 predictions (registered before any classification run)

Written: Wed Oct 21 20:44:18 EDT 2026 (output of `date`). This file is never edited after its md5 is logged in P/COORDINATION.md.
Lane: Cairn X2. Workspace: P/tier0-opt/math/x2-survivors/. No-Claim: classification says nothing about closure.

## 0. What was seen before this file

- I read OPEN-PATTERNS.md (8805c0cf), RESULT-accidents.md (51f286a9), PAPER.md 3.3-3.5, join24swap/SWAP.md, gate.py, tier0/lvlN.c, tier0v2.py, run_c.py.
- From join24swap/gate.jsonl I used only the per-equation `children` count (and A) to size the model. I printed three gate rows and the first
  equation's stderr counters (124416_222222222399: children 11876872, tail-dead 103, open 43, exact 0). No classification, anchor test
  or descent has been run on any survivor. The model below uses parents24.txt and cfgL24.txt only, never an engine output line.
- The h12 corpus (parents, cfgs) is the scratchpad copy named in gate.py: .../scratchpad/h12/<eq>/{cfgL24.txt,parents24.txt}.

## 1. Definitions (level 24; the OPEN-PATTERNS anchor sense, not the HSHADOW 192/384 sense)

Survivor populations, per equation (k = q = number of non-1 digits; an equation is (s, multiset M)), counted as distinct (a, nu, canonical eps):

- **R**: every child that passes the level-24 residue tests (the 8 primes of 10^24-1, fixed a). R = OPEN lines + EXACT lines + tail-dead children.
  Tail-dead children are not printed by the engine; they are emitted by an instrumented copy (inst/lvlN_x2.c = join24swap/lvlN.c plus one added
  `emit("DEAD",...)` call; md5 85b3b3a951608765741294282f7781ef, binary 0e898aa6ec1062d90de4914f8904c6ae). The copy is gated against join24swap/lvlN: sorted OPEN+EXACT lines identical and DEAD count = tail-dead counter, on all 228.
- **T**: the engine's level-24 output, the OPEN and EXACT lines (distinct keys).
- **D**: members of T whose Python classification with descent (pydesc.classify_batch, do_descent=1, kcap=400, as tier0v2.solve_equation runs it) is OPEN,
  i.e. the survivors that go on to level 48. Members resolved by descent (RESOLVED, SOLUTION, DEAD) are listed separately.

Pattern value: V = R_nu + sum_j (d_j - 1) 10^{e_j}, with nu and the e_j the residues as integers in [0, 24).
- **Shadow (anchored)**: y := V mod R_24 is nonzero and y = 2^a' 3^b' 7^c' (exact big-integer test). Equivalent to OPEN-PATTERNS (†) at L = 24 / PAPER 3.5:
  there is an S-unit y, 0 < y < R_24, with y + kappa R_24 = V (kappa = V // R_24, required 0 <= kappa <= 8k). y is unique when it exists.
  Recorded per survivor: y, (a',b',c'), kappa, and whether a' = a (the engine's 2-adic exponent).
- **Accident**: a survivor with no such y.
- Why this sense: at L = 24 every candidate y' of the pattern satisfies y' = V mod R_24 (mod R_24), so a shadow is exactly a pattern the modular and
  10-adic tests cannot separate from a small S-unit; an accident has no such partner. A false shadow needs a random V to hit one of about 1.7e4 S-units below R_24 = 1.1e23,
  probability about 1e-19 per pattern, so the test is exact for practical purposes (reported as a bound, not a derivation).
- Half-anchors (2^J V = y mod R_24 with 2^J not dividing y; RESULT-accidents 4.4) are classified accident and counted in a diagnostic column (J = 1..64), since their a-class cannot be engine-admissible.
- Equations with A >= 64 (level-12 output under separate audit in P/tier0-opt/kt-audit-l12/): 9437184_222222222222222222229, 9437184_22222222222222222266,
  9437184_2222222222222222289. They are reported on their own row and are excluded from the pooled headline numbers.

## 2. Uniform model and its predicted accident counts

From RESULT-accidents.md Table 1 and Section 2: for a child of a level-12 survivor (a, pattern), P(child passes the level-24 residue tests) = rho'_24/rho'_12
= 6.361e-9 / 1.684e-3 = 3.777315914489311e-06 per (a, child), independent of the pattern, measured 0.996 +- 0.011 of this value on random lifts.
- E_R(eq) = children(eq) x 3.777e-6. The children count is the engine's (distinct children; reproduced here as sum over parents of 2 x prod_(digit, residue)(multiplicity+1)).
- E_T(eq) = E_R x (probability a residue accident passes the engine tail test). Computed by model.py (seeded, 20000 parent/child draws per equation): the parent's
  K_12 pinned digits are fixed by its coset; a child keeps them only if the matching digit elements are not lifted; the remaining digits of Y = 2^a 3^b 7^c mod 10^K are uniform over the
  coset of the image of the parent lattice in (Z/10^K)^*; the tail rule is the engine's. Assumption (not verified): the child's position inside that image is uniform for an accident.
- E_D: not predicted from first principles. The descent pass rate d for accidents is estimated from the data (non-anchored members of T run through descent); RESULT-accidents 3(b) reports 0.24-0.4
  on level-24 tail survivors, upper bound 1. E_D = d x E_T, so D-stage uniformity has the same content as T-stage uniformity.
- Intervals: exact Poisson 95% on the count given the mean; the model-side uncertainty (r24 +-3%, MC se in the table) is added to the ratio interval.
- Per equation: model_table.csv (md5 74eda782f22025f87818aaba8ad93bab); raw: model_out.jsonl (md5 7ec5d2cf94aff13f118ff13caf20c75f); code model.py (md5 65025053af7c52c3bc8ceb83c8572556).

Pooled model predictions (accident counts, 95% Poisson interval):

| k | equations | children | E_R residue accidents [95% Poisson] | E_T tail-passing accidents +- MC se [95% Poisson] |
|---|---|---|---|---|
| 5 | 2 | 336 | 0.0 [0, 0] | 0.00 +- 0.00 [0, 0] |
| 6 | 8 | 5224 | 0.0 [0, 0] | 0.00 +- 0.00 [0, 0] |
| 7 | 22 | 295724 | 1.1 [0, 4] | 0.04 +- 0.00 [0, 1] |
| 8 | 32 | 6299936 | 23.8 [15, 34] | 1.12 +- 0.00 [0, 4] |
| 9 | 49 | 73544896 | 277.8 [246, 311] | 13.79 +- 0.02 [7, 22] |
| 10 | 52 | 643707814 | 2431.5 [2335, 2529] | 120.01 +- 0.13 [99, 142] |
| 11 | 33 | 2465169952 | 9311.7 [9123, 9501] | 470.39 +- 0.72 [428, 513] |
| 12 | 17 | 2677908756 | 10115.3 [9919, 10313] | 547.22 +- 1.06 [502, 594] |
| 13 | 5 | 697604216 | 2635.1 [2535, 2736] | 151.29 +- 0.41 [128, 176] |
| 15 | 2 | 1822366272 | 6883.7 [6722, 7047] | 465.38 +- 2.10 [424, 508] |
| 17 | 1 | 87692932 | 331.2 [296, 367] | 26.35 +- 0.12 [17, 37] |
| 18 | 2 | 1346900798 | 5087.7 [4948, 5228] | 387.30 +- 1.49 [349, 426] |
| all 225 excluding A>=64 | 225 | 9821496856 | 37098.9 [36722, 37477] | 2182.90 +- 2.91 [2092, 2275] |
| k<=12 excluding A>=64 | 215 | 5866932638 | 22161.3 [21870, 22454] | 1152.58 +- 1.29 [1087, 1220] |
| k>=13 excluding A>=64 | 10 | 3954564218 | 14937.6 [14699, 15178] | 1030.32 +- 2.61 [968, 1094] |
| A>=64 (3 equations, reported separately) | 3 | 17356821196 | 65562.2 [65061, 66065] | 5210.75 +- 14.90 [5070, 5353] |

## 3. Predictions and decision rules

Ratio rho_S = observed accidents / E_S at stage S in {R, T}, with exact Poisson 95% interval widened by the +-3% model uncertainty.
- SUPPRESSED: upper bound of rho_S < 0.8. ENHANCED: lower bound > 1.25. Otherwise CONSISTENT with uniform.

**H-owner (the relayed prediction)**: the shadow fraction of D at k >= 13 is >= 0.99 (pooled over the 10 equations with k >= 13 and A < 64).
- PASS: point estimate >= 0.99 and N(D) >= 100. FAIL: point estimate < 0.99. INCONCLUSIVE: N(D) < 100 (stated with the Clopper-Pearson interval).
- The same fraction is reported for T and R and for k <= 12.

**H-uniform (my forecast, registered as the competing hypothesis)**: rho_R and rho_T are CONSISTENT. Then E_T(k>=13, A<64) = 1030 accidents sit in T, and H-owner can pass only if
descent removes all but about 1% of them, or if shadows number more than about 1e5 in T (the sweep records hundreds of anchors per equation family, so I put that below 5%).
My forecast: H-owner FAILS at k >= 13 on T, and on D unless d <= about 0.01; rho_R in [0.8, 1.25]; the accident fraction of D at k >= 13 is above 1%.
Confidence: MEDIUM on rho_R (model tested to +-1% on random lifts, never on the descent-selected parents of the sweep); LOW on the D-stage statement.

**Kill test for "accidents are uniform at level 24"**: refuted (suppression direction) if rho_R is SUPPRESSED pooled over the 225 equations, or rho_T is SUPPRESSED pooled over the 225.
A suppression factor f would still not make anchor-first provable unless accidents vanish; the verdict states f with its interval and E_T x f against 1.
Corroborated if both are CONSISTENT. ENHANCED at either stage is reported as a departure in the other direction.

**Controls (must pass before the numbers are read)**:
1. A pattern built from a known S-unit (y = 111132 and 3 random S-units below R_24, as a proper digit pattern with kappa = 0, and one with a digit above the top and kappa = 1) must classify shadow with the right (y, kappa).
2. Random pattern values (random nu, eps, digits from a real multiset, 10^5 draws) must classify accident (expected shadow rate about 0; any shadow is investigated).
3. Real survivors with one residue shifted by 1 (a shadow turned into a perturbed value) must classify accident.
4. The classifier given a planted false anchor (y = 5 x S-unit) must refuse.
5. Instrumented-copy gate: OPEN+EXACT lines of lvlN_x2 equal join24swap/lvlN's on all 228; join24swap/lvlN equals tier0/lvlN (md5 20e091fc) on sorted output sha256.

## 4. Known limits stated in advance

- The anchor test is exact; the model side is a heuristic tested only to level 48 on random lifts.
- Shadows killed by the tail test are visible only through the instrumented copy; the engine-only view (T) understates the shadow population and cannot see them.
- k means q (digit count). k >= 13 holds 10 equations (A < 64) plus 3 with A >= 64; 215 equations have k <= 12.
