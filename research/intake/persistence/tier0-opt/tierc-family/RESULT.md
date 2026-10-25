# Tier C family test: can the witness-lemma membership be decided for a whole family?

2026-10-24, lane `tierc-family`, one process at a time under `nice -n 10`, stdlib Python through `uv run --no-project python -I`. Nothing under `tier0/` or the other `tier0-opt/` subdirectories was edited; their data files were read.

**Answer in one paragraph.** The membership delta in Lambda_L + K_L collapses to one congruence on the digits, and that congruence does not mention the anchor y (Section 2). It reproduces every recorded wrap-0 shadow verdict (Section 3), at 100x to 1000x lower cost than the lattice route on Tier A/B (Section 4). It does not help Tier C: it decides the single shadow child of a word, and at Tier C a word has 10^2 to 10^7 other children that survive 193 and 769 and need the same per-pattern work as before. Measured reduction in cost per word on Tier C: at most 1.06x. The kill criterion (below 100x) fires. Result: **negative for Tier C, positive and exact for the shadow itself. Do not retry without new data** (Section 5).

## 1. Prediction against outcome

Prediction file `PREDICTION.md`, md5 `6b64226b83acfef422adc8f1caa3341a`, registered before any run.

| id | predicted | outcome | verdict |
|---|---|---|---|
| P1 | conductor exponents (c2, c5) equal the bound alpha+2, beta+1: (11,5) at 192, (15,5) at 384, (12,5) at 480, (11,7) at 288 | measured (9,5), (13,5), (10,5); inferred (9,7) at 288. Exponents are alpha and beta+1, two below the bound in the 2-part | bound held, equality falsified |
| P2 | lookup equals the full lattice test on 100% of words | 711 words x 4 levels, 0 disagreements (`refcheck.out`); also 1335/1335 and 4317/4320 against Cairn's independent pipeline (Section 3) | confirmed |
| P3 | whole-key kill fractions at 192 / 384 / 480 / 1152 about 0 / 86 / 27 / 91 percent | 0 / 86.2 / 26.9 percent (recorded cut rates 0 / 86.4 / 27.0); 1152: 2 of the 6 recorded patterns, and 144 of 182 predicted untested (Section 6) | confirmed at 192, 384, 480; 1152 only on the six |
| P4 | at least 95% of alive words structural (independent of y) | 100%: the image of Lambda_L in (Z/m_L)^* is trivial, so no accident class exists | confirmed, stronger |
| P5 | word-to-profile compression at least 100 for k >= 14 | compression exactly 1.0 on all 1335 keys: every digit position is below len(y) <= 15 < a+13 | falsified |
| P6 | zero Tier C anchors admit a wrap-0 representation | 45,088 of 1,284,882 S-unit anchors y < 10^97 pass the necessary digit-sum filter (`tc_domain.out`); the anchor-first census (RESULT-anchorfirst Table 1, documented, not re-measured here) puts wrap-0 at 22 to 29 percent of Tier C anchored patterns | falsified |
| P7 | children passing 193 and 769 about 2^(r+1)/148417 per word, position independent | measured means 1831.5 vs 1808.7 (k = 31, r = 27), 107.8 vs 113.0 (r = 23), 14453 vs 14469 (k = 34, r = 30), 14814098 vs 14816519 (k = 44, r = 40); minimum over placements never zero | confirmed |
| criterion | kill criterion fires with probability 0.85 | fired | confirmed |

## 2. The family invariant

Data used (Cairn tables, discrete logs taken as given): Lambda_96 from `lattice96.txt` (20 primes); Lambda_192 and Lambda_384 chained from `levelprimes.txt`; Lambda_480 from `levelprimes480.txt` (22 primes). Reproduced orders (`selftest.out`, `tables.out`): |G_96| = |G_192| = 2^9 5^4, |G_384| = 2^13 5^4, |G_480| = 2^10 5^4, equal to the documented table.

