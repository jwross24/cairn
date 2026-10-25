# Level-480 shadow on the Tier C rank-2 depth-1 survivors (vertex 3416267673274176 = 2^6 * 3^27 * 7)

P = /Users/jwross/Documents/cairn/research/intake/persistence. Everything is in `P/tier0-opt/tierc-r2shadow/`; nothing else was written. PREDICTION.md was written before any certificate ran and is unedited.

Labels: "closed by the cut", "closed by the sandwich (U'')", "open". Nothing here is PROVEN.

## 0. Answer

Partly. The shipped binary `cport_shadow480w` (md5 8ac5bbd646fd36cec064b45005692d55, verified) cannot take any of the 5 rank-2 survivors or the 14 rank-1 patterns: all have k >= 25 digits and `read_case` stops at 24 (`KMAXC`); the only k > 24 route, `--tierc`, hardcodes the one k = 31 pattern. So as shipped: 5/5 and 14/14 NOTAPPL (exit 2, `FATAL: pattern with more than 24 non-1 digits is unsupported`; this is a structural limit, not a mathematical one).

With a copy of the source in this directory (a new entry point `--rep-file` that feeds an explicit representation to the unchanged `run_rep480`, plus two optional resource caps), validated against the shipped binary, 5 of 5 rank-2 survivors are closed by the sandwich (U'') and 13 of 14 rank-1 patterns (the 14th has no U'' row). The 32 s route therefore generalizes in verdict (5/5, bound about 10^301 to 10^302 digits against U'' of 10^190 to 10^219, margin 83 to 111 orders of magnitude), but not in cost uniformity: CPU per survivor is 1.0, 1.0, 8.4, 8.6 and 850 s (median 8.4 s, mean 174 s). The k = 29 survivor costs 100 times the others because the level-480 child space grows with k.

Revised rank-2 bill, 5 samples, heavy tailed: mean 174 CPU-s [bootstrap 95%: 2.5, 512] per survivor; times 7.2e6 survivors [1.4e6, 1.5e7] gives 1.4e4 core-days [40, 8.9e4] = 40 core-years [0.1, 240] (interval is the product of the two intervals, so conservative, but n = 5 and the tail is one point; the upper end is not reliable). Method A central was 1.47e7 core-days, so the route is about 10^3 times cheaper, and 5 times above the fixed-32 s sensitivity (2.7e3). Caveat that can move this: the 5 survivors have k = 25 to 29; survivors with k = 30 to 34 (Tier C k_max is 34) were not sampled and would have larger child spaces (S3 at k = 29 already needs 1.5e11 right-half probes and 847 MB; the shipped caps would refuse it). Do not retry a larger bill estimate without survivors of k >= 30.

## 1. How a survivor maps to the tool

A tierc-rank survivor is `(y, words = [(d, e)], nu, wrap)` with y + wrap * R_96 = R_nu + sum (d - 1) 10^e. This is exactly the tool's `Rep` (nu, n, d[], e[]); `run_rep480` computes the wrap itself and stops if V - y is not a nonnegative multiple of R_96. Case lines (`s M a y nu eps`) rebuild representations from the digit multiset and so cannot carry k > 24. `mk_inputs.py` writes both the case line (`data/r2.cases`, `data/r1.cases`) and the rep-file line (`data/r2.rep`, `data/r1.rep`: `y nu n d:e ...`, sorted by (d, e) as `tierc_rep` does). `verify_inputs.py`: for all 19 lines the digit product equals 3416267673274176, V - y is a multiple of R_96 with wrap 0, and every e is in 0..95.

The 5 rank-2 survivors: `tierc-rank/r2g_survivors.jsonl` (3) are a subset of the 5 recovered by `survival.py r2w0_pooled_pat.jsonl 2` (`r2w0_pooled_survivors.jsonl`, md5 88024caaa427d4195b1f33b566e4d092; 5/25,082, same node counts 24,912 / 301,056 / 445,952 / 652,800 / 18,186,240 as costmodel3). The 14 rank-1 patterns are `r1w0_surv_prod.jsonl`.

