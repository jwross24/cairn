# Final stage: Lemma C depth 1, then the Baker-lattice sandwich, in C

`cport.c` mirrors the fixed Python reference: `deepcut.py` 09c4b6ce, `sandwich.py` 4c495c96 (tier0 files were only read;
a copy with matching md5 served as the reference). `cport.c` md5 29105783 (the gate below ran on md5 2f70b773; the later
edits are the 24-digit support and nothing else, rechecked: 27,436 depth-1 rows byte-identical, 43 sandwich rows identical).

## Semantics mirrored

1. Copy bookkeeping by digit index: the tail of a case is built from each item's own assigned copy; no `(d, e)` key.
2. A record is identified by `(s, M, a, y, nu, eps)`; a second record on the same anchor is processed (s=324, a=2, y=111132 has two).
3. Wrap range `k_wrap < 8|M| + 2`.
4. A tail divisible by 5 is a dead case (counted, never cut); `cut_full` aborts if it ever receives one.
5. A recorded pattern absent from the representations, or an anchor without representations, aborts (exit 3).
6. A nearest norm of 0 reports bound -1.0, as in Python.

Additions: `--dfs` (depth-first sub-coset enumeration, bounded memory, identical rows to the breadth-first path), a
multiset-table size that no longer wraps at 4096 distinct multisets (it looped forever at about 4800 records), more than 31
free items reported as BUDGET, more than 16 non-1 digits reported UNSUPPORTED by the runner.

## Gate (C against the fixed Python, compared in Python by `tools/compare_final.py`)

Reference runs on a frozen snapshot of runall_final, trees_c and trees_mac (5992 stream records, 2820 distinct), pyref in
`tools/pyref_final.py`, cheapest records first, stopped when the budget ran out.

| Gate | Result |
|---|---|
| Depth 1, every Python-finished record (1239 patterns, 6901 representations, k <= 8; superset of the DEEPCUT-run and 0545 inputs it reached) | printed line, per-rep closed flag, case count equal: 0 mismatches; 104 exact nearest-norm integers equal |
| Sandwich, the 43 survivors of the 0545 file, Python finished 36 (145 rep-depth entries) | verdict, case counts, survivor-count lists equal: 0 mismatches; 113 exact nearest-norm integers equal |
| `--dfs` against breadth-first | all 186 rep-depth rows identical |
| `entries()` copy against `classify_open.entries` | identical on 5992 records |
| Selftest (nearest point 2000, 300/300 genuine S-units survive K=96..480, 300/300 corrupted tails excluded, 60/60 own patterns kept and 60/60 moved-copy dropped) | PASSED |

Logs: `logs/finalstage/`.

Mutants (scratch copies built by `tools/mk_mutants.py`, each refused by the same gate):

| Mutant (fix reverted) | Gate verdict |
|---|---|
| m1 `(d, e)` dict bookkeeping | 85 mismatches on the 36 sandwich patterns |
| m2 collapse by anchor | the Python record for s=324 a=2 y=111132 (second `eps`) is absent from C |
| m3 wrap range k <= 9 | 16 mismatches (representation counts differ) |
| m4 5-divisible tail kept alive | 6 mismatches on the planted file `data/planted_5L.jsonl` (no real record contains such a tail: 0 events on all data) |

## Final stage on the current files

Command (reads the three sweep files, copies a snapshot, never writes to tier0; safe while the sweep appends):

```
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport && make && \
nice -n 10 uv run --no-project --with sympy --with gmpy2 python tools/final_stage.py --out <dir> --jobs 2 \
  --pattern-timeout 2400 --deadline-epoch <unix time>
```

Output: per-vertex lines and a summary in `<dir>/FINAL-STAGE-run.txt` (copy: `FINAL-STAGE-run.txt`).

Run on the snapshot in `logs/finalstage/manifest.json` (trees_mac 3,269,828 bytes, md5 ed0d402e), one process, loaded machine:
133 vertices, 115 fully CLOSED, 18 not; 5440 open patterns: 4673 closed by Lemma C depth 1, 573 by the sandwich, 194 not decided
(191 not run before the 01:15 deadline, 1 timed out, 2 have more than 16 non-1 digits). 0 patterns came back OPEN. Wall 5099 s
(depth 1: 98 s). Timings are floors under load.