**Fact A (computed, exact).** Write |G_L| = 2^alpha 5^beta and m_L = 2^alpha 5^(beta+1). Then (alpha, beta+1) = (9,5), (9,5), (13,5), (10,5) for L = 96, 192, 384, 480, and for each:
(a) Lambda_L is contained in K_m = {(b,c): 3^b 7^c = 1 mod m_L} (basis vectors checked, `hindex.out`; the image of Lambda_L in (Z/m_L)^* has one element, `tables.out`);
(b) [Z^2 : Lambda_L + K_L] = [Z^2 : K_m], with m_L the smallest modulus for which this holds (searched over c5 and c2 separately, then jointly);
(c) the index of K_L is phi(10^L)/2, so the image of <3,7> has index 2 in (Z/10^L)^*, cut out by the single condition "u = 3 mod 4 iff u mod 5 is in {2,3}".
From (a) and (b): Lambda_L + K_L = K_m, because Lambda_L + K_L is contained in K_m and has the same index. The same holds with the window kernel for any exponent a <= L - alpha (the window modulus is 2^(L-a) 5^L, a multiple of m_L).

**Theorem F (shadow survival as a congruence; conditional on Fact A and HSHADOW section 8).** Let y = 2^a 3^b 7^c = R_nu + sum_j (d_j - 1) 10^(e_j) be a wrap-0 representation. Let a word fix a set F of digits at distinct positions (copy 0) and leave U unplaced; put S_F = sum over F of (d_j - 1) 10^(e_j) and S_U likewise. For L in {96, 192, 384, 480} the shadow of the word survives level L (and the word exists at level 96) iff

  R_96 + S_F = y (mod 2^(a+alpha_L) 5^(beta_L+1)),

equivalently

  10^nu + 9 S_U = 0 (mod 2^(a+alpha_L) 5^(beta_L+1)).

*Proof.* HSHADOW section 8: survival iff delta = v_w - (b_y, c_y) lies in Lambda_L + K_L, with v_w any point of the window class 2^a 3^b 7^c = W (mod 10^L), W = R_L + S_F. By Fact A this group is K_m, so survival iff 3^(delta_b) 7^(delta_c) = 1 (mod m_L), that is W/2^a = y/2^a (mod m_L), that is W = y (mod 2^(a+alpha) 5^(beta+1)). Existence of v_w needs W/2^a in the image of <3,7>; by Fact A(c) that is a condition mod 20, implied by the congruence because 4 and 5 divide m_L. R_L = R_96 (mod 10^96), and 2^(a+alpha) 5^(beta+1) divides 10^96 for a <= 83. The second form follows from y = R_nu + S_F + S_U (wrap 0) and 9 R_96 = 10^96 - 1. Level 96 is the case L = 96 and gates every higher level. Hypotheses beyond the lemma's: wrap 0, the Lemma C depth-1 word set (distinct fixed positions), the Cairn prime tables. ∎

What is family data here. The quotient map G_L -> H_{m_L} = <3,7> mod m_L (an isomorphism, because the image of Lambda_L is trivial) sends delta to W/y mod m_L. The verdict is a function of (nu, a, the multiset of (d-1, e) over U) alone. The anchor drops out. Consequences:
- Level 192 has the same modulus as level 96, so it kills no shadow. Level 384 needs agreement to 2^(a+13) and 5^5; 480 to 2^(a+10) and 5^5; 288 (inferred, 2^9 5^6) to 2^(a+9) and 5^7; 1152 (inferred, 2^13 5^6) to 2^(a+13) and 5^7.
- The mechanism of the 182 recorded survivors at 384 (`structure.out`): a word is alive when its unplaced digits cancel the missing run of ones, for example one unplaced digit 8 at position nu, giving 10^nu (9*7 + 1) = 2^6 10^nu.
- A family of arrangements sharing the low profile (positions below a+13) has one verdict. In the recorded data the profile is the whole arrangement (compression 1.0, P5), so the gain over per-word lattice tests is a constant factor, not a combinatorial one.