Obstacles checked:
1. U'' table. `data/utable_u2.txt` has k <= 24; `utable_u2_k31.txt` has a = 0 only. The survivors need (25,1), (26,4), (28,4), (29,4); the integer table `cport-shadow/data/utable_u2_k29.txt` (k <= 29, a <= 24, 725 rows, md5 21675a9d...) has them (copied, not edited). Its documented cross-check (rows k <= 24 byte-identical to utable_u2.txt) is in `cport-shadow/logs/utable_u2_k29.log`. The rank-1 pattern with k = 31, a = 2 has no row in any table: NOTAPPL, no extrapolation.
2. Wrap-0 anchor: accepted (printed `wrap=0`; the 1,335 regression includes wrap-0 reps).
3. Rank-1 patterns are run through the same rank-2 lattice and U'' (a superset of the rank-1 candidate set and a larger ceiling), so closure is valid but conservative.

## 2. Verdicts

Rank 2 (5 survivors; all wrap 0; rep-file build; U'' from the k29 table):

| id | y | k | a | nu | U'' (log10) | verdict | bound (digits) | words | child space | wall s | CPU s | RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 2636931307236912 | 28 | 4 | 13 | 215.07 | closed by the sandwich (U'') | 10^301.45 | 48 | 6.06e16 | 8.81 | 8.56 | 293 |
| S2 | 32419593738 | 25 | 1 | 10 | 190.67 | closed by the sandwich (U'') | 10^302.08 | 30 | 2.18e15 | 1.09 | 1.04 | 144 |
| S3 | 2636931307236912 | 29 | 4 | 6 | 218.79 | closed by the sandwich (U'') | 10^301.20 | 72 | 2.29e18 | 884.16 | 850.05 | 847 |
| S4 | 2636931307236912 | 28 | 4 | 15 | 215.07 | closed by the sandwich (U'') | 10^301.64 | 16 | 4.71e16 | 8.56 | 8.35 | 293 |
| S5 | 142910862192 | 26 | 4 | 9 | 198.06 | closed by the sandwich (U'') | 10^301.73 | 2 | 1.88e15 | 1.09 | 1.04 | 280 |

Closed by the cut: 0; open: 0; budget: 0 after the caps below. With the default caps of the code (child space <= 6e16, right half <= 5e9), S1 (space 6.056e16, 1% over) and S3 (2.29e18) return BUDGET (`runs/r2_1.txt`, `runs/r2_3.txt`). S1 and S3 are therefore verdicts of the cap-raised build `cport_r2c` (`--mitm-space-cap 1e19 --mitm-right-cap 1e11` for S1, `1e12` for S3). The cap only bounds work; the meet-in-the-middle is exact (Bloom filter plus exact second pass). The default-cap result for S1 was BUDGET, so S1 and S3 count as "closed with a raised resource cap", S2/S4/S5 with the default caps.

Rank 1 (14 patterns, secondary; `runs/r1_table.txt`): 13 closed by the sandwich (U'') (bounds 10^301.09 to 10^301.95 digits vs U'' 10^190.7 to 10^218.7), 1 NOTAPPL (R4: k = 31, a = 2, nu = 7, no U'' row). Five (R2, R3, R7, R12, R13) needed the raised cap (default-cap BUDGET at spaces 6.95e16 to 1.8e17). CPU s: 14.0, 10.4, 10.4, -, 5.0, 2.0, 10.4, 6.0, 0.6, 0.8, 1.2, 14.5, 39.5, 1.7 (median 6.0 s, max 39.5 s).

## 3. Controls

