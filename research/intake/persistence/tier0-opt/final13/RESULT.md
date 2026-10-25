# Final stage on 13 base-10 vertices (Lemma C depth 1, cport sandwich, level-480 shadow certificate)

Labels: a pattern is "closed by the cut" or "closed by the sandwich (U'')". Both are conditional on Lemma C, Matveev, Yu 2007 Theorem II and the pattern list. Nothing is PROVEN.

No-Claim: a green run here shows the final-stage certificates close the recorded open patterns of these 13 vertices under the stated conditions; it does not prove the pattern list is complete, does not verify the Baker tables beyond their recorded provenance, and is not a Lean-checked result.

All paths below are under `P = /Users/jwross/Documents/cairn/research/intake/persistence`; outputs are in `P/tier0-opt/final13/`. Nothing under `tier0/`, `cport/`, `cport-shadow480w/` or `kt-audit-l12/` was written. No `make`, no git. Every compute process ran under `nice -n 10`, at most 2 at a time.

## Headline

- The final stage consumes the anchored exceptional entries of the three row files, not the row-level `open` counts. For the 13 vertices that is 18,690 full-key patterns (the row-level `open` counts sum to about 126k; the difference is unanchored level-96 patterns and the way `open` counts are kept, see Seams).
- Lemma C depth 1 closes 14,370 of 18,690; 4,320 survive (23.1%; the 138-vertex run had 1,335 of 8,027, 16.6%).
- Closing certificate 1, cport sandwich with `data/utable_u2.txt`: 4,294 of 4,320 survivors finished, 4,294 CLOSED, 0 open, 0 budget. 26 survivors (k = 12, 14, 15, 16, 17) were not finished: 22 never started and 4 were running when I stopped the run (see Cost). Smallest margin over all finished sandwich representations: bound minus log10 U = +4.31 (log10 digits; my own definition, see Seams).
- Closing certificate 2, level-480 shadow `cport_shadow480w` (md5 8ac5bbd6): 4,320 of 4,320 closed: 903 by the cut, 3,417 by the sandwich (U''), bounds from 10^300.79 digits up. 0 NOTAPPL, 0 open, 0 budget. This covers the 26 that cport did not finish.
- Positive control: 3 of 3 vertex lines byte-equal to `cport/FINAL-STAGE-run-U2.txt`.
- Planted negative: with every U entry at 10^400, the shadow run refuses exactly the 3,417 sandwich-closed patterns and keeps the 903 cut-closed ones. The cport sandwich with the inflated table refused 14 of 14 sampled survivors (the sample is small, see Seams).
- Vertex status: 11 of 13 vertices have every anchored pattern closed. 1161216 and 11239424 also have every anchored pattern closed, but their rows carry open patterns that are not in the exceptional list (3 and 5, level-96, bound 1.32e27 digits); `final_stage.py` flags both `RECORD-MISMATCH` and would not print CLOSED for them. Those 8 patterns are outside what any final-stage certificate here covers.

## Commands

Depth 1 (survivor count; `--deadline-epoch 1` makes every survivor "unrun", so no sandwich ran in this pass; its `-> OPEN` vertex lines in `d1/FINAL-STAGE-run.txt` are that artifact, not a verdict):

```
cd P/tier0-opt/cport
nice -n 10 uv run --no-project --with sympy --with gmpy2 --with mpmath python tools/final_stage.py \
  --vertices 331776,11239424,3779136,2939328,69441624,3281116734,1161216,7112448,13226976,46294416,1741824,1492992,9483264 \
  --utable-file data/utable_u2.txt --out P/tier0-opt/final13/d1 --jobs 2 --pattern-timeout 3600 --deadline-epoch 1
```
(`run_d1.sh`.) Wall 658 s (deepcut 656 s), 2 processes, machine load average 8 to 27.

Positive control (`run_control.sh`): same command with `--vertices 2667168,1843968,368947264 --out final13/control --jobs 1`, no deadline. Wall 28.4 s.

Full cport sandwich on the survivors (`run_sw.sh`): same command with `--reuse P/tier0-opt/final13/d1 --out final13/full --jobs 2`, no deadline. It ran 7,515 s before I stopped it (Cost).