**Where the family route fails (exact point).** The proof needs a witness: for wrap 0 the integer y itself satisfies every modular condition at every prime. A child other than the shadow, or any child of a wrap >= 1 representation, has no witness. Its modular class is (b', c') + Lambda_L where (b', c') solves the system 2^a 3^b 7^c = V_child mod p at each prime p of the level, so it involves dlog_p(V_child) at the primes where the lattice image is nontrivial. No character of G_L factors through (nu, positions): the survivors among non-shadow children are counted by the subset-sum DP, not by a congruence. Section 5 measures how many there are at Tier C.

## 3. Validation against recorded verdicts

The test (`famtest.py`) is Theorem F. Output per key is ALIVE (some wrap-0 word alive), SHADOW_DEAD (wrap-0 representations exist, none alive), or NO_WRAP0 (no wrap-0 representation; the test claims nothing). A key is killed by the family test only when it is SHADOW_DEAD and all its representations are wrap 0 ("pure"); the count of representations comes from the recorded table.

| set, level | recorded | family test | discordant |
|---|---|---|---|
| 1335 patterns, 192 | no recorded cut (documented: 192 kills no shadow) | 1333 ALIVE, 2 NO_WRAP0, 0 SHADOW_DEAD | 0 |
| 1335, 384 (`shadow1335.tsv`) | 1153 CLOSED-cut, 182 CLOSED-sandwich | 1151 SHADOW_DEAD + 2 NO_WRAP0, 182 ALIVE | 0 |
| 1335, 480 (`x4w_480_1335.tsv`) | 360 cut, 975 sandwich | 359 SHADOW_DEAD + 1 NO_WRAP0 (cut); 974 ALIVE + 1 NO_WRAP0 (sandwich, wrap-1 survivors, a former NOTAPPL pattern) | 0 |
| 4320 patterns, 480 (`final13/shadow/s480w.tsv`) | 903 cut, 3417 sandwich | 904 SHADOW_DEAD, 3414 ALIVE, 2 NO_WRAP0 | 1, explained next |
| pure-wrap-0 keys only, 384 | 912 cut, 171 sandwich | 912 killed, 171 ALIVE | 0 |
| pure-wrap-0 keys only, 480 (4320 set) | 531 cut, 2250 sandwich | 531 killed, 2250 ALIVE | 0 |

The one discordant key is `9483264 22222222366777 0 1361367`: its shadow is dead and its eight recorded survivors all lie in a wrap-8 representation (`s480w.txt` line 3186: `(w=8,...,alive=8)`). It is not pure, so the test makes no kill claim for it. No pure key and no key in any family-granularity group carries a recorded survivor and a KILL: 0 violations over 912 + 531 kills.

Family-granularity kills (SHADOW_DEAD for every member, all members with a wrap-0 representation), 1335 set (`fam_table.out`):

| grouping | families | killed at 192 | killed at 384 | killed at 480 | killed families containing a recorded survivor |
|---|---|---|---|---|---|
| key | 1335 | 0 | 1151 | 359 | 0 |
| (vertex, multiset, a) | 1008 | 0 | 849 | 248 | 0 |
| (vertex, multiset) | 598 | 0 | 454 | 96 | 0 |
| vertex | 42 | 0 | 16 | 3 | 0 |

Per-word agreement with the older witness runs (`WITNESS-sand6-288.txt`), six sandwich patterns: at 288 the test kills `28672 2244788 0 330812181` and `28672 22224788 0 330812181` outright and loses one word of `28672 2227888 0 78121827`; at 480 one word of `42336 22334677 1 3281116734`. All match the recorded `A`/`x` strings word for word. At 1152 (conductor (13,7), inferred) it closes exactly the two patterns that `EXTINCT1152-run.txt` closes (counts per level in `plant.out`).

Exact lattice reference against the congruence: 711 words stratified by fate (459 dead at 96, 199 alive at 96 and dead at 384, 53 alive at 480) from 60 keys (30 survivors, 30 cut), each tested at 96, 192, 384, 480 with `window_coset` and `Lambda_L + K`: 0 disagreements (`refcheck.out`).

## 4. Planted negatives, mutants, and cost