| control | result |
|---|---|
| Positive, shipped binary, 3 lines of `cases_1335.txt` (`runs/pos3.*`) | recorded rows reproduced exactly: 302.29 / alive 6 (k = 18), CLOSED-cut (k = 5, a = 2), 302.81 / alive 1 |
| Regression of the rep-file build on the full 1,335 (`runs/reg1335_r2.tsv`) | sha256 equal to `cport-shadow480w/runs/x4w_480_1335.tsv` (b50d2840...), 1335 of 1335 closed (`sha_cmp.py`) |
| Adapter: recorded k = 31 pattern as a rep-file line (`data/k31.rep`, built from `TIERC_CLASSES`) | rep0 line, `min nn` and VERDICT line equal to the shipped binary's `--tierc` output, timing removed (`cmp_k31.py`, exit 0; comparer itself exits 1 on a different file); run again on the final binary (`runs/k31_repfile_c.txt`) |
| Planted negative: U'' set to 10^400 (`mk_inflated.py` from final13) on S1 to S5 | 5/5 `VERDICT open` (bounds unchanged, U'' = 400); also 2 rank-1 patterns (R1, R6) open; k = 31 control open. Zero closures by the sandwich, so the run is not void |
| Inputs | `verify_inputs.py`: 19/19 lines satisfy product, wrap-0 identity, e range |

The planted negative was run for S3 under the same raised cap (`runs/neg_r2_3.txt`, 773 s). Not run: a planted point inside the survivor cosets (the shipped acceptance tests for the machinery are in `cport-shadow480/RESULT.md`, not repeated).

## 4. Timings and the bill

CPU s (user + sys): 8.56, 1.04, 850.05, 8.35, 1.04 (`bill.py`): mean 173.8, median 8.3, bootstrap 95% of the mean [2.5, 512.0]. Survivors 7.2e6 [1.4e6, 1.5e7] (tierc-rank Section 5): 1.45e4 core-days [40.5, 8.89e4]. Method A for the same five: 1.1e3 to 8.2e5 core-s each, mean about 1.6e5 core-s; the shadow is faster by 10^2 to 10^3 per survivor, and S3 (Method A 8.2e5 core-s) by 970 times. The 8.5 s class (S1, S4, k = 28) and the 1 s class (S2, S5) are what the "32 s" figure resembled.

## 5. Commands

```
md5 cport-shadow480w/cport_shadow480w   # 8ac5bbd646fd36cec064b45005692d55
uv run --no-project python -I ../tierc-rank/survival.py ../tierc-rank/r2w0_pooled_pat.jsonl 2 r2w0_pooled_survivors.jsonl
uv run --no-project python -I mk_inputs.py data/r2 r2w0_pooled_survivors.jsonl   # also: data/r1 ../tierc-rank/r1w0_surv_prod.jsonl ; k31
nice -n 10 clang -O2 -std=gnu11 -Wall -Wextra -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function -I/opt/homebrew/include -o cport_r2c src/cport_r2.c -L/opt/homebrew/lib -lgmp -lm
# shipped binary, one survivor line:
nice -n 10 ../cport-shadow480w/cport_shadow480w shadow480 --lattice data/lattice96.txt --utable data/utable_u2_k29.txt --levelprimes data/levelprimes480.txt --cases data/r2_c1.txt --only data/r2_o1.txt
# rep-file runs (S2, S4, S5 default caps; rank 1 likewise):
nice -n 10 ./cport_r2c shadow480 --rep-file data/r2_r2.rep --lattice data/lattice96.txt --levelprimes data/levelprimes480.txt --utable data/utable_u2_k29.txt
# S1, S3 and five rank-1 patterns: add --mitm-space-cap 1e19 --mitm-right-cap 1e11 (S3: 1e12)
# planted negative: --utable data/utable_inflated_400_k29.txt
nice -n 10 ./cport_r2c shadow480 --rep-file data/k31.rep ... --utable data/utable_u2_k31.txt   # adapter control
```
Logs: `runs/` (`r2_*.txt`, `r1_*.txt`, `neg_*.txt`, `*.err` hold `/usr/bin/time -l`).