Level-480 shadow (`run_shadow.sh`, inputs from `mk_shadow_inputs.py`): 
```
B=P/tier0-opt/cport-shadow480w
nice -n 10 $B/cport_shadow480w shadow480 --lattice $B/data/lattice96.txt --utable $B/data/utable_u2.txt \
  --levelprimes $B/data/levelprimes480.txt --cases shadow/cases.txt --only shadow/only.txt --tsv shadow/s480w.tsv
```
671 s real, 606 s user, one process. Case lines are `s M a y - -`, one per anchor, the format of `cport-shadow480w/data/cases_1335.txt` (4,320 survivor full keys are 4,320 distinct anchors).

Planted negative, shadow (`run_shadow_neg.sh`): same command with `--utable shadow/utable_inflated_400.txt` (built by `mk_inflated.py` from `cport-shadow480w/data/utable_u2.txt`; md5 f32488ec equals the file `kt-audit-l12/shadow-new/inputs/utable_inflated_400.txt` reported there). 493 s.

Planted negative, cport sandwich (`sample_negative.py`): 200 survivors drawn with `random.Random(13)` from finished patterns with k <= 12; each run with `cport sandwich --dfs` and a table built from `full/utable.txt` with every U set to 10^400, 300 s limit each. I stopped it after 14 patterns (Cost).

Step-5 shadow-new cross-check with the level-480 binary: `mk_newcases.py` then the shadow command on `newcases/cases.txt` (338 cases), 37 s.

## md5

```
b95707a1983b6fc6e5c330d90dcfbdbc  cport/cport (existing binary, not rebuilt; equals the md5 in NOTES-u2.md)
8ac5bbd646fd36cec064b45005692d55  cport-shadow480w/cport_shadow480w
e1fc6a5544e95d2f7aae1a3653b37304  cport/tools/final_stage.py
fc14488840c4da41c492e309629c1a62  cport/tools/stage_io.py
cd1e4f5092b5b53896d84a214e5cdf04  cport/data/utable_u2.txt (equal to cport-shadow480w/data/utable_u2.txt)
010c8bacd3b5b612c11473a3b95a87d3  data/lattice96.txt (cport and cport-shadow480w copies equal)
3d16b8e000452c7f896c72c29d4edcb7  cport-shadow480w/data/levelprimes480.txt
3382a57f8934f6b20878b343a00bf6e4  trees_mac.jsonl snapshot (50,948,620 bytes; d1/snap and full/snap; equal to the live file when I checked)
3c02cbac7e1ae8e9c5c05c60c3540bc9  trees_c.jsonl snapshot (107,216 bytes)
c2a3f37d1bc9bbb90ea8e4aedc527759  runall_final.jsonl snapshot (32,826 bytes)
109625a846a1d071b117047c436db413  full/utable.txt (the (k, a) pairs of the survivors)
565f256f88fab83908b2f643fc212f28  d1/pattern_status.json
49c88dbecbf75d2ebc0bcec85708f4f0  shadow/cases.txt
a1d0376bff93ffaa69d2533baa7243ee  shadow/s480w.tsv
5104179e9cbd3fb6e782bf7363bebb0a  shadow/s480w_neg.tsv
f32488ece1722b8b4ed9070ba678c7c1  shadow/utable_inflated_400.txt
71de53b912d4866b9159d7c5f53c49e0  mk_shadow_inputs.py
bde6c33b2874ec8d9670605ca3f68104  parse_sw.py
b43dad7d891e8a9e19ac7aec10fd042c  tier0/lvlN
e547259ef483d1cfc5bf8f86d3d0ccee  tier0/lvl12
```

## Per-vertex table

Columns: open = anchored full-key patterns fed to the stage; d1 = closed by Lemma C depth 1; surv = depth-1 survivors; cport = survivors cport closed by the sandwich (CLOSED, no open or budget) / survivors cport did not finish; margin = smallest (reported bound - log10 U) over the sandwich representations cport closed, log10 digits; 480w = closed by the level-480 shadow (cut + sandwich) with the smallest sandwich bound in log10 digits.

