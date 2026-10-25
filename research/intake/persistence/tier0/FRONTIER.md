# The base-10 frontier, ranked (2026-10-20 15:00 EDT)

177 vertices in T_2 ∪ T_4 ∪ T_6 ∪ T_8 (from the 10^4000 enumeration; roots included); 105 done in the
result files (runall_final, trees_c, trees_mac as of 05:45) — every one of them CLOSED (computation + Lemma C +
sandwich); 72 remain. Costs at the measured C level-12 rates (gated lvl12.c 66 ns/pattern; Cairn's tier0-opt
8 ns, not yet swapped into the sweep) and at a hypothetical GPU kernel (10^10 patterns/s). Forecast from the
sweep: open-at-96 patterns ≈ 1×10^-8 × level-12 patterns (median; 90th percentile 3×10^-7), Lemma C depth 1
closes 94% of them, the sandwich closes the rest at depth ≈ max(2, ⌈(log10 G(k,a) − 24)/48⌉).

| tier | tree | vertex s | 2^a3^b7^c | level-12 patterns | k_max | multisets | days, 1 core @8ns | days, 10 cores @8ns | GPU days @1e10/s | forecast open@96 | forecast sandwich depth |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | A_6 | 184473632 | 2^5·3^0·7^8 | 9.75e+09 | 13 | 5 | 0.0 | 0.00 | 0.00 | 1e+02 | 5 |
| A | A_8 | 131712 | 2^7·3^1·7^3 | 9.85e+09 | 11 | 15 | 0.0 | 0.00 | 0.00 | 1e+02 | 4 |
| A | A_6 | 133413966 | 2^1·3^4·7^7 | 1.32e+10 | 12 | 5 | 0.0 | 0.00 | 0.00 | 1e+02 | 4 |
| A | A_6 | 122472 | 2^3·3^7·7^1 | 1.57e+10 | 11 | 26 | 0.0 | 0.00 | 0.00 | 2e+02 | 4 |
| A | A_8 | 13824 | 2^9·3^3·7^0 | 1.72e+10 | 12 | 59 | 0.0 | 0.00 | 0.00 | 2e+02 | 4 |
| A | A_6 | 24192 | 2^7·3^3·7^1 | 1.87e+10 | 11 | 39 | 0.0 | 0.00 | 0.00 | 2e+02 | 4 |
| A | A_8 | 691488 | 2^5·3^2·7^4 | 2.25e+10 | 11 | 17 | 0.0 | 0.00 | 0.00 | 2e+02 | 4 |
| A | A_8 | 18432 | 2^11·3^2·7^0 | 2.25e+10 | 13 | 58 | 0.0 | 0.00 | 0.00 | 2e+02 | 5 |
| A | A_2 | 1229312 | 2^9·3^0·7^4 | 2.46e+10 | 13 | 12 | 0.0 | 0.00 | 0.00 | 2e+02 | 5 |
| A | A_6 | 666792 | 2^3·3^5·7^3 | 3.54e+10 | 11 | 19 | 0.0 | 0.00 | 0.00 | 4e+02 | 4 |
| A | A_2 | 368947264 | 2^6·3^0·7^8 | 3.75e+10 | 14 | 7 | 0.0 | 0.00 | 0.00 | 4e+02 | 5 |
| A | A_8 | 1121144263281 | 2^0·3^4·7^12 | 3.86e+10 | 16 | 3 | 0.0 | 0.00 | 0.00 | 4e+02 | 6 |
| A | A_6 | 1162261467 | 2^0·3^19·7^0 | 4.90e+10 | 19 | 10 | 0.0 | 0.00 | 0.00 | 5e+02 | 7 |
| A | A_8 | 112896 | 2^8·3^2·7^2 | 6.35e+10 | 12 | 35 | 0.0 | 0.00 | 0.00 | 6e+02 | 4 |
| A | A_2 | 314928 | 2^4·3^9·7^0 | 7.03e+10 | 13 | 50 | 0.0 | 0.00 | 0.00 | 7e+02 | 5 |
| A | A_6 | 1382976 | 2^6·3^2·7^4 | 8.96e+10 | 12 | 23 | 0.0 | 0.00 | 0.00 | 9e+02 | 4 |
| A | A_6 | 41472 | 2^9·3^4·7^0 | 9.29e+10 | 13 | 84 | 0.0 | 0.00 | 0.00 | 9e+02 | 5 |
| A | A_8 | 1417176 | 2^3·3^11·7^0 | 9.58e+10 | 14 | 40 | 0.0 | 0.00 | 0.00 | 1e+03 | 5 |
| A | A_6 | 163296 | 2^5·3^6·7^1 | 1.13e+11 | 12 | 48 | 0.0 | 0.00 | 0.00 | 1e+03 | 4 |
| A | A_6 | 1843968 | 2^8·3^1·7^4 | 1.24e+11 | 13 | 18 | 0.0 | 0.00 | 0.00 | 1e+03 | 5 |
| A | A_6 | 139968 | 2^6·3^7·7^0 | 1.42e+11 | 13 | 76 | 0.0 | 0.00 | 0.00 | 1e+03 | 5 |
| A | A_2 | 93312 | 2^7·3^6·7^0 | 1.50e+11 | 13 | 85 | 0.0 | 0.00 | 0.00 | 1e+03 | 5 |
| A | A_2 | 3111696 | 2^4·3^4·7^4 | 1.61e+11 | 12 | 24 | 0.0 | 0.00 | 0.00 | 2e+03 | 4 |
| A | A_6 | 96768 | 2^9·3^3·7^1 | 2.07e+11 | 13 | 59 | 0.0 | 0.00 | 0.00 | 2e+03 | 5 |
| A | A_6 | 3687936 | 2^9·3^1·7^4 | 3.90e+11 | 14 | 22 | 0.0 | 0.00 | 0.00 | 4e+03 | 5 |
| A | A_8 | 124416 | 2^9·3^5·7^0 | 4.28e+11 | 14 | 105 | 0.0 | 0.00 | 0.00 | 4e+03 | 5 |
| A | A_8 | 4148928 | 2^6·3^3·7^4 | 5.76e+11 | 13 | 31 | 0.1 | 0.01 | 0.00 | 6e+03 | 5 |
| A | A_2 | 393216 | 2^17·3^1·7^0 | 6.01e+11 | 18 | 63 | 0.1 | 0.01 | 0.00 | 6e+03 | 7 |
| A | A_6 | 1778112 | 2^6·3^4·7^3 | 8.04e+11 | 13 | 44 | 0.1 | 0.01 | 0.00 | 8e+03 | 5 |
| A | A_6 | 2667168 | 2^5·3^5·7^3 | 8.73e+11 | 13 | 39 | 0.1 | 0.01 | 0.00 | 9e+03 | 5 |
| A | A_6 | 19361664 | 2^7·3^2·7^5 | 1.05e+12 | 14 | 28 | 0.1 | 0.01 | 0.00 | 1e+04 | 5 |
| A | A_6 | 221184 | 2^13·3^3·7^0 | 1.13e+12 | 16 | 110 | 0.1 | 0.01 | 0.00 | 1e+04 | 6 |
| A | A_6 | 3211264 | 2^16·3^0·7^2 | 1.18e+12 | 18 | 30 | 0.1 | 0.01 | 0.00 | 1e+04 | 7 |
| A | A_6 | 331776 | 2^12·3^4·7^0 | 2.33e+12 | 16 | 139 | 0.2 | 0.02 | 0.00 | 2e+04 | 6 |
| A | A_2 | 11239424 | 2^15·3^0·7^3 | 2.33e+12 | 18 | 27 | 0.2 | 0.02 | 0.00 | 2e+04 | 7 |
| A | A_8 | 3779136 | 2^6·3^10·7^0 | 4.19e+12 | 16 | 113 | 0.4 | 0.04 | 0.00 | 4e+04 | 6 |
| A | A_6 | 2939328 | 2^6·3^8·7^1 | 5.63e+12 | 15 | 90 | 0.5 | 0.05 | 0.01 | 6e+04 | 6 |
| A | A_6 | 69441624 | 2^3·3^11·7^2 | 7.47e+12 | 16 | 40 | 0.7 | 0.07 | 0.01 | 7e+04 | 6 |
| A | A_6 | 3281116734 | 2^1·3^14·7^3 | 7.49e+12 | 18 | 15 | 0.7 | 0.07 | 0.01 | 7e+04 | 7 |
| A | A_4 | 1161216 | 2^11·3^4·7^1 | 1.00e+13 | 16 | 118 | 0.9 | 0.09 | 0.01 | 1e+05 | 6 |
| A | A_2 | 7112448 | 2^8·3^4·7^3 | 1.04e+13 | 15 | 69 | 1.0 | 0.10 | 0.01 | 1e+05 | 6 |
| A | A_6 | 13226976 | 2^5·3^10·7^1 | 1.17e+13 | 16 | 80 | 1.1 | 0.11 | 0.01 | 1e+05 | 6 |
| A | A_6 | 46294416 | 2^4·3^10·7^2 | 1.57e+13 | 16 | 57 | 1.4 | 0.14 | 0.02 | 2e+05 | 6 |
| A | A_2 | 1741824 | 2^10·3^5·7^1 | 1.59e+13 | 16 | 126 | 1.5 | 0.15 | 0.02 | 2e+05 | 6 |
| A | A_6 | 1492992 | 2^11·3^6·7^0 | 1.61e+13 | 17 | 190 | 1.5 | 0.15 | 0.02 | 2e+05 | 6 |
| A | A_6 | 9483264 | 2^10·3^3·7^3 | 1.91e+13 | 16 | 70 | 1.8 | 0.18 | 0.02 | 2e+05 | 6 |
| A | A_2 | 9633792 | 2^16·3^1·7^2 | 2.02e+13 | 19 | 57 | 1.9 | 0.19 | 0.02 | 2e+05 | 7 |
| A | A_2 | 116169984 | 2^8·3^3·7^5 | 2.34e+13 | 16 | 48 | 2.2 | 0.22 | 0.03 | 2e+05 | 6 |
| A | A_6 | 914838624 | 2^5·3^5·7^6 | 2.97e+13 | 16 | 39 | 2.7 | 0.27 | 0.03 | 3e+05 | 6 |
| A | A_6 | 23612624896 | 2^12·3^0·7^8 | 3.05e+13 | 20 | 19 | 2.8 | 0.28 | 0.04 | 3e+05 | 7 |
| A | A_8 | 33718272 | 2^15·3^1·7^3 | 3.95e+13 | 19 | 51 | 3.7 | 0.37 | 0.05 | 4e+05 | 7 |
| A | A_6 | 13716864 | 2^7·3^7·7^2 | 4.24e+13 | 16 | 99 | 3.9 | 0.39 | 0.05 | 4e+05 | 6 |
| A | A_6 | 9437184 | 2^20·3^2·7^0 | 6.44e+13 | 22 | 165 | 6.0 | 0.60 | 0.07 | 6e+05 | 8 |
| B | A_6 | 71663616 | 2^15·3^7·7^0 | 3.13e+15 | 22 | 406 | 289.8 | 28.98 | 3.62 | 3e+07 | 8 |
| B | A_6 | 226492416 | 2^23·3^3·7^0 | 4.29e+15 | 26 | 308 | 397.2 | 39.72 | 4.97 | 4e+07 | 9 |
| B | A_8 | 1194891264 | 2^11·3^5·7^4 | 5.32e+15 | 20 | 149 | 492.5 | 49.25 | 6.16 | 5e+07 | 7 |
| B | A_6 | 169869312 | 2^21·3^4·7^0 | 5.73e+15 | 25 | 382 | 530.6 | 53.06 | 6.63 | 6e+07 | 9 |
| B | A_8 | 4182119424 | 2^10·3^5·7^5 | 5.79e+15 | 20 | 126 | 535.7 | 53.57 | 6.70 | 6e+07 | 7 |
| B | A_6 | 1792336896 | 2^10·3^6·7^4 | 7.41e+15 | 20 | 161 | 686.5 | 68.65 | 8.58 | 7e+07 | 7 |
| B | A_6 | 13884223438848 | 2^14·3^1·7^10 | 1.56e+16 | 25 | 45 | 1442.7 | 144.27 | 18.03 | 2e+08 | 9 |
| B | A_6 | 2113929216 | 2^25·3^2·7^1 | 2.84e+16 | 28 | 247 | 2632.6 | 263.26 | 32.91 | 3e+08 | 10 |
| B | A_2 | 1811939328 | 2^26·3^3·7^0 | 3.41e+16 | 29 | 387 | 3155.5 | 315.55 | 39.44 | 3e+08 | 11 |
| B | A_6 | 11329339392 | 2^19·3^2·7^4 | 4.04e+16 | 25 | 150 | 3738.9 | 373.89 | 46.74 | 4e+08 | 9 |
| B | A_6 | 4444263936 | 2^9·3^11·7^2 | 4.39e+16 | 22 | 262 | 4067.9 | 406.79 | 50.85 | 4e+08 | 8 |
| B | A_6 | 3699376128 | 2^23·3^2·7^2 | 4.61e+16 | 27 | 212 | 4265.9 | 426.59 | 53.32 | 5e+08 | 10 |
| B | A_8 | 1783627776 | 2^20·3^5·7^1 | 1.57e+17 | 26 | 449 | 14507.8 | 1450.78 | 181.35 | 2e+09 | 9 |
| C | A_6 | 3416267673274176 | 2^6·3^27·7^1 | 1.72e+19 | 34 | 306 | 1596297.1 | 159629.71 | 19953.71 | 2e+11 | 12 |
| C | A_4 | 128421199872 | 2^23·3^7·7^1 | 2.57e+19 | 31 | 925 | 2375759.4 | 237575.94 | 29696.99 | 3e+11 | 11 |
| C | A_6 | 913217421312 | 2^29·3^5·7^1 | 8.59e+19 | 35 | 911 | 7958280.1 | 795828.01 | 99478.50 | 9e+11 | 12 |
| C | A_8 | 727326941773824 | 2^39·3^3·7^2 | 5.53e+21 | 44 | 834 | 512128986.8 | 51212898.68 | 6401612.33 | 6e+13 | 12 |
| C | A_8 | 112717121716224 | 2^34·3^8·7^0 | 9.86e+21 | 42 | 2446 | 913324811.8 | 91332481.18 | 11416560.15 | 1e+14 | 12 |
| C | A_6 | 1438916737499136 | 2^24·3^6·7^6 | 1.38e+22 | 36 | 829 | 1277494321.3 | 127749432.13 | 15968679.02 | 1e+14 | 12 |

