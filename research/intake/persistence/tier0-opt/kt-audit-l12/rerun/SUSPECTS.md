# Level-12 suspects (KT[64] overrun, pre-swap binary)

Swap epoch 1792646338 (ctime of tier0/lvl12, md5 e547259e...). tier0/lvlN is md5 b43dad7d (ctime 1792646505).
A is `tier0v2.two_adic_bound(M)`, the same value `export_cfg.export` writes as cfg A and
`gen_l12_cfg.py` / `list_eqs.py` use for the 50-equation list.

## Which files the base-10 conclusions rest on
- `tier0/trees_mac.jsonl` (93 rows, written by `run_trees_c_v2.py` -> `run_c.run` -> `tier0/lvl12`): 21 equations with A >= 64.
- `tier0/trees_mac.jsonl.eqs.jsonl` (2348 per-equation lines, the resume store; `run_trees_c_v2.py` lines 42-60 reuse a stored equation instead of rerunning it):
  70 lines belong to the unfinished vertex 13226976, of which 3 have A >= 64.
- `tier0/trees_c.jsonl` (31 rows, same driver family): 0 equations with A >= 64. Not affected.
- `tier0/runall_final.jsonl` (53 rows, `runall_v2.py` -> `tier0.solve_equation` without `l12=`): level 12 runs in Python, never execs lvl12. Not affected.

## Counts (suspects.tsv, 24 rows, 5.92e12 patterns)
| class | count | rows |
|---|---|---|
| A 64-67 (superset only) | 20 | 18 in trees_mac.jsonl rows, 2 in the unfinished vertex |
| A >= 68 (can miss survivors) | 4 | 69441624 x3 (A 70, rows), 13226976 233333346679 (A 69, unfinished vertex) |

The 50-equation list in GATE.md / unverified.txt includes equations the sweep has not reached (pending vertices); those run on the current binary when reached.

## Unfinished vertex 13226976
- `eqs.jsonl` mtime 1792646391 (swap + 53 s). The running equation 222333366799 has lvl12 workers started 01:19:56 (swap + 58 s): post-swap.
- The last stored equation (npat 3.96e11, A 62) straddles the swap; A < 64 so unaffected.
- The 3 suspects (npat 2.40e11, 2.72e11, 3.09e11) precede it in the file. Measured rates in this audit (2e8-4e8 patterns/s on 2 processes) put each tens of seconds to minutes before the last equation started, so they ran pre-swap. The per-equation completion time is not logged: this timing is inferred, not read.
- Resume risk: `run_trees_c_v2.py` takes stored equations from `eqs.jsonl`, so these 3 stored results will enter the vertex row unless rerun and replaced.

## Can a 64-67 superset change a verdict?
Reasoned from code, plus 2 measurements.
- Level-12 output lines OPEN/EXACT become survivors (`run_c.py` 75-80); EXACT lines are accepted as solutions only after `factor237` and `Coset.contains` (`run_c.py` 85-87).
- `classify` returns SOLUTION only after the same `factor237` check (`tier0v2.py` 249); an extra survivor is therefore either DEAD, a genuine solution, or OPEN (K == 0 returns OPEN, `tier0v2.py` 236). Extra survivors cannot create a wrong child.
- `closed = nopen == 0 and found == known` (`run_c.py` 114, `run_trees_c_v2.py` 72). Extra OPEN entries only raise `nopen` and lower `min(bounds)`: the error direction is a weaker claim, never a wrong CLOSED.
- Positive-control asserts (`tier0v2.py` 422) cannot fail on a superset.
- Measured (393216 A66, 3779136 A64): pre-swap lvl12 vs current lvl12, both with current lvlN: identical open, sols, bounds, level 24/48/96 counts; only level-12 survivors differ (2,858,343 vs 493,449; 1,981,162 vs 343,200). Level-12 counts match GATE.md.
- A >= 68 is different: missed true survivors can yield a false CLOSED, a missed child, or an overstated digit bound.

## Separate finding
Recorded level >= 24 counts for the 2 tested suspects differ from the current lvlN even with the pre-swap lvl12 (393216: level-24 survivors 318 recorded vs 415 current, final open 0 vs 24). The lvl12 change does not explain it. The recorded rows are consistent with a lvlN older than the current build (cause not established here). Two A < 64 controls (368947264, A 51 and 47) reproduce open, sols and bounds exactly, though their level-12 survivor counts differ by ~20x (older lvl12 settings), so only open/sols/bounds are the comparison keys.
