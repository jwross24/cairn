# Hypothesis queue: new mathematics for the persistence search

One shared queue for the chat session and Cairn. Anyone may add an entry; an entry moves only on an executed kill test.
Statuses: OPEN (not yet tested), TESTING (kill test running, who and where), KILLED (the test refuted it; keep the entry
and the evidence), SURVIVED (the test passed; next step named), ADOPTED (the chat merged it into the tier0 engine under
the gate). Calibration tags follow RULE 2: a survived entry is CONJECTURE or STRONG-EMPIRICAL, never PROVEN without Lean
plus a statement review. Agreement between same-family agents counts once.

Every entry: claim; why it would matter (the factor it removes, in patterns or anchors); kill test (one command or
computation, under 2 CPU-hours, with a registered prediction); owner; status; evidence path.

## H1. Anchoring Lemma
- Claim: every pattern open at level 96 is anchored, i.e. an exact integer identity y (+ R_96) = R_ν + Σ(d_j−1)10^{e_j}
  with y a {2,3,7}-unit of height ≤ H(level), for an explicit H.
- Matters: anchor-first enumeration (RESULT-anchorfirst.md) replaces level-12 pattern enumeration; Tier B and C cost
  scales with anchors (10^4–10^5 per Tier-C vertex), not patterns (10^11–10^14).
- Kill test: on every recorded open pattern with full (ν, eps) (sweep recording in tier0-opt/patterns/), find any open
  pattern with no anchor of height ≤ 10^10; then attempt the proof route (the coset of Λ_96 + M and its reduced
  representative). Prediction: 0 unanchored among recorded patterns (OPEN-PATTERNS.md found 299/299 anchored).
- Owner: Cairn H1 lane. Status: KILLED as stated (2026-10-20, tier0-opt/math/h1-anchoring/REPORT.md). An exact
  counterexample outside the program: u = 3^156·7^214 (256 digits), V = u mod R_96, q = 100, passes all 20 level
  congruences and its coset holds no S-unit below 10^98 (PROVEN-ON-PAPER + exact computation). The open set is anchored
  patterns plus accidents (a pattern value landing in the S-unit subgroup mod Q by chance, 5.3e-38 per pattern);
  expected accidents per equation 2e-13 summed over the 1,628 recorded equations, 2.3 at q = 30, 2.2e8 at q = 40,
  1.35e11 at q = 44 (agrees with Codex H10). Restricted form, CONJECTURE: every open pattern is anchored for q ≲ 22–26.
  Consequence: anchor-first enumeration is a forecast, never a certificate, unless accidents are excluded by proof;
  at Tier C only the sandwich removes them. Data: run_exact 3153/3153 ok; 90 anchors exceed 1e10 (max 1.0e14), so
  the 'height ≤ 10^10' kill test was already killed. Decisive unrun test: a q = 14 equation (2^9·3^5) to level 48,
  where the accident model predicts ~500 accidents and H1 predicts 0.

## H2. Per-anchor closure
- Claim: one computation per anchor (y, k) decides all patterns it carries, e.g. a carry automaton over Z/10 intersected
  with the 10-adic S-unit cosets mod 10^{96D}.
- Matters: the chat's named direction (COORDINATION chat 18:55: "one coset per anchor for all its patterns").
- Kill test: per-anchor verdicts must reproduce Lemma C's per-pattern verdicts exactly on DEEPCUT-run (288/11) and the
  current sweep set (1,213 closed), with planted genuine points surviving. Prediction: exact agreement, with cost per
  anchor ≤ 100× the cost per pattern.
- Owner: Cairn H2 lane. Status: SURVIVED at depth 1 (tier0-opt/math/h2-anchor-closure/RESULTS.md). At depth 1 no
  carries occur (one digit per class at copy 0), so Lemma C's cut is exactly L ≡ y (mod 5^5·2^(a+9)); an automaton
  enforces it (2-adic parity forced per digit, a 5-adic filter on the first five digits), with no discrete logarithms.
  Equivalence PROVEN-ON-PAPER conditional on Λ_96's image being the full kernel mod 5^5 and 2^9 (STRONG-EMPIRICAL).
  Differential (sample: first 347 patterns + every 4th): 0 verdict and 0 case-count disagreements on 2,936
  representations (589 patterns, 109 anchors); closes 9 of 16 patterns deepcut capped out on. Planted: 1,434 genuine
  lattice points on 239 anchors, 0 false kills; 2,808 SELF patterns all open. Cost: 0.019 s for 589 patterns vs
  1,154 s for Python deepcut (~6e4×). The test never uses the anchor identity, so it should also decide accidents
  (untested: no accident data). Not covered: depth ≥ 2, the sandwich. Sharing keys on the coset residue, not the
  anchor. Does not remove Tier C's 1e11–1e14 pattern count.

## H3. Sharper lower bounds at small depth
- Claim: Laurent's two-logarithm bound (and Bugeaud–Laurent p-adic) beats Matveev where the linear form has two or three
  logarithms, lowering the depth at which the sandwich closes.
- Kill test: recompute G(k, a) with the sharper bound for the 43 SANDWICH survivors; report the depth drop. Prediction:
  at least one depth level earlier on most of them. Does not change the exponential shape (LIT2.md).
- Owner: unassigned. Status: OPEN.

## H4. Representation technique (Becker–Coron–Joux) for the pattern sum
- Claim: the level-12 test is a weighted subset sum in a finite group; BCJ representations lower the enumeration
  exponent where classical meet-in-the-middle failed (IDEAS.md).
- Kill test: a cost model on two Tier B vertices before any build. Prediction: unknown; written down before computing.
- Owner: unassigned. Status: OPEN.

## From the independent Codex brainstorm (tier0-opt/math/codex-brainstorm.md, 2026-10-20; Codex did not see H1–H4)