md5: `cport_r2` 0a2189139de34856895bf5b6ac67f38d; `cport_r2_v1` 3778138b99e1190b84bc5d28c0157e16; `cport_r2c` 44a21fe793f6d93d432f30d98878ab17; `src/cport_r2.c` d335e210e9eb2fee065ebbb2d78d43ec (shipped source bdfae2c9ee58dad5f5097233e1ebf367; `src/cport_r2_v1.c` db7b584f..., `src/cport_r2_v2.c` 512b80c0... are the intermediate states); `data/r2.rep` a8978f6423293e073d8477584e8f5cec; `data/r1.rep` 15ee625a88b8626c6c210d5c49fed7a7; `data/k31.rep` aacdbebb01bcf7e0d589ad674bac7289; `data/utable_inflated_400_k29.txt` 9ffaaff9727d101dd73ae7366ee42543; `runs/r2_1_cap.txt` c85bd1bc...; `runs/r2_2.txt` 99d2dbfe...; `runs/r2_3_cap2.txt` bf01d452...; `runs/r2_4.txt` 1269e0ff...; `runs/r2_5.txt` 211aa251...; `runs/neg_r2_3.txt` 5af33aae...; `runs/reg1335_r2.tsv` a9576d7f9ea97b41d6b27dd61186624e. All output md5s: `md5_outputs.txt`.

## 6. Seams

1. The verdicts come from a modified copy, not the shipped binary. Changes: `--rep-file` (new entry; reads `y nu n d:e...`, sorts like `tierc_rep`, sets `g_dedup = 1` as `--tierc` does, uses the same `run_rep480` and `verdict480`), a `table_has` check that turns a missing U'' row into NOTAPPL, a BUDGET diagnostic line, and `--mitm-space-cap` / `--mitm-right-cap` (defaults 6e16 and 5e9, the shipped constants). The shared code path is validated by the k = 31 byte-comparison and the 1,335 regression, both of which exercise only default caps and, for the rep-file, one pattern. The dedup of equal (d, e) digits and the meet-in-the-middle above the shipped 6e16 / 5e9 caps were validated by no independent exhaustive comparison at these sizes (the shipped brute-force checks cover small spaces only); S1, S3 and five rank-1 results depend on them. The source patch scripts (`edit_patch*.py`) rewrote the copy only.
2. The "sandwich" needs the bound 10^301-302 digits to exceed U''; U'' for (k, a) is the Baker ceiling from the cited tables (Matveev, Yu 2007 Thm II, Lemma C), taken as given. The step assumes a solution has at least 480 digits (cport-shadow480 Seams).
3. Only the representation recorded in each survivor is run, not all representations of its digit multiset; closure of that representation is what the survivor record needs.
4. The bill uses n = 5 survivors, all wrap 0, k = 25 to 29 (S3 alone supplies 98% of the CPU). The product-of-intervals combination assumes survivor count and per-survivor cost are independent; they are not (cost grows with k). The 7.2e6 survivor count carries the tierc-rank seams (anchored population only).
5. Rank-1 patterns use the rank-2 lattice and U'' (conservative). R4 (k = 31, a = 2) is NOTAPPL for want of a table row.
6. Process deviations: one foreground `sleep 1` (inside a `ps` check); one command blocked by `dcg` (dynamic-path redirect in a shell loop, not retried; replaced by literal commands); two Python scripts patched a copy of C source in this directory; a first run used a Python `-c` string for two short tabulations (not heredocs); `caffeinate -w` was used to wait on a process. Concurrency never exceeded 2 compute processes. `survival.py` was run from `tierc-rank` as read-only code with `PYTHONDONTWRITEBYTECODE=1`.
7. Negative result: the shipped `cport_shadow480w` on k > 24 patterns. Do not retry without a build whose entry point takes explicit representations.

No-Claim: nothing here is PROVEN or Lean-checked; verdicts are conditional on Lemma C, Matveev, Yu 2007 Thm II, the cport_shadow480w seams, and the pattern list.
