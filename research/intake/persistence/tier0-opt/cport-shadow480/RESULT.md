# Level-480 step on the Tier-C pattern y = 3^3 7^10, k = 31

Standing: ordinary proof, machine-executed. The Tier-C pattern is "closed by the sandwich (U'')" at pattern level, conditional on Lemma C, Matveev, Yu 2007 Theorem II and the pattern list. Nothing is PROVEN; not a vertex result.

## Verdict

Pattern y = 7626831723 (a = 0, b = 3, c = 10), 31 digits in classes 0..9, nu = 2, one representation: **CLOSED-sandwich**. Bound 10^302.28 digits (min nearest-point norm has 606 digits) against U''(31,0) = 10^246.0183 (`data/utable_u2_k31.txt`, md5 822e0945, row `31 0`). Margin 56.26 orders. CPU 4 s.

| stage | count |
|---|---|
| digit classes (units (d,e) with multiplicity) + nu unit | 15 |
| Lemma C depth-1 words (at most 5184 deduped masks by count, not instrumented) | 6 |
| level-480 child space per word, as multiset compositions over the 6 words' shared unit set | 2.398e16 |
| zero-sum children mod 31*41*61*211*241*3541*9091 (1.269e17), meet-in-the-middle (Bloom candidates 174,003, verified matches 1) | 1 (the shadow) |
| (word, child) pairs | 6 |
| after the 22 level-480 primes | 3 (words 1, 2, 5 die at 18453761) |
| K = 480 windows tested / alive | 3 / 3 |

Command: `./cport_shadow480 shadow480 --tierc --lattice data/lattice96.txt --utable data/utable_u2_k31.txt --levelprimes data/levelprimes480.txt` (`runs/tierc_k31_run2.txt`).

## What was built

`src/cport_shadow480.c` = `cport_shadow.c` plus the command `shadow480` (diff: 838 added lines, 4 changed lines). All decisions are exact integers (GMP, u128, no floats). The `shadow` command is unchanged in behavior.
- Word children at level 480: each unplaced digit takes t mod 5, the length shifts by 96 sn (sn in 0..4). At the seven trivial-image primes the child passes iff Delta' == 0 (mod their product). All children are enumerated as compositions per distinct (d, e) unit and solved by meet-in-the-middle (Bloom filter over the 5.5e7-entry half, 4.4e8-entry streamed half, exact verification by a second pass). Words only differ by which digits are forced to group 0, so one solve serves all words.
- Every zero-sum child is cut by all 22 level-480 primes (21 under 2^64 plus the 33-digit prime via GMP Pohlig-Hellman; `data/levelprimes480.txt`, md5 3d16b8e0) and the K = 480 window over the digits it puts in copies 1..4.
- `dc_stage` gets an opt-in dedupe of identical (d, e) digits (otherwise the 8 equal digits of class 5 multiply the words).
- Per word: trivial image at the seven primes and tau == 0 are checked; otherwise the representation is NOTAPPL.

## Acceptance