## H5. Two-ended Baker chain (Codex idea 1)
- Claim: meet the top-down Matveev chain with a bottom-up 5-adic Yu chain (T_j are 5-adic units since digit 5 is
  excluded), n ≤ X_j + Z_j optimized over the split j (Bugeaud–Kaneko arXiv 1704.00432, Thm 2.1, (2.2), Lemma 3.1).
- Matters: Codex reports n < 10^237 / 10^332 / 10^465 for k = 22 / 31 / 44 (a > 0), forecasting sandwich depths
  5 / 7 / 10. Still exponential in k; leaves enumeration intact.
- Kill test: independent audit of the theorem application (assigned to the H3 lane), then recompute against
  baker_chain.py. Correlated with H3 (both shrink G); count once if they agree.
- Owner: Cairn H3 lane (audit). Status: TESTING.

## H6. Anchor carry DP intersected with Lemma C (Codex idea 2)
- Claim: enforce Lemma C's finite-quotient condition inside the anchor representation DP, eliminating high columns
  existentially. Codex's own probe compressed 1.32× on 27 records (2.6–32.7× on constructed cases). Same target as H2.
- Status: OPEN; folded into the H2 lane's comparison.

## H7. Additive lift sums joined against the multiplicative image (Codex idea 3)
- Claim: at a lift, enumerate the S-unit residue image H from the parent coset mod selected new primes, and join two
  balanced additive partial-sum lists on it (Dimitrov–Howe arXiv 2105.06440 balanced lifting); work → √(BH) + Z.
- Kill test: 60 CPU-min on ten large recorded parents, primes 73 and 137; prediction 100× fewer generated tuples.
- Status: OPEN.

## H8. Shared deep-cut states across histories (Codex idea 4)
- Claim: histories with the same exponent coset and remaining (d, e mod 96) multiset have identical futures; merge them
  in a DAG through sandwich depths. Kill test: 90 CPU-min on sandwich survivors to depth 6, prediction 100×. LOW.
- Status: OPEN.

## H9. Valuation-aware suffix constraints before the ladder (Codex idea 5)
- Claim: search admissible suffixes mod 10^K with the digit-product budget, keeping all three exponents; a = v2(t) only
  when v2(t) < K. Also removes the non-terminating two_adic_bound for k ≥ 36. Kill test: 90 CPU-min, 2-heavy multiset
  from RESULT-dpcount.md, planted genuine S-units with a ≥ K must survive; prediction 100× fewer lift nodes.
- Status: OPEN.

## H10. Finite certificate of anchoredness (Codex idea 6)
- Claim: for fixed M and a, an independently checked unsatisfiability certificate that no level-96 survivor lacks an
  anchor in a bounded envelope. Codex's uniform-residue heuristic predicts 1.4e3–1.1e11 accidental memberships per a
  before descent, which argues AGAINST H1 holding outright. Correlated with H1; the H1 lane's counterexample hunt is the
  first test.
- Status: OPEN.

## From ideation round 1 (tier0-opt/math/ideation/IDEAS-ROUND1.md, 2026-10-20; /modes-of-reasoning + /idea-wizard lane)
Headline: no idea found that removes the six-plus orders Tier C needs; the best gives ~12–21× across every stage. At Tier B
the work sits in the 12→24 and 24→48 lifts (tests outnumber outputs by 10^7–10^8).

## H11 (R1.1). Branch split on 3 | y′ and 7 | y′ — HIGH
- Claim: the level-12 pattern fixes y′ mod 3 and mod 7, hence whether b = 0 and c = 0; test against ⟨2,7⟩, ⟨2,3⟩ or ⟨2⟩
  in those branches instead of ⟨2,3,7⟩. Survivors drop 12.6× at level 12 and 21× at levels 24–96 (exact index
  arithmetic; sampled 12.4–12.8×); 8,180/8,180 genuine zero-free S-units pass, a wrong subgroup passes 20/8,180.
- Kill test: engine-level differential on 72, 224, 10800, 14336, 8192, 28672 (solutions identical, plants 100%,
  open@96 a subset with each removal justified). Owner: Cairn r1-branch-split lane. Status: SURVIVED
  (tier0-opt/math/r1-branch-split/REPORT.md): sound (PROVEN-ON-PAPER); 87/87 equations identical solutions and
  children; 608/608 plants; final open sets identical; level-12 survivors and level-24 children 19–20× fewer, but
  levels 24–96 only 1.0–1.3× (the 21× prediction is falsified); measured end to end 1.07–1.36× at q ≤ 13, Tier B
  extrapolated 5–10×. Next: a C-side filter, then the chat's call on adopting it into tier0.

## H12 (R1.2). Stage-ratio law — MEDIUM
- Claim: at k = 25 the 12→24 lift does ~224 tests per level-12 pattern (level 12 < 1% of Tier B work); the 24→48 lift
  overtakes near k = 31. So GPU effort on level 12 is misdirected for Tier B. Kill test: 1 CPU-h on k = 16, 17 equations.
- Status: OPEN.

## H13 (R1.3). Dual enumeration at level 24 — MEDIUM-LOW
- Claim: enumerate the ~3.4e13·(A+1) S-unit residues mod Q24 once for all vertices and decode; beats the lift only above
  k ≈ 24–25 (~40× at k = 29), whole-pipeline ≤ ~10×. Status: OPEN.

## H14 (R1.4). Tail-word conditioning plus a join — LOW; counts once with H4 and H7.
## H15 (R1.5). One integer sweep for level 12 of every vertex — correct, low impact (level 12 < 1% at high k).
## H16 (R1.6). Calibrated accident constant — MEDIUM; counts with H1
- Observed non-anchored survivors / uniform model ≈ 1.2e-3 flat at level 24 for k = 11–14 (135 equations). Predicted
  Tier C non-anchored open patterns per vertex 2.3 to 1.8e8 (≤ 0.3% of the anchored count); Tier B ≤ 2e-5 per vertex.

