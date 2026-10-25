# Branch split in the level-12 kernel (untracked research code)

Not swapped. The swap waits for the algorithm owner's soundness confirmation of `math/r1-branch-split/REPORT.md`.

## What it does

`y = 2^a 3^b 7^c`. If 3 does not divide `y` then `b = 0`; if 7 does not divide `y` then `c = 0`. Whether 3 | y and 7 | y
depends only on `nu` and the residues `eps` mod 6. At level 12 the lattice is fixed (`u1 = (0,900)`, `u2 = (9900,0)`), so
the test is `b mod 9900 == 0` and/or `c mod 900 == 0` on the coset base point. An OPEN line failing it is not printed.
EXACT lines are never filtered. `lvl12` takes an optional fifth argument `bs`; without it the output and the stderr line
are the reference's (gatev2 corpus stage PASS). With it, stderr gains ` bsdrop N`.

Placement: `lvl12.c`, at the point where OPEN is printed. Argued against libpydesc (`scan12`/`batch12`): the dropped lines
never exist, so the kernel's file output, `scan12`, `batch12`, `RawSurv` and the Python fallback all see one consistent
survivor set with one edit, where a library filter needs the same logic in three readers. A library filter also still pays
for printing and parsing the ~20x lines (about 1.5M OPEN lines for 28672). The check runs only per OPEN line, so the
kernel's hot loop is untouched. The prototype's ~1.4 s Python filter is gone.

## Files and base

Candidates: `lvl12.c`, `lvl12` (build: `cc -O3 -march=native -o lvl12 lvl12.c`; Apple clang does not reproduce the
production binary bit for bit from the unchanged source either, so identity is by behavior), `run_c.py`.
Bases (md5 checked 2026-10-20 22:1x EDT): `tier0/lvl12.c f1130875b4623aee0f3c8063bb618445`, `tier0/run_c.py
9ccbe990096113f775b0d34794925d76`, `tier0/lvl12 c1fc636b487cc7036dc439ac3e7f5dcf`, `tier0/lvlN
9f3da70416f50aedb0b5a55d441a630a`, `tier0/tier0v2.py 2dd0ee1123def50fd46974f2f9205c16` (unchanged).
Candidate md5: `lvl12 078d8908354f7c71acac39faeb4cb1b8`, `lvl12.c 850e43b373f8efb0484c37c2da1f53a5`, `run_c.py
1035f9321b45f22cfe65871c653e7a97`; SHA256 in `SHA256`. `lvl12.c.base`/`run_c.py.base` are the bases for diffing.

`run_c.py`: passes `bs` unless `BRANCHSPLIT=off` (then production behavior); removes `bsdrop` from `c_stats` (row schema
unchanged) and keeps it in `r['bsdrop']`; raises RuntimeError if the kernel in its directory does not report `bsdrop`
when requested (an old kernel next to the new `run_c.py` fails loudly, never silently unfiltered). Other tier0 scripts that
call `lvl12` directly pass no `bs` and are unchanged.

## Swap procedure (not performed)

```
P=/Users/jwross/Documents/cairn/research/intake/persistence
cd $P/tier0 && md5 -q lvl12.c run_c.py lvl12      # must print the three base md5s; otherwise rebase and rerun the gates
mkdir -p $P/tier0-opt/branchsplit/backup-pre-swap
cp -p $P/tier0/lvl12 $P/tier0/lvl12.c $P/tier0/run_c.py $P/tier0-opt/branchsplit/backup-pre-swap/
cd $P/tier0-opt/branchsplit && cc -O3 -march=native -o lvl12 lvl12.c      # optional; a prebuilt lvl12 is shipped
cp -p lvl12 lvl12.c run_c.py $P/tier0/
cd $P/tier0 && uv run --no-project --with gmpy2 --with sympy python difftest.py 72 98,189,294,1161216
```

Install `lvl12` and `run_c.py` together (a new `run_c.py` with the old kernel raises). Relaunch: processes in flight keep
the old modules and the old binary; stop `run_trees_c_v2.py` or let the equation in flight finish, then start the same
command line; it resumes from its output files. Rows written before and after mix validly.
Rollback: copy the three files back from `backup-pre-swap/`; `BRANCHSPLIT=off` also restores production behavior with the
new files in place (the kernel is then run without `bs`).
gatev2: use the dylib-aware scratch copy (`tools/gatev2_dylib_src.patch` in `../patterns`) plus
`tools/gatev2_branchsplit.patch` here, and `GATE_PY_OVERLAY=gate-overlay`.

## Fields that change versus production (everything else is identical)