| vertex | open | d1 | surv | cport closed / unfinished | margin | 480w cut + sandwich = total | min 480w bound | not closed |
|---|---|---|---|---|---|---|---|---|
| 331776 | 1573 | 1244 | 329 | 328 / 1 | +4.59 | 91 + 238 = 329 | 301.28 | 0 |
| 1161216 | 2636 | 2042 | 594 | 594 / 0 | +4.59 | 111 + 483 = 594 | 300.79 | 0 (3 unlisted level-96 open patterns, see Seams) |
| 1492992 | 3191 | 2474 | 717 | 715 / 2 | +4.30 | 150 + 567 = 717 | 300.87 | 0 |
| 1741824 | 3189 | 2479 | 710 | 705 / 5 | +4.42 | 135 + 575 = 710 | 300.79 | 0 |
| 2939328 | 1169 | 946 | 223 | 223 / 0 | +4.77 | 52 + 171 = 223 | 301.09 | 0 |
| 3779136 | 855 | 698 | 157 | 156 / 1 | +4.57 | 24 + 133 = 157 | 301.45 | 0 |
| 7112448 | 1493 | 1084 | 409 | 409 / 0 | +4.88 | 94 + 315 = 409 | 300.81 | 0 |
| 9483264 | 1954 | 1384 | 570 | 564 / 6 | +4.31 | 117 + 453 = 570 | 300.81 | 0 |
| 11239424 | 297 | 198 | 99 | 97 / 2 | +4.92 | 9 + 90 = 99 | 300.89 | 0 (5 unlisted level-96 open patterns) |
| 13226976 | 1155 | 922 | 233 | 233 / 0 | +4.70 | 55 + 178 = 233 | 301.30 | 0 |
| 46294416 | 846 | 643 | 203 | 201 / 2 | +4.65 | 49 + 154 = 203 | 300.86 | 0 |
| 69441624 | 270 | 211 | 59 | 56 / 3 | +4.89 | 14 + 45 = 59 | 301.24 | 0 |
| 3281116734 | 62 | 45 | 17 | 13 / 4 | +5.09 | 2 + 15 = 17 | 301.38 | 0 |
| total | 18690 | 14370 | 4320 | 4294 / 26 | +4.30 | 903 + 3417 = 4320 | 300.79 | 0 |

"closed by the cut" for the cport columns means Lemma C depth 1 (all of d1); the cport sandwich closed all 4,294 survivors it finished, and every one of them has at least one representation closed by the sandwich (that is why it survived depth 1). The 26 unfinished survivors are listed in `full/not_completed_keys.txt` (4 in flight at the stop first, then the 22 never started; by k: one each at 12, 14, 15, 19 at 16, 4 at 17).

The 480w sandwich closures need U'' only for patterns that survive its cut; all 3,417 appear with a finite bound, and all of them flip to `open` in the negative.

## Positive control

`cmp_control.py` compares the per-vertex lines in Python: 2667168, 1843968 and 368947264 are byte-equal to the same lines of `cport/FINAL-STAGE-run-U2.txt` (open patterns 387 / 104 / 12; cut 303 / 84 / 10; sandwich 84 / 20 / 2). The control snapshot is the larger trees_mac (50.9 MB) than the 6.66 MB snapshot behind the reference; the three vertices' rows are unchanged, which the equality shows.

## Planted negative

- Shadow (`cmp_neg.py`): same 4,320 keys in both runs. Verdict pairs (real, inflated): (CLOSED-sandwich, open) 3,417; (CLOSED-cut, CLOSED-cut) 903; nothing else. So exactly the sandwich-closed patterns are refused and the cut-closed ones stay closed.
- cport sandwich, sample of 14 (all finished before the stop; k <= 12, 9 vertices): 14 of 14 REFUSED, 0 closed (`neg/sample_negative.tsv`, md5 255f1cd3). Every survivor needs the sandwich on at least one representation, so a refusal is the expected result for all of them; the sample shows the gate refuses, not how many it would refuse out of 4,320.

## Cost

Projection before the sandwich: the 138-vertex run spent 3,987 s of sandwich on 1,335 survivors; scaled by survivors that is about 3.6 h for 4,320. The measured run: patterns up to k = 14 and most of k = 15 finished quickly (a few hundred seconds at most); the k = 15 to 17 tail went slow (single patterns of 10 to 45 minutes). I did not log the exact time at which the slow tail began. I let it run 7,515 s, then stopped the background task (`TaskStop`), which ended `final_stage.py` and its two `cport` children. The remaining 26 were projected at a further several hours (22 patterns at 16 to 17 digits, measured 10 to 45 minutes each on 2 processes under load 20 to 27), so I did not wait. Their per-pattern outputs in `full/sw/` are whatever the processes had written; `parse_sw.py` classifies them (a pattern counts as finished only when its `.txt` holds an `s=` line). Because the stop skipped `final_stage.py`'s own summary, there is no `FINAL-STAGE-run.txt` in `full/`; the per-vertex table above comes from `parse_sw.py full/sw d1/pattern_status.json full/not_completed_keys.txt`.

