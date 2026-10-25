# H1 (Anchoring Lemma): mechanism, data, obstruction, counterexample

Tags: PROVEN-ON-PAPER (my argument, unchecked by anyone else), STRONG-EMPIRICAL, CONJECTURE, HEURISTIC.
Nothing here is PROVEN. Files in this directory are the evidence; no existing file was edited.

## Verdict

H1 as stated (every pattern open at level 96 is anchored with explicit small height) is
- FALSE for arbitrary equations: explicit engine-OPEN pattern with no small anchor (section 4). PROVEN-ON-PAPER plus an exact computation.
- Its height form "<= 10^10" is already killed by the recorded data (section 2): 90 patterns, 17 anchors exceed 1e10, max 1.0e14.
- CONJECTURE (restricted form): holds for equations with q <= ~22 non-1 digits. The uniform-residue accident model (section 3) that predicted failure at q >= ~26-30 was TESTED in section 7 and REFUTED at q = 14 level 48 (predicted 42 accidents, observed 0 of 17 survivors), so the Tier-C failure claim is withdrawn: there is no evidence either way at Tier-C scale, only the q = 100 construction.

## 1. Mechanism

Notation: V = R_nu + sum (d_j-1) 10^{e_j} with e_j in [0,96); R_96 = 21 Q exactly (v_3 = v_7 = 1, no other prime power: LTE); the sieve uses the 20 primes of 10^96-1 other than 2,3,5,7, so it is a congruence mod Q only.

A1 (PROVEN-ON-PAPER). For 0 < y < R_96: y + k R_96 = V has an integer solution iff y = V mod R_96, and then 0 <= k <= V/R_96 <= 1 + 8q. So the exact identity carries no information beyond a congruence; "small representative implies exact identity" is true, but only with the extra condition y = V mod 21, which the sieve does not test. Seam: for 3126 of the 3154 recorded triples the sweep stores only (a, y), not (nu, eps), so the 21-part is checked for the 27 positioned rows (27/27, all k = 0) and, for the rest, only that SOME representation of y with multiset M exists (run_exact).

A2 (PROVEN-ON-PAPER, Lean for the congruence part: `RepunitCongruence.candidate_modEq`). Anchored implies open: every candidate is = y mod R_96.

A3 (PROVEN-ON-PAPER). No pigeonhole, Minkowski or covering-radius argument can force a small representative. Computed (density.py): index of Lambda_96 = 2.80999e56 (matches DEEPCUT), shortest vector 7.85e27 (reproduced), so lambda_2 ~ 3.6e28 and the covering radius is >= ~1.8e28. A box of height T in (b,c) meets every coset only when T^2 >~ 2.8e56, T >~ 1.7e28, giving y with ~1e28 digits. S-units below 10^98 per fixed a number ~1.2e4, covering a fraction ~4e-53 of the cosets. A small coset point is therefore never forced; it is a coincidence of probability ~1e-52 unless the pattern was built from it.

