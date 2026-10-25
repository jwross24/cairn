# TB-ANCHORED: anchored side of Tier B vertex 71663616 (all 195,464 depth-1 survivors certified) and the anchored bill of all 13 Tier B vertices

P = /Users/jwross/Documents/cairn/research/intake/persistence. Everything is in `P/tier0-opt/tierb-anchored/`; nothing in `P/tier0/`, `sandwich-cong/`, `tierc-r2shadow/` or `tierc-r2bill/` was edited (read in place; the one binary I used from `sandwich-cong/` and the one from `tierc-r2shadow/` were copied to `bin/`). `PREDICTION.md` was written before any compute and is unedited except one timestamp typo (16:12 corrected to 15:59 EDT, before any compute).

Labels (exact): vertex 71663616: **anchored side closed by the cut/sandwich (U''), conditional on Lemma C, Matveev, Yu 2007 Thm II and the pattern list; unanchored side open (Hypothesis H).** The vertex itself is not called closed. The 12 other vertices are priced, not closed.

## 0. Answer

1. **Exact enumeration of the whole anchored census of 71663616** (66,193 (y,k,nu) cells, 299,922,194 patterns; every cell's pattern count equals the census count, 0 mismatches): **195,464 patterns survive depth 1 = 0.0652% (exact count, no sampling error)**. Wrap 0: 193,683 of 125,161,748 (0.155%). Wrap >= 1: **1,781** of 174,760,446 (0.00102%), not zero. 96.3% of the survivors sit on anchors with a <= 4 (188,277 of 195,464); none has a >= 15.
2. **All 195,464 survivors went through the certificate engine; 195,464 closed** (50,578 closed by the cut = 25.9%; 144,886 closed by the sandwich (U'') = 74.1%); open 0, BUDGET 0, NOTAPPL 0, ERROR 0, killed 0. The 1,781 wrap >= 1 survivors are all closed (740 cut, 1,041 sandwich). Total 4,639 CPU-s = 1.29 CPU-hours (mean 0.0237 s, median 0.0176 s, p99 0.096 s, max 0.378 s; peak RSS 20 MB). Engine: `cport_cong --word-mitm` (see Section 4 for the engine switch and its checks).
3. Registered chat prediction: survival 0.2% +- 0.05: **FALSE** (exact 0.0652%). Zero wrap >= 1 survivors: **FALSE** (1,781). Every survivor CLOSED-cut or sandwich, none open: **TRUE** (195,464/195,464).
4. All 13 vertices, anchored side, from measurement: **about 1.3e7 depth-1 survivors [0.8e7, 1.9e7]; certificate bill about 5.0 core-days [2.4, 8.8]**; plus the enumeration pass of about 1.5 microseconds per pattern (1.7e10 patterns: about 7 CPU-hours). This is roughly 0.5 day on 10 cores. SPRINT-TIERBC's "days on the Mac" was right in order; "10^6 to 10^7 core-seconds" overestimated by about 30x (measured 4.3e5 core-s).

## 1. The depth-1 congruence and what it reduces to

Theorem F with wrap (HSHADOW addendum, check_wplus.py 3b9248e0, CHECK-WPLUS.txt 6367e6f4): a word (fixed set F with at most one digit per position class, U-set the rest) survives iff 10^nu + 9 S_U + w == 0 mod 2^(a+9) 5^5 (d1 = 2^7...5^4..., v2 = 7, v5 = 4). With 9V = 9y + w(10^96 - 1) - (10^nu - 1) and S_U = T - sum_F (T = V - R_nu, the digit mass), the left side equals 9y + 1 - 9 sum_F(d-1)10^e + w 10^96 == 9(y - L) mod the modulus, where L = R_96 + sum_F (d-1)10^e (10^96 vanishes mod 2^(a+9) 5^5 since a + 9 <= 69). So **the word survives iff L == y mod 2^(a+9) 5^5**; w and nu enter only through which digits the representation has. Only digits at positions e < a + 9 can change L modulo that modulus, so survival of a pattern is a function of its low-position configuration (e < a + 9). `enum_surv.c` enumerates the low configurations by DFS over the exact backward DP counts (a port of `tierc-rank/anchor_dp.c` with the forward-layer-pruned backward table), tests "exists F with L == y" with 2-adic and 5-adic prefix pruning, and adds the number of completions (exact `G` count) for survivors and non-survivors. Count-conservation: survivors + non-survivors = census count for all 66,193 cells (0 mismatches); the same for vertex 4 (101,763 cells, 287,670,253 patterns) and vertex 8 (117,031 cells, 1,560,031,123 patterns). This is the congruence derived from the addendum plus the elementary reduction above; it is not the shipped check_wplus code.

Reference for the cross-check: `d5b_depth1.py` (md5 8b6e556d) cannot run here (its libraries `anchorlib`, `sandwich_lite` and the `/home/claude` paths are not on disk). The reference used is the exact word enumeration of `tier0/wordlift.py::depth1_words` (the same objects as `check_wplus.py`): all choices of at most one digit per class, v2(L) == a and 5 not dividing L, then `descent.cut_coset(co0, a, L, 96)` non-empty with `co0 = Coset((b_y, c_y), Lam96)`. `ref_check.py` is this with prefix pruning on v2 and 5 only (necessary conditions; the leaf test is the unmodified `cut_coset`). It also verifies the integer identity sum (d-1)10^e = y + k R_96 - R_nu and the digit product for every pattern.

## 2. Congruence versus exact cut

Uniform samples of the census (cells weighted by pattern count, then a uniform pattern in the cell by the exact DP), both wrap classes: 12,000 wrap 0 and 12,000 wrap >= 1, plus 400 survivors drawn uniformly from the 195,464 as positive controls.

| file (`work/`) | patterns | wrap 0: C reject / exact reject | wrap 0: C accept / exact accept | wrap >= 1: reject / reject | wrap >= 1: accept / accept | disagreements |
|---|---|---|---|---|---|---|
| xc_a.ref | 12,000 | 5,915 / 5,915 | 5 / 5 | 6,079 / 6,079 | 1 / 1 | 0 |
| xc_b_part_aa.ref | 3,100 | 1,589 / 1,589 | 4 / 4 | 1,507 / 1,507 | 0 | 0 |
| xc_b_part_ab.ref | 3,100 | 1,546 / 1,546 | 1 / 1 | 1,553 / 1,553 | 0 | 0 |
| xc_b_part_ac.ref | 3,100 | 1,573 / 1,573 | 2 / 2 | 1,525 / 1,525 | 0 | 0 |
| xc_b_part_ad.ref (2,700 uniform + 400 enriched survivors) | 3,100 | 1,363 / 1,363 | 397 / 397 | 1,335 / 1,335 | 5 / 5 | 0 |
| **total** | **24,400** | | | | | **0** |

The uniform part is 24,000 patterns (12,000 wrap 0 and 12,000 wrap >= 1 by construction of the plan, `mk_plan.py`), of which 15 are depth-1 survivors by the C congruence (`work/xc_v0.out`: 23,985 rejects, 15 accepts) and the exact reference agrees on all 24,000; the 400 enriched survivors (a uniform draw from the 195,464, first 400 of `surv_v0_s3000.txt`) all accepted by both. Identity failures 0. A further run of 60 enriched survivors (`xc_pos60.ref`, a subset of the same 400) gave 60 of 60 agreeing accepts. The exact reference needed no reduction of the choice set (`reduced 0`). It took about 12 CPU-hours of the Mac in total (about 1.2 s per uniform pattern).

Planted non-survivors: 6 survivors with their lowest-position digit moved up by one position (`mk_planted.py`, `plant_run.py`): the original survives in both C and the exact reference (6/6), the planted pattern is rejected by both (6/6). The comparison can fail (it reports MISMATCH per pattern) and both classes occur in it: accepted and rejected patterns each agree.

## 3. Verdicts and cost, vertex 71663616 (all 195,464 survivors; `results_all2.jsonl` md5 5f7c9721, `summ_v0.json`)

| digits k | survivors | closed by the cut | closed by the sandwich | mean CPU-s | median | max |
|---|---|---|---|---|---|---|
| 10 | 123 | 14 | 109 | 0.016 | 0.016 | 0.028 |
| 11 | 668 | 128 | 540 | 0.016 | 0.015 | 0.042 |
| 12 | 5,208 | 1,147 | 4,061 | 0.016 | 0.015 | 0.050 |
| 13 | 15,228 | 3,479 | 11,749 | 0.018 | 0.016 | 0.105 |
| 14 | 27,175 | 7,435 | 19,740 | 0.020 | 0.017 | 0.148 |
| 15 | 38,954 | 10,962 | 27,992 | 0.021 | 0.016 | 0.207 |
| 16 | 42,265 | 11,090 | 31,175 | 0.024 | 0.017 | 0.339 |
| 17 | 33,879 | 8,446 | 25,433 | 0.028 | 0.020 | 0.378 |
| 18 | 20,185 | 5,214 | 14,971 | 0.029 | 0.022 | 0.213 |
| 19 | 8,621 | 2,134 | 6,487 | 0.030 | 0.022 | 0.205 |
| 20 | 2,448 | 450 | 1,998 | 0.029 | 0.023 | 0.173 |
| 21 | 625 | 79 | 546 | 0.031 | 0.027 | 0.094 |
| 22 | 85 | 0 | 85 | 0.031 | 0.030 | 0.062 |
| all | 195,464 | 50,578 | 144,886 | 0.0237 | 0.0176 | 0.378 |

CPU is user + sys of one `nice -n 10` process per survivor, including process start (about 0.015 s). Guards: 3 GB RSS, 7,200 CPU-s each; none fired; no stage needed raised caps; no BUDGET. k is the number of non-1 digits. Survivors with k > 22 do not exist at this vertex (k_max 22). The U'' table is `tierc-r2bill/data/utable_u2_k34.txt` (e15bb126), covering every (k, a) that occurs.

Cost is flat in k here (0.016 to 0.031 s), unlike Tier C rank-2 (R2BILL: seconds to 10^3 s at k >= 25), because k <= 22 stays well below the regime where the level-480 child space blows up, and because `--word-mitm` cuts the meet-in-the-middle space. Survival by a (pattern counts in parentheses): a = 0: 66,374 (3.54e7); 1: 31,851; 2: 27,257; 3: 22,759; 4: 40,036; 5: 3,434; 6: 786; 7: 651; 8: 353; 9: 1,782; 10: 103; 11: 6; 12: 2; 13: 11; 14: 59; none for a >= 15.

## 4. Engines, regression, controls (which engine produced which verdict)

| engine | binary md5 | used for |
|---|---|---|
| `cport_cong --word-mitm` (sandwich-cong, copied to `bin/`) | 4669f006bd6f77e708bbb32daa0ad4f2 | all 195,464 vertex-0 verdicts (`results_all2.jsonl`), vertex 4 and 8 thinned samples, the 10 sampled vertices, controls, inflated negative |
| `cport_r2c` (tierc-r2shadow, copied to `bin/`) | 44a21fe793f6d93d432f30d98878ab17 | the 1,335 regression, 300 survivors on the old engine, inflated negative on the old engine |

* Regression 1,335 cases (`shadow480`, `utable_u2.txt`): `cport_cong --word-mitm` and `cport_r2c` both produce a TSV with sha256 b50d28407773bf762...cb34b2 (md5 a9576d7f9ea97b41d6b27dd61186624e), byte-equal to `cport-shadow480w/runs/x4w_480_1335.tsv` (`runs/reg1335_cong.tsv`, `runs/reg1335_r2c.tsv`).
* Both engines on the same 300 survivors (the first 300 of a uniform random 3,000-survivor sample): 300 of 300 identical label and identical VERDICT line (timing removed). CPU 7.5 s (cong) vs 9.0 s (r2c) in total: at k <= 22 the old engine is already fast, the sixteen-fold gain is for k >= 25.
* R2BILL control cases C1 to C5 (`tierc-r2bill/data/rep_C*.rep`, 5 rank-2 survivors): 5 of 5 closed by the sandwich with `cport_cong`, as recorded in R2BILL.
* Planted negative: U'' set to 10^400 (`utable_inflated_400_k34.txt`, 7cc685d6) on 8 survivors that the real table closes by the sandwich, plus 4 closed by the cut: both engines give 8 of 8 `open` and 4 of 4 still closed by the cut (the cut does not use U''). A gate shown to refuse: zero sandwich closures under the inflated table.
* Count conservation and the exact backward-DP counts of the C port equal the census counts for 66,193 + 101,763 + 117,031 cells.

## 5. The bill for all 13 vertices (anchored side only)

Exact enumeration with thinned survivor emission (a uniform Bernoulli thinning of the survivors, then every thinned survivor certified): vertices 0 (all survivors certified), 4 (p = 0.1: 16,065 of 160,868) and 8 (p = 0.02: 26,384 of 1,317,160). The other ten vertices: 2,000 cells drawn with probability proportional to pattern count, exact survival fraction per cell, thinned survivors certified (3,000 per vertex), bootstrap 95% interval over the 2,000 draws. **Calibration of the sampler on vertex 0, where the answer is exact: the sample estimate was 3.9e-4 [2.3e-4, 5.7e-4] against the exact 6.52e-4, so the 95% interval missed the truth; the sampled vertices are probably underestimated by a factor 1.3 to 1.7 (heavy-tailed cells). Do not retry this sampler for rates without more cells; use the exact pass.**

| v | s | patterns | basis | survivors (95%) | certificate CPU-s (95%) | core-days |
|---|---|---|---|---|---|---|
| 0 | 71663616 | 2.999e8 | exact; all certified | 195,464 | 4,639 (census) | 0.05 |
| 1 | 226492416 | 3.121e8 | sampled | 2.36e5 [1.06e5, 4.01e5] | 4,791 [1,748, 8,771] | 0.06 |
| 2 | 1194891264 | 3.133e8 | sampled | 1.17e5 [6.9e4, 1.75e5] | 2,035 [1,115, 3,160] | 0.02 |
| 3 | 169869312 | 4.270e8 | sampled | 2.19e5 [1.0e5, 3.71e5] | 6,290 [1,644, 13,351] | 0.07 |
| 4 | 4182119424 | 2.877e8 | exact; thinned certified | 160,868 | 5,139 [5,064, 5,221] | 0.06 |
| 5 | 1792336896 | 4.070e8 | sampled | 2.54e5 [1.31e5, 4.28e5] | 6,595 [2,491, 13,772] | 0.08 |
| 6 | 13884223438848 | 2.888e8 | sampled | 2.21e5 [8.0e4, 4.01e5] | 7,765 [1,819, 16,025] | 0.09 |
| 7 | 2113929216 | 1.334e9 | sampled | 7.69e5 [3.62e5, 1.31e6] | 22,912 [9,997, 40,529] | 0.27 |
| 8 | 1811939328 | 1.560e9 | exact; thinned certified | 1,317,160 | 42,506 [41,675, 43,412] | 0.49 |
| 9 | 11329339392 | 1.374e9 | sampled | 1.23e6 [6.7e5, 1.92e6] | 46,690 [17,589, 85,441] | 0.54 |
| 10 | 4444263936 | 1.978e9 | sampled | 6.39e5 [3.43e5, 1.01e6] | 11,802 [5,928, 19,283] | 0.14 |
| 11 | 3699376128 | 1.892e9 | sampled | 1.83e6 [1.08e6, 2.69e6] | 73,924 [35,501, 121,671] | 0.86 |
| 12 | 1783627776 | 6.649e9 | sampled | 5.78e6 [3.58e6, 8.68e6] | 198,071 [76,041, 384,859] | 2.29 |
| total | | 1.712e10 | | 1.30e7 [0.82e7, 1.91e7] | 433,160 [205,250, 760,133] | 5.0 [2.4, 8.8] |

For the exact vertices the survivor count is exact; the interval on the CPU-s is the bootstrap on the certified sample's mean cost only. CPU-s counts include process start (about 0.015 s each).

Exact survival rates: vertex 0 6.52e-4 (195,464), vertex 4 5.59e-4 (160,868), vertex 8 8.44e-4 (1,317,160). Wrap >= 1 survivors: v0 1,781; v4 2,115; v8 145,039 (11% of v8's survivors). Verdicts in all certified samples: closed only (cut or sandwich); v4: 3,117 cut / 12,948 sandwich; v8: 4,953 cut / 21,431 sandwich; the ten sampled vertices 0 open, 0 BUDGET in about 30,000 certified survivors (`est_v*.json`, `results_sv*.jsonl`). v8 (k up to 29): mean 0.032 s, max 1.9 s, peak RSS 415 MB; v4: mean 0.032 s, max 0.93 s.

Enumeration cost (count/emit pass, one process, `nice`, under machine load average 20 to 50): vertex 0 about 15 minutes wall (8.5 CPU-min), vertex 4 about 30 minutes, vertex 8 about 35 minutes; about 1.5 microseconds per pattern, so about 7 CPU-hours for 1.712e10 patterns. The earlier census DP (5,364 s) is not repeated here.

Total, central: survivors 1.30e7 [0.82e7, 1.91e7]; certificate CPU 4.3e5 s = **5.0 core-days [2.4, 8.8]** (sum of the per-vertex lower and upper bounds, so conservative); with the v0 calibration factor 1.7 applied to the ten sampled vertices the central rises to about 8 core-days. Either way: single-digit core-days, under a day on 10 cores.

## 6. Prediction scorecard

| claim | outcome |
|---|---|
| Chat: survival 0.2% +- 0.05 on 71663616 | **FALSE**: 0.0652% exact. The chat figure came from at most 30 patterns per hit over a hit sample; the exact count is 3.1x lower. Do not retry the hit-sample estimate. |
| Chat: zero wrap >= 1 survivors | **FALSE**: 1,781 (v0), 2,115 (v4), 145,039 (v8). The 0/53,279 sample missed a 1e-5 rate. |
| Chat: every survivor CLOSED-cut at 480/1152 or sandwich at >= 10^300, none open | **TRUE** on the 195,464 (cut 25.9%, sandwich 74.1%; sandwich bound about 10^302 digits against U'' far below it, e.g. 10^128 and 10^121 on two spot checks) |
| Mine: survivors 7.5e5 [4.5e5, 1.35e6] | **FALSE**: 1.95e5, 3.8x lower |
| Mine: wrap >= 1 survivors nonzero | TRUE |
| Mine: congruence vs exact 0 disagreements on >= 20,000 | TRUE (see Section 2) |
| Mine: cut-closed 60 to 90% | **FALSE**: 25.9% |
| Mine: zero open; BUDGET < 1% | TRUE (0 open, 0 BUDGET) |
| Mine: CPU/survivor median 0.3 s, mean 2 s [0.5, 10] | **FALSE**: median 0.018 s, mean 0.024 s (new engine; old engine 0.030 s on 300) |
| Mine: vertex 0 bill 17 core-days [3, 90] | **FALSE**: 0.054 core-days (1.29 CPU-h) |
| Mine: 13-vertex bill 1,000 core-days [150, 5,000] | **FALSE**: about 5 core-days [2.4, 8.8] |
| SPRINT-TIERBC: "10^6 to 10^7 core-seconds", days on the Mac | too high by about 30x: 4.3e5 core-s |
| Mine: failure modes (cport rejects c = 0 or wrap >= 1 reps; count mismatch with census) | did not occur |

## 7. Seams

1. The reference for the congruence is `wordlift.depth1_words`-equivalent with `cut_coset`, not `d5b_depth1.py` (unrunnable here). The 24,400 comparisons are one sample of the census; they test the congruence on the patterns the sample draws, with only 15 accepted patterns in the uniform part (positives are rare, 0.06%), plus 400 enriched survivors and 6 planted rejects. The rejects dominate; the positive side rests on the enriched set.
2. "Survives depth 1" here is the K = 96 window word test only. The certificate engine tests each survivor's representation (the recorded one), as in R2BILL: a survivor pattern is a representation (multiset with positions, nu, wrap), and closure of that representation is what the record needs.
3. The pattern list is the anchored census (S-units y < 10^98 with a <= 60, digit-sum filter, `hits_tierB13.tgz`); unanchored patterns are outside it. The census is taken as given (its per-cell counts were reproduced exactly for v0, v4, v8, not independently derived).
4. Conditional on Lemma C, Matveev, Yu 2007 Thm II, the U'' table (k <= 34), and the cport seams recorded in tierc-r2shadow and sandwich-cong RESULT.md (MITM above the default caps not validated by exhaustive comparison; `--word-mitm` verified byte-equal on 1,335, 548 of 548, and 300 of 300 here).
5. Ten of thirteen vertex bills are sampled, with the v0 calibration miss stated above; 13 of the 13 are anchored side only. The 3 exact vertices have exact survivor counts and a bill computed from a thinned (Bernoulli) certified sample for v4 and v8.
6. Process deviations: several `sleep` calls inside background watcher loops; a first dcg block on a dynamic redirect path (not retried; replaced by literal commands and a Python runner); one bare `python3 -c "print(1)"` early (no effect); `kill -STOP/-CONT` on my own reference process to stay at two concurrent compute processes; the SPRINT-TIERBC.md md5 changed from 1127da9f to 40a8c049 during the session (the chat session edits it; it was only read).
7. The v0 count pass found nothing that contradicts Theorem F; the 0.2% chat figure and the "no wrap >= 1" statement should not be copied into FRONTIER.md.

## 8. No-claim

Green on 71663616's anchored side says nothing about unanchored (accident) patterns, and nothing about vertices I only priced. Nothing here is PROVEN or Lean-checked. Negatives: "the hit-sample depth-1 rate (0.2%)", "zero wrap >= 1 survivors", "importance-sampled cell estimates for rates" are all refuted; do not retry without new data.

## 9. Commands and md5s

Inputs (verified): SPRINT-TIERBC.md 40a8c049a0864133adfb926ff4faca31 (changed during the session from 1127da9f), HSHADOW.md 74374ae7218d4d8cc44644cbf349fe32, check_wplus.py 3b9248e0fef6f7d0656962c3869ab9bd, CHECK-WPLUS.txt 6367e6f4a172f0ff20cf957460f9bb7e, hits_tierB13.tgz f9ed09e477c14000e8918a327aa6feaf, tierB13.txt d9ee4bcf023142e07ddc810b26280705, DEPTH1-v0.txt 4e3ec9cccba826814972169afc8115fd, d5b_depth1.py 8b6e556dc810045eca87d51d3937d25b, utable_u2_k34.txt e15bb126b2a672d10e939a840a5fe522, utable_inflated_400_k34.txt 7cc685d694a8e7c6e047f02099844faa, x4w_480_1335.tsv md5 a9576d7f9ea97b41d6b27dd61186624e (sha256 b50d28407773bf762...).

Mine: `enum_surv.c` f9500cec576beabe553797f14307f4cb (thinning source); `enum_surv_v1.c` ead150d85f7eb51a07e783bfdd294600 (source of binary `enum_surv`, 2831550e5b43200707b3dc78f161c3b8, used for the first counts); `enum_surv2` f9d2dc992a136d7eefbd976eb2ca3cb5 (used for emit; byte-equal output to `enum_surv` without thinning, checked on one cell and by the identical survivor total 195,464); `run_surv.py` afa763f3521034171e561d7e63856c2d; `ref_check.py` 9ceae2f60164a68461261fc1cf7d3487; `bin/cport_cong` 4669f006bd6f77e708bbb32daa0ad4f2; `bin/cport_r2c` 44a21fe793f6d93d432f30d98878ab17; `results_all2.jsonl` 5f7c97212485d413507b27203835c7d5; `results_fv4.jsonl` e5f310466375fc90c284edd713aee9ca; `results_fv8.jsonl` 5a5794b118c452604eb1a5d7fbad837e; `work/emit_v0.out` f136bf582dd6ea111fac46017c5a8e63; `work/count_v0.out` d8661ca6ae41a84116d5f3394a28649f; `work/full_v4_emit.out` 3a0effa1ebacfbb183bb574b0444d6ea; `work/full_v8_emit.out` 5139a624834a61de6be2212b29ea4444; `summ_v0.json` e535aaee12febdad4b8b8d75a9719eeb; `full_v4.json` 94ca7d5f61e5c454739f8dc72d0cb1f7; `full_v8.json` a370ab379bcb7b88c5a72937e660a744; `work/xc_v0.out` b7f90fa54eb7898efcb68bb8a8d14bfe; `work/xc_a.ref` df763466e32fb317b7e619a968618615; `results_s300old.jsonl` 4a8ff0fff1f6722737b3b88d85cf10c0; `results_s3000cong.jsonl` 3cd5a4cddbeb49f81562600fc141cc9f; `results_neg.jsonl` 09cebc35cdfda4bb9ec953a41d8fed8c; `results_negold.jsonl` dd66d425e7d7a3583a64673e7943e055; `results_ctrl5.jsonl` 28663daacb5fb8e8e17342ceb2b1da55; `PREDICTION.md` a9eac5dccd6a97eaaf75206214266a16.

```
PY="uv run --no-project python -I"   # nice -n 10 throughout
$PY mk_triples.py 0                                   # y k nu cells and census counts
./enum_surv2 15 7 0 count < work/triples_v0.txt       # exact survivors, count conservation (analyze_count.py)
./enum_surv2 15 7 0 emit < work/triples_v0.txt > work/emit_v0.out
$PY mk_plan.py 0 12000 12000 11 work/plan_v0_xc.txt; ./enum_surv 15 7 0 sample 11 < work/plan_v0_xc.txt > work/xc_v0.out
(cd ../../tier0 && uv run --no-project --with sympy python -I ../tier0-opt/tierb-anchored/ref_check.py <part> 71663616)
TB_BIN=$PWD/bin/cport_cong TB_FLAGS="--word-mitm" $PY run_surv.py work/emit_v0.out ../tierc-r2bill/data/utable_u2_k34.txt all2 def
TB_BIN=$PWD/bin/cport_r2c $PY run_surv.py work/surv_v0_s300.txt ../tierc-r2bill/data/utable_u2_k34.txt s300old def   # cmp_engines.py
./bin/cport_cong shadow480 --word-mitm --lattice ../tierc-r2shadow/data/lattice96.txt --utable ../tierc-r2shadow/data/utable_u2.txt --levelprimes ../tierc-r2shadow/data/levelprimes480.txt --cases ../tierc-r2shadow/data/cases_1335.txt --only ../tierc-r2shadow/data/only_1335.txt --tsv runs/reg1335_cong.tsv
./enum_surv2 10 5 5 emit 31 0.1 < work/triples_v4.txt; ./enum_surv2 26 3 0 emit 32 0.02 < work/triples_v8.txt   # summ_full.py
$PY do_vertex.py <v> 2000 3000 <seed>; run_surv.py ... sv<v>; est_vertex.py <v>   # ten sampled vertices; total.py
```
