# Level-480 step with the wrap target tau = -w/9

Standing: ordinary proof, machine-executed. Patterns are "closed by the sandwich (U'')" or "closed by the cut", conditional on Lemma C, Matveev, Yu 2007 Theorem II and the pattern list. Nothing is PROVEN; no vertex status changes.

## What was built

`src/cport_shadow480w.c` is `../cport-shadow480/src/cport_shadow480.c` (md5 3ef219d0) with `run_rep480` taking the target from the representation's wrap. Diff size: 46 added lines, 13 removed lines, 20 hunks (`diff` output).
- `g_y` holds the anchor y = 2^a 3^b 7^c, set by both callers. The wrap is w = (V - y) / R_96, computed with `mpz_tdiv_qr`; a nonzero remainder or a negative quotient stops the program.
- Per word, at each of the seven trivial-image primes (31, 41, 61, 211, 241, 3541, 9091; the run reports T=7 for every representation): tau_word = (T_w - V) / (10^96 - 1) mod p is computed and compared with -w/9 mod p. A mismatch prints the prime, both values, key, word and wrap, then stops (`FATAL: shadow480: per-word tau differs from the wrap target`). A basis not trivial at p still gives NOTAPPL.
- The meet-in-the-middle target is -w/9 mod (31*41*61*211*241*3541*9091), computed from the same modulus the unit values use. For w = 0 the target is 0 and the code path matches the old one.
- The shadow (empty subset, sn = 0) is required in the solution set only when the target is 0; at a nonzero target its presence stops the run.
- `brute480` takes the target as an argument (the old routine hard-coded 0); `--brute-max` sets its space ceiling; `--plant-mitm` compares each planted solution set with the brute set.
- Mutants: `--mutant oldtau` (expected tau 0, mismatch gives NOTAPPL, as before), `--mutant target0` (tau check correct, search target forced to 0), `--mutant wrapp1` (expected tau uses w + 1). `--verbose` adds `REP480` lines (wrap, words, G, compat, alive per representation) and `rep=`/`wrap=`/`target=` on `MITM480` lines.

Build command (run in this directory; same flags as `../cport-shadow480/Makefile`):
`nice -n 10 clang -O2 -std=gnu11 -Wall -Wextra -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function -I/opt/homebrew/include -o cport_shadow480w src/cport_shadow480w.c -L/opt/homebrew/lib -lgmp -lm` (no warnings).

Files: binary `cport_shadow480w` md5 8ac5bbd646fd36cec064b45005692d55; source md5 bdfae2c9ee58dad5f5097233e1ebf367. Every run used `nice -n 10`, one core at a time or two in parallel.

## Verdicts of the four former NOTAPPL patterns

Command: `./cport_shadow480w shadow480 --lattice data/lattice96.txt --utable data/utable_u2.txt --levelprimes data/levelprimes480.txt --cases data/cases_4.txt --only data/only_4.txt --verbose --dump-surv runs/four_surv.jsonl --points runs/four_points.jsonl --tsv runs/four_w.tsv > runs/four_w.txt 2> runs/four_w.err`

| pattern (s M a y) | reps | words | level-480 verdict | bound | alive | level-384 shadow verdict (VERDICTS_1335.tsv) |
|---|---|---|---|---|---|---|
| 3211264 222222277888 2 1411788 | 7 | 2 | CLOSED-cut | - | 0 | CLOSED-cut |
| 393216 222222244468 0 330812181 | 14 | 39 | CLOSED-sandwich | 10^301.62 digits | 28 | CLOSED-cut |
| 3211264 2222222247788 0 7411887 | 6 | 2 | CLOSED-sandwich | 10^302.8 | 2 | CLOSED-cut |
| 393216 2222222223488 0 330812181 | 17 | 86 | CLOSED-sandwich | 10^302.17 | 34 | CLOSED-sandwich (10^239.08) |

None is open. The wrap-1 representations (all other representations of the four patterns have wrap 0, 39 of 44), each with one zero-sum child at target -1/9 = 70508254406912506 mod 1.269e17 and no shadow in the set:

| pattern | rep | wrap | words | G | child-compatible | passed 22 primes | windows | alive |
|---|---|---|---|---|---|---|---|---|
| 3211264 222222277888 2 1411788 | 1 | 1 | 2 | 1 | 1 | 0 | 0 | 0 |
| 393216 222222244468 0 330812181 | 12 | 1 | 4 | 1 | 2 | 2 | 4 | 4 |
| 3211264 2222222247788 0 7411887 | 3 | 1 | 2 | 1 | 1 | 1 | 2 | 2 |
| 393216 2222222223488 0 330812181 | 15 | 1 | 4 | 1 | 2 | 0 | 0 | 0 |
| 393216 2222222223488 0 330812181 | 16 | 1 | 4 | 1 | 2 | 2 | 4 | 4 |