## Breakthrough round (tier0-opt/math/breakthrough/, 2026-10-20 night)
- B3 (archimedean, tier0-opt/math/breakthrough/b3-archimedean/REPORT.md): best unconditional bound for this family,
  two-ended Matveev + Bugeaud–Kaneko 5-adic chain with 2^a folded into the varying rational (a ≤ 40):
  log10 G′ = 281 (k = 31), 394–402 (k = 44), against 541–599 / ≈ 775 now (PROVEN-ON-PAPER, interval-certified;
  BK (2.2) constant taken from BK, Yu's original unread). Depth needed 6 / 8: not shallow. Negative results:
  hypergeometric methods (HEURISTIC), gap-structure LP shows meet-in-the-middle optimal in its class (exact on
  k = 6, 10, 14), Bugeaud–Laurent inapplicable, end reduction ≈ 10^12. THE TARGET: a per-gap bound gap ≤ C·h^θ with
  θ ≤ 0.75 for this family would close Tier C at depth 1; every known theorem has θ = 1.
- B1 (obstruction map, tier0-opt/math/breakthrough/b1-obstruction/MAP.md): three factors multiply — the Baker bound
  (×≈10^18.6 per non-1 digit; one-ended log10 G = 849.7 for the k = 44 vertex), the lattice barrier (rank-2 (b, c)
  lattice certifies only n > sqrt(det), so ≈ 2·log10 G pinned digits are needed: depth 12–18 one-ended, 7–10
  two-ended), and (D+1)^q copy choices per pinned window (10^56 per pattern at k = 44). Shared root: the k interior
  positions are reached only from the two ends. W1 needs log10 G′ ≤ 168 at k = 44 (per-digit multiplier 10^3.6, or
  10^7 two-ended): constant polishing cannot reach it. Unexploited structure, ranked: (1) per-pattern exponent rank —
  ~57% of patterns are y = 2^a (finite), ~38% rank 1 (depth roughly halves), ~5% rank 2 (full cost; worst case
  unchanged); (2) 2-adic forcing of low digits (admissible tails ~ℓ^5.2 vs 2^ℓ for 2^39·3^3·7^2; depth 1 only);
  (3) character-sum / large-sieve control of accidents (would settle H1 rigorously, closes nothing alone). Open
  item that may matter most: live sub-coset growth measured at ×3–5 per depth for k ≤ 15, irreconcilable with
  (D+1)^q — forwarded to B2. New-math targets N1–N4 (MAP.md §5): polynomial-in-k gap bound whose constant does not
  carry the lower part's height; effective Evertse with ε = 1/k; character-sum bound on accidents; 5-adic forcing.
- Codex deep attempt (tier0-opt/math/codex-deep-attempt.md, W2, blind to B1–B3): barrier NOT broken. PROVEN-ON-PAPER:
  (T1) inside a coset whose units agree mod 10^s, extending the suffix by h ≤ s − a digits is an exact LINEAR
  congruence A_u z1 + A_v z2 − Σ w_j x_j ≡ β (mod 10^h), x_j ∈ {0,1} (nilpotence of g − 1; 3,528 checks, and the
  over-precision case fails as predicted); (T2) an interval certificate that rejects a whole family of copy choices
  in polynomial time (510 small tests: 180 sound rejections, 0 false); (T3) saturation of Λ_96's image mod 2^9·5^5
  forces any EXPLICIT output list to hold 2^r cosets for r independent occupied classes; (T4) one optional digit 2
  destroys affine-hull compression. Where it breaks: when the exponent box exceeds the modulus and the coefficient
  gcd is 1 (exactly the reachable Tier-C case: 527-digit coordinate bounds vs M = 10^96), every multiplier fails.
  Open task it names: minimize exponent height over the symbolic Boolean family without enumerating its fibers.
  Note: T3 bounds explicit lists, while B1 measured only ×3–5 live sub-coset growth per depth at k ≤ 15; B2 is
  reconciling the two.
- Lean (commit 5b54f1d, lean/Grounding/Persistence{ExactIdentity,BranchSplit,BlockLift}.lean; green build, standard axioms)
  with a cross-family statement review (Codex, read-only): ExactIdentity MATCHES (exact_identity_iff, k_bound — the
  conditional identity, not H1's anchor existence); BranchSplit MATCHES except value_modEq_of_modEq_twelve (assumes
  mod 12 where the paper claims mod-6 dependence for 7) and the d ≥ 1 caveat (truncated subtraction); the gcd filter is
  not formalized; BlockLift DOES-NOT-MATCH Codex T1 (assumes 10^s | t and exponentiates 1 + t; the paper's weighted
  two-generator statement under v2(g−1) ≥ s−a, v5(g−1) ≥ s with integer exponents is not covered). Lean lane closing
  the gaps. None of this is PROVEN yet in the RULE 2 sense for the BlockLift claim.

## Corrections (2026-10-20 23:25, from the H1 lane's §7 and the drafting lane's NOTE-2026-10-21.md §8)
- H1 / H10 / H16: the decisive test RAN (H1 REPORT.md §7; s = 124416, M = 2^9·3^5, q = 14, to level 48): the
  uniform-residue accident model predicted 42 (20–100) accidents, OBSERVED 0 (17 level-48 survivors, all anchored
  descendants); the model overshoots by ≥ 480× at level 24 and ≥ 29× at level 48 because lower-level survivors are far
  from uniform. The accident forecasts above (2.3 at q = 30, 2.2e8 at q = 40, 1.35e11 at q = 44; H16's calibrated
  constant) are upper bounds of a refuted model, NOT forecasts. The Tier-C failure claim is withdrawn: no evidence
  either way at Tier-C scale; only the q = 100 construction (3^156·7^214) stands, and it lies outside every vertex.
  Restricted H1 stays CONJECTURE. Anchor-first remains a forecast (not a certificate) because no proof excludes
  accidents.
- B3: the bound is certified only for a ≤ 40, while Tier-C configurations need A ≥ 100–160 (B1; chat 18:55 on
  two_adic_bound). For a > 40 the 2^a fold gives no gain; B3 does not yet cover all of Tier C.
- H2's group fact (Λ_96's image is the full kernel mod 2^9·5^5) is proved on paper in Codex's deep attempt (T3,
  valuations (9,5) and (10,5) of the basis); its STRONG-EMPIRICAL tag can rise to PROVEN-ON-PAPER pending review.
