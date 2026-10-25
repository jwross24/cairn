# Codex blind Lane 2 level-24 lift: validation (executor run)

Date 2026-10-21. Directory: tier0-opt/codex-blind-lane2/. Nothing under tier0/ or the engine was edited. Agreement between my own runs is not independent evidence; the reference is the pre-existing join24 binary and Lane 2's own binary.

## 1. Source and builds
- Extracted report lines 6-1518 of codex_lane2_report.md to lvl24_blind.c: 1513 lines, first line `#include <stdio.h>`, last `}`, zero fence lines. md5 8d9ccf03f35c7fbafe06f5aa3ff5faf4.
- `cc -std=c11 -O3 -Wall -Wextra lvl24_blind.c -lm -o lvl24_blind` (macOS cc): 0 warnings (build.err is 0 bytes). Binary md5 ce5c73b5af6fb22455690ab6465c3d9e.
- `-DMUTANT_WINDOW_SHIFT=1` -> mut_window (md5 6bbfb2f801074a44dd2707793cefcac8), `-DMUTANT_625_SHIFT=1` -> mut_625 (md5 957132b8c0239c68af428b14a61f31a7): 0 warnings each.
- Reference: tier0-opt/join24swap/lvlN, md5 b43dad7d891e8a9e19ac7aec10fd042c (not rebuilt).

## 2. Primary differential (diff.py)
Equations: the gate.py selection (dirs of the h12 corpus with cfgL24.txt and a nonempty parents24.txt) = 228, asserted. Per equation: both binaries, `nice -n 10`, 2 concurrent; compare exit status (both 0), byte length and sha256 of the LC_ALL=C-style sorted stdout (Python bytes sort, no dedup), counters parents/children/open/exact, and that stdout OPEN/EXACT line counts equal the stderr open/exact counters. Per-case records: diff_<label>.jsonl; stdout/stderr in runs/.
| run | result |
|---|---|
| primary | **228/228 match** (216 nonempty reference outputs, 12 empty) |
| BLIND_FORCE_KEY=73 | 228/228 |
| BLIND_FORCE_KEY=137 | 228/228 |
| BLIND_FORCE_KEY=73,137 | 228/228 |
Force-key effect confirmed with the instrumented copy (INSTR_KEY=1, eq 124416_2222233689, 10591 parents): default chooses key 73 for all 10591 parents; forced 73 -> 73; forced 137 -> 137; forced 73,137 -> 73,137. Note default == 73, so the 73 run exercises the same path as primary; 137 and 73,137 are the distinct paths. Wall seconds (blind): primary 211, 73 154, 137 759, 73,137 332.

## 3. Mutants
Both run on all 228 equations, all exit 0 (no crash counted).
- MUTANT_WINDOW_SHIFT=1: 216/228 differ (12 match = exactly the 12 empty-reference equations). Witness: eq 124416_222222222399, reference sorted sha256 prefix 56efcb57a15d (43 lines), mutant 90ec1ed9e3c5 (9 lines); first missing line `OPEN 106 2 0 0 0 0 2 3 4 5 23 23 1 0 23 405641250 901029393` (34 missing, 0 extra).
- MUTANT_625_SHIFT=1: 216/228 differ (same 12 match). Same equation: mutant output empty (e3b0c44298fc), 43 reference lines missing, same first line.
- 625 premise from the actual config (prem.py on 124416_222222222399/cfgL24.txt): component 2 is cidx [2], cmod [625], 25 entries, all coordinates multiples of 25 (order-25 subgroup of Z/625); adding 1 to any key leaves the image for 25 of 25 keys.