## Tiers

- **Tier A — 53 vertices, 3.9e+14 patterns in all.** The running Mac sweep (cap 2e13) covers all but the
  six between 2e13 and 7e13. At 8 ns on 10 cores the whole tier is ≈ 4 days; at the sweep's current
  66 ns ≈ 30 days. Forecast: all close (open@96 up to ~6×10^5 per vertex, k ≤ 22, sandwich depth ≤ 7).
  The sandwich at that scale needs the cut in C, not Python (10^4–10^5 patterns × thousands of sub-cosets).
- **Tier B — 13 vertices (together with Tier C: 19, not the 18 quoted earlier), 4.0e+17 patterns, k = 20–29.** CPU-infeasible on one Mac (10 years on 10 cores);
  a GPU level-12 kernel at 10^10/s makes the six smallest (3–7×10^15) ≈ 1 month in all and the tier ≈ 15 months.
  The lift 12→24 (2^(k+1) children per survivor, 1/40 of patterns) is then the bottleneck: it also needs the GPU or a smarter lift.
- **Tier C — 6 vertices, 2.9e+22 patterns, k = 31–44.** Not computable by enumeration on any hardware we have
  (10^22 patterns). This is the true frontier; it contains 128421199872 (the last A_4 vertex: closing it would
  bound the persistence of every number with digital root 4). New mathematics or nothing.