## SANDWICH-full.txt

`tools/sandwich_full.py` over the 43 non-CLOSED lines of `DEEPCUT-run-final-d1.txt` (md5 680a1733): all 43 CLOSED, full
enumeration, 76 s wall on 2 processes, smallest margin +4.96 (log10), the four named patterns included. Command and source md5s
are in the file header. The measured sub-coset counts (for example 34,476 for k=11 at depth 4) are far below (D+1)^k because the
cuts discard most extensions.

## Not verified

- Python reference coverage stops at k <= 8 for depth 1 and at 36 of the 43 patterns for the sandwich; k >= 9 and the 7 heaviest
  sandwich patterns have no Python counterpart (the C results there rest on the gated code path only).
- Planted genuine points: only the C selftest chain and own-pattern tests; the REDTEAM-SANDWICH scripts are not in the repo, so
  its attacks were not rerun, and no planted point goes through the runner.
- The Baker table is imported from `baker_chain.py` (5bb85b4a); its 17 overlapping entries match `data/utable.txt`.
- Earlier logs under `tools/run_sound*.sh` refer to the removed `--sound` flag.

## Theorem U′ stage (two-ended chain)

Table: `data/utable_prime.txt`, k = 1..24, a = 0..24, built by `tools/mk_utable_prime.py` from B3's chain (`b3_chain.py`),
interval-certified integers rounded up, U (baker_chain) kept wherever U′ > U (0 such entries; log `logs/finalstage/utable_prime.log`).
`tools/cross_utable.py` compares against `h3_fold.best`: 606 of 606 points agree to 0.01, including the certified
281.50 / 279.23 / 280.06 (k = 31) and 402.11 / 393.93 / 394.75 (k = 44) at a = 0 / 1 / 40 (`logs/finalstage/cross_utable.txt`).
The C binary is unchanged for this: `--utable data/utable_prime.txt` selects it; the runners take `--utable-file`.

43 survivors under U′ (`SANDWICH-full-Uprime.txt`): 43/43 CLOSED, 16 at depth 1 and 27 at depth 2 (under U: 7, 26 and 10 at depths
2, 3, 4), smallest margin 10^0.33 digits. Selftest (planted genuine points, 300/300 chain, 60/60 own patterns) PASSED unchanged.

Support for up to 24 non-1 digits (digit counts in the multiset key take 5 bits; tables enlarged). The two 18-digit patterns of
vertex 393216 close at depth 1 with a case budget of 5,000,000 (322,400 and 297,120 cases; the Python default budget of 200,000 would
report BUDGET).

Final stage with U′ on the live files at 03:00 to 03:43 EDT (`FINAL-STAGE-run.txt`, snapshot manifest `logs/finalstage/manifest-final6.json`,
trees_mac 6,087,252 bytes; earlier statuses of patterns already CLOSED under U′ were reused from the 01:43 run
`FINAL-STAGE-run-Uprime-partial-0143.txt`; the run under U is kept as `FINAL-STAGE-run-pre-Uprime.txt`):

```
python3 tools/final_stage.py --out <dir> [--reuse <previous dir>] --jobs 2 --pattern-timeout 3600 --deadline-epoch <unix time> \
  --utable-file data/utable_prime.txt          (run with: uv run --no-project --with sympy --with gmpy2, under nice -n 10)
```

Result: 137 vertices, all 137 fully CLOSED; 7645 open patterns: 6426 closed by Lemma C depth 1, 1219 by the sandwich, 0 left.
Wall of the last invocation 2548 s on 2 processes under load average above 30, so a floor. The earlier 194 undecided patterns and the
two 18-digit ones are among the closed ones. Every sandwich closure here rests on U′, so the whole result is conditional on Matveev
and on Bugeaud–Kaneko (2.2) as quoted from Yu (audit against Yu's original pending in `math/yu-audit/`); the depth-1 closures do not.