Times: depth 1 658 s wall; shadow 671 s wall (606 s CPU); shadow negative 493 s; control 28 s; step-5 cross-check 37 s; cport sandwich 7,515 s wall on 2 processes (partial).

## Step 5: inputs soundness

### Shadow-new cases

The KT audit (`kt-audit-l12/rerun/RESULT.md`) found 2,825 raw anchored exceptional entries (344 distinct on (s, M, a, y)) absent from the recorded trees_mac rows of 8 vertices. For the 13 vertices here:

| vertex | needs shadow-new cases? | distinct cases | closed in shadow-new (level-384 `cport_shadow`) |
|---|---|---|---|
| 11239424 | yes | 72 | 72 of 72 (61 cut, 11 sandwich) |
| 1161216 | yes | 64 | 64 of 64 (61 cut, 3 sandwich) |
| 2939328 | yes | 52 | 52 of 52 (48 cut, 4 sandwich) |
| 331776 | yes | 7 | 7 of 7 (7 cut) |
| 3779136 | yes | 20 | 20 of 20 (18 cut, 2 sandwich) |
| 69441624 | yes | 123 | 123 of 123 (117 cut, 6 sandwich) |
| 7112448 | no new-only entries (0) | 0 | none needed |
| 13226976 | no new-only entries (0); its three A >= 64 equations reproduce their stored results | 0 | none needed |
| 46294416, 1741824, 1492992, 9483264, 3281116734 | no KT suspect equation, nothing to add | 0 | none needed |

