# Accidents: are level-96 residue survivors rarer than uniform? (No. The uniform model is exact at every level we can test.)

*2026-10-21, scout `accidents` (`/home/claude/night/accidents/`). Code: `structure.py` (group/index structure per level),
`tables.py` (character tables for the membership test, with BFS cross-checks), `acc.c` (C sampler: uniform labelled
level-96 patterns, exact residue test at 12/24/48/96 via l-primary characters, lift enumeration 12→24→48→96, a-class),
`control.py` (positive/negative controls), `analyze.py` (rates, cluster-robust intervals, a-class, exact-anchor test,
engine tail test + descent via `tier0v2.classify`/`descent.descend`), `coset.py` (Λ'_L, K*_L, (b,c)-coset of a pattern),
`anchortest.py` (ordinary and half anchors), `anchored_pats.py`/`anchored_many.py` (all anchored level-96 patterns of a
multiset on given / all small S-units, by a carry DP), `distinct_global.py` (distinct lift values), `engine_counts.py`
(the recorded sweep vs the model), `tierc_forecast.py`. Logs: `run_*.log`, `run_*.analysis.txt`, `anchrun*.log`.
Calibration: every number below is an exact computation or a Monte-Carlo estimate with the stated interval; the
"uniform model" is a heuristic, and the verdict about Tier C is an extrapolation of a model that was tested only up to
level 48 (stated as such). Total CPU ≈ 1 h 55 min, one process at a time (the C stages dominate).*

## 0. Verdict in five lines

1. **The residue survival test is uniform.** For uniformly random level-96 patterns of four multisets (q = 11, 11, 13, 14)
   the survival probability equals |H_L|/Q_L at level 12 (to 0.1 %), at level 24 (direct: 0.96–1.06×; via lifts of level-12
   survivors: 0.996 ± 0.011× pooled) and at level 48 (via lifts of level-24 survivors: 1.12 ± 0.10× pooled, 1275 survivors).
   Nothing is suppressed; if anything the point estimate at 48 is slightly *above* uniform.
2. **Lifts of anchored parents are uniform too** (mechanism (c) refuted): 4304 anchored level-12 patterns of 2^9·3^5
   lifted to 24 produce 641 distinct non-anchored survivors against 644 predicted; their level-24 reductions lifted to 48
   produce 5 against 3.1 predicted. Earlier "0 of 6 expected" readings were an artefact of counting duplicate lift values.
3. **The H1-REPORT §7 "uniform model overshoots by 29–480×" is an accounting error, not a phenomenon**: it used the
   <2,3,7> index instead of the fixed-a index (×75 at level 24 → 48) and ignored the K* = 3/4/5-digit 10-adic tail test
   (×~0.1 per new pinned digit). With both, the uniform model predicts for s = 124416, M = 2^9 3^5: 2.7–4.6 k survivors at
   level 24 after the tail test (observed 1 097, the rest is descent) and **0.1–0.2 accidents at level 48 (observed 0)**.
4. **Where the index lives (mechanism (a))**: at every level only the l-primary components l = 2, 3, 5, 11 of
   G_L = (Z/Q_L)^* have index > 1; at level 96 the index 4.35×10^31 of <2,3,7> is 2^68 · 3^11 · 5^4 · 11^3, and the index
   1.38×10^37 of <3,7> (fixed a) is 2^75 · 3^13 · 5^6 · 11^4. The 16 other prime-power parts of the p−1 impose nothing. But the
   measured rates show the pattern values see these 2-/3-/5-/11-power-residue conditions as independent: no suppression.
5. **No proof route.** Accidents at Tier C are expected in numbers 1.7×10^5–1.6×10^13 per vertex before the 10-adic tail
   test and ≈ 10^1–10^10 after it (Table 8), 10^-11–10^-4 of the anchored count. A character-sum / large-sieve bound can only
   prove equidistribution (that accidents *exist* in the predicted number), never their absence, and the only exact
   route is the dense DP over Z/Q_96 (10^94 cells). **Anchor-first cannot be turned into a certificate by excluding
   accidents.** The open set at Tier C is anchored patterns plus a thin (10^-4–10^-6 relative) but absolutely large
   (≫ 1) population of accidents that look, to every modular/10-adic test, exactly like the q = 100 construction.

## 1. Formalization

Level L ∈ {12, 24, 48, 96}: P_L = primes of 10^L − 1 other than 2, 3, 5, 7 (5, 8, 11, 20 primes; Q_L = ∏ P_L is squarefree:
log10 Q_L = 9.72, 21.72, 45.72, 93.72). G_L = (Z/Q_L)^*, H_L = <2,3,7>, H'_L = <3,7>. A level-L pattern P = (ν, {(d_j, e_j)})
has value V_P = R_ν + Σ (d_j − 1) 10^{e_j}; **S_L** := V_P mod Q_L ∈ H_L (this is "V mod p ∈ <2,3,7> for all p" taken jointly;
V ≡ 0 mod p counts as failure); **S'_L(a)** := V_P ∈ 2^a H'_L (the engine's (a, pattern) survival; a is determined modulo
ord_L := |H_L|/|H'_L| = 12, 900, 19 800, 316 800, so with a ≤ A at most one a is admissible from level 24 on and only a
fraction (A+1)/ord_L of S_L-survivors has an admissible a). **Anchored**: V_P = y + k R_L with y an S-unit, 0 ≤ k ≤ 8q+1
(OPEN-PATTERNS (†)); **half-anchored** (new, §4.4): 2^J V_P ≡ y (mod R_L) with 2^J ∤ y (a-class a_y − J < 0, never admissible).
**Accident**: S_L-survivor that is neither. Uniform model: P(S_L) = ρ_L := |H_L|/Q_L, P(S'_L(a)) = ρ'_L := |H'_L|/Q_L, and
P(S_{2L} | S_L) = ρ_{2L}/ρ_L.

**Table 1 — group structure (structure.py, exact).**

| L | |H_L| | [G_L : H_L] | ρ_L = |H_L|/Q_L | ρ'_L (fixed a) | ρ_L/ρ_{L/2} | ρ'_L/ρ'_{L/2} | ord_L(2) | components with index > 1 (l: index of H_L / of H'_L) | K*_L |
|---|---|---|---|---|---|---|---|---|---|---|
| 12 | 1.07e8 | 40 | 2.021e-2 | 1.684e-3 | – | – | 12 | 2: 8/32, 5: 5/5, (3: 1/3) | 3 |
| 24 | 3.03e16 | 1.38e5 | 5.725e-6 | 6.361e-9 | 2.833e-4 | 3.777e-6 | 900 | 2: 1024/4096, 3: 27/243, 5: 5/125 | 4 |
| 48 | 4.12e34 | 9.56e10 | 7.796e-12 | 3.937e-16 | 1.362e-6 | 6.189e-8 | 19 800 | 2: 2^20/2^23, 3: 729/6561, 5: 125/3125, 11: 1/11 | 5 |
| 96 | 8.90e61 | 4.35e31 | 1.683e-32 | 5.311e-38 | 2.158e-21 | 1.349e-22 | 316 800 | 2: 2^68/2^75, 3: 3^11/3^13, 5: 5^4/5^6, 11: 11^3/11^4 | 5 |

(ρ'_96 = 5.311e-38 reproduces H1-REPORT's per-(pattern, a) figure; the task's "|H| ≈ 10^39" is not a quantity that
occurs — |H'_96| = 2.81e56 is the index of Λ_96, |H_96| = 8.9e61.) K*_L = digits pinned 10-adically on the fixed-a coset
(`coset.py`, = tier0v2.ten_adic_K): 3, 4, 5, 5 — the level-96 lift adds residue selectivity (×1.3e-22 per a) but no new
pinned digit. Why only l = 2, 3, 5, 11: |H_l| ≤ (max_p l^{k_p})^3 because H_l has 3 generators, while |G_l| = l^{Σ k_p};
a prime l dividing a single p − 1 has index 1 unless 2, 3, 7 are all l-th powers mod p, which never happens here. So "V
mod p ∈ <2,3,7> for all 20 primes" is **equivalent** to 68 binary, 11 ternary, 4 quinary and 3 undenary character conditions
(the annihilator generators in `tables.json`: 18 + 8 + 4 + 3 at level 96), and the membership test in `acc.c` evaluates
exactly these (checked against BFS-built H_l at levels 12/24 and against 200 random S-units and 10^4 perturbed patterns,
`control.py`; indices from the annihilator lattices equal Table 1's).

## 2. Sampler

Labelled uniform patterns: ν ~ U[0,96), e_j ~ U[0,96) i.i.d. for the q digits of M (repeated residues allowed, as in
the engine's pattern space). Stage A: 2×10^7 direct samples per multiset, nested tests at 12, 24, 48, 96. Stage B: all
2^{q+1} lifts (ν + 12t_0, e_j + 12t_j) of a reservoir of level-12 survivors, tested at 24 — a uniform sample of level-24
patterns conditioned on level-12 survival. Stage C: all lifts to 48 of the level-24 survivors (up to 3×10^8 tests).
Stage D: all lifts to 96 of every level-48 survivor. Intervals: Poisson for direct counts; for the lift stages the
labelled lifts of one parent come in clusters (permuting identical digits gives the same value), so the interval is
computed with parents as clusters, and the rate over *distinct multiset lifts* (2∏(j+1) per parent) is given as well.
Multisets: 2^9 3^5 (s = 124416, the H1 §7 equation), 2^9·3·9 (s = 13824), 2^6 3^2·4·6·7 (s = 96768), 2^9 3^3·7 (s = 96768).

**Table 2 — survival vs uniform (obs/uniform in parentheses; 95 % intervals).**

| M (q) | P(S12) direct | P(S24) direct | P(S24 \| S12) lifts | P(S48 \| S24) lifts | P(S96 \| S48) lifts |
|---|---|---|---|---|---|
| 2^9 3^5 (14) | 404251/2e7 = 2.021e-2 [2.015e-2, 2.027e-2] (1.000) | 110/2e7 = 5.50e-6 [4.47e-6, 6.53e-6] (0.961) | 2.823e-4 ± 7.9e-6 (0.996 ± 0.028) | 1.447e-6 ± 2.7e-7 (1.06 ± 0.20) | 0/1.42e7 (uniform expects 3e-14) |
| 2^9·3·9 (11) | 399412/2e7 = 1.997e-2 [1.991e-2, 2.003e-2] (0.988) | 114/2e7 = 5.70e-6 [4.65e-6, 6.75e-6] (0.996) | 2.889e-4 ± 6.3e-6 (1.020 ± 0.022) | 1.673e-6 ± 3.4e-7 (1.23 ± 0.25) | 3/8.27e5, all anchored (§4.4); 0 accidents (expects 2e-15) |
| 2^6 3^2 4 6 7 (11) | 403658/2e7 = 2.018e-2 [2.012e-2, 2.024e-2] (0.999) | 116/2e7 = 5.80e-6 [4.74e-6, 6.86e-6] (1.013) | 2.777e-4 ± 4.5e-6 (0.980 ± 0.016) | 1.397e-6 ± 2.6e-7 (1.03 ± 0.19) | 3/6.64e5, all (half-)anchored; 0 accidents (expects 1e-15) |
| 2^9 3^3 7 (13) | 404089/2e7 = 2.020e-2 [2.014e-2, 2.026e-2] (1.000) | 121/2e7 = 6.05e-6 [4.97e-6, 7.13e-6] (1.057) | 2.802e-4 ± 6.7e-6 (0.989 ± 0.024) | 1.590e-6 ± 2.0e-7 (1.17 ± 0.15) | 0/7.82e6 (expects 2e-14) |
| **pooled** | 2.014e-2 (0.997) | 461/8e7 = 5.76e-6 (1.006 ± 0.09) | 113 313/4.01e8 = 2.823e-4 (**0.996 ± 0.011**) | 1 275/8.37e8 = 1.524e-6 (**1.12 ± 0.10**) | 0 accidents / 2.4e7 |
| uniform | 2.021e-2 | 5.725e-6 | 2.833e-4 | 1.362e-6 | 2.16e-21 |

Rates over distinct multiset lifts: 12→24: 1.007, 1.013, 0.987, 0.999; 24→48: 0.90, 1.16, 1.04, 1.12 (same conclusion).
Chain products reproduce the direct rates (P(S24) chain/uniform = 0.993, 1.004, 0.980, 0.989).

**Table 3 — a-class of survivors** (x = a mod ord_L; the engine's admissible fraction is #{a ≤ A : a ≡ x}): uniform at
every level — mean x/ord = 0.456–0.462 at level 12 (ord 12, histogram flat: 248, 265, 224, 283, 245, 248, 250, 246, 243, 256, 243,
249 for 3000), 0.497–0.502 at 24 (fraction x ≤ 49: 0.0546–0.0566 vs 50/900 = 0.0556; x ≤ 150: 0.170–0.172 vs 0.168), 0.43–0.54 at
48 (1275 survivors, x ≤ 150 in 0.0–1.5 % vs 0.76 %). So the engine's (a, pattern) survivors are a (A+1)/ord_L fraction of the
S_L survivors, exactly as the fixed-a index says; **this factor (12/900 = 1/75 at the 12→24 step for A ≈ 49, then
900/19 800 = 1/22, then 19 800/316 800 = 1/16) is what H1-REPORT §7 omitted.**

## 3. Mechanisms

**(a) Correlated residues of sparse-ones numbers.** The index structure is as concentrated as the task suspected (only
l = 2, 3, 5, 11; 2-part dominant; the 9901-coupling at level 12 generalizes to the 2-parts of all 20 primes at 96), but the
pattern values are *not* biased with respect to these characters: survival = 1/index at 12, 24 and 48 to within the
intervals (Table 2), for the joint condition and for the a-class. (The dpcount scout saw the same at level 12 to 0.2 % on
the Tier-C multisets.) Nothing changes in kind between the 24→48 and 48→96 steps (new primes with ord_p(10) = 16 and 48
versus 32 and 96; new 2-/3-/5-/11-characters), so there is no reason to expect the 48→96 conditional to deviate.
*Refuted as a suppression mechanism.*

**(b) The 10-adic descent (K* ≤ 5) kills unanchored survivors.** True, large, and *explicit* — but it is a kill of
accidents, not a reason they are rarer than uniform, and it is hereditary (a child's pinned digits extend the parent's).
Measured on random residue-survivors with a = x (`analyze.py`, tier0v2.classify rule per digit; a ≥ K* in most cases, as
for Tier C where A ≥ 118):

| L | K* | P(first 1, 2, 3, 4, 5 pinned digits consistent) — 2^9 3^5 | 2^9·3·9 | 2^6 3^2 4 6 7 | 2^9 3^3 7 | engine-OPEN after descent |
|---|---|---|---|---|---|---|
| 12 | 3 | .151, .031, .0047 | .154, .029, .0053 | .152, .026, .0067 | .153, .032, .0093 | 5/1500, 3/1500, 2/1500, 4/1500 (1.3–3.3e-3) |
| 24 | 4 | .071, .015, .0053, < 7e-4 | .086, .023, .0027, < 7e-4 | .070, .013, .0020, < 7e-4 | .083, .023, .0067, < 7e-4 | 0/1500 each (x ≤ 49 subsample: 0–1/1500 pass tail, 0 OPEN) |
| 48 | 5 | .009, 0, … (434) | .079, .040, .010, 0, 0 (202) | .068, .025, 0, … (162) | .044, .006, 0, … (477) | 0/1275 |

Per new pinned digit the pass rate is 0.15–0.35 (the first digit is lower, 0.07–0.15, because a ≥ 1 forces an even
digit which must be a 2/4/6/8 of M at residue 0). The engine's own level-12 statistics agree: for the k = 11–14 equations
(a,pattern) pairs/pattern = 7.5 % (uniform 2.02 % × (A+1)/12 = 7.6 % for A = 44) and tail-dead = 99.4 %. For the 5-digit
tail at level 48/96 with a ≥ 5 the pass rate is ≈ 10^-4 (product of the per-digit rates; 0 of 1275 observed, < 3e-3).
Anchored patterns pass by construction (their anchor's digits are the tail) — so the engine's survivors are
anchored-enriched by ~10^4 relative to residue survivors, which is the whole content of "the sweep's open set is anchored".

**(c) The chain of conditional probabilities is not independent.** Tested two ways. (i) For random parents, Table 2:
conditionals at 1.00 and 1.12 × uniform. (ii) For *anchored* parents (the actual ancestors of the open set): all anchored
level-96 patterns of 2^9 3^5 on the 5424 S-units y < 10^15 with k ≤ 2 (4304 patterns, `anchored_many.py`), reduced to level
12, all 2^15 lifts tested at 24; reduced to 24, all lifts tested at 48; and the same for the sweep's 285 recorded anchors
with k ≤ 12 on all four multisets (`anchored_pats.py`). Counting *distinct lift values globally* (the lift sets of
different anchored parents overlap heavily, and labelled lifts repeat values; `distinct_global.py`):

| parent set | parents (distinct values) | distinct lift values | uniform expected accidents | observed accidents | anchored lifts found |
|---|---|---|---|---|---|
| 2^9 3^5, y < 1e15, k ≤ 2, level 12 → 24 | 4304 | 2 273 453 | **644** | **641** (and 385 anchored) | – |
| same, level 24 → 48 | 4304 | 2 273 471 | 3.1 | 5 | 4304 (one per parent) |
| 2^9 3^5, sweep anchors, k ≤ 12, 24 → 48 | 641 | 385 656 | 0.53 | 0 | 641 |
| 2^9·3·9, sweep anchors, 24 → 48 | 82 | 32 224 | 0.04 | 0 | 82 |
| 2^6 3^2 4 6 7, 14 anchors, 24 → 48 | 770 | 181 845 | 0.25 | 0 | 770 |
| 2^9 3^3 7, 6 anchors, 24 → 48 | 124 | 154 085 | 0.21 | 0 | 124 |
| anchored level-48 parents, 48 → 96 (the six completed sets above, 1 724 parents with overlaps, plus the first 885 of the y < 1e15 set before that stage was cut for budget) | 2 609 | ≈ 1.5×10^6 | 3×10^-15 | 0 | 2 609 (exactly one surviving lift per parent) |

Lifts of anchored parents are accidents at exactly the uniform rate (641 vs 644). *Refuted.* (A first reading "0 observed
vs 6 expected" came from counting labelled or per-parent-distinct lifts, which multiply-count the same value; it is
retracted.) Note also what the lift tree of an anchored parent looks like: every anchored level-48 parent has exactly
one surviving lift at 96 (its anchored lift) — the "one child alive per level" of OPEN-PATTERNS, now measured on 2609
parents — while a random level-48 survivor has 32768 × 2.2e-21 = 0 surviving lifts.

**Re-reading H1-REPORT §7 with the right model** (s = 124416, M = 2^9 3^5, A = 49; engine numbers from
`trees_mac_0125.jsonl`): level 12: N_12 = 8.80e9 patterns → uniform (a,pattern) survivors 8.80e9 × 0.0202 × 50/12 = 7.4e8,
tail+descent pass 2–3e-3 (Table 3b: measured 3.3e-3; the engine's tail-dead implies 6.1e-3 with its a-mixture) → ≈ 2–4.5e6
vs 4.54e6 observed. Level 24: 3.51e9 (a, child) pairs × ρ'_24/ρ'_12 = 3.78e-6 → 13 260 residue survivors; 4th pinned digit
0.2–0.35 → 2.7–4.6 k; descent → observed 1 097 (ratio 0.24–0.4, the descent). Level 48: 1.387e7 children × 6.19e-8 = **0.86
residue accidents, × 5th digit 0.15–0.25 → 0.13–0.21 expected; observed 0** (17 anchored survivors). H1's "42 (20–100)" is
not reproducible from any consistent choice of index; the "≥ 29–480× overshoot" is this factor 75 (a-class) × 0.2–0.35 (tail)
at level 24 and 16 × 0.2 at level 48. The whole recorded sweep (`engine_counts.py`, 2051 equations): Σ children at 48 =
5.30e8 → 32.8 residue accidents (fixed a) × tail 0.2 ≈ 6 expected engine-visible accidents at level 48 across the entire
sweep, and 3.4e7 children at 96 → 4.6e-15 at level 96. So the sweep (k ≤ 18) could never have seen an accident at 96 and
would have seen ~6 at 48 (indistinguishable in the recorded counts from anchored-48 patterns whose anchored lift is a
SOLUTION or is merged — S48 − S96 = 1535 is dominated by those). H16's "1.2e-3 × uniform at level 24" is the same
omission: the engine's level-24 survivors are 0.07–0.10 × the fixed-a residue prediction (k = 11–14), i.e. one tail digit
times descent.

## 4. Findings beyond the brief

4.1 **Survivors with no admissible a** are the bulk of S_L survivors from level 24 on (1 − (A+1)/ord_L: 94 % at 24, 99.7 %
at 48, 99.96 % at 96 for A = 49). Any accounting that uses ρ_L instead of (A+1)ρ'_L overstates engine accidents by that
factor. (Table 3.)

4.2 **The chain sampler reaches anchored patterns.** With 25 000 random level-12 parents and all lifts, the explored
level-96 subtree (≈ 1.7e15 patterns of 6e23 for q = 11) contained 3 + 1 ordinary anchored patterns (anchors 1 = 2^0 3^0 7^0
with k = 1, 1029 = 3·7^3, 42 = 2·3·7, 345744 = 2^4 3^2 7^4) and 2 half-anchors; all six were the only level-96 survivors
among 1.5e6 lifts of 364 random level-48 survivors. An anchored pattern is anchored at every level below (same y), and
in a uniform sample the anchored fraction of survivors is ≈ 1.2e-4 at level 12 (3/25000: the pattern value is small),
1.5e-4 at 24 and 0.5 % at 48 (6/1275; 6/364 for the two q = 11 multisets, 0/911 for q = 13, 14) — the crossover from accident-dominated to anchored-dominated survivor sets happens
between 48 and 96, where ρ_96/ρ_48 = 2e-21 removes every accident from the lift tree while each anchored parent keeps
exactly one child. This is the quantitative reason the sweep's level-96 open set is 100 % anchored at k ≤ 18 (Table 8:
μ_96 ≈ 10^-18–10^-14 per equation), and the reason it will not be at Tier C.

4.3 **The engine's tail+descent at level 12 passes 1.3–3.3e-3 of residue survivors, the level-24 fourth digit 0.2–0.35, the
level-48 fifth digit 0.15–0.25, and level 96 pins nothing new** (K*_96 = K*_48 = 5): after level 48 only the residue
test (×1.35e-22 per a) and Lemma C's copy-choice enumeration act on an accident.

4.4 **Half-anchors.** Digits above the top at position 96 − j contribute (d − 1)·10^{−j} mod R_96, so a pattern can satisfy
2^J V ≡ y (mod R_96) with y a small S-unit and 2^J ∤ y (e.g. 611…1142 = R_96 + 5·10^95 + 31 ≡ 63/2; found twice at q = 11).
These pass the <2,3,7> test with a-class a_y − J ≡ −1 and are never engine-admissible (a ≥ 0 needs a ≡ 316 799). 5^k is in
<2,3,7> mod Q_96 only for k ≡ 0 mod 96, so there is no analogous "5-anchor" family. Irrelevant for accidents; recorded
so the next reader does not mistake them for accidents.

## 5. Tier-C forecast under the (now tested) uniform model

**Table 8 — expected residue accidents at level 96 per Tier-C vertex** (`tierc_forecast.py`: μ = Σ_M N_96(M)·(A+1)·ρ'_96
with N_96(M) = 96 ∏ C(95 + m_d, m_d), A from RESULT-dpcount's lower bounds; tail pass 10^-4–10^-3 from §3(b); Lemma C depth 1
≈ 1 for q ≥ 25 and A ≥ 87 since the 2^q copy choices exceed the 640 000 constraint classes (H1 §3, RESULT-anchorfirst §4)).

| vertex | #M | k | Σ N_96(M) | A | μ_96 residue (per a summed) | after tail (×1e-4 … ×1e-3) | anchored patterns (RESULT-anchorfirst) | accidents / anchored |
|---|---|---|---|---|---|---|---|---|
| 3416267673274176 | 306 | 17–34 | 1.34e42 | 118 | 8.5e6 | 8.5e2 – 8.5e3 | 1.9e11 | 5e-9 – 5e-8 |
| 128421199872 | 925 | 13–31 | 2.61e40 | 118 | 1.7e5 | 17 – 170 | 5.1e11 | 3e-11 – 3e-10 |
| 913217421312 | 911 | 14–35 | 3.27e42 | 122 | 2.1e7 | 2.1e3 – 2.1e4 | 1.5e12 | 1e-9 – 1e-8 |
| 727326941773824 | 834 | 17–44 | 2.09e48 | 144 | 1.6e13 | 1.6e9 – 1.6e10 | 8.9e13 | 2e-5 – 2e-4 |
| 112717121716224 | 2446 | 16–42 | 8.80e47 | 135 | 6.4e12 | 6.4e8 – 6.4e9 | 1.5e14 | 4e-6 – 4e-5 |
| 1438916737499136 | 829 | 17–36 | 1.24e47 | 125 | 8.3e11 | 8.3e7 – 8.3e8 | 1.4e14 | 6e-7 – 6e-6 |

(At level 48 the same vertices have 10^19–10^25 residue accidents, 10^15–10^21 after the tail: the level-48 population is
accident-dominated by 10^8–10^10 over anchored patterns, consistent with "the 12→24 lift is the wall".) For the sweep's
k = 11–14 equations μ_96 = 6e-18–5e-14 and μ_48 = 15–19 000 before the tails (×5e-5 after the 12- and 24-digit tails →
0.001–1), matching the 0 unanchored level-48 survivors.

## 6. Mechanism analysis and proof route (task 3)

The data show no level at which accidents are ≥ 10× below uniform (the largest deviation is +12 % ± 10 % at 48, the wrong
sign). So the honest statement is the negative one, with the reasons why no proof can go the other way:

* **Character sums go the wrong way.** #S'_L(a) = (1/I') Σ_{χ ∈ (G/2^a H')^} χ̄(2^a) Σ_P χ(V_P). Any Weil/Karatsuba-type bound on
  the inner sum over the iterated sumset {R_ν} + Σ_j {(d_j − 1)10^e} gives |error| ≤ √(N·Q) (Karatsuba's bound for
  Σ_{x∈A,y∈B} χ(x + y) with |A||B| = N), i.e. it proves #S' = N/I' (1 + o(1)) only when N ≫ Q·I'^2 ≈ 10^168 — and then it
  proves accidents *exist*. Absence (#S' = #anchored) would need the error term below 1, i.e. exact vanishing of 10^31
  character sums; no analytic method does that. The exact count is the dense DP over Z/Q_96 (RESULT-dpcount: 10^94 cells).
* **No algebraic coincidence forces V_P ∈ H.** The index lives in the 2-, 3-, 5-, 11-power-residue symbols of V_P at the 20
  primes (Table 1) and the measured independence of these symbols on pattern values is complete at 12, 24, 48 (Table 2,
  Table 3, §3(c)). A coincidence V_P ≡ V_{P'} (mod Q_96) between two patterns of height < 10^97 forces V_P − V_{P'} = jQ_96 with
  |j| ≤ 2000 and has probability ≈ N^2 · 2000/Q ≈ 10^-11 for N = 10^40: it does not produce accidents. The only structural
  survivors are the generalized anchors (ordinary and half), and their count is what anchor-first already enumerates.
* **Consequently anchoring cannot be certified by excluding accidents.** The uniform model, tested to ±1 % at 24 and ±10 %
  at 48 on 10^9 lift tests and 10^8 direct samples, predicts μ_96 ≫ 1 accidents for every Tier-C vertex (Table 8). An
  anchor-first census of a Tier-C vertex is therefore an *undercount of the open set by ≈ 10^1–10^10 patterns* (relative
  10^-4–10^-11), and each of those accidents is a pattern on which Lemma C's coset argument has no anchor to work from:
  its coset's nearest point is ≈ 10^27 away (H1 A3), its 10-adic tail is consistent to 5 digits by selection, and Lemma C
  depth 1 does not bite for q ≥ 25, A ≥ 87. They are exactly the q = 100 construction at Tier-C size, and they will exist
  unless the sieve is changed (more modular levels: each extra level multiplies μ by its ρ' ratio, e.g. 192 would give
  ×10^-40-ish — but at the cost of the lift blow-up FRONTIER.md already rules out).
* **What *could* be proved** (and would be useful for a different purpose): the equidistribution direction. For q with
  N_96(M) ≫ Q_96 ≈ 10^94 (q ≳ 50) Karatsuba's bound makes #S'_96(a) = N ρ' (1 + O(√(Q I'^2/N))) rigorous, i.e. a *lower* bound
  on accidents. Not needed by the program.

## 7. Budget and files

CPU ≈ 1 h 55 min total on one core at a time: four main runs 10 min each (stage C, 3×10^8 level-48 tests at 1.5 μs, dominates),
four analyses 3 min each (Python discrete logs + classify + descent), anchored-parent runs ≈ 12 min (DP generation +
2.8×10^8 lift tests), structure/tables/controls 2 min, distinct-value counts 4 min. Peak RSS < 400 MB.

Files: `structure.json` (primes, logs, components), `tables.json`/`tables.txt` (annihilator characters, chi_a),
`run_{q14,q11a,q11b,q13}.{log,surv,analysis.txt,analysis.json}` (every survivor at every level with its a-class),
`anch*_*.{p96,p24,p48}` (anchored pattern sets), `anchrun*.{log,surv}`, `all_anchors.txt` (285 sweep anchors).
Reproduce: `python3 structure.py && python3 tables.py && gcc -O2 -o acc acc.c && python3 control.py && ./run_main.sh &&
for n in …; do python3 analyze.py run_$n $M 1500; done`.