Rows of `run_vertex_c.py` / the trees rows, checked on vertices 72, 224, 8192, 14336, 28672 (`tools/vcmp.py`, logs
`vcmp_*.json`):
- `c_stats.open`: kernel OPEN lines printed (production open = new open + `r['bsdrop']`).
- `levels[*]`: survivors (third element) and class counts (fourth) at level 12; `n_in`, survivors and classes at 24 and
  above (children tested, 18.7-20x fewer at 24). `n_in` at level 12 is unchanged. An equation that closes at an earlier
  level has a shorter `levels` list (14336 and 8192 each have equations that stop one level earlier).
- `open_patterns.level` (last level run) for an equation with no open pattern (its `items` is empty either way).
Identical in every row: `s, M, npat, open, sols, bounds, exceptional`, `open_patterns.items` and `.M` (every field of
every coset, in order), `c_stats` keys `patterns, zero, prefilter-dead, (a,pattern), tail-dead, exact`.
So solutions, children and the final open sets are identical.

## Gate record (`GATE-PLAN.txt` registered before the runs; logs in `logs/`)

- G1 difftest 72, 224, 10800: IDENTICAL (`g1_difftest.log`).
- G2 production vs candidate rows 72, 224, 8192, 14336, 28672: no unexpected difference (`vcmp_*.json`). Survivors at
  level 12: 14336 503,581 -> 25,773 (19.5x); 28672 1,512,118 -> 75,420 (20.1x); 8192 289,508 -> 15,207 (19.0x); level-24
  children tested 28672 253,278,832 -> 12,954,640 (19.6x). Level-48/96 survivors equal production's.
- G3 gatev2 (dylib overlay, `gate-overlay/run_c.py`, `--lvl12` candidate, 2 jobs): `--fast` PASS, 21/21 plants;
  default PASS, 538 equations, 33 big multisets (10800, 14336), 39/39 plants (`gate_fast/`, `gate_default/`). The scratch
  gatev2 normalizes `levels` and `c_stats.open` in the vertex-stage comparison and requires candidate survivors <=
  reference (`/private/tmp/persist-branchsplit/gatev2x`, `tools/gatev2_branchsplit.patch`). The gatev2 kernel stages test
  the kernel without `bs` (byte-identical to the reference); the flag-on kernel is covered by G6 and the pipelines.
  Planted negatives for the gate: lvl12 mutants swap37 and drop3 FAIL `--fast` (vertex stage FAIL, plants 19/21 and 16/21).
- G4 the lane's 608 plants (same enumeration, cap 232,906,752) through the candidate pipeline: 608/608 recovered
  (`plants_cand.jsonl`).
- G5 mutants built from the kernel source (`tools/make_mutants.py`): both make vertex 224 raise POSITIVE CONTROL LOST
  (`mut_*_224.err`), lose 60 (swap37) and 142 (drop3) of the 608 plants (the lane's counts), and the kernel
  differential reports mismatches on 72 and 224 (the stronger check; it also covers vertices where the positive control
  holds).
- G6 kernel differential (`tools/kdiff.py`, `kdiff_vertices.log`): for every equation of 14336, 28672, 8192, 10800, 72, 224,
  `lvl12 bs` output equals the production kernel's output with the prototype's `branchsplit.keep` (unmodified) applied to
  every OPEN line, line for line and in order; all other counters equal, `open + bsdrop` = reference open;
  `lvl12` without `bs` equals the reference output. 14336: 503,581 OPEN lines, 477,808 dropped by both; 28672: 1,512,118,
  1,436,698; 0 mismatches.
- G7 wall time per vertex, `run_vertex_c.py` at 2 cores, best of 3, alternating production/candidate, machine load 16-32
  on 10 cores throughout (other jobs running), so times are noisy:

| Vertex | production | candidate | ratio |
|---|---|---|---|
| 72 | 0.68 s | 0.73 s | 0.93 |
| 224 | 1.29 s | 1.40 s | 0.92 |
| 8192 | 5.53 s | 3.95 s | 1.40 |
| 14336 | 6.65 s | 4.15 s | 1.60 |
| 28672 | 18.29 s | 8.35 s | 2.19 |

  The small vertices are process-startup dominated and show no gain at this noise level.

## Not verified

- Gains on Tier B vertices (extrapolation only); ncores=10 and multi-hour operation; a Linux/x86 build (the kernel
  already needs NEON).
- The kernel mutants were killed by the pipelines and kdiff; no mutant of `run_c.py`'s flag plumbing was run beyond the
  loud-failure check by inspection.
- Filtering at levels 24 and above (the prototype did it in Python) is not done here; survivors at 48 and 96 matched
  production, and the 24-level children were already cut at their parents.