- Research note draft with all fifteen source disagreements: tier0-opt/math/NOTE-2026-10-21.md §8.
- Lean status after the second cross-family statement review (Codex, read-only, of 91e8b74's working tree): every
  lemma in lean/Grounding/PersistenceExactIdentity.lean, PersistenceBranchSplit.lean and PersistenceBlockLift.lean now
  has a green build (standard axioms) AND a statement-level review. MATCHES: exact_identity_iff, k_bound, R_mono,
  pow_le_R, the mod-3 / mod-7 helpers, exponent_zero_of_not_dvd_{three,seven}, value_modEq_three_int, sum_modEq_int,
  unit_zpow_lift, prod_dvd, dvd_ten_pow. MATCHES-WITH-NOTED-GAPS: two_generator_lift (Codex T1's linearization
  identity; representatives and the identification with 3^u1·7^u2 left to callers; stops before the Boolean suffix
  equivalence), value_modEq_seven_of_modEq_six and value_modEq_three_of_modEq_three (natural subtraction: d ≥ 1).
  Superseded, kept: pow_one_add_modEq and its ℕ form (abstract step only). So these Lean statements meet RULE 2's two
  conditions FOR WHAT THEY STATE; the program-level claims built on them (the branch-split filter's correctness,
  the linear block lift as an algorithm, H1's anchor existence) are not formalized and keep their earlier tags.
- Codex θ attempt (tier0-opt/math/codex-theta-attempt.md, blind to the Claude θ lane): NO unconditional sublinear gap
  bound for the full family. Proved on paper: (T1) the relevant height is the non-smooth cofactor R of the prefix
  numerator N = 9⌊y/10^e⌋ + 1 = 2^r 7^t R (no 3 since N ≡ 1 mod 9); when R = 1 the gap bound is height-free (only
  log B); sublinear growth of log R in the prefix length would give θ < 1, but (T2) explicit admissible prefixes
  (two 2s, rest 1s) have log R > (h−1) log 10, so prefix sparsity alone cannot force it; (T3) an exact
  bounded-coordinate rejection test; (T4) a constructive limit on local congruence arguments. Where it breaks: a gap
  theorem must exclude a single candidate, and covolume / affine surjectivity cannot; simultaneous prefix + low-fiber
  control "might" force separation (LOW, no inequality found).
- Claude θ lane (tier0-opt/math/breakthrough/theta/, blind to the Codex θ attempt): NO θ < 1; every route gives θ = 1.
  Proved on paper: θ < 1 ⇔ an effective Roth-type bound with constant polynomial in 1/ε (T1); a θ < 1 bound uniform
  in k would force k ≥ n^(1−θ)/C non-1 digits for every S-unit, far beyond the known c·log n/log log n (T2);
  linear dependence on the prefix height is optimal for single-approximant forms (T3, Lemma H); lattice coordinates
  lose (generator heights 10^28.2, 10^28.7) (T4); the p-adic side stays linear (T5); NO-GO: no combination of
  archimedean prefix and 2/5-adic suffix bounds beats the meet-in-the-middle value, exact witness on 300/300 (T6).
  POSITIVE, to audit: T7 — for a ≥ 1, a digit-by-digit 2-adic argument gives p_{m+1} ≤ 6.32 + 3.32·p_m with no Baker
  constant, bounding a unconditionally; claimed consequence: B3's bounds hold for all a, log10 G′ = 279.5 / 394.2
  (a ≥ 1) and 281.5 / 402.1 (a = 0) at k = 31 / 44 (exhaustive 728,256 cases, 0 violations; planted negative
  refused). This would remove B3's a ≤ 40 caveat; it must be reconciled with the documented A ≥ 100–160 (sent to the
  H3 audit). T9: depth 1 needs a per-gap multiplier ≤ 10^2.6 two-ended against Matveev 10^16.7 / Yu 10^18.2: a
  deficit of 10^14–10^16. Context (STRONG-EMPIRICAL): all 37,375,388 S-units below 10^300 have ≥ ~0.8n non-1 digits;
  the largest n with k ≤ 12 is 20; the longest run of 1s is 8. Open: per-gap constants 10^14–10^16 smaller; an
  effective Roth-type theorem with polynomial ε-dependence; a structural reason sparse prefixes are never near an
  S-unit.
- H3 / B3 audit (tier0-opt/math/h3-h4/REPORT.md): H3 KILLED as predicted-by-hypothesis (no archimedean form in the
  chain has two logs; Laurent has nothing to apply to; real top constants drop log10 G by ~3.6 and move 0 of the 43
  survivors). B3 VERIFIED (conditional on Bugeaud–Kaneko (2.2) as a safe weakening of Yu as quoted by
  Bérczes–Evertse–Győry 2009, Bugeaud–Evertse 2017, Cai 2019, valid for log B ≥ 15; Yu's original not read):
  independent retype G′(31) = 281.50 / 279.23 / 280.06 and G′(44) = 402.11 / 393.93 / 394.75 at a = 0 / 1 / 40,
  matching B3 to 0.01; for a = 100, 130, 160: 280.4–280.6 (k = 31) and 395.1–395.3 (k = 44). The a ≤ 40 caveat is
  NOT a real limit (the fold adds a·log 2 to one height; candidates keep the anchor's a). On the 43 SANDWICH survivors
  the two-ended chain improves all 43 (depths 2/3/4 on 7/26/10 become 1 on 16 and 2 on 27). T7 re-derived without
  error, but it does not force a ≤ 6; it is not needed for fixed a; consistent with A = 118–144. Verdict: safe to
  replace Theorem U in SANDWICH.md for k = 31, 44 and fixed a ≤ 160, with the BK/Yu assumption stated.
- H4 KILLED: not a needle problem (1/49.5 of patterns survive, so any method costs at least the survivor count;
  a modulus join gains ≤ 2×; perfect listing moves total cost < 2% since enumeration is 1.9% of the work).
- N4 literature (tier0-opt/math/breakthrough/n4-literature/LIT3.md, raw sources in raw/): nothing meets W1, W2 or a
  rigorous Wall-1 count. Actionable: (1) Fonga, arXiv:2608.27802 (Aug 2026, READ): v2 is uniformly bounded on
  "fixed exceptional digits, arbitrary 1s, no 0", by the same digit-by-digit 2-adic recursion as the θ lane's T7;
  its Theorem 4.1 gives the EXACT max v2 per digit multiset by a finite recursion (re-implemented; reproduces
  D = {4,4,7} → 7) — candidate replacement for two_adic_bound, which does not terminate for k ≥ 36 (H9);
  (2) Mignotte–Voutier three-log kit, arXiv:2205.08899: 10^5–10^6 over Matveev, applicable only to three-log forms
  (rank-1 branches with 2^a folded, archimedean half) — ~40–50% of the needed log-gain there, not depth-1 closure;
  (3) Skolem certificates (Bilu et al. arXiv:2204.13417): unconditional output, conditional termination
  (RULE-2-admissible), one variable — formalizes the ladder, no speedup; (4) a Lean statement of the v2 recursion;
  (5) Saye arXiv:2202.13256 as a design reference for H9. Negatives: no sumset-into-subgroup count fits Wall 1;
  no Dimitrov–Howe / Bertók–Hajdu successor; no 4–5-log Matveev improvement; no effective Roth with polynomial 1/ε.
- N2 (Wall 1, tier0-opt/math/breakthrough/n2-accidents/): NO rigorous "accidents < 1" bound is reachable, and no usable
  exact alternative. Proved on paper: one-sided bounds also count anchored patterns (2e11–1.5e14 per Tier-C vertex),
  so certifying zero needs relative slack < 1e-11; per-prime methods lose 4.8e34 at level 96 because survival is a
  rank-2 coupling across primes (per-prime density product 3.5e-3 vs joint 7.26e-38); character sums have a √N
  floor (error/main 9e12–8.5e16 at Tier C); large sieve best 3.3e94 (1e46–1e54 too big); partial-prime DP leaves
  34–43 orders; exact DP over Z/P_L needs ~1e95 cells at level 96. Heuristic (model known to overshoot ≥ 15×):
  accidents 3e-10–9e-6 of the anchored count per vertex. Consequence: "open set = anchored set" is likely false or
  unprovable at the top of Tier C (q ≳ 28); certificates there need per-pattern closure, a full count (infeasible)
  or a structural proof.
- N1-Codex (tier0-opt/math/codex-n1-attempt.md): PROVED ON PAPER that the target is EXACTLY affine in the Boolean
  copy choices for every free position ≥ max(a+2, ⌈(K+a)/2⌉), using the 2- and 5-adic logarithms (exact coefficients
  log_p(1+ρ_i), not ρ_i: dropping the series loses bits, e.g. K = 8, ρ = 112 gives log_2 = 240 mod 256), and that the
  full exponent condition is a system of affine integer congruences in (x, b, c) of rank q + 3. NOT established: any
  computational gain over enumeration — low-position branching stays exponential, one-hot dimension grows with q·D,
  and a nearest point outside the box does not prove all points miss it. Prototype passed small planted boxes; no
  43-survivor differential, BKZ or Kannan run. The Claude N1 lane continues on the computational question.
- Yu audit (tier0-opt/math/yu-audit/; owner-supplied Yu 2007 Forum Math. 19, 187–280 and Yu 2013 Acta Math. 211,
  315–382): BK (2.2) VERIFIED as a safe weakening of Yu 2007 p.190's "first consequence" for every B ≥ 3, p = 5
  (the "log B ≥ 15" condition was an artifact of the secondary quotations) — but that consequence is printed WITHOUT
  proof ("details omitted", p.194). Sharper constants for our 3-log 5-adic forms (C: BK 10^15.09 → Yu 2007 Thm II
  10^9.30 → Yu 2013 Main 10^7.37): best PROVED IN PRINT (Yu 2007 Theorem II, Part II pp.74–93 of the pdf, over
  K = Q(i), with Theorem 1 for the dependent cases) gives log10 G′ = 230.2 (k = 31) / 324.3 (k = 44) at a = 0
  (222.5 / 317.8 at a = 1): depth 5 / 7 instead of 6 / 8; 20 of the 43 SANDWICH survivors move from depth 2 to 1.
  Best published statement (Yu 2013 Main, Theorem II's proof omitted in print): 208.4 / 295.1, depth 4 / 6.
  Unverified: table constants read from page images; 50-digit fixed-point numerics, not interval-certified.
- B2 (Wall 2, tier0-opt/math/breakthrough/b2-sandwich/; report returned as text): NO subexponential method. Proved on
  paper (given the group fact): depth-1 feasibility depends only on L mod 5^5·2^(a+9) (248/248 vs cut_coset), which is
  why depth ≥ 2 never kills; the bound depends on all of L and distinct digit strings give distinct cosets, so the only
  equivalences are permutations of equal digits. STRONG-EMPIRICAL (k = 5–11): the leaf count is POLYNOMIAL in D,
  degree ≈ 0.72k − 2.8 (not (D+1)^k with base growing per depth); per-depth ratios 2.0 (k = 5) to 6.7 (k = 10), max 18;
  C-port fit log10(count/rep) = 0.50k − 2.66; bound = 47.98·D − 0.414·log10 V + 24.04, so the depth needed is set by
  the Baker cap. Compression: equal-digit dedup 2.05×, cross-pattern cache 2.4×, H8 DAG ~2× (its 100× prediction
  KILLED); Fourier/additive kernels count but cannot certify emptiness. HEURISTIC extrapolation (±5 orders): at q = 31,
  ~10^16 leaves per pattern at D = 6 and ~10^21 at the old D0 = 11; at q = 44, ~10^24 at D = 6 and ~10^27 at D = 8.
  Times 10^11–10^14 open patterns per Tier-C vertex: infeasible on this formulation. The only remaining lever on the
  exponent is the Baker cap (Yu's sharper constants cut D by 1–2); a subexponential route needs a certificate rejecting
  whole Boolean families (Codex T2), untested at Tier-C scale. Small counts at k ≤ 11 come from digits bunching into
  5–10 equal-value classes all in the low window; whether Tier-C anchors bunch the same way is unmeasured.
- Codex Yu check (tier0-opt/math/codex-yu-check.md, independent extraction from the PDFs before reading yu-audit/):
  the 2007 constants AGREE (Thm II 10^9.3028, Thm 1 10^11.268, Thm 3 10^9.905, p.190 consequence 10^13.047; Y07
  case III, K = Q(i), d = 2, κ = 0); three 2013 constants were too optimistic in the Claude lane (2013 Thm 1 10^9.92,
  Thm 2 10^8.62, Main 10^9.32 / 10^8.02; the smaller 2013 bounds have proofs explicitly omitted in print, and 2013
  Theorem II's printed h^(1) is inferred to be a typo for h^(2)). So the PROVED-IN-PRINT route stands: Yu 2007
  Theorem II (Part II pp.260–279; "final details abbreviated", p.279) with Theorem 1 for dependent cases, log10 G′ =
  230.2 (k = 31) / 324.3 (k = 44) at a = 0, depth 5 / 7 — candidate Theorem U″ after interval-certified numerics.
  The 2013 rows of the Yu table (208.4 / 295.1 etc.) are withdrawn pending recomputation with Codex's constants.
- N3 (joint prefix/suffix lattice search, tier0-opt/math/breakthrough/n3-joint-search/NOTE.md): the pair test is sound
  (PROVEN-ON-PAPER given a log-floor assumption; planted S-units with n up to 10^281 digits recovered; perturbed
  inputs return empty; prototype on 9 small-vertex settings agrees with every recorded child), needs only
  2·log10 G′ pinned digits (tail fixes a), but the pair count is C(w,k)·W(M), independent of the split, with no hash
  join (the test is a lattice intersection, not an equality) and no partial-slab pruning: 10^58.7–10^79.6 pairs per
  Tier-C vertex (10^37–10^56 when fed by the level-96 sieve, within 10^2–10^3.4 of the sandwich's own count: the same
  computation in other coordinates). Break-even needs log10 G′ ≈ 20–26. KILLED as a Tier-C route.
- Fonga v2 bound (tier0-opt/v2bound/, NOTES.md has the swap procedure; not swapped): Fonga arXiv:2608.27802 Thm 4.1
  ported (Python + a 256-bit C kernel, ~3.5e7 nodes/s). Exact max v2 over zero-free integers with the given non-1
  multiset and any number of 1s; the old two_adic_bound takes a max over sub-multisets (old ≥ exact) and hangs at
  k ≥ 36 because its tail set explodes. Differential: paper's 4 examples (7, 13, 15, 9) and brute force on 11 small
  multisets agree; of 2,015 recorded multisets 1,670 equal, 345 lower (max drop 11), 0 higher; 162/162 recorded
  children pass; 8,244 of 8,807 zero-free S-units below 10^4000 confirmed, 563 undecided at the node cap (not a pass).
  Planted off-by-one mutants: 483 and 19 violations. Tier-C A values (max-k multiset per vertex): 120 (k = 34),
  120 (k = 31), 129 (k = 35), 152 (k = 42), 157 (k = 44); 2^24·3^6·7^6 (k = 36) unfinished, queued for 05:30 with a
  4-hour cap. A swap only narrows a's range (never drops a child); goldens and gate corpora that embed A would move.
  Single arXiv source; recursion's proof read, no gap found; not Lean-checked.
- Theorem U′ final stage (tier0-opt/cport/FINAL-STAGE-run.txt, NOTES-finalstage.md): U′ table k 1..24, a 0..24,
  interval-certified, U′ ≤ U at all 600 entries; the 43 hard survivors all CLOSED at depths 16×1 + 27×2 (min margin
  10^0.33 digits). Final stage on a fresh trees_mac snapshot: 137/137 vertices in the live files fully CLOSED;
  7,645 open patterns = 6,426 Lemma C depth 1 + 1,219 sandwich, 0 left. The sandwich closures rest on BK (2.2) as a
  weakening of Yu 2007 p.190 (printed without proof); the U″ lane (Theorem II, proved in print) is running to remove
  that dependence. PROVEN-ON-PAPER conditional on the quoted theorems; not Lean-checked.
- Blind cross-family check (tier0-opt/math/codex-blind/run-20261020-231459-760749): Codex's independent re-implementation
  from the hypotheses only agrees with SWAP 6 on 2,015,699/2,015,699 level-12 outputs (vertices 14336, 28672) and with
  Lemma C on 969/969 sampled representations; 8/8 planted points kept. Sample agreement, not proof.
- U″ candidate (tier0-opt/cport/NOTES-u2.md): CORRECTS the Yu entry above. The 2007 constant carries a factor e^n that
  the audit and the Codex check dropped; Theorem II is 10^10.606, and the certified U″ values are log10 G″ = 246.0
  (k = 31) / 345.0 (k = 44) at a = 0, not 230.2 / 324.3; depths stay 5 / 7. Built over Q(i) at 2+i; 43/43 gate
  (33 depth 1, 10 depth 2, margin +4.93); final stage 138/138 CLOSED, 8,027 patterns, 0 left. Awaiting chat OK.

## Corrections (2026-10-21 06:10, from the chat's RESULT-accidents.md 51f286a9)
- H1 / H10 / H16: the 23:25 correction above is itself wrong. The 42-accident prediction used the ⟨2,3,7⟩-conditional
  count instead of fixed a and applied no tail test; residue survival of uniformly random patterns is exactly uniform
  at levels 12/24/48 (obs/uniform 0.98–1.12, 2e7 samples per multiset, 4 multisets), and lifts of anchored parents are
  uniform too. Corrected prediction for s = 124416 at level 48: 0.13–0.21 accidents; observed 0, consistent with the
  uniform model. The whole sweep expects ~6 engine-visible accidents at level 48 and 5e-15 at 96, so it could never
  have seen one. Tier C expects 10^1–10^10 accidents per vertex after the tail. H1 is KILLED-with-mechanism; the
  conjecture "anchoring for q ≲ 22–26" is retired; H16's 1.2e-3 has the same omission. Anchor-first stays a forecast;
  no character-sum route certifies anchoring.
- B3's "a ≤ 40" caveat above does not apply: the chain is valid for any fixed a up to 160 (ledger, 2026-10-20).

## Tier B lane results (2026-10-21 07:30, tier0-opt/math/tierb-lift/; predictions registered 01:19 in PREDICTIONS.md)
- H12 (stage-ratio law): MEASURED on ~330 equations, k = 6–21, production with branch split. Lift 12→24 child tests per
  pattern grow x1.60 per digit (fit exp(-10.8 + 0.472k), 0.25 at k = 20), within x2 of P1 at k = 13. Level-12 survivors
  per pattern ~2e-5 for k ≤ 18, 1e-4–3e-4 for the all-2s multisets at k = 20–21: P1's 1/940 was WRONG by ~50x. Lift
  24→48 grows x1.67 per digit at 95–230 ns per child. Level 12 costs 5–10 ns per pattern-core, not < 1% of Tier B:
  H15's "< 1%" is REFUTED.
- H7 (join): SUPPORTED at level 24. lvlJ.c hashes the second child half on its residue mod 73 (or 73·137) against the
  exactly computed coset of K (order 2, or 68); survivors go through the unchanged lvlN test. Differential vs lvlN:
  97/97 equations byte-identical (96 non-empty); mutants 1 and 2 each caught on 3/3. Speedup x6 at ~2e3 children per
  parent, x11–14 at 6e3–2.2e4, flat x12–14 at k = 20; P4 (≤ x3) is KILLED. Level 48: 2 equations only (one with 0
  survivors on both sides), x1.4 and x3.0, mutant 1 caught on 0/2 — the level-48 join is NOT shown to gate.
- H13 (dual): SUPPORTED at level 12 only. dual12.c matches production on 4 multisets (2, 4, 4, 22 survivors, cosets
  identical); three mutants caught. Cost independent of N12, modeled ~1000x cheaper than level 12 at Tier B (35 ns step
  cost from small runs). At level 24 the dual loses (P3 holds), on paper only.
- Model (k > 21 extrapolated; A = 40 and a x3 level-48 join gain assumed): all 13 Tier B vertices 3.7e4 Mac-days with
  production vs 1.8e3 with dual12 + join24 + join48 (x21). Six smallest (k 20–26) 5–17 Mac-days each; k 25–29 400–1,300
  core-days each. P5 (none under 10 Mac-days) is REFUTED on the model for four vertices. Not run end to end through
  run_c.py; not adopted into the engine.

## N1 lane results (2026-10-21 07:45, tier0-opt/math/breakthrough/n1-boolean-cvp/; predictions registered 01:08)
- Boolean-CVP sandwich via 5-adic linearization: SUPPORTED as an exponent halving, REFUTED as polynomial in q. For free
  digits at positions ≥ s = 96E the congruence 2^a 3^b 7^c ≡ T(x) mod 10^K is one linear congruence mod 10^(K−s), exact
  iff K ≤ 2s − a (Theorem 1, PROVEN-ON-PAPER); the 5-adic log's second difference has valuation exactly p+q, so no affine
  map is exact past 2s (Prop. 1.2). The low half stays enumerated: E = ceil((D + a/96)/2) blocks. Dual-multiplier
  certificates never close a pattern with a genuine point in the Baker disc (Theorems 3–4, PROVEN-ON-PAPER). Nothing
  Lean-checked.
- Differential: reproduces SANDWICH-full.txt on all 43 keys (145 rows; nn and labeled sub-coset counts identical; 0
  inexact leaves); 28 depth-2 comparisons vs deepcut.py, 0 mismatches. Certificates alone close 43/43 (395 bases); 0/173
  bases certify one depth short. Planted points: 0 false closures (57 + 21 small-scale, 8 Tier-C-scale, 12 genuine
  S-units).
- Tier C, one pattern (Codex pattern, q = 31, 10 occupied classes, k = 31, log10 U = 281.51): all 440,640 depth-3 bases
  at D = 6 certified, 0 failed (Cairn re-summed family_0..5.log DONE rows: 93,312 + 46,656 + 93,312 + 82,944 + 41,472 +
  82,944). 3.77 h on one Python core against ~3.4 core-years for pure enumeration. Certificates still hold at
  log10 U = 304. That PATTERN closes at k = 31 conditional on Lemma C, the U bound and the pattern list; not a vertex
  census.
- k = 44 (synthetic, 13 extra free digits): E = 4/D = 8 certifies 0/16; E = 5/D = 10 certifies 6/6 but needs ~1.1e11 bases
  (~3,000 core-years). Base count N_E ≤ 5184^E: exponential in occupied classes × depth. Registered misses: P5/P8 band
  (mean −0.47 vs [−0.45, −0.05]); "N_8 > 10^25" wrong (2.8e13).

## Lift ideation round (2026-10-21 16:45, tier0-opt/math/lift-ideation/; predictions registered 15:19, unedited)
- Engine defect found: tier0/lvlN.c KT[64] overrun for A ≥ 64 (see ledger 16:40); audit lane running.
- (a) join48 on the KT[512] source: identical to production on 213/214 equations (the 214th is a KT equation, where it matches the fixed build), x1.92 (predicted x2.0, HELD); strengthened mutant caught 173/173, 2^a→1 mutant 172/173 (one equivalent mutant, recorded KILLED per the registered kill); the old j%8 mutant is caught 0/173 and is useless.
- (b) three-way join at 2^{(k+1)/3}: KILLED — identical output, meet ops x1.20 of two-way, CPU unchanged, slope 0.48–0.67 not 1/3.
- (c) Metal prefilter: identical 40/40 (L24), 213/214 (L48); x18.8 over lvlN at L24 (window held), median x4.6 at L48 (setup-bound, MISSED) but x150–166 on the two largest equations; saturated 2.7e9 / 1.09e10 children/s.
- (d) rank-0/1 fast path: KILLED as a speedup — 0.03% of parents decided, no rank-0 parent; no survivor dropped.
- (e) adversarial vertex: MISSED as framed (spread at equal k ≤ x2.2); the budget is the adversary — vertex 1783627776 alone ~760 GPU-h nominal, ~1,900 at p95.
- CUDA model (modeled, H100 SXM, 2.69 USD/GPU-h, 16.7x the M5's measured 1.0e12 IMAD/s at efficiency 0.6): Tier B 2,085 GPU-h nominal (band 1,100–6,000; ~5,600 USD, band 2,300–24,000; 261 h on 8 GPUs); level 12 is 41%; the 4e13-line host survivor stream must be consumed on device. Porting effort is the lane's estimate. The lane's model.py rerun with defaults gives 5.29e3 Mac-days, not the Tier B lane's quoted 1.8e3 — unreconciled.
- Recommended order: KT fix (owner's go, gated), then join24 as drop-in (~x9 CPU) with a gate of ≥ 200 equations including every A ≥ 64 one.

## Queue claims (LOOP-PROTOCOL.md §3–4; tier0/LOOP-PROTOCOL.md md5 df7135bd)
| id | owner | step reached | prediction | kill condition | data |
|---|---|---|---|---|---|
| X2 | Cairn | 3 (prediction tested; FALSIFIED — a step-7 negative result) | ≥ 99 % of level-24 descent survivors are anchored shadows at k ≥ 13 (PREDICTIONS.md e3d4618b, registered 20:44, unedited) | shadow share < 99 % at k ≥ 13, or accidents measurably below the uniform model | the 228 gated equations (tier0-opt/join24swap/gate.py), fixed lvlN; result tier0-opt/math/x2-survivors/RESULT.md 052add30: shadows 438/1,140 = 0.384 [0.356, 0.413] at k ≥ 13; accidents/model 1.018 [0.979, 1.061] (residue stage), 1.000 [0.930, 1.075] (tail stage) — uniform, no crack; do not retry without new data |
| A1 | Cairn (runs Codex blind) | 1 (running) | the pipeline never closes a planted genuine child (G0 = 117649 under 1512, G1 = 6174 under 168, G24 = 16777216 under 24696, withheld from known) nor the synthetic 10-adic point S384 within a bound containing it; contradictory negative controls close | any plant closed, or a withheld child not rediscovered, or a negative control kept | tier0-opt/redteam-plants/driver.py b77d4f84 (Codex design, codex_report.txt); run 1 in progress — run_c withheld 3/3 PASS, G132 residue path 4/4 PASS, S384 Lemma C depths 1–2 PASS so far; native lvl12/lvlN stages ERRORED on a driver bug (json.dumps of PosixPath in call()); run 2 (driver_native.py ea392b4e = fixed driver + stage selector, tier0/lvl12 e547259e, lvlN b43dad7d, run2/run2.log): native stages 15/15 PASS (G0, G1, G24 × lvl12 both branch modes + lifts 24/48/96, each the plant's single OPEN row with its coset), parity controls 15/15 closed; planted negative (plants moved off their coset, run2/driver_neg.py) FAILs as it must; `known` withholding not exercised by native stages |
| L2w | unclaimed (parked) | 4 (mechanism measured) | a tail-digit window prune on join24's A half (Codex lvl24_blind `build_window`/`window_pass`, applied before the K-loop) cuts join24's level-24 CPU on the 228 by 12–17 s of ~58 s (bound 22.9 s), almost all on 9437184_* | transplanted join24 not byte-equal on the 228, or saving < 5 s, or a loss on 9633792_* without a C0·K gate | measured on 9437184_22222222222222222266: probes 388M → 196M at the same key set, post-meet work 59.6M → 27M; blind's window costs 8 µs/parent and loses on 9633792_*; scratch evidence in the session scratchpad lever24/; parked until join24 is swapped and a profile shows level 24 still dominates the per-vertex cost; the stderr `tail-dead` counter would drop, so its gate comparison must change |
