# Rank-2 bill for Tier C vertex 3416267673274176 = 2^6 * 3^27 * 7, with k = 30 to 34 sampled

P = /Users/jwross/Documents/cairn/research/intake/persistence. Everything is in `P/tier0-opt/tierc-r2bill/`; nothing else was written. `PREDICTION.md` was written before any compute here and is unedited. It predicted about 1e3 core-years [30, 2e4]; the measurement is about 200 times lower (Section 0), so the prediction was wrong in the direction of cost.

Labels: "closed by the cut", "closed by the sandwich (U'')", "open", "NOTAPPL", "BUDGET".

## 0. Answer

The rank-2 residue of this vertex is a payable bill, not a wall, on the sampled strata. Central bill 5.4 core-years (1,980 core-days), bootstrap 95% interval [3.6, 7.8], BUDGET cases entering as measured lower bounds. With the two BUDGET cases priced at the 7,200 CPU-s guard: 8.0 [3.8, 13.9]. A stacked worst-case envelope (Section 5) is about 43 core-years. That is 0.5 years on 10 cores (envelope 4.3 years), or 2 days on 1000 rented cores (envelope 16 days).

Why it fell from the earlier 40 core-years [0.1, 240]: that bill rested on one survivor (S3, 850 CPU-s, 98% of the cost). In 547 sampled wrap-0 survivors the costs are median 2.8 s, mean 39 s, and the largest two are k = 31 cases the tool cannot finish (below). S3's 850 s is reproduced under the new table (control C3: 847.8 s) and sits in the upper tail (8 of 547 survivors cost 600 s or more).

What stays unbounded: two k = 31 survivors (t347, t348) abort inside the tool with `FATAL: mitm480: candidate list too large` (fixed 2^26 Bloom-candidate cap in `src/cport_r2.c` line 2393) after 1,445 and 2,581 CPU-s. They are BUDGET with those lower bounds; the true cost is unknown and the code as built cannot give it. k = 32 to 34: 0 survivors in 49,835 sampled wrap-0 patterns (95% upper rate 7.4e-5), so the top end must allow for them.

## 1. U'' table through k = 34

`../cport/tools/mk_utable_u2.py` unchanged, `--kmax 34 --amax 60` (the S-unit range is a <= 60; sampled survivors have a <= 15). Output `data/utable_u2_k34.txt`, 2,074 rows (34 x 61), about 3 minutes. `cmp_utable.py`: the k <= 29, a <= 24 rows (725) equal `cport-shadow/data/utable_u2_k29.txt` in value and byte for byte (md5 21675a9d...). Values, log10 U'' at a = 0 / 1: k = 30: 231.98 / 232.11; 31: 246.02 / 232.78; 32: 247.29 / 246.71; 33: 260.09 / 249.19; 34: 264.37 / 260.79. The certificate bound is about 10^301, so every row sits far under it. Seam: the new rows k = 30 to 34 carry only the cross-checks the tool itself has (interval-certified integer N); the second-typing and planted-negative checks of `NOTES-u2-k29.md` were not repeated for them.

## 2. Survivors