## What closes a frontier vertex, once enumerated

Levels 12→96 (C), Lemma C depth 1 (closes ~94%), the sandwich for the rest: depth D with
10^(72+48(D−1)) > G(k, a). For k = 22: G ≈ 10^317, D = 6–7; sub-coset counts grow ~×3–5 per depth, so
≈ 10^4 cut operations per surviving pattern — fine in C, slow in Python.

## Forecast registration

Open@96 per vertex = patterns × 1×10^-8 (interval ×0.1–×30); survivors after Lemma C = 6% of those; every
survivor closes by the sandwich at the depth above. A Tier-A vertex whose counts fall outside those intervals is
audited before its result is used.


## Tier C after the fan-out (2026-10-20 18:45 EDT; RESULT-anchorfirst.md, RESULT-dpcount.md, LIT2.md)

Three independent scouts, one conclusion: **Tier C is beyond every method we have or the literature has.**
- *Exact survivor counting* (dpcount): level-12 survival is a one-pass dense DP over Z/P, P = 5 291 005 291 —
  the count of a 10^22 enumeration without doing it — but it is a 64 GB-RAM job per equation (10.6 GB minimum
  state), ~100 node-days for the 6 251 Tier-C equations; validated exactly against 12 recorded equations
  (zero / prefilter-dead / (a,pattern) counts reproduced to the unit). Monte Carlo with the exact test
  (6.2×10^8 samples): survival 1/49.5 for every vertex (generic: (1 − ∏(1−1/p))/40), survivors 3×10^17–3×10^20,
  level-24 lift inputs 10^24–10^28 per vertex. The lift, not level 12, is the wall; and the engine's 2-adic
  bound A does not terminate for k ≥ 36 multisets (true A ≥ 100–160).