**Planted delta (`plant.out`).** For key `14336 227888 0 78121827` (recorded CLOSED-sandwich at 384), points (b_y, c_y) + lambda + kappa with lambda in Lambda_L and kappa in K_L (random coefficients up to 40) were turned into windows W = 2^a 3^b 7^c mod 10^L. At each of 192, 384, 480: 25 of 25 planted members are ALIVE in the family test and the lattice reference; 25 of 25 random non-members are dead in both. The family test refuses to kill every planted member.

**Mutants (300 random cut keys, all 182 survivors).** Modulus too strict, 5^6 at 384 and 480: kills 57 of 182 recorded survivors. 2^14 at 384: kills 80 of 182. Modulus too loose, 2^12 at 384: 27 of 300 cut keys wrongly alive. The 5^4 loose mutant changed nothing on 300 cut keys, so this data does not detect the 5-adic lower edge; that edge rests on the lattice index search alone.

**Cost, Tier A/B (`costs.out`; 131 patterns, 12 per k from 5 to 18).** Reference route: the lattice test per word, emulating the wordlift route (unit costs measured: 0.18 ms per prefiltered word at level 96, 7.8 ms per valid word for 192 + 384 + 480). Family route: one congruence per word, 0.38 microseconds, enumerating all subsets.

| quantity | geometric mean ratio | 95% bootstrap interval |
|---|---|---|
| shadow decision, representation enumeration excluded | 718x | 605 to 850 |
| per pattern including the common representation enumeration | 9.9x | 8.5 to 11.5 |
| by k = 5-8 / 9-11 / 12-14 / 15-18 | 1015 / 661 / 576 / 693 | not computed |

The representation search (digit DP) dominates once the shadow test is O(1): 26.9 s of the 176.8 s total.

**Cost, Tier C sample (`tc_cost.out`).** Cairn's per-pattern final stage for a word costs a subset-sum DP over Z/148417 plus an exact test of every child that survives 193 and 769, the shadow being one candidate among them. The family test removes the shadow's lattice cost and nothing else. Measured on synthetic Tier C words (vertex multisets with 8 random placements per setting; r unplaced digits, 4 or 8 digits fixed; a complete-anchor Tier C sample does not exist in the repository):

| vertex multiset | k | r | children passing 193*769, expected | measured mean (min to max) | DP seconds (Python) | cost ratio per word, per-pattern / family |
|---|---|---|---|---|---|---|
| 2^23 3^7 7 | 31 | 27 | 1809 | 1832 (1768 to 1910) | 0.086 | 1.032 (1.027 to 1.036) |
| same | 31 | 23 | 113 | 108 (83 to 167) | 0.070 | 1.046 (1.040 to 1.058) |
| 2^6 3^27 7 | 34 | 30 | 14469 | 14453 (13992 to 14712) | 0.091 | 1.016 (1.016 to 1.017) |
| same | 34 | 26 | 904 | 892 (836 to 943) | 0.081 | 1.037 (1.025 to 1.045) |
| 2^39 3^3 7^2 | 44 | 40 | 1.48e7 | 1.481e7 (1.480e7 to 1.482e7) | 0.125 | 1.00003 |
| same | 44 | 36 | 9.26e5 | 9.261e5 (9.242e5 to 9.274e5) | 0.125 | 1.0004 |

Unit costs: child test at the seven level-192 primes 7.7 microseconds (Python, children that die at the first prime; children that pass 193 and 769 cost more, so the ratios above are upper bounds); family shadow test 0.38 microseconds; lattice shadow route over 96/192/384/480 3.2 ms. The DP is k * 148417 operations per word (about 0.07 to 0.125 s in Python, measured); a C port of the DP was not timed here.

Pattern-level coverage: wrap-0 patterns are 22 to 29 percent of Tier C anchored patterns (documented census). An infinite speedup on that share alone gives at most 1/(1 - 0.29) = 1.41x on the pattern list.

## 5. The negative

KILL CRITERION: the reduction in cost per pattern on the Tier C sample is at most 1.06x per word (1.00003x at k = 44) and at most 1.41x per pattern list, against a threshold of 100x. **Stop.**

