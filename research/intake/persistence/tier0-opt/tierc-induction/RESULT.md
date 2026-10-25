# Tier C by induction on size: negative result (lane 3, 2026-10-24)

Verdict: no induction shape closes Tier C. Shape (b) is circular, shape (a) keeps the exponent box fixed and its
step fails at the first exceptional prefix on 100% of real data, shape (c) has no step at all. The kill criterion
fires: every shape fails with a measured shortfall above 10^10 or with no inequality to measure. Do not retry without
new data. Missing ingredient: a map from a large child (or its exceptional prefix) to a strictly smaller instance of
the same problem, or an effective Baker-type bound with sublinear dependence on the prefix height (theta lane, open
item 3).

No-Claim: nothing here is PROVEN or Lean-checked; on-paper steps await a cross-family statement review.

## 1. Prediction against outcome

Prediction file: PREDICTION.md, md5 014ffc39328905189d4d1cd22188314d, written before any S-unit arithmetic.

| id | prediction | outcome | verdict |
|---|---|---|---|
| PP1 | witness of an exceptional prefix is the candidate itself beyond G* in [10^13, 10^17] | derived (section 3b); G*(3 logs) = 10^13.78 / 10^13.93, G*(4 logs) = 10^16.02 / 10^16.18 at k = 31 / 44 | confirmed |
| PP2 | nesting keeps the box B | derived (3a) | confirmed |
| PP3 | no step in (c); iterations 17 (k=31) and 22 (k=44) if a step with the Baker multiplier existed | 16.63 -> 17 and 21.88 -> 22 | confirmed |
| PP4 | per-prefix enumeration above 10^100 | to reach the depth-1 target 10^72: 10^94.9 (k=31, j0=24), 10^152.1 (k=44, j0=37). Reaching the corpus is impossible: floor 10^14.7 | confirmed in order of magnitude, k=31 case 10^94.9 sits below the stated 10^100 |
| DP1 | longest zero run 8..11, none >= 12 | 8 (50 runs of length 8), none above | confirmed |
| DP2 | longest common leading prefix of distinct census units 14..17 digits | 10 digits (Benford random model expected 1190 pairs sharing >= 12; observed 0) | FALSIFIED |
| DP3 | no census run with s+g >= 16 has another S-unit sharing the leading s+g digits | 0 of 70,314; the first unshared bucket is s+g = 10 (8 of 343 shared at s+g = 9) | confirmed, stronger |
| DP4 | |Spearman(g_(j-1), g_j)| < 0.3 | -0.002 on 203,876 pairs | confirmed |
| DP5 | census ratio (s+g)/s below 10^1.3 for s >= 3 | maximum 3.33 (s = 3) | confirmed |

DP2 is the one miss. The prediction treated leading digits as random (birthday bound). They are not: the mantissas of
2^a 3^b 7^c in a box form a rank-3 set with Dirichlet-type spacing, so the closest pair agrees to about 3 log10(box) =
10 digits, not 15 to 17. Consequence: the empirical separation is stronger than the random model, and the Baker
separation bound at that box (G*(3 logs) at B = 2.1*10^3 is about 10^11.9 digits) is looser than the data by about
10^10.9. This strengthens the data side of (b) and changes no on-paper conclusion.

## 2. Definitions used

Notation of theta/NOTES.md section 1. s_j = n - E_j (prefix digits), g_j = E_j - E_(j+1), N_j the prefix numerator,
Lambda_j = M 10^(-E_j)/N_j - 1 with 0 < Lambda_j <= 80 10^(-g_j)/N_j. Gamma = <2,3,5,7> in Q*. A prefix is exceptional
at box B when some z in Gamma with exponents at most B has |z/N_j - 1| < c B^(-4) (T8). Scales for Tier C:
4 log10 B = 1126 (k = 31, log10 U = 281.5) and 1608 (k = 44, log10 U = 402.1). Chain constants as in NOTES: Matveev
K = 10^16.7 and Yu Y = 10^18.2 per block, K0 = Z0 = 10^14.7 at the two ends.

## 3. The shapes

### 3b. Descent on the exceptional witness. Verdict: PROVEN-ON-PAPER that it is circular; HEURISTIC part marked