- *Anchor-first* (prediction under the anchoring hypothesis): ~10^5 anchor (y, k) pairs per vertex carrying
  10^11–10^14 anchored patterns at level 96 — agreeing within ×0.9–1.7 with the sweep-calibrated forecast
  (1×10^-8 × patterns) for all six vertices (two independent routes; strongest Tier-C evidence for the
  hypothesis). Wrap values k up to ~115 occur (the 0 ≤ k ≤ 9 of OPEN-PATTERNS.md is a property of small
  vertices). Lemma C depth 1 kills 90–99.99% per pattern; what is left is 10^9–10^12 survivors per vertex, each
  needing a depth-7–18 sandwich over 2^k sub-cosets: not finishable. 40/40 sampled patterns closed at depth 1;
  nothing resembles a genuinely open equation. What is missing is a closure *per anchor* (one coset for all
  patterns of an anchor; ~10^5–10^6 objects per vertex) rather than per pattern.
- *Literature* (LIT2): no effective upper bound better than (C log n)^k exists (Stewart 1980, Bugeaud–Kaneko
  2018, Bugeaud 2018/2026); polynomial-in-k would follow from abc / Robert–Stewart–Tenenbaum (then ~5×10^3
  digits at k = 44 — a 10^11 search) but is conditional and inadmissible under RULE 2; every complete resolution
  of a many-term exponential equation on record enumerates residue classes and pays exponentially per term
  (Dimitrov–Howe 2021: ×3.5 per term; Bajpai–Bennett 2023: 5 terms is the effective frontier).

So the even-target conjecture reduces, with everything we have, to these six equations — stated with their
exact sizes above — and the honest paper says so. The one research direction with a shape is the per-anchor
closure; it is a new question, not a computation.