A4 (HEURISTIC, structure). The open set at level 96 is the union of (i) anchored patterns: V built from a small S-unit y, open with certainty by A2; (ii) accidents: V lands in 2^a<3,7> mod Q by chance, probability rho = |H|/Q = 2.81e56/(R_96/21) = 5.3e-38 per pattern (the per-pattern probability that a uniform residue lies in a subgroup; my first table used |H|/phi(Q) = 7.3e-38, which is 1.37x too high, Codex's figure is the correct one). Expected accidents per equation: mu = N_96 * rho with N_96 = 96 * prod_d C(95+m_d, m_d). H1 holds exactly when mu << 1. Accident cosets have nearest point ~1e27, so they never have a small anchor (A3).

## 2. Data (STRONG-EMPIRICAL)

Registered in NOTES.md before running. Command run as specified: `classify_open.out`.
- 3154 distinct (vertex, multiset, anchor) triples from 6990 recorded open patterns (open count equals exceptional-list length in every row, so no open pattern lacks a recorded coset point): SELF 51, CARRY 2636, zero-digit anchor 467 (the script labels these UNANCHORED, meaning "y has a 0 digit", not "no anchor"); NOT-S-UNIT 0, ZF-OTHER 0.
- The CLI never calls `run_exact`, so no "NO EXACT IDENTITY" line can ever print. I called it via run_exact_driver.py: 3153 ok, 0 fail. specific_check.py (own positions, the 27 rows that have them): 27/27 identities hold, all k = 0.
- Anchors: 210 distinct, max 100461232161612 = 2^2 3^21 7^4; 501 patterns exceed 1e9, 90 exceed 1e10 (17 anchors), 10 exceed 1e13. The "1134213192" cap in OPEN-PATTERNS is stale.
- q of open patterns is 2..14. Expected accidents summed over all 1,628 recorded equations: 2.0e-13 (model_check.out). So 0 unanchored was predicted by the accident picture as well: the data are uninformative about H1 at large q.
- Density model validation (model_by_q.out, HEURISTIC with partial support): predicted random survivors at level 12 vs engine counts: obs/pred = 1.09 (q=2), 0.82 (q=3), falling to 0.05-0.14 for q >= 6 (the engine's prefilters and zero-digit/tail kills, which the model omits, so the model is an upper bound). At level 24 obs/pred = 11 (q=7), 2.1 (q=8), 0.44 (q=9), 0.09 (q>=10): anchored excess at small q, random-dominated at larger q. Level-24 vs level-12 scaling holds across a 4e-6 factor. Level 48 (obs 7952 vs predicted random 6.5) is anchored-dominated, so the model is not validated where it matters (96).

## 3. Codex idea 6: the accident heuristic (answer)

Arithmetic: confirmed. Using N_96 as in A4 and the true index/phi, mu per equation at 2/3 twos, 1/3 threes: q=24: 1.4e-5; q=30: 2.3; q=36: 1.5e5; q=40: 2.2e8; q=44: 1.35e11 (mu_table.out; times 0.73 for |H|/Q). Codex's 1.4e3-1.1e11 per fixed a for the Tier-C domains is consistent (they use |H|/Q, I earlier used |H|/phi).
Does descent or the tail test remove them? Evidence from the constructed accident (section 4): classify() returned OPEN and descend() returned ('OPEN', set()) for q = 100, K = 5. The classify tail test constrains only the lowest K <= 5 digits (K is fixed by Lambda_96: image index 4*5^4 and 2^8) so passes an accident with probability ~0.19^5 for small q but ~0.4^5 ~ 1e-2 for q ~ 40 (each position is occupied with probability ~q/96): at most a 1e2-fold reduction. Lemma C depth 1 survives a case with probability ~1.6e-6 over 2^q copy choices, so it kills essentially nothing once 2^q >> 6.4e5 (q >~ 25). Hence accidents are not removed by the existing level-96 machinery at Tier-C q. They are removed only by the Baker sandwich (G(k) ~ 10^(11.5+13.9k), depth ~13 at k = 44), the cost RESULT-anchorfirst already identifies. So the open set at Tier C is "anchored + accidents", and anchor-first enumeration is an undercount by an unknown (heuristically comparable or larger) factor. Caveat: mu is per (pattern, a); loop over a multiplies it by up to A+1.
Can the small-vertex data distinguish? No: both pictures predict 0 accidents for q <= 14 (mu <= 1e-13). A discriminating test exists at level 48, where mu_48 = 5e2 (q = 14, M = 2^9 3^5), 2.5e4 (q = 16): run the engine on one q = 14-16 equation to level 48 and count survivors whose nearest coset point exceeds 1e6 digits. Not run (budget). Prediction: ~mu_48 * 0.1 accidents, versus 0 under H1.

## 4. Adversarial construction (PROVEN-ON-PAPER + exact computation)

counterexample.py, counterexamples.json, counterexample.out, descend_try.out.
Take u = 2^a 3^B 7^C with B, C in [150,260] (u has > 200 digits). Let V = u mod R_96, nu in [0,96), Z = V - R_nu, one entry per nonzero decimal digit of Z (a digit 9 splits into d = 9 and d = 2). Then V = R_nu + sum (d_j-1)10^{e_j} exactly, V = u mod R_96 (asserted), so the pattern passes all 20 prime congruences with coset (B,C) + Lambda_96. Selection: tail test only. Result: first hit a = 0, B = 156, C = 214 (u: 256 digits), nu = 0, q = 100; tier0.classify returns OPEN with K = 5; tier0 descend returns ('OPEN', set()). The coset's other points are >= 7.85e27 away, so the only S-unit y with that residue in any range < 10^(1e27) is u itself, with 256 digits > 98: no exact identity with any S-unit of height < 10^98 exists (an identity needs y <= V < 10^96). 477 candidate patterns were found for a = 0 alone. Caveat: q = 100 is far outside any program vertex (s = product of digits is not a tracked vertex); this refutes the unconditional statement and shows the mechanism, not a Tier-C counterexample. A Tier-C-scale (q <= 44) accident would need ~1/rho = 2e37 patterns tested (the membership map is multiplicative, V additive: no meet-in-the-middle I could find): not attempted, infeasible on one core.
A first run with B, C in [40,240] produced u with 55 digits (< R_96), which are anchored, not counterexamples; I caught it from u_digits and reran.

## 5. Lean-ready statements (arithmetic core only)

```lean
theorem exact_identity_iff {L y V : ℕ} (hyV : y ≤ V) :
    y ≡ V [MOD R L] ↔ ∃ k, V = y + k * R L

theorem k_bound {L q : ℕ} (d : Fin q → ℕ) (hd : ∀ j, d j ≤ 9) {ν : ℕ} {e : Fin q → ℕ}
    (hν : ν < L) (he : ∀ j, e j < L) :
    (R ν + ∑ j, (d j - 1) * 10 ^ e j) / R L ≤ 1 + 8 * q
```
Conditional H1 (restricted form, CONJECTURE until the hypothesis is discharged): for an equation with N_96(M) * |H|/Q < 1 the expected accidents are below 1, which is a probabilistic claim and not a Lean theorem. The provable core is: Open96(V,a) := exists b c, 2^a 3^b 7^c = V [MOD Q] ; Anchored(V) := exists y S-unit, y < R 96, y = V [MOD R 96] ; the three Lean items are `candidate_modEq` (exists), `exact_identity_iff`, and the 21-part: y = V [MOD 21] added to a mod-Q congruence gives mod R_96 (Nat.ModEq.of_coprime, R_96 = 21 Q, gcd(21,Q) = 1). The counterexample in section 4 is a `decide`/`norm_num` certificate (256-digit numbers, 20 prime congruences); the bound for "no S-unit in the coset below 10^98" needs the Lambda_96 shortest-vector claim, which is a computation not in Lean.

## 6. Weakest extra hypothesis that closes H1

(Q-ANCHOR) "No pattern value V of the equation lies in 2^a<3,7> mod Q except V = y mod R_96 for an S-unit y < R_96." It is equivalent to H1, so the weakest independent form is the counting one: sum over a of N_96(M) * |H|/Q < 1/2, true for q <= ~24 (2/3-2s shape) and false from q ~ 28. No proof of it beyond counting is known to me; a proof would have to control the additive structure of V against the multiplicative subgroup H (a character-sum/equidistribution bound for sparse-digit sums modulo Q), which I have not attempted.

## 7. Decisive test at level 48 (STRONG-EMPIRICAL for this equation; registered in NOTES.md before the run)

Files: l48_driver.py (patches levels to 12,24,48 in the engine's own run_c.run, read-only use of tier0/), l48_run.log, l48_result.json, l48_classify.py/.out, l48_model_vs_obs.out.
Equation s = 124416, M = 2^9 3^5 (q = 14, A = 49), 298 s on one core.
- Level 12: 8,803,791,360 patterns, 4,544,237 survivors. Level 24: 3,510,549,840 children, 1,097 survivors. Level 48: 13,874,912 children, 17 survivors, all engine-OPEN.
- All 17 anchored (nearest coset point small, exact identity found by run_exact): anchors 13122, 111132, 133923132. Accidents: 0.
- Registered prediction of the accident picture: 42 (plausible 20-100). Observed 0. The accident picture, as a uniform-residue model, is refuted for this equation. Anchoring picture: 0, observed 0.
- Where the uniform model fails: predicted hits per a at levels 12/24/48 are 1.8e7, 5.3e5, 5.0e2; observed survivors 4.5e6, 1.1e3, 17 (the observed survivors at 48 are all anchored descendants). Even summing over no a-multiplicity the model overshoots by >= 480x at level 24 and >= 29x at level 48. Survivors of the lower levels are far from uniform in the level-L subgroups (digit-structured values, the y = 0 mod p and prefilter kills), so N_96 * rho_96 is not an estimate of accidents. Sections 1 A4 and 3 and mu_table.out should be read as an upper bound of an invalid model, not as a forecast.
- Seam: only the 17 engine-OPEN patterns were classified; coset survivors killed by the tail test or descent are not retained by the driver (level 24 lost 162, level 48 none lost). With 0 of 17 survivors at 48 not anchored the test says nothing about q = 100, where the explicit construction (section 4) stands.
- Sibling retrodiction agrees: 7 q = 13-14 equations, 46 level-48 survivors, level-96 counts equal, 0 accidents.
Net status of H1: unconditional statement false (section 4); at q <= 14 every open pattern seen (3154 triples plus 17 here) is anchored; no evidence that accidents appear before q ~ 100, and no proof they do not. CONJECTURE.
