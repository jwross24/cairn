# Shadow certificate over the new-only anchored patterns of the A >= 64 rerun

Label: closed by the sandwich (U''), conditional on Matveev and Yu 2007 as `cport-shadow/RESULT.md` states. Nothing PROVEN, nothing Lean-checked, no vertex status changes.

## Inputs and method

- Source: `rerun/out/eq_ex_*.json`, 22 files present at the time of the run. New-only entries = `exceptional_new` minus `exceptional_recorded` as a multiset, per equation.
- Case line format as in `cport-shadow/data/cases_1335.txt`: `s M a y - -` (M = concatenated digits, no nu/eps, so every representation of the anchor is certified). `--only` keys are the first four fields.
- Builder `build.py` (`new` mode skips every key already present in the given verdict TSVs, so a rerun picks up only the later files). Binary `cport-shadow/cport_shadow`, `--lattice data/lattice96.txt --utable data/utable_u2.txt --levelprimes data/levelprimes.txt`.
- Entries flagged a solution: 0. Entries with a string y (`~10^N`): 0.

## Counts per vertex (raw -> distinct; verdicts)

| vertex | raw | distinct | CLOSED-cut | CLOSED-sandwich | not closed / budget / error |
|---|---|---|---|---|---|
| 11239424 | 504 | 72 | 61 | 11 | 0 |
| 1161216 | 809 | 64 | 61 | 3 | 0 |
| 2939328 | 621 | 52 | 48 | 4 | 0 |
| 331776 | 37 | 7 | 7 | 0 | 0 |
| 3779136 | 67 | 20 | 18 | 2 | 0 |
| 393216 | 24 | 6 | 6 | 0 | 0 |
| 69441624 | 252 | 59 | 57 | 2 | 0 |
| 7112448 | 0 | 0 | | | |
| 13226976 | 0 | 0 | | | |
| total | 2,314 | 280 | 258 | 22 | 0 |

280 of 280 distinct entries close. The 22 sandwich closures carry certified bounds 10^237.95 to 10^239.32 digits against U'' about 10^128 to 10^146 (the same regime as the 1,335 run). The two still-running equations had no eq_ex file; `build.py new inputs/<next> runs/new1.tsv` then the same command processes them (a rebuild against the finished set printed `to_run 0`).

## Positive control

`build.py control` rebuilds case lines from the RECORDED exceptional entries in `tier0/trees_mac.jsonl`, `trees_c.jsonl`, `runall_final.jsonl` for vertices 3211264, 393216, 124416, 28672, 14336 (raw 6,155, distinct 1,710). 356 of those keys are in VERDICTS_1335.tsv, and all 356 built lines are byte-identical to lines of `cport-shadow/data/cases_1335.txt`. Running those 356 gives verdict AND bound equal to VERDICTS_1335.tsv on 356 of 356 (`compare.py`; 292 CLOSED-cut, 64 CLOSED-sandwich). The remaining 1,354 distinct recorded entries have no reference (they closed before the final stage) and were not run.
(The control's recorded source is `tier0/*.jsonl`, since the eq_ex recorded lists are empty for most of the nine vertices; the two with nonempty recorded lists, 13226976 and 7112448, are not in the 1,335.)

## Planted negative

The same 280 entries with a U table whose every entry is 10^400 (`inputs/utable_inflated_400.txt`): `258 of 280 patterns closed`; the 22 sandwich-class entries (exactly the 22 from the real run, `cmp` identical) are refused, e.g.
`s=11239424 M=2222222222227778 a=0 y=330812181 k=16 log10 U=400.0 ... -> open bound 10^(10^239.29 ...`. The 258 CLOSED-cut stay closed, as they have no surviving coset.

## Seams

- The negative tests only the sandwich comparison; it does not test the DP or prime cuts (those are covered by `cport-shadow/RESULT.md` section 4).
- Entries are deduplicated on (s, M, a, y) within each equation file; the same y can appear for different equations of a vertex and is kept as separate cases.
- Only anchors from `exceptional_new` are covered; unanchored open patterns are not in scope here.
- The `--only` file was the cases file itself (its first four fields are the key).
- Two equations unfinished at the time of the run; vertex totals for 13226976 and 7112448 are zero new-only entries among the files present.

## md5

- cport_shadow 64f4864277a41d06331fdb9d047082a7 (matches cport-shadow/RESULT.md 64f48642)
- data/utable_u2.txt cd1e4f5092b5b53896d84a214e5cdf04
- inputs/new1_cases.txt 5ad1a8617993275968470aed15028868
- runs/new1.tsv 7973735b32bfb09de70195a69e773c9f; runs/new1.txt 744b9b62250146146922e05a4e79076d; runs/new1_reps.tsv bb0ffdaaaab9b48811ea9316a8db2f2e
- inputs/ctl_cases.txt af64946f760116d06de329db9befd282; runs/ctl.tsv cd0788ed0e44b762e91a94d3d4a1e80f
- inputs/utable_inflated_400.txt f32488ece1722b8b4ed9070ba678c7c1; runs/neg_inflated.tsv 4b0e9ccc89b4cc2d66487871753ab68b
- build.py f14795a35fa2a01ce4669bb4e85b25c0

## Last 2 equations (69441624 22333333336779 and 2233333367799)

`build.py new inputs/new3 runs/new1.tsv` (log `runs/build_new3.txt`): raw new-only 2,825 over all 24 equations, distinct 344, 64 not yet run (69441624 raw 763, distinct 123). Run from `../../cport-shadow` with the same binary and data files: `runs/new3.tsv` (9d8e9552), `runs/new3.txt`, inputs `inputs/new3_cases.txt` (e0d77089). 64 of 64 close: 60 by the cut, 4 by the sandwich (U'') at 10^238.81 to 10^239.24 digits; content failures 0, lattice mismatches 0, non-applicable words 0. Totals over all 24 equations: 344 of 344 close, 318 cut, 26 sandwich.