1. Regression (final binary, `shadow` command): the 43 and the 1,335 give whole-file byte-identical `.tsv` to `runs/reg43_old.tsv` (fresh run of the old binary) and `data/shadow1335.tsv`; `VERDICTS_43.tsv` C-full column 0 of 43 mismatches (`tools/compare_reg.py`).
2. `shadow480 --brute480` on the 43 versus `tier0/wordlift480.py` output (`WORDLIFT480-run.txt`): 43/43 same verdict (31 CLOSED-sandwich, 12 CLOSED-cut), same per-representation words / trivial primes / alive counts, bounds within 0.05 (rounding). In every run the meet-in-the-middle set equals the exhaustive set (`--brute480`).
3. See Verdict.
4. Planted negatives (all at k = 31, on the real 6 words and the real 22-prime chain):
   - 12 planted exact points of the word cosets (coordinates 75..116 digits) with their residues at all 22 primes and their 480-digit tail prescribed: all 12 survive the primes and the window, the coset contains the point, nn <= its norm, and the sandwich is refused at the point's own digit count and at U'' (`runs/plants_k31_result.txt`: `PLANTS 12 refused 12, shifted-point control rejected 12`).
   - 8 planted zero-sum children (random compositions, target set to their sum) recovered by the meet-in-the-middle: 8 of 8 (`PLANT-MITM`, 1 to 3 solutions each).
   - Ceiling at the exact boundary U_b (303 digits): CLOSED-sandwich; U_b + 1: `VERDICT open`; the `--mutant loosen` (compare against U - 1) at U_b + 1: `VERDICT CLOSED-sandwich` (verdict flips).
   - Mutant `skipchain=18453761` (drop one level-480 prime from the cuts): alive 3 -> 6, bound 10^302.28 -> 10^299.63; with the boundary table U_b the verdict flips to `VERDICT open bound 10^(10^299.63 log10 U''=302.2758`.
   - Mutant `skipT=9091` (drop 9091 from the filter modulus): zero-sum children 1 -> 1710 (caught by count).
   - Independent Python check (`tools/verify480.py`): the 3 survivor points satisfy all 20 level-96 and 22 level-480 congruences and the 480-digit tail; shifted by (1, 0): 3 of 3 fail.
5. Non-shadow child path: no non-shadow child exists at k = 31, so it is exercised with a reduced filter and chain {31, 41} (`--filter480 31,41 --use480 31,41`) on two patterns against a Python reference built on `wordlift480.lift_word_f` (`tools/py_ref480.py`): same number of distinct surviving cosets (9) and same minimum norm on `22333467`; same counts on `2227888`. Python counts permutations of equal-position digits separately (51 vs 27 survivors), the distinct cosets agree.

## Seams (assumed, not checked)

- Lemma C, Matveev, Yu 2007 Theorem II, the U''(31,0) table row (taken from the package's `k31run/utable_u2_k31.txt`, not recomputed here) and the pattern list.
- The certificate assumes the solution has at least 480 digits; shorter numbers are not covered by this step.
- Only the representation nu = 2, De = TIERC_CLASSES is run; other representations or anchors of vertex 128421199872 are untouched.
- `src/block480.c.txt` is a leftover scratch copy of the inserted block (could not be deleted); it is not built.
- "Planted words" here are exact points and children built for this pipeline; the package's `ucert/planted.py` node format was not reused.
- Load on the machine was high; times are CPU seconds.

## X4: level 480 against the 192/384 shadow on the 1,335

Command: `nice -n 10 ./cport_shadow480 shadow480 --lattice data/lattice96.txt --utable data/utable_u2.txt --levelprimes data/levelprimes480.txt --cases data/cases_1335.txt --only data/only_1335.txt --tsv runs/x4_480_1335.tsv` (`runs/x4_480_1335.txt`, `.err` holds `time -l`).

| level-384 shadow (VERDICTS_1335.tsv) → level 480 | patterns |
|---|---|
| CLOSED-cut → CLOSED-cut | 359 |
| CLOSED-cut → CLOSED-sandwich | 791 |
| CLOSED-sandwich → CLOSED-sandwich | 181 |
| CLOSED-cut → NOTAPPL | 3 |
| CLOSED-sandwich → NOTAPPL | 1 |

- Level 480 closes 1,331 of 1,335. The four NOTAPPL patterns (3211264 222222277888, 3211264 2222222247788, 393216 222222244468, 393216 2222222223488) have a representation whose word fails the trivial-image or tau = 0 check; the 384 shadow closes all four, so the two routes together close 1,335 of 1,335.
- Level 480 never opens a pattern the 384 shadow closed, and never closes one by the cut that the 384 shadow closed by the sandwich.
- The 384 shadow kills more cosets outright (1,153 cut against 359); level 480 closes more by the sandwich because its bound is higher (about 10^302 digits against about 10^239).
- Cost: 44.4 s user CPU, 82.5 s wall, 82 MB peak resident, 52,742 discrete logs. The 384 shadow took 80 s CPU on the same set (`../cport-shadow/RESULT.md`). Single runs on a loaded host (load about 17 on 10 cores), so the ratio of about 1.8 has no interval.
