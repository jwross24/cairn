# SWAP 8: level-24 join in tier0/lvlN (gate passed; swap NOT applied)

Workspace: `tier0-opt/join24swap/`. `tier0/` and the engine are untouched. The owner performs the copy.

## What the drop-in is

`join24swap/lvlN.c` = `tier0/lvlN.c` (md5 841b4b15, the KT[512] source) plus 194 added lines and no removed or changed line
(`lvlN.diff`, `diff ../ktfix/lvlN.c lvlN.c`). Additions: `#include <math.h>`; a join block before `main` (key-set construction,
half lists, hash meet, plain per-parent fallback); one line in `main`:

    if(Lold==12 && Lnew==24 && join_setup()) return join_run(argv[2]);

- Command line, stdout format and the stderr counter line are those of `tier0/lvlN`. At levels 48 and 96 `main` takes the unchanged
  original path (same code, `children` equal on all 214 + 194 runs).
- At level 24: `join_setup` finds no usable key set -> original path. A parent whose half list would exceed 3e7 entries or whose
  slot count exceeds 64 -> plain enumeration for that parent. Mutant hooks and `JOIN_*` environment variables exist only under
  `-DJOIN_MUTANTS` (the gate's `lvlN_mut`); the production build reads no new environment variable.
- stderr `zero` and `dead` at level 24 are smaller than the old binary's (the join never enumerates the children it skips);
  `children`, `tail-dead`, `open`, `exact` are equal. Only `tier0v2.py` line 461 (verbose print) reads `zero`/`dead`; no result row does.

Build: `cc -O3 -march=native -o lvlN lvlN.c`. Binary to ship = the gated file itself, `join24swap/lvlN`, md5
**b43dad7d891e8a9e19ac7aec10fd042c** (a rebuild is not byte-identical; Mach-O UUID differs, md5 cd875fb9, so copy the gated file).
Source md5 54db62e8ea6246cb6967e7e7aec72f76. Reference (production now): `tier0/lvlN` 20e091fc7eecabb906406dfd37bed87d,
`tier0/lvlN.c` 841b4b15efc0c62790ef6ae6869daad3; pinned copy `join24swap/lvlN_prod_ref` (same md5).

## Gate results (log: `gate.jsonl`, `stage_gate.jsonl`; driver `gate.py`, `stage_gate.py`, summary `summ.py`)

| check | command | result |
|---|---|---|
| level 24 differential vs pinned production, h12 corpus | `uv run --no-project python gate.py diff24 3` | 228 of 228 equations: rc 0 both, sha256 of full sorted output, sha256 of OPEN lines, sha256 of EXACT lines, tail-dead/open/exact counters and `children` all equal. Includes all 3 A >= 64 equations (9437184_222222222222222222229 A=67, 9437184_22222222222222222266 A=64, 9437184_2222222222222222289 A=67: 870, 2553, 1856 OPEN lines). 216 equations have OPEN+EXACT >= 1, 177 have >= 8. |
| levels 48 and 96, same differential | `gate.py diff4896 3` | 214 (L48) and 194 (L96) of those runs identical, all rc 0, `children` equal |
| mutant M1' (drop odd K) | `gate.py mut24 3`, `lvlN_mut`, `JOIN_MUTANT=3`, compared with the new binary (identical to production on every equation) | caught on 211 of 216 non-vacuous equations and on 177 of 177 with count >= 8; the 5 uncaught have count 1-2 (124416_4466666, 124416_468899, 14336_227888, 14336_47888, 28672_444788) |
| mutant M2 (2^a replaced by 1) | `JOIN_MUTANT=2` | caught on 213 of 216; the 3 uncaught (14336_227888, 14336_47888, 28672_444788) have every surviving parent at a = 0, where 2^a = 1 already, and no forced key set (`JOIN_FORCE_SET` 0-7) catches them either: equivalent on the outputs |
| forced key sets, unmutated | `gate.py force 3` (`JOIN_FORCE_SET` 0-7) | 33 equations (every 7th of the corpus), all 8 forced sets identical to production |
| ASan/UBSan, A >= 64 | `gate.py asanfull 3` | full level-24 parent files of the 3 A >= 64 equations: rc 0, no report |
| ASan/UBSan, all | `gate.py asan 3` | first 300 parents of every equation at levels 24/48/96 (636 runs): rc 0, no report (A >= 64: levels 24, 48, 96 included) |
| ASan planted negative | `lift-ideation/lvlN_asan` (KT[64] source) on the first parent of the A=64 equation | rc 134, `global-buffer-overflow ... lvlN.c:119 in read_cfg`: the harness refuses the old table |
| difftest | `stage_gate.py difftest` (staged copy of tier0 with the new binary behind a logging wrapper) | vertex 72 IDENTICAL (9 equations), 10800 IDENTICAL (17), plus 6 (2), 224 (5), 162 (5) |
| vertex 14336 end to end | `stage_gate.py v14336`, staged ref vs new | 16 equations + summary row: rows identical; all 41 `lvlN` calls (stdout sorted, sha256) identical |
| vertex 14336 planted negative | `stage_gate.py neg` (`lvlN_mut`, `JOIN_MUTANT=3`) | rows and call outputs differ: the comparison refuses |
| golden vertices 4, 14, 27, 98, 189, 294, 72 and eq6 | `stage_gate.py golden` | new == ref on all 8; new == stored golden on 4, 14, 27, 98, 189; 294, 72, eq6 differ from the stored golden exactly as the production binary does (golden predates lvlN, as recorded 2026-10-20 15:21) |

Skipped or not exercised: `c_oracle` (raw lvl12 output; lvl12 is untouched by this swap); `gatev2` full run (not run); the vertices
4/14/27/98/189 make no `lvlN` call, so they confirm nothing about this swap beyond the pipeline still running.

## Timing (rusage CPU seconds, one process, nice 10, loaded host; pinned ref vs new, level 24, 228 equations)

Total 995.7 s -> 59.4 s (16.8x). The three A >= 64 equations: 100.4 -> 4.3 s, 288.1 -> 13.1 s, 239.8 -> 10.7 s. Among the 32 equations
whose new CPU exceeds 0.2 s the speedup median is 13.2x (range 9.3-23.4x). For equations that cost under 0.06 s the new binary is
slower by a fixed start-up cost (key-set tables): 94 of 228 equations, at most +0.039 s each, 1.84 s in total against 938 s saved on the rest.
Levels 48/96: same code path, 89.5 -> 82.6 s and 4.4 -> 4.9 s (load noise, no change intended).

## Swap procedure (owner)

    cd /Users/jwross/Documents/cairn/research/intake/persistence
    md5 tier0-opt/join24swap/lvlN                      # b43dad7d891e8a9e19ac7aec10fd042c
    md5 tier0/lvlN tier0/lvlN.c                        # 20e091fc7eecabb906406dfd37bed87d, 841b4b15efc0c62790ef6ae6869daad3
    mkdir -p tier0-opt/join24swap/backup-pre-swap
    cp -p tier0/lvlN   tier0-opt/join24swap/backup-pre-swap/lvlN
    cp -p tier0/lvlN.c tier0-opt/join24swap/backup-pre-swap/lvlN.c
    cp -p tier0-opt/join24swap/lvlN.c tier0/lvlN.c.swapnew && mv tier0/lvlN.c.swapnew tier0/lvlN.c
    cp -p tier0-opt/join24swap/lvlN   tier0/lvlN.swapnew   && mv tier0/lvlN.swapnew   tier0/lvlN
    md5 tier0/lvlN tier0/lvlN.c                        # b43dad7d891e8a9e19ac7aec10fd042c, 54db62e8ea6246cb6967e7e7aec72f76

The `mv` swaps the directory entry; a running `lvlN` process keeps the old inode, and the sweep's next spawn picks up the new binary.
Revert: `cp -p tier0-opt/join24swap/backup-pre-swap/lvlN tier0/lvlN.swapnew && mv tier0/lvlN.swapnew tier0/lvlN` (same for `lvlN.c`).

Post-swap check (from `tier0/`, arguments separate because zsh does not word-split):

    cd tier0
    nice -n 10 uv run --no-project --with gmpy2 python difftest.py 72 98,189,294,1161216
    nice -n 10 uv run --no-project --with gmpy2 python difftest.py 10800 11519532122112
    # one level-24 equation against the pinned production binary:
    d=/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12/9437184_22222222222222222266
    nice -n 10 ./lvlN $d/cfgL24.txt $d/parents24.txt | sort | shasum -a 256
    nice -n 10 ../tier0-opt/join24swap/lvlN_prod_ref $d/cfgL24.txt $d/parents24.txt | sort | shasum -a 256   # equal

## No-Claim

A passed gate shows the drop-in reproduces `tier0/lvlN` on the 228 + 214 + 194 tested (equation, level) pairs, three A >= 64 equations,
and the staged vertices above. It proves nothing about untested equations: the corpus holds only three A >= 64 equations, none of
which exceeds A = 67, while Tier B sampling found A = 70-89 on most k >= 16 multisets (lift-ideation/RESULT.md). The join's exactness
(every skipped child fails the key-prime coset test) is argued in the source comment and checked by differential only, not proved.
Agreement between runs of my own binaries is not independent evidence; the independent legs are the production binary as reference and
the pure-Python engine in difftest.
