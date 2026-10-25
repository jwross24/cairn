# KT rerun of the 24 A >= 64 base-10 equations (current binaries)

The run used `rerun.py --workers 1 --ncores 2` (tag `cur`, log `full.log`, report `report.txt`, per-vertex totals
`vertex_summary.txt`). It ran on tier0/lvl12 e547259e (KT fix2) and tier0/lvlN b43dad7d (join24, with the KT fix of 20e091fc).
All 24 equations exited with rc 0. They are the equations whose level 12 ran under the KT[64] lvl12 (`suspects.tsv`, `SUSPECTS.md`).

## Per equation

| outcome | count |
|---|---|
| differ from the recorded row in `open` and `bounds` | 20 |
| equal to the recorded row | 4 (the three equations of the unfinished vertex 13226976, and 7112448_222233466777) |
| differ in `sols` | 0 |

The recorded rows came from the pre-fix lvlN, whose KT[64] overrun dropped true level-24 survivors. On 393216, rerunning
with the pre-swap lvl12 and the current lvlN reproduces the new open count, not the recorded one. So the cause of the
undercount is the lvlN defect; the lvl12 change alone (A 64–67, superset) moves no open count.

## Per vertex (all suspect equations substituted together)

| vertex s | suspect equations | recorded open | new open | closed (recorded → new) | digit bound | found |
|---|---|---|---|---|---|---|
| 11239424 | 5 | 1342 | 1841 | false → false | 10^27.12 unchanged | [] |
| 1161216 | 3 | 16727 | 17533 | false → false | unchanged | [128421199872] unchanged |
| 2939328 | 2 | 6565 | 7186 | false → false | unchanged | [1792336896, 3699376128] unchanged |
| 331776 | 1 | 7066 | 7103 | false → false | unchanged | [914838624] unchanged |
| 3779136 | 2 | 4907 | 4974 | false → false | unchanged | [] |
| 393216 | 1 | 2153 | 2177 | false → false | unchanged | [] |
| 69441624 | 6 | 1710 | 2473 | false → false | unchanged | [] |
| 7112448 | 1 | 8766 | 8766 | false → false | unchanged | [] |
| 13226976 | 3 | no row yet (vertex in progress) | per-equation open equal to the stored pre-swap results | — | — | — |

The recorded open count was too low by 2,817 across 8 vertices. No vertex verdict, digit bound, or found-child list changes,
and no child was missed. The four A >= 68 equations add no solution.

## Seam

`deepcut.py` reads only each row's `exceptional` entries: the anchored open patterns whose nearest coset point lies inside the
bound (run_c.py 92–111). The `cur` run computed them but did not save them, so it cannot say whether the 2,817 extra open
patterns include anchored ones that deepcut never saw.

The `ex` rerun (`rerun.py --tag ex`, which saves `exceptional_new` and `exceptional_recorded`) is running to settle this.
rerun.py was edited for it; the previous copy is `rerun.v1.py` (md5 73f1bc40).

The complete-below claims at 10^1.3e27 digits stand: the bound is the minimum over all open patterns, anchored or not,
and it is unchanged.

## Anchored entries (ex rerun, 24 of 24 equations)

The recorded rows lack 2,825 anchored exceptional entries that the fixed lvlN finds; 0 entries are recorded-only, and none
is flagged a solution. Deduplicated on (s, M, a, y) they are 344 cases. All 344 close under cport_shadow (binary 64f48642):
318 by the cut, 26 by the sandwich (U'') with bounds 10^237.95 to 10^239.32 digits (`../shadow-new/RESULT.md`; batches
`runs/new1.tsv`, 280 cases from 22 equations, and `runs/new3.tsv` 9d8e9552, 64 cases from the last 2 equations of 69441624).

- Positive control: 356 recorded entries rebuilt into case lines are byte-identical to lines of `cases_1335.txt` and match
  `VERDICTS_1335.tsv` 356/356 on verdict and bound.
- Planted negative: with every U entry inflated to 10^400 the same 22 sandwich cases are refused and the 258 cut cases stay
  closed.
- Label: "closed by the sandwich (U'')", conditional on Matveev and Yu 2007. Nothing is PROVEN, and no vertex status changes.
- The 64-case batch ran with no planted negative of its own; the binary, inputs builder and command equal the first batch's.
