# Tier B: what the final stage costs once the enumeration exists

*2026-10-21 15:55 EDT, chat session. Inputs: TABLES.md (Tier-B rows), FRONTIER.md (forecast registration),
FINAL-STAGE-run-U2.txt (138 vertices, per-vertex Lemma C / sandwich counts), NOTES-u2.md + utable_U2.txt (U″ to
k = 24, plus k = 31), RESULT-peranchor.md (box-CVP cost model). Nothing here is a result on a Tier-B vertex; it is a
cost forecast, and it changes the Tier-B plan: the final stage is a second bottleneck, not an afterthought.*

## 1. Depth needed per vertex (U″, lower bound 10^(72 + 48(D−1)))

| s | k_max | patterns | log₁₀ U″ (a = 0 / a ≥ 1) | depth D | note |
|---|---|---|---|---|---|
| 1811939328 | 29 | 3.4e16 | 230.0 / 218.0 | 5 | U″ interpolated between k = 24 and 31 |
| 71663616 | 22 | 3.1e15 | 176.0 / 164.2 | 4 | |
| 169869312 | 25 | 5.7e15 | 198.0 / 188.5 | 4 | interpolated |
| 226492416 | 26 | 4.3e15 | 206.0 / 195.9 | 4 | interpolated |
| 1792336896 | 20 | 7.4e15 | 162.1 / 149.0 | 3 | |
| 2113929216 | 28 | 2.8e16 | 222.0 / 210.6 | 5 | interpolated |
| 3699376128 | 27 | 4.6e16 | 214.0 / 203.2 | 4 | interpolated |
| 4444263936 | 22 | 4.4e16 | 176.0 / 164.2 | 4 | |
| 11329339392 | 25 | 4.0e16 | 198.0 / 188.5 | 4 | interpolated |
| 13884223438848 | 25 | 1.6e16 | 198.0 / 188.5 | 4 | interpolated |
| 1194891264 | 20 | 5.3e15 | 162.1 / 149.0 | 3 | |
| 1783627776 | 26 | 1.6e17 | 206.0 / 195.9 | 4 | interpolated |
| 4182119424 | 20 | 5.8e15 | 162.1 / 149.0 | 3 | |

Depth 3–5 everywhere; the U″ table should be extended to k = 29 (Cairn: `mk_utable_u2.py` with the certification
step) before any of this is run — the interpolation is only for planning. With U′ instead of U″ the depths would be
4–6; with the original U, 5–7.

## 2. Lemma C depth 1 stops killing as k grows — measured, not assumed

From FINAL-STAGE-run-U2.txt, open patterns at level 96 aggregated by k = Ω(s):

| k | open | killed at depth 1 | to sandwich | depth-1 kill rate |
|---|---|---|---|---|
| 9 | 84 | 81 | 3 | 0.964 |
| 10 | 254 | 235 | 19 | 0.925 |
| 11 | 432 | 397 | 35 | 0.919 |
| 12 | 848 | 731 | 117 | 0.862 |
| 13 | 3023 | 2524 | 499 | 0.835 |
| 14 | 1190 | 985 | 205 | 0.828 |
| 16 | 1132 | 908 | 224 | 0.802 |
| 18 | 951 | 718 | 233 | 0.755 |

The survival fraction 1 − rate is close to linear in k (≈ 0.023 per unit of k from k = 9 to 18). The mechanism is
visible: the depth-1 verdict depends on the target mod 5^5·2^9 (index 640000) but there are up to 2^k − (class
collisions) copy choices, and the kill requires every choice to fail. Extrapolated to Tier B: survival ≈ 0.45–0.50
at k = 20–22, ≈ 0.6–0.7 at k = 25–29 — not the 6% written into FRONTIER.md's forecast registration (a k ≤ 11
figure). **Forecast correction:** survivors after Lemma C ≈ 0.5 × open@96, not 0.06 ×.

With open@96 ≈ patterns × 10^-8 (FRONTIER.md; accidents uniform, RESULT-accidents.md): Tier B has ≈ 4.0×10^9 open
patterns at level 96 and ≈ 2×10^9 sandwich jobs at depth 3–5, k = 20–29. (Interval ×0.1–×30 on the open@96 rate
carries through.)