Tools from `tierc-rank` run read-only (`draw_wrap.py`, `anchor_dp2 sample`, `parse_samples.py`, `verify_pat.py`; the depth-1 test is `survival.py`'s `analyze_rank` called by `surv_k.py` with the same arguments, no stratification). The sampler does not stratify by k, but its cost is per cell (about 0.4 s of setup per cell, sampling is free: 1 vs 400 patterns from one cell take the same 0.45 s). So one uniform draw of millions of patterns replaced stratification, and no reweighting is needed: every estimate is a plain uniform-sample estimate.

| stratum | patterns sampled | verify_pat invalid | depth-1 survivors | rate, 95% CP |
|---|---|---|---|---|
| wrap 0 (4 draws: seeds 1001, 2002, 3003/4004, 6006) | 4,580,000 | 0 | 547 | 1.19e-4 [1.10e-4, 1.30e-4] |
| wrap > 0 (seed 5005) | 500,000 | 0 | 3 | 6.0e-6 [1.2e-6, 1.8e-5] (CP computed on the stated counts; the upper end is the order of magnitude, `bill2.py` prints only the wrap-0 CP) |

Populations: wrap 0 has 3.618e10 patterns (1,442,653,443 in the 40,000-pair sample times 1003249/40000), wrap > 0 has 1.075e11. Survivors: wrap 0 4.3e6, wrap > 0 6.5e5 (all three wrap > 0 survivors are on y = 60761421, wrap 9, k = 25 to 29). Total 5.0e6, inside the earlier 7.2e6 [1.4e6, 1.5e7]. The earlier "0 of 14,918" for wrap > 0 was a small sample; 3 of 500,000 is consistent with its upper bound.

Survivors by k (wrap 0): tested patterns and survivors.

| k | tested | survivors | rate |
|---|---|---|---|
| <= 24 | 929,935 | 125 | 1.34e-4 |
| 25 | 647,333 | 81 | 1.25e-4 |
| 26 | 736,024 | 116 | 1.58e-4 |
| 27 | 825,555 | 106 | 1.28e-4 |
| 28 | 620,295 | 63 | 1.02e-4 |
| 29 | 437,347 | 36 | 8.2e-5 |
| 30 | 235,352 | 12 | 5.1e-5 |
| 31 | 98,324 | 8 | 8.1e-5 |
| 32 to 34 | 49,835 | 0 | 0 (95% upper 7.4e-5) |

k >= 30 holds 20 survivors, none above 31. Survival rate per pattern falls slowly with k; at k = 30, 31 it is about half the k = 25 to 27 rate.

## 3. Verdicts (all 550 survivors; `vtab.out`)

Wrap 0, `cport_r2c` (md5 44a21fe793f6d93d432f30d98878ab17, verified), default caps first, then raised caps (`--mitm-space-cap 1e30 --mitm-right-cap 1e14`) on BUDGET, new U'' table:

| k | n | closed by the cut | closed by the sandwich (U'') | open | NOTAPPL | BUDGET | needed raised caps |
|---|---|---|---|---|---|---|---|
| 20 to 23 | 62 | 11 | 51 | 0 | 0 | 0 | 0 |
| 24 | 63 | 13 | 50 | 0 | 0 | 0 | 1 |
| 25 | 81 | 11 | 70 | 0 | 0 | 0 | 12 |
| 26 | 116 | 18 | 98 | 0 | 0 | 0 | 24 |
| 27 | 106 | 12 | 94 | 0 | 0 | 0 | 35 |
| 28 | 63 | 9 | 54 | 0 | 0 | 0 | 28 |
| 29 | 36 | 4 | 32 | 0 | 0 | 0 | 22 |
| 30 | 12 | 0 | 12 | 0 | 0 | 0 | 7 |
| 31 | 8 | 2 | 4 | 0 | 0 | 2 | 5 |
| total | 547 | 80 | 465 | 0 | 0 | 2 | |

Wrap > 0 (3 survivors, rep-file path accepts the nonzero wrap): 3 closed by the sandwich (U'') at default caps, 0.7 to 7.7 CPU-s. "Closed by the cut" here is the certificate's own cut applied to the survivor; it is a closure of the representation tested, as in the earlier report.

BUDGET (2): t347 (y = 28342368844941312, k = 31, nu = 6) and t348 (y = 133995176056631232, k = 31, nu = 18, default-cap space 1.59e19, the largest seen). Both aborted by the tool's fixed candidate cap, not by the guard (RSS 143 and 187 MB, far under 4 GB), at 1,445 and 2,581 CPU-s. Lower bounds only.

## 4. k-dependence of cost (CPU s per survivor, wrap 0)

| k | n | mean | median | max | share of total CPU |
|---|---|---|---|---|---|
| <= 24 | 125 | 1.5 | 1.0 | 9.1 | 0.9% |
| 25 | 81 | 7.3 | 2.3 | 41.0 | 2.8% |
| 26 | 116 | 16.7 | 3.2 | 201.3 | 9.1% |
| 27 | 106 | 39.5 | 7.5 | 922.8 | 19.6% |
| 28 | 63 | 72.7 | 8.9 | 919.8 | 21.4% |
| 29 | 36 | 117.4 | 27.8 | 928.7 | 19.8% |
| 30 | 12 | 104.8 | 22.7 | 606.9 | 5.9% |
| 31 | 8 | >= 551 (2 lower bounds) | 34.5 | >= 2,581 | >= 20.6% |
| 32 to 34 | 0 | not observed | | | |

Cost grows about 2 to 2.5 times per unit k from 24 to 27, then flattens in the mean (the means for 27 to 30 are within a factor 3 of each other and carry one or two 600 to 900 s cases each). The earlier "100 times from k = 28 to 29" was one survivor. Within a k the spread is three orders of magnitude (k = 29: 0.5 to 929 s), so k alone does not price a survivor; the printed MITM space does (default-cap BUDGET detail), with closed cases running up to space 3.8e18 at 600 to 930 s. k = 31 is the first k where the tool itself fails (2 of 8).

## 5. The bill (`bill2.py`, `bill2.out`)

Estimator: uniform sample, so bill = N_pop x (sum of survivor CPU)/(patterns tested), per stratum. Bootstrap: 20,000 resamples; survivor count Poisson (normal approximation), costs resampled with replacement, population scale lognormal sd 0.07 (95% +-14%, from the +-14% of the rank-2 total in `tierc-rank` Section 2.2); the same scale draw applies to both strata.

| scenario | core-years | core-days | 10 cores | 1000 cores |
|---|---|---|---|---|
| central, BUDGET at lower bounds (1,445 and 2,581 s) | 5.4 | 1,980 | 0.54 yr | 2.0 days |
| bootstrap low / high (95%) | 3.6 / 7.8 | 1,310 / 2,830 | 0.36 / 0.78 yr | 1.3 / 2.8 days |
| BUDGET cases priced at 7,200 s, central [95%] | 8.0 [3.8, 13.9] | 2,930 | 0.8 yr | 2.9 days |
| pooled with the earlier 25,082-pattern sample (5 survivors incl. S3) | 5.6 [3.8, 7.9] | | | |
| stacked envelope: bootstrap high + unseen k = 32 to 34 at the 95% upper rate and 7,200 s each (6.7) + a 2.9% (95% upper) fraction of all survivors at 7,200 s (28.2) | about 43 | 15,500 | 4.3 yr | 16 days |

The envelope stacks three upper limits and double counts part of the mean; it is a ceiling for planning, not an interval. Wrap > 0 adds 0.07 core-years. The BUDGET survivors enter every scenario as their measured lower bound or a larger stand-in, never as zero. The top end beyond the envelope is not bounded: a survivor whose cost is above 7,200 CPU-s, or one the tool cannot run at all (the k = 31 cap), is not priced by anything here.

## 6. Controls

| control | result |
|---|---|
| Earlier 5 survivors (C1 to C5) rerun with the new table | 5/5 closed by the sandwich (U''), CPU 9.8, 1.2, 847.8, 8.3, 1.1 s against 8.56, 1.04, 850.05, 8.35, 1.04 earlier (`results_ctrl.jsonl`) |
| Planted negative: U'' set to 10^400 on every row (`data/utable_inflated_400_k34.txt`, md5 7cc685d6...) on C1, C2, C4, C5, s193 (k = 30), s196 (k = 31, my largest k closed by the sandwich) and s171 (k = 28) | 7/7 `open`, 0 closed by the sandwich (`results_neg.jsonl`). The run is not void |
| Table prefix | 725/725 rows equal `utable_u2_k29.txt` (`cmp_utable.py`) |
| Sampler validity | `verify_pat.py`: 0 invalid in 5,080,000 patterns (anchor identity, digit product) |
| Binary | md5 of `cport_r2c` verified before use; same file as in `tierc-r2shadow` (read in place) |

Not run: the planted-negative check on a k = 32+ survivor (none exists), and an independent exhaustive comparison of the meet-in-the-middle above the 6e16 / 5e9 default caps (seam inherited from `tierc-r2shadow`).

## 7. Commands (from `P/tier0-opt/tierc-r2bill`; `PY` = `uv run --no-project python -I`, all under `nice -n 10`, `PYTHONDONTWRITEBYTECODE=1`)

```
PY ../cport/tools/mk_utable_u2.py --kmax 34 --amax 60 --out data/utable_u2_k34.txt --log logs/utable_u2_k34.log --prime ../cport/data/utable_prime.txt   # with --with mpmath --with sympy --with gmpy2
PY cmp_utable.py
PY ../tierc-rank/draw_wrap.py ../tierc-rank/s2_40k.out N SEED draw_X.txt w0        # N,SEED: 20000/1001, 60000/2002, 750000/3003, 750000/4004, 3000000/6006 ; "other" with 500000/5005
../tierc-rank/anchor_dp2 6 27 1 sample SEED 1 < draw_X.txt > samp_X.out
PY ../tierc-rank/parse_samples.py samp_X.out pat_X.jsonl ; PY ../tierc-rank/verify_pat.py pat_X.jsonl
PY surv_k.py pat_X.jsonl surv_X.jsonl tally_X.json 1.0
PY mk_reps.py ; PY mk_reps2.py surv_b3.jsonl t data/survivors_meta_b3.tsv data/ids_b3.txt ; PY mk_reps2.py osurv_o1.jsonl w ...
PY run_jobs.py data/ids_all.txt data/utable_u2_k34.txt def1 defonly         # default caps
PY run_jobs.py data/ids_raised.txt data/utable_u2_k34.txt raised1 raised    # raised caps on BUDGET (ids_raised3 for the second batch)
PY run_jobs.py data/ctrl_ids.txt data/utable_u2_k34.txt ctrl def
PY run_jobs.py data/ids_neg.txt data/utable_inflated_400_k34.txt neg raised
PY bill2.py > bill2.out ; PY vtab.py > vtab.out
```
`run_jobs.py` wraps `cport_r2c shadow480 --rep-file data/rep_ID.rep --lattice ... --levelprimes ... --utable T` (tierc-r2shadow data files read in place), two workers, polls RSS and CPU every 0.5 s and kills at the limit.

md5: `utable_u2_k34.txt` e15bb126b2a672d10e939a840a5fe522; `utable_inflated_400_k34.txt` 7cc685d694a8e7c6e047f02099844faa; `run_jobs.py` eb0c25757a98bb0dca64efb4df2e3175; `bill2.py` 458d3a4e3c07d8105bba8fc33497ac4a; `surv_k.py` bc400dd85d22c472f799f3312e1b4bde; `PREDICTION.md` a3618994bf82d994957a4f3528eea6fa; `results_def1.jsonl` b8ab619f...; `results_raised1.jsonl` 2d7c87fe...; `results_def3.jsonl` 2b137843...; `results_raised3.jsonl` c0b5fa0a...; `results_ctrl.jsonl` e662dbd7...; `results_neg.jsonl` d7d75ec2...; `results_o1.jsonl` fb0c52dd...; `bill2.out` 7fc1fa77...; `vtab.out` 6c13ec30...; `pat_p1` 0bf26900..., `pat_p2` 9e96819b..., `pat_b1` bf53eaeb..., `pat_b2` 819c2514..., `pat_b3` 7935891d..., `pat_o1` 721bf060.... Per-job logs: `runs/`.

## 8. Seams

1. Memory guard: 4 GB RSS per process, not 8 GB, because swap was 92% used by other jobs when the run began. No job reached it (peak RSS 1.7 GB); the CPU guard of 7,200 s never fired. The two BUDGET cases are tool aborts.
2. Raised-cap runs use `--mitm-space-cap 1e30 --mitm-right-cap 1e14`, effectively uncapped and bounded by the guard; S3-style validation of the MITM above the default caps is the inherited seam of `tierc-r2shadow` (Section 6 there).
3. The depth-1 survival test and the certificate treat only the recorded representation of each survivor, as in `tierc-r2shadow`.
4. Wrap > 0 survivors have 3 samples on one y; their cost and count are indicative only. They also carry a = 0, covered by the table.
5. k = 32 to 34 are unsampled as survivors, not shown absent: 0 of 49,835 patterns, and the survival rate trend with k is 2 data points (k = 30, 31). The k = 34 population is 229 patterns in the whole sample.
6. The bill is conditional on the survivor population being the anchored population (`tierc-rank` seams 1 to 3) and on the cost of the two k = 31 abort cases, which is a lower bound.
7. Process deviations: one `python3 -c 1` timing probe (bare python3, once); one empty heredoc fed to `uv run ... python -` (it ran nothing); a `setrlimit(RLIMIT_AS)` probe script `rl_test.py` that failed on macOS (not used); `sleep` calls appear only inside background until-loops and the driver (`Event.wait`); `sed -i` was applied to my own `run_jobs.py` twice; the sampler `anchor_dp2` and the per-cell setup were read but not modified. Concurrency never exceeded 2 compute processes. Other jobs on the machine were not touched.
8. Negative: the k = 31 survivors t347 and t348 cannot be finished by `cport_r2c` as built. Do not retry them without a build with a raised candidate cap (line 2393 of `tierc-r2shadow/src/cport_r2.c`) or a larger Bloom filter; with the same binary the result is the same abort.

## 9. Do not retry without new data

- A larger sample of k = 25 to 29 survivors: 402 of them are closed; the bill is set by the tail, not by more of these.
- The single-survivor extrapolation (S3 as typical): it sits near the 98.5th percentile (8 of 547 survivors cost 600 s or more), not at the mean.
- The earlier 40 core-year figure and its [0.1, 240] interval: replaced by this measurement.
- Anything about k = 32 to 34 without sampling them as survivors (about 5e6 more patterns would put the 95% upper rate near 7e-6) and a binary that passes the k = 31 candidate cap.

No-Claim: nothing here is PROVEN or Lean-checked; verdicts are conditional on Lemma C, Matveev, Yu 2007 Thm II, the cport_shadow480w seams, the modified-build seams of tierc-r2shadow, and the pattern list.