Reason: (1) measured: the shadow is one child among 2^(r+1)/148417 + 1 per word, which is 10^2 to 10^7 for the Tier C settings tried (r = k - 4 and k - 8); (2) shown in Section 2: the other children have no witness, so the family congruence does not decide them; (3) measured in Python: the DP that lists them costs 0.07 to 0.125 s against 3.2 ms for the lattice shadow test and 0.38 microseconds for the congruence. Not measured: the real distribution of r over Tier C depth-1 words, and the C port's DP time; a small r would shift the ratio, which is why the reopening condition below names it.

**Do not retry without new data.** The data that would reopen it: a family-level handle on non-shadow children, namely a character or quotient of G_L through which dlog_p(V_child) at the nontrivial-image primes factors through family data; or Tier C depth-1 survivor words with r below about 16 unplaced digits in volume (no such sample exists; the anchor-first runs recorded zero depth-1 words in all sampled anchors).

What remains true and usable: Theorem F gives the exact survival rule for wrap-0 shadows at 192, 384, 480 (and, inferred, 288, 768, 1152) as a congruence, so the Tier A/B final stage can replace its per-word lattice tests by a modular reduction (718x on the shadow decision, 9.9x per pattern end to end).

## 6. Seams

- The conductor exponents were found by a lattice index search at 96, 192, 384, 480. For 288, 768, 1152 they are inferred as (alpha, beta+1) from the documented |G_L| (2^9 5^6, 2^13 5^4, 2^13 5^6) and checked on the six recorded patterns only (per-word match at 288 and 480, pattern match at 1152). The prediction that 144 of the 182 patterns alive at 384 die at 1152, 135 at 288, and none at 768 (`fam_1152.out`) is untested and differs from the registered estimate of about one third; it counts shadows only, non-pure patterns may survive through wrap >= 1 representations.
- Wrap >= 1 representations were not enumerated here; "pure" uses the recorded representation counts. A key with a wrap-0 shadow dead and surviving wrap >= 1 children is not a kill (one such key in 4320).
- The Lambda_L tables are Cairn's discrete logs (taken as given, not recomputed); every statement is conditional on them and on HSHADOW section 8.
- The Tier C sample is synthetic (vertex multisets, random placements, 8 per setting); no sampled set of real Tier C depth-1 words exists in the repository. The r distribution of real Tier C words is unknown; the table brackets it with r = k - 4 and k - 8. The child test timing uses random children, an underestimate of the cost of candidates that pass 193 and 769.
- The share of wrap-0 patterns (22 to 29 percent) and the pattern counts are the anchor-first census, not re-measured. My digit-sum filter (45,088 of 1,284,882 anchors pass at m_max = 126) is a necessary condition only; the exact decomposition DP was not run.
- Cost ratios use a Python emulation of the lattice route, not Cairn's C port. The per-word Python timing of the port is not available; the 155 ms per pattern of `final13/shadow/s480w` (670.85 s real for 4320 patterns, full pipeline) is context only.
- The 5-adic lower edge of the conductor (5^4 versus 5^5) is not visible in the recorded verdicts (mutant test), only in the index computation.
- Process note: two bare `python3` invocations (one in-place text edit of a scratch file, one trivial no-op) fell outside the `uv run --no-project python -I <file>` rule; no research data passed through them.

## 7. Files

`PREDICTION.md` (md5 6b64226b83acfef422adc8f1caa3341a), `famlib.py` (5cd90a92), `famtest.py` (a94ae0cf), `tables.py`, `validate.py`, `validate2.py`, `refcheck.py`, `plant.py`, `costs.py`, `tc_dp.py`, `tc_cost.py`, `tc_domain.py`, `fam_table.py`, `fam_1152.py`, `purewrap.py`, `hindex.py`, `structure.py`, `selftest.py`, with outputs `*.out`, `validate_rows.json`, `validate2_rows.json`, `costs.json`, `tc_cost.json`. Leftover scratch: `dbg.py`, `odd.py`, `analyze.py`, `analyze480.py`. Nothing was deleted, staged, or committed.

No-Claim: nothing here is PROVEN or Lean-checked; family verdicts are conditional on the witness lemma, Lemma C, Matveev, Yu 2007 Thm II and the pattern list.