Every word of every representation of the four patterns passed the tau assertion at all seven primes.

## Acceptance

A. Byte-identity checks (`tools/cmp.py`):
- X4 command from `../cport-shadow480/RESULT.md` with the new binary and `--tsv runs/x4w_480_1335.tsv` (md5 a9576d7f9ea97b41d6b27dd61186624e): `1335 of 1335 patterns closed`. The 1,331 rows closed in `../cport-shadow480/runs/x4_480_1335.tsv` have sha256 662e238faa6f646ffea342abc44d8c843ebaf5dfc2bb3e15d0b3cf57eb46a578 in both files, same order (Python, not shell diff).
- `shadow` command: `./cport_shadow480w shadow --lattice data/lattice96.txt --utable data/utable_u2.txt --cases data/cases_1335.txt --only data/only_1335.txt --levelprimes data/levelprimes480.txt --diag --tsv runs/reg1335w.tsv`: 117,127 bytes, sha256-equal to `data/shadow1335.tsv`. The reference carries the `--diag` last column; without `--diag` the file has 116,909 bytes and differs in the last column in the rows inspected (first three differing rows; not compared exhaustively).

B. See the verdict tables. Level 480 closes all four, agreeing with the level-384 shadow on closure.

C. Planted negatives:
- `--mutant oldtau` (`runs/four_m_oldtau.tsv`, md5 a552c88d6ca43c7227e7f204464380d6): all four patterns return NOTAPPL, the old verdicts.
- `--mutant target0` (`runs/four_m_target0.tsv`, md5 076568a0142fd3b82660108eaed39a1e): the shadow becomes the wrap-1 child (`shadow=1`, `notshadow_alive=0`), the wrap-1 survivors vanish (alive 28 to 24 and 34 to 30), and 3211264 2222222247788 flips from CLOSED-sandwich to CLOSED-cut. With `--brute480` added (`runs/four_m_target0_brute.err`) the run stops with `BRUTE480 MISMATCH`.
- `--mutant wrapp1` (`runs/four_m_wrapp1.err`): `shadow480: per-word tau 24 != -w/9 = 17 mod 31 (key=[3211264 222222277888 2 1411788 - -] word=0 wrap=1)`, exit 2.
- Planted compositions: `--brute480 --brute-max 8e9 --plant-mitm 8` on the four patterns (`runs/four_brute.txt`, md5 71d6936f196a37a8be4b6db9e80155a8): 18 representations with words, 8 planted compositions each, 144 of 144 `planted_found=1 brute_same=1`; the main solve of every representation, including the five wrap-1 ones at target -w/9, equals the exhaustive set (no `BRUTE480 MISMATCH`); the tsv equals `runs/four_w.tsv`. The planted targets are the compositions' own random sums, not -w/9; the -w/9 case is the main solve compared with brute.
- Independent Python check `tools/verify480w.py` (reads `runs/four_points.jsonl`, y from the key, the 20 level-96 and 22 level-480 primes, the 480-digit tail, V - y divisible by R_96, quotient zero at the seven trivial primes, survivor not tagged shadow): 10 of 10 wrap-1 survivor points pass (`runs/verify4_ok.txt`, exit 0); with b shifted by 1, 0 of 10 pass (`runs/verify4_perturbed.txt`, exit 1).

D. `--tierc` with `data/utable_u2_k31.txt` (`runs/tierc_k31w.txt`): after removing the timing token and the `PLANT-MITM` lines (absent from the reference command), the text equals `../cport-shadow480/runs/tierc_k31_run2.txt` (sha256 8e76729c5f885e2d..., equal). Verdict line: `VERDICT CLOSED-sandwich bound 10^(10^302.28 log10 U''=246.0183`.

## Seams

- A wrap-0 word whose tau differs from 0 stops the program here; the old binary returned NOTAPPL for it. No such word occurs in the 1,335.
- The window cut on the child's 480-digit tail does not depend on the wrap (same code as the wrap-0 path and as the level-192 stage); not re-derived here.
- Trivial-image primes are read from the data (seven of the 22 level-480 primes have a trivial basis image); -w/9 is taken mod their product by CRT inside the unit arithmetic.
- Brute comparisons cover the four patterns only.
- This is a consistency check of the -w/9 target against the 384 shadow and the exhaustive search; HSHADOW section 7 is not proven by it.

## Leftovers

`Makefile.orig` (copy of the old Makefile, unused), `data/cases_1.txt`, `data/only_1.txt`, `runs/t1.*`, `runs/four_m_*`, earlier-binary outputs overwritten in place; `/private/tmp/.../scratchpad/edit*.py` (edit scripts). Nothing was deleted, staged or committed.