Proposition B. Let j satisfy s_j + g_j > G4 + 3, where G4 = C(4) A (1 + ln B) / ln 10 with C(4) = 1.4 * 30^7 * 4^4.5
and A = ln2 ln3 ln5 ln7 (Matveev, D = 1). Then every z in Gamma with exponents at most B and z != M 10^(-E_j) satisfies
|z/N_j - 1| > Lambda_j. The candidate M is the strict nearest element of Gamma_B to N_j.

Proof. Put eta = z/N_j - 1 and L'' = M 10^(-E_j)/z - 1 = (Lambda_j - eta)/(1 + eta) != 0, a four-logarithm form in
2, 3, 5, 7, so |L''| > 10^(-G4). If |eta| <= Lambda_j then |L''| <= 3 Lambda_j, hence Lambda_j > 10^(-G4)/3,
and Lambda_j <= 80 10^(-s_j - g_j) forces s_j + g_j <= G4 + 3. Contradiction. QED (Matveev constants as recomputed in
chain_calc.py: C(3) = 1.432e11 reproduces NOTES T10's 1.43e11; C(4) = 1.568e13 by the same formula.)

G4 = 10^16.02 (k = 31) and 10^16.18 (k = 44).

What this does to the descent. T8's "witness M' of the exceptional prefix" is M itself whenever the prefix is longer
than G4. The descent claims a second configuration (M' with its own sparse prefix and long run) of smaller height.
Proposition B says the only element of Gamma_B closer to N_j than Lambda_j is M, so no such M' exists in the range
where Lambda_j is small enough to matter. A witness z with Lambda_j < |eta| < c B^(-4) is not excluded, but nothing
forces it to exist: the previous best approximants of N_j in smaller boxes B' sit at |eta| of order B'^(-3) (Dirichlet
covering heuristic, HEURISTIC), which is above their own exceptional line c B'^(-4), so they are non-exceptional
and the step's conclusion (a smaller exceptional configuration) is false for them.

Contradiction with T10. T10 gives separation of distinct S-units at 10^13.93 digits (3 logs). The descent needs it at
the exceptional scale 1126 to 1608 digits: a deficit of 10^10.7 (both k). Even a complete closure of that deficit
yields uniqueness of the witness, which is the hypothesis of Proposition B and not a bound on g_j. There is no
inequality in which the descent's output enters: the shortfall is structural, not a number.

Data (witness_out.txt, census_out_300.txt):
- corpus children, every (child, prefix j): another S-unit below 10^141 shares the leading L = p_(j+1) - 1 digits in
  7700/7700 pairs at L = 1 and 361/7331 at L = 8; 0 of 7247 at L = 9, and 0 for every L from 9 to 40 (about 150,000
  pairs, 21,245 above the 40-digit cap).
- census below 10^300, zero runs of length >= 5: 0 shared of 69,672 with s+g >= 18, 0 of 70,314 with s+g >= 16, and the
  first fully unshared bucket is s+g = 10.

### 3a. Nesting. Verdict: fails at the step "exceptional at j implies exceptional at j-1 at smaller size"

Hypothesis H_a(B). No S-unit with exponents at most B has a prefix of at most j blocks followed by a zero run longer
than 4 log10 B + c. Step. If N_j is exceptional at box B then N_(j-1), or its witness, is exceptional at a box B' < B.
Base. Corpus below 10^6885 or census below 10^300.

Where it fails, three independent places:
1. The box does not shrink. The only witness of N_(j-1) in the range of Proposition B is the same M, so B' = B.
2. N_(j-1) is exceptional exactly when s_j > 4 log10 B + c (M is within 10^(-s_j) of it). Exceptional at j needs
   s_(j+1) above that scale. The first exceptional index j* is the least j with s_(j+1) above the scale, and by
   minimality s_(j*) is below it. So the implication fails at j* for every candidate. Measured on the 8,806 corpus
   children (corpus_out.txt), with theta the scale: theta = 10: 8090/8090 violate it; theta = 20: 5739/5739;
   theta = 40: 1907/1907. This is forced by the definition, not a statistical finding; the useful number is the jump
   s_(j*+1)/s_(j*) the step would have to bound. Measured maximum 1.67, 1.33, 1.17 (medians 1.11, 1.05, 1.03). Proven
   bound: 1 + K = 10^16.7 (Matveev) or 10^18.2 (Yu). Depth 1 needs 10^2.67 two-ended at k = 44 and 10^3.82 at k = 31
   (T9, recomputed in chain_out.txt): shortfall 10^12.9 to 10^15.5.
3. The prefix is not an instance. If N_j were an S-unit, it would be a smaller instance. Codex T1: N_j = 2^r 7^t R. On
   175,707 real prefixes with s_j >= 6, R = 1 in 0; median log R / log N_j = 0.989, fifth percentile 0.889. Codex
   Theorem 2 gives the same conclusion on paper for the admissible prefix P_h (log R_h > (h-1) log 10).

Base case. The first exceptional prefix has s_(j*) at most 1126 to 1608 digits. Checking all such prefixes by lattice
reduction needs 10^88.5 (k = 31) and 10^126.1 (k = 44) cases (prefix_count_out.txt), which is T8's cost. The corpus and
census are no help: they list S-units, not sparse prefixes.

Per-block empirical multiplier (census, g >= 4, runs by prefix length s): ratio (s+g)/s is 8.00 at s = 1, 4.50, 3.33 at
s = 3, 2.60, 2.33, 1.70, 1.39, 1.23, 1.10, 1.06 at s >= 129. Corpus interior ratios: 6.0 at s_j = 1 falling to 1.05
at s_j >= 65. Spearman(g_(j-1), g_j) = -0.002 and Spearman(s_j, g_j) = -0.011, so a previous gap predicts nothing
about the next. The truth is far below what depth 1 needs; the gap is in the proof.

### 3c. Strong induction on n with the corpus as base. Verdict: fails at "no step exists"; numbers below

Hypothesis H_c(N): no child with at most N digits (N = 6885 from the zero-free corpus). Step required: a child with
n in (N, mu N] yields a child or instance with at most N digits, mu = the per-step multiplier. No operation does this:
the prefix is not an S-unit (3a, point 3), the child is a single S-unit y, and the Baker cap enters only through
inequalities in which n is bounded from above (T6): the system is feasible with n = min_m F(m) (exact witness in T6),
so the assumption n > N is never an input that can tighten it.

Measured:
- Iteration count if a step with the Baker multiplier existed: (log10 U - log10 6885)/16.7 = 16.63 -> 17 (k = 31) and
  (402.1 - 3.84)/18.2 = 21.88 -> 22 (k = 44).
- Floor of the Baker end: E_k <= Z0 = 10^14.7, which exceeds 6885 by 10^10.86. No top-end work can cover the
  corpus alone; the corpus is out of reach of the chain at any depth (j0 = k leaves 10^14.7).
- Reproduction of T6: k = 44 gives 396.90 (NOTES: 396.9); k = 31 gives 281.90 (the B3 value 281.5 uses its own constants).

Variant (c'): induction on the number of verified blocks j0, base computed by lattice reduction (T8 per prefix), Baker
above j0 (chain_out.txt, chain_target_out.txt):

| k | j0 | cost (reductions) | log10 U |
|---|---|---|---|
| 31 | 0 / 1 / 3 / 10 / 20 / 24 / 31 | 1 / 10^4.0 / 10^11.9 / 10^39.5 / 10^79.1 / 10^94.9 / 10^122.6 | 281.9 / 270.3 / 254.0 / 196.7 / 105.7 / 71.2 / 14.7 |
| 44 | 0 / 1 / 3 / 10 / 20 / 37 / 44 | 1 / 10^4.1 / 10^12.3 / 10^41.1 / 10^82.2 / 10^152.1 / 10^180.8 | 396.9 / 387.3 / 371.1 / 305.9 / 221.6 / 71.6 / 14.7 |

Each verified level buys about 10 to 28 orders at 10^4 cost. With a ceiling of 10^12 reductions (assumed budget; the
unit cost of one reduction was not measured here and does not matter at these magnitudes) j0 = 3 and log10 U stays
above 250. Depth-1 target 10^72 needs 10^94.9 (k = 31) and 10^152.1 (k = 44): shortfall 10^83 to 10^140.

## 4. Planted negatives (witness_out.txt)

- N1: step (b) tester `unique_witness` on a real child (n = 62) at L = 6, where competitors exist: FLAGGED. Control
  at L = 24: certified unique. A mutant tester that always answers "unique" would certify N1, so the negative
  separates the real tester from the mutant.
- N2: a planted twin sharing 39 leading digits with the child is inserted into the key set: FLAGGED. Same query
  without the twin: certified unique.
- N3: record census unit 2^126 3^75 7^81 (143 digits, leading 14683, then 8 zeros). Step (a) claim "(s+g)/s <= 2" with
  s = 5, g = 8: FLAGGED (ratio 2.6). At lambda = 3 it holds, which shows the tester is not set to always refuse.

## 5. Strongest objections

1. Constants. The kill criterion rests on the four-logarithm Matveev/Yu constants. Mignotte-Voutier's three-logarithm
   kit is 10^5 to 10^6 better (HYPOTHESES N4 line, not re-verified here) and applies to three-log forms only. For
   such blocks the depth-1 deficit would fall to about 10^8 to 10^10. It does not rescue any shape: (a) and (b) fail
   at structure (box fixed, witness is the candidate) and (c) has no step, none of which depends on a constant.
2. Scale. The census reaches B near 10^3 and the corpus children have k near 0.8 n, nothing like k = 31 to 44 at
   n above 6885. The data show the steps do not hold at small scale and that truth is far inside the needed
   multipliers; they are not evidence about 10^400. The structural failures are proofs, not extrapolations.
3. Proposition B depends on Matveev's theorem as quoted (BMS 9.4 via NOTES) and on my reading that D = 1 and A_i = ln of
   the bases is admissible with the base 5 and exponents at most B; C(3) matched NOTES, C(4) is the same formula.
4. The Dirichlet remark on previous approximants is HEURISTIC and supports only the "not forced to exist" part of (b).
5. A cleverer induction might use a different parameter than size (number of terms in the unit equation). The classical
   shape for sums of S-units is induction on the number of terms with the Subspace Theorem at the step; that step is
   ineffective (literature, from memory, not read in this session). It is a research direction, not a result.

## 6. Seams

- Verified here: census of all 37,375,388 S-units below 10^300 (rebuilt by my own script; count matches theta_07);
  zero-free corpus of 8,806 children (identity 9y+1 = 10^n + sum c_i 10^(E_i) asserted on every row); the digit and
  key tables; the chain arithmetic. Not verified: Matveev's statement (constants taken from NOTES and BAKER-CHAIN,
  C(3) cross-checked), Yu/BK constants and the 14.7, 16.7, 18.2 inputs (NOTES), the T8 threshold c B^(-4) and its O(1).
- Corpus columns: the file has digits, then a, b, c, then a tag; (a, b, c) are columns 2 to 4 of each row. Confirmed by
  all 8,807 rows being zero-free under that reading, not from a README.
- Convention: p_j is the 1-based position of the j-th non-1 digit of y, s_j = p_j, g_j = p_(j+1) - p_j. The agreement
  length for the witness check, L = p_(j+1) - 1, is conservative by one digit because c_i can be a single digit.
- No lattice reduction was run; the per-prefix cost is a count of prefixes, not a measured time.
- One compute process at a time, nice 10, `uv run --no-project python -I <file>`; nothing deleted, nothing under tier0 or
  existing tier0-opt subdirectories touched, no git.
- Literature on Evertse/Subspace and on Mignotte-Voutier is not first-hand here.

## 7. Files and md5

PREDICTION.md 014ffc39328905189d4d1cd22188314d; census_scan.py 05338b2c16244f9fe3fb4b0c06e19405 with
census_out_300.txt b9e6cfa9f5c8ad3da4ac9f50d977847c; corpus_children.py 8d2c35a64b6ab87090bf07f8923545b6 with
corpus_out.txt 9d5b671f9e810b904d3b1336decf7e85; witness_check.py 0e725d885a6e0b9a666ab791e42582d1 with witness_out.txt
ef65602fdbc9ec35ff9680014194b562; chain_calc.py e5b6fbb25b9546c59811b3707a03b729 with chain_out.txt
ea2d542c4743423c5717b6ec24cc6d64; chain_target.py edd931c957e80a02af6bda71845f15dc with chain_target_out.txt
66ea2cb6394f2be96a8795f51decadd4; prefix_count.py fdb4abf94fed1ba76f381154612ff0ae with prefix_count_out.txt
3c9dec42fa7960a3bf8a2ae1e3eb623e. probe_zf.py reads the corpus column layout.

No-Claim: nothing here is PROVEN or Lean-checked; on-paper steps await a cross-family statement review.