Checked by `shadow_new_check.py` over `kt-audit-l12/shadow-new/inputs/new1_cases.txt` and `new3_cases.txt` against `runs/new1.tsv` and `runs/new3.tsv`: 344 case lines, 344 distinct, 344 verdict rows, 0 cases without a row, every verdict CLOSED-cut or CLOSED-sandwich. For the 13 vertices that is 338 cases (393216's 6 are the remainder). None of the 338 coincides with a survivor anchor in this run (overlap 0), so they are additional cases, not duplicates. As a cross-check these 338 cases also ran through `cport_shadow480w` (`newcases/`): 338 of 338 closed (253 cut, 85 sandwich, smallest bound 10^300.79 digits). The shadow-new verdicts are level-384; the level-480 run is mine and the split between cut and sandwich differs because the levels differ.

Conclusion: the final-stage verdicts of the six vertices above hold only together with these cases. Those cases close. Nothing in the 13-vertex stage ran them; they are separate files and are counted here from the KT files.

### Which lvlN produced which rows

Evidence (all read, none changed):
- `tier0/lvlN` md5 b43dad7d has ctime 1792646505 (2026-10-22 01:21:45 EDT); `tier0/lvl12` md5 e547259e has ctime 1792646338 (01:18:58). `lvlN.orig-3493e68c` (md5 eb634ce3) is the pre-fix binary. SUSPECTS.md gives the same swap epoch.
- `trees_mac.log.11` is the sweep run that produced the 13 rows (birth 2026-10-20 23:04:05, last write 2026-10-22 21:26:52). Its 20 per-vertex elapsed seconds sum to 166,966 s; birth to last write is 166,967 s. So the vertices ran one after another and each elapsed value is that vertex's wall time. Windows by cumulative sum (epoch seconds, `eqs_timing.py`): 3281116734 finished 1792605219 (before the swap); 13226976 started 1792640071 (the row mtime SUSPECTS.md uses for "pre-swap") and finished 1792652522 (after the swap, straddling it); 46294416 started 1792652522, 1741824 1792668911, 1492992 1792683512, 9483264 1792698818 and finished 1792718812, every one after the swap by at least 6,017 s.
- `trees_mac.jsonl.eqs.jsonl` (the append-only per-equation store, 2,801 lines) has contiguous blocks per vertex. KT counted 2,348 lines at swap time. Blocks: 3281116734 lines 2076 to 2090; 13226976 2278 to 2357; 46294416 2358 to 2414; 1741824 2415 to 2540; 1492992 2541 to 2730; 9483264 2731 to 2800 (`eqs_lines.py`). The four later vertices start above 2,348.

Findings:
- 46294416, 1741824, 1492992, 9483264: produced after the fixed lvlN and lvl12 were in place (both time routes agree). Not covered by the KT rerun, and not needing it.
- 3281116734: produced before the swap, with the pre-fix lvlN. Its 15 equations have two-adic bounds A of at most 62 (`a_check.py`, same `two_adic_bound` as `tier0v2.py`): 30, 36, 40, 48, 51, 55, 57, 58, 60, 60, 60, 61, 61, 62, 62. The KT suspect class is A >= 64 (`SUSPECTS.md`), so no equation of this vertex is a KT suspect.
- 13226976: straddles the swap; its three A >= 64 equations ran before it, were rerun by KT on the current binaries and reproduce the stored per-equation open counts (259, 160, 185).

Soundness seam, plainly: 3281116734's row (and every A < 64 equation of the other pre-swap vertices) was computed by the pre-fix lvlN. The KT audit tested that the pre-fix lvlN is wrong at A >= 64 (the KT[64] overrun) and that two A < 64 controls (368947264 at A 51 and 47) reproduce open, sols and bounds. That is two equations. I did not rerun 3281116734 or any other A < 64 equation, and I did not establish that no A < 64 equation is affected. Its 62 patterns (45 cut, 17 sandwich/shadow) close in this stage, but the stage cannot tell whether the row itself is complete. This is a seam, not a repair; I did not try to fix it.

## Seams

- Scope of "open patterns". The brief's 466 to 23,785 per vertex are the row `open` counts. The stage works from `exceptional` lists of the anchored entries (18,690 full keys here). For 11 vertices `open` equals the listed count. For 11239424 (1342 vs 1337 listed) and 1161216 (16,727 vs 16,724) it does not: 5 and 3 level-96 open patterns on equations 2222222222227778 and 222222222444777 (11239424) and 22222222233667 (1161216), recorded with bound 1.3242e27 digits, carry `open_patterns` data (lattice and a, nu, eps items) but no anchor. No certificate in this run covers them (`rec_mismatch*.py`). The KT rerun's open-count increases (+499 and +806 for these vertices) are within 5 and 3 of the raw anchored counts (504 and 809); that equality is an observation, the cause is not established here.
- The 26 survivors cport did not finish are closed only by the level-480 shadow, a single certificate; the cut and sandwich certificates do not agree on them because cport did not run.
- Margin definition. "bound minus log10 U" is computed by `parse_sw.py` from the per-representation tuples in cport's output (`('CLOSED-sandwich', depth, count, bound, ...)` and `log10 U=` in the same line). It is not the margin `sandwich_full.py` prints (bound minus log10 G), so +4.30 is not comparable to the +4.93 in `NOTES-u2.md`. I did not read the C code that produces the tuple's fourth field.
- cport sandwich negative: 14 patterns, not the planned 200 (each inflated run took up to about 3 minutes); chosen with a fixed seed but stopped early, so the sample is the first 14 of the draw, in the draw's order.
- The shadow negative tests only the sandwich comparison, not the DP or prime cuts (as in the earlier shadow RESULT files).
- `cport_shadow480w` verdicts rest on its own seams (`cport-shadow480w/RESULT.md`): wrap-0 versus wrap-1 representations, the window cut taken from the level-192 path, brute comparisons on four patterns only. I did not re-derive them.
- The positive control compares three vertices' summary lines, not per-pattern rows.
- The depth-1 pass and the full-sandwich pass each took a fresh snapshot; their trees_mac md5 values are equal (3382a57f), so both saw the same rows. The sweep had finished by then (log.11 last write precedes this run).
- Time-window argument for the four post-swap vertices assumes `trees_mac.log.11` elapsed values are per-vertex wall times (supported by the sum matching to 1 s) and that `lvl12` and `lvlN` are executed per equation, not held open by a running process (SUSPECTS.md says the post-swap workers started with the new binary; I did not inspect the sweep driver).
- Stray files I created: `a_3281116734.py` (an abandoned stub, empty effect), `eqs_timing.py` (its timing section ran only as a function source for `a_check.py`; its full run was stopped as slow). Nothing was deleted.
- One `python3 -c 1` call ran by mistake during the session (no input, no output, no file effect). All analysis scripts ran with `uv run --no-project`.
- A request to signal the two cport children directly was refused by the session's permission classifier; I stopped the run through the task tool instead. The stop therefore also killed the in-flight patterns, which is why 4 are "in flight at stop".
- Nothing here checks that `utable_u2.txt` is a valid Baker table beyond what `NOTES-u2.md` records (selftest, second typing, e^n slip noted there).
- Every closure is conditional on Lemma C, Matveev, Yu 2007 Theorem II and the pattern list; Yu Part II's omitted details are unresolved per `NOTES-u2.md`.