## 4. Short-EXACT case (the key question)
Construction (gen_cases.py -> cases/short_exact.{cfg,par}): base config 124416_222222222399/cfgL24.txt with q=1, digits `2`, KT[a]=4 for all a; parent line `2 2 0 1 0` (a=2, nu=2, eps=[0], b=1, c=0). Y=2^2*3=12, t=(0,0). md5 cfg 63f235cd25fad0a5bfd0adb7e6f513cd, par ea050e5ebd3c8bcc488889a75f9825dc.
- join24 reference: `EXACT 0 2 2 0 0 0 12`, counters children 4, open 0, exact 1.
- lvl24_blind: identical line and counters. (Matches Codex's claim that the source retains the witness.)
- Lane 2 BEST (`LANE2_E0=3 LANE2_A=3 LANE2_C=1 LANE2_WCAND=40 src/lane2`): **no output, exact 0**, rc 0, with `CSTAT parents 1 dead_parents 1`. **Correctness defect in BEST.**
Isolation: the same binary without LANE2_C (`LANE2_E0=3 LANE2_A=3 LANE2_WCAND=40`) prints the EXACT line; `LANE2_C=1` alone drops it. Cause (read, ideaC/c_window.inc c_prepare): the class loop over the K padded digits does `if(d == 0){ dead = 1; break; }`, so with K=4 and Y=0012 every class is dead and the parent is skipped; the EXACT predicate in tail_test (nY%Lnew==nu, no padding test) is never reached. Lane 2 binary md5 9f4a49119d6fa87c310cacd2b010ba5d (built 20:13); lane2.c (md5 fbec746d...) and c_window.inc (md5 081e181b...) carry mtimes 20:38 and 20:38, later than that binary. A rebuild of the current source unchanged (`cc -O3 -march=native lane2.c -lm`, md5 71030e49...) shows the same behavior on all four affected cases, so the defect is in the current source too. I did not touch those files.
Other affected cases (BEST drops, reference and blind print one EXACT each): short_exact_kt3 (KT=3, Y=012 padded), a0_21 (Y=21, a=0, KT=5), short_exact_a1_18 (Y=18, a=1, KT=4). Not affected when KT equals the length (short_exact_kt2: KT=2, OPEN+EXACT both printed by all three), and not affected for a0_27/a0_63/a0_189 (KT=6,6,7 with 2-3 digit Y, yet BEST still prints the EXACT; I did not investigate why the zero rule does not kill these parents). BEST also passed 228/228 only because no corpus parent has a true solution shorter than KT.
Scope: observed on 4 constructed cases; I did not measure how often production parents have short true solutions. No fix applied (BEST is Lane 2's; the fix is to exempt EXACT witnesses, i.e. treat a leading zero pad as live when Y has fewer than K digits and the length/count conditions hold, and re-run the 228 and these cases; that remedy is a suggestion, unverified).

## 5. Other focused checks (focused.py; three implementations on every case; cases/cases.json)
All 19 cases: join24 == blind (rc 0, sorted sha equal) with HALFMAX default, with the HALFMAX=1 build and with the ASan build. BEST agrees on 15, disagrees on the 4 above.
- K<1 (k_lt1, a0_21_k0, long_*_k0): all three print the OPEN line; agree.
- a=0: a0_* cases (above).
- Repeated copies in a slot / multiple slots of one digit: long_rep (Y=3363432789843, digits 2,3x5,4x2,6,7,8x2,9, repeated (digit,residue) pairs, e.g. 3 at positions 0 and 12) and long_multi (Y=1121144263281, one digit at several residues), each with KT=0,4,12; all three print the OPEN line. The 228 corpus also exercises these (primary 228/228).
- Partial batches: instrumented copy (lvl24_blind_instr.c, md5 4f601864ef336ed71451e7a142372b32, not the tested binary; its outputs match) reports flush sizes on eq 124416_222222222399: batch1 1316, batch2 1567, batch3 892, batch4 4346; on eq 124416_2222233689: 4953, 4460, 2499, 3900. Partial batches of sizes 1-3 are exercised, and those two equations match the reference.
- Recursive fallback: `lvl24_blind_halfmax1.c` (HALFMAX 30000000ULL -> 1ULL, md5 2b48eab55b839bb5ecf19eb2fa7460b7, executor-only copy) -> halfmax1. Instrumented HALFMAX=1 copy confirms the fallback is taken (plain_parents 3609 of 3925 and 10591 of 12513 on the two equations; 0 with default HALFMAX). Outputs: 19/19 focused cases join24==blind; STRIDE=19 corpus subset (12 equations, 10 nonempty) 12/12 match. Not the full 228 for this build (bounded subset only).
- Level 48 / 96 headers (corpus cfgL48/cfgL96 with their parents): rc 2, stdout 0 bytes, stderr `this executable supports only level 12 -> 24`.

## 6. ASan/UBSan
`cc -std=c11 -O1 -g -fsanitize=address,undefined` -> lvl24_blind_asan (md5 aa590f096b1baef03232130b7850eb7d), 0 build warnings. detect_leaks=0 (macOS). Scope: all 19 focused cases (0 sanitizer reports in full stderr, rc 0, outputs equal join24) and the STRIDE=19 corpus subset (12 of 228 equations, 12/12 match, 0 reports in runs/*.asan.err). Not the full corpus.

## 7. Skipped / limits
- Full-228 run for the HALFMAX=1 and ASan builds: skipped (subset only).
- No GCC/Linux run (the executor is macOS cc).
- Mutants were not checked against internal work counters; only stdout.

## Commands
- Build: see section 1. Differential: `uv run python -I diff.py ./lvl24_blind primary`; `... ./lvl24_blind k73 BLIND_FORCE_KEY=73` (likewise 137, 73,137); `... ./mut_window mutw`; `... ./mut_625 mut6`; `STRIDE=19 ... ./halfmax1 halfmax1`; `STRIDE=19 ... ./lvl24_blind_asan asan`.
- Cases: `uv run python -I gen_cases.py`; `uv run python -I focused.py all [blindbin=... tag=...]`.
- Witness/premise helpers: wit.py, prem.py.
