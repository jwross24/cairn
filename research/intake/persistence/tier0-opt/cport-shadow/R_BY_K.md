# r by k on the 1,335 final-stage sandwich patterns

Source: `cport_shadow shadow --stats runs/stats1335.tsv` (one row per representation: k, words, min r, max r, sum of 2^(r+1), histogram of r over words),
inputs `data/cases_1335.txt` (the 1,335 patterns of `FINAL-STAGE-run-U2.txt`, snapshot md5 a6911e81 of trees_mac), C Lemma C depth-1 enumeration of
`cport.c` (dc_stage D = 1, unchanged). Aggregation script output: `runs/rbyk_summary.json`.

Definitions. A pattern has k non-1 digits. Each representation (nu, positions) of the anchor gives the depth-1 words (Lemma C at K = 96).
A word fixes some digits at copy 0; **r = the digits it leaves unplaced** (copy t >= 1). "Words" counts depth-1 words summed over the
representations of a pattern. `sum 2^(r+1)` is the child count of the word lift 96 -> 192 for the pattern (the cost the shadow certificate avoids).

| k | patterns | representations | reps with a word | words | r over words: min / median / mean / max | max r on a pattern | mean words per pattern | mean sum 2^(r+1) | max sum 2^(r+1) | 3^(k-9) |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 2 | 2 | 2 | 3 | 1 / 1 / 1.00 / 1 | 1 | 1.5 | 6 | 8 | |
| 6 | 8 | 9 | 8 | 11 | 1 / 2 / 1.82 / 3 | 3 | 1.4 | 11 | 40 | |
| 7 | 26 | 41 | 27 | 50 | 0 / 3 / 2.58 / 4 | 4 | 1.9 | 30 | 160 | |
| 8 | 126 | 441 | 153 | 324 | 0 / 4 / 3.54 / 5 | 5 | 2.6 | 75 | 576 | |
| 9 | 248 | 1461 | 384 | 928 | 0 / 4 / 4.28 / 6 | 6 | 3.7 | 197 | 2.3e3 | 1 |
| 10 | 333 | 3383 | 585 | 1629 | 0 / 5 / 4.92 / 7 | 7 | 4.9 | 424 | 7.3e3 | 3 |
| 11 | 268 | 4032 | 597 | 2845 | 0 / 6 / 5.48 / 8 | 8 | 10.6 | 1.4e3 | 1.9e4 | 9 |
| 12 | 172 | 3041 | 455 | 3600 | 2 / 6 / 6.18 / 9 | 9 | 20.9 | 4.3e3 | 4.8e4 | 27 |
| 13 | 84 | 1532 | 246 | 2321 | 3 / 7 / 6.92 / 10 | 10 | 27.6 | 1.0e4 | 1.5e5 | 81 |
| 14 | 40 | 798 | 126 | 1299 | 4 / 9 / 8.26 / 11 | 11 | 32.5 | 2.9e4 | 2.0e5 | 243 |
| 15 | 15 | 205 | 42 | 611 | 5 / 10 / 9.60 / 12 | 12 | 40.7 | 1.0e5 | 6.4e5 | 729 |
| 16 | 9 | 94 | 23 | 480 | 6 / 9 / 9.25 / 12 | 12 | 53.3 | 1.6e5 | 5.1e5 | 2.2e3 |
| 17 | 3 | 10 | 6 | 200 | 8 / 10 / 9.96 / 13 | 13 | 66.7 | 2.4e5 | 5.4e5 | 6.6e3 |
| 18 | 1 | 1 | 1 | 24 | 12 / 13 / 12.75 / 14 | 14 | 24.0 | 3.7e5 | 3.7e5 | 2.0e4 |

Totals: 1,335 patterns, 15,050 representations, 14,325 depth-1 words; every pattern has at least one word. Histogram of r over all words:
r = 0..14 -> 6, 55, 190, 620, 1603, 2665, 3120, 2585, 1529, 886, 511, 361, 169, 22, 3.

Observations (read off the table; the sample is the 1,335 patterns that survive Lemma C depth 1, so it is biased toward large r by construction).

- r grows with k at about 0.55 k to 0.72 k (median r / k: 0.20 at k = 5, 0.50 at k = 10, 0.56 at k = 16, 0.72 at k = 18); the maximum on a pattern
  is r = k - 3 or k - 4 for k >= 14. The planning figure "r <= 7 as at k <= 11" holds for k <= 10 only (max r 7 at k = 10), and fails from k = 11 (max 8) on.
- Words per pattern grow with k (1.4 at k = 6, 10.6 at k = 11, 53 at k = 16), roughly doubling per two units of k up to k = 12 and slower beyond (small samples at k >= 16).
- The mean word-lift child count `sum 2^(r+1)` grows from 11 (k = 6) to 3.7e5 (k = 18). It exceeds the WORDLIFT.md estimate 3^(k-9) at every k:
  by a factor 160 at k = 12, 140 at k = 15, 19 at k = 18 (mean over the patterns of that k). In this sample the estimate is low, not high.
  The exponent of the copy choices is not removed by the word lift; the shadow certificate (one DP over Z/148417 per representation) is the part
  that removes it.
- Limits: k <= 18 here, the k = 20..29 Tier-B range is an extrapolation; r is measured at level 96 depth 1 on representations of anchors from the
  sweep files, not on Tier-B anchors.