## 3. What a sandwich job costs at k = 20–29

Enumeration (deep_cut as written, or the C port): the depth-1 enumeration alone is up to 2^k cut operations per
pattern (2^29 ≈ 5×10^8 at 27 ns ≈ 15 s), before any deeper stage; depths 2..D then cost ≈ (2^r)^(D−1) more,
since every extension of a depth-1 survivor survives (DEEPCUT.md). 2×10^9 jobs × 15 s is 10^3 years. **Dead.**

Box-CVP (RESULT-peranchor.md): cost ≈ (#words below the frontier) × LLL(dim 2 + f) with 0 enumeration nodes on
everything seen so far; #words ≈ 4^r where r = pattern digits left unplaced after depth 1 (the depth-1 survivor is
the anchor's shadow and places the rest at copy 0). On the 43 k ≤ 11 patterns r ≤ 7 and the whole thing costs
≈ 6 LLLs per pattern. The forecast for Tier B hinges entirely on r at k = 20–29, which nobody has measured:
- r ≤ 7 (as at k ≤ 11): ≈ 10–40 LLLs of dimension ≤ 30 per job; with fplll ≈ 10 ms per LLL → ≈ 0.3 s per job →
  2×10^9 jobs ≈ 2×10^4 core-days. **Comparable to the enumeration itself (2.7×10^4 core-days at 8 ns).**
- r ≈ 10–12: ≈ 10^6 LLLs per job (§4 of RESULT-peranchor.md) → hopeless.
Measurement needed now, on data we already have: the r distribution of the 1335 sandwich patterns of the final
stage, by k (the C port has every pattern; r = number of digits not placed at copy 0 by the surviving depth-1 word).
If r grows with k the way the depth-1 survival does, Tier B's final stage is harder than its enumeration.

## 4. Consequences for the plan

1. The Tier-B cost model (1.8×10^3 Mac-days ×21 for the enumeration) must add the final stage: at best the same
   order again, at worst dominant. Any "GPU makes Tier B a month" statement is about the level-12 pass only.
2. The two levers that act on the final stage, in order of promise:
   (a) **Raise the level, not the depth, for survivors** — but selectively: the full lift 96→192 costs 2^(k+1)
   children per pattern (10^9 at k = 29), yet only the depth-1 *survivor word* needs lifting (its copy-0 digits are
   fixed; the free positions are the r unplaced ones): 2^(r+1) children, each a cut of index ≈ 10^38 (the new
   primes of level 192). That is the box-CVP's "words below the frontier" done modularly instead of by LLL, and it
   composes: 192 → 384 at 2^r children each. **Prototyped the same afternoon (WORDLIFT.md, `wordlift.py`):**
   43/43 of the level-96 survivors and 21/21 of a k = 14–16 sample close at level 384 depth 1 (bound 10^239 digits,
   37 + 19 of them with no survivor at all), 102 + 227 surviving children, ×20–140 cheaper than the full lift and
   with no depth enumeration. But r ≈ k − 5 and the words multiply with the digits above position 9, so the cost per
   Tier-B pattern is still Σ_words 2^(r+1) ≈ 3^(k−9): the exponent of the copy choices is not removed. §3's
   conclusion stands; the new lead is H-shadow (WORDLIFT.md §5).
   (b) C/fplll box-CVP (RESULT-peranchor.md §5) for the r ≤ 7 regime.
3. Nothing in §1–§3 touches Tier C: at k = 31–44 the enumeration (10^22) is the wall, and the only closure route
   that bypasses it remains the conditional one (CONDITIONAL.md: RST[1] closes 128421199872 with the existing
   corpus; the other five need the corpus to 10^6883).

## 5. Calibration

Every number in §2 is read off FINAL-STAGE-run-U2.txt (138 vertices, U″ table); the k = 15, 17, 19 rows are empty
because no enumerated vertex has that Ω. §1's interpolated U″ values and §3's per-job costs are forecasts and are
labelled so. No vertex changes status.
