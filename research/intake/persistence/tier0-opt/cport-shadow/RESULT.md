# Lane 3: the shadow certificate in the C final stage

Standing: ordinary proof, machine-executed, conditional on Matveev and Yu 2007 (U'') for the CLOSED-sandwich class; nothing Lean-checked. Verdicts are
"closed by the sandwich (U'')"-class at most, never PROVEN. No vertex changes status; nothing is swapped into production; `cport/`, `tier0/` and the engine are untouched
(`cport_shadow.c` is a copy; its diff against `cport/cport.c` is `cport_shadow.diff`: 797 added lines, 1 changed line = the usage string, 1 added dispatch line).

HSHADOW.md version: the on-disk `tier0/HSHADOW.md` has md5 792ad735 (mtime 18:44 EDT). The chat line of 19:15 cites 2b5cd764. This port follows the on-disk 792ad735
text (3 facts of section 2, the DP and 3-step certificate of section 3). The two md5 values name different texts; which one the chat meant is unresolved.

## 1. What was built

`src/cport_shadow.c` (md5 a83d7289 at the time of writing; `make` builds `cport_shadow`, md5 of the binary 64f48642; a rebuild changes the binary bytes, not the source) = `cport.c` plus the command
`cport_shadow shadow` (and `dptest` for the planted DP checks). All integer arithmetic is exact: GMP for cosets, 10-adic cuts and sandwich comparison
(`sandwich_closes`, an exact integer inequality), `unsigned __int128` mulmod for the discrete logs (Pohlig-Hellman with BSGS per prime power,
every result re-exponentiated), no floating point in any decision. Per representation of an anchor:

1. Depth-1 words from the unchanged `dc_stage` (Lemma C at K = 96). r = unplaced digits of a word.
2. One counting DP over Z/148417 (layered reachability bits, backtracking enumeration) listing every (S, sn) with
   Delta(S, sn) = sum_{j in S} (d_j - 1) 10^{e_j} + sn * 10^nu / 9 equal to the word's target tau (mod 148417). The ν-shift item is `10^nu * 9^-1 mod 148417`.
3. Per word, checked directly: the word basis maps to 1 modulo 193 and 769 (trivial image), `content(basis)` is divisible by 768, the lattice equals Lambda'_a
   (same index, basis inside it), and tau = (2^a 3^{b0} 7^{c0} - V) / (10^96 - 1) modulo 193 and 769 (tau = 0 exactly when the shadow passes both primes).
4. The shadow: cut by the seven level-192 primes (exact `dlog` of V), then the K = 192 window, then **all** level-384 branches (see section 2), then the
   K = 384 window; survivors get the exact nearest-point norm and are compared with U'' by the exact inequality.
5. Every non-shadow level-192 candidate from the DP (S inside the unplaced digits of the word) is tested exactly: seven primes, then the K = 192 window over the
   subsets of S fixed at copy 1. A survivor is carried to level 384 by the same general routine (`lift384_state`), so the certificate never relies on "the shadow is the only child".

Level-384 step (`lift384_state`). A level-192 state is a set of fixed digits (copy 0 or 1) and unplaced digits with t == rho (mod 2). Its level-384 children are
(sn', b): length nu1 + 192 sn', unplaced digit j at residue rho_j + 2 b_j (mod 4). At all four level-384 primes 10^192 == -1, hence
V2 = V1 + (10^192 - 1)(sum_{b_j = 1} (d_j - 1) 10^{e_j + 96 rho_j} + sn' 10^{nu1} R_192) == V1 - 2 Delta'. The children landing in the image of the coset at the two
smallest-image primes are found by meet-in-the-middle on a sorted half-sum table (targets: the |T_p1| |T_p2| residues of the coset image, 12 for 3457 x 12289); each candidate
is then tested exactly at all four primes, and each survivor goes through the K = 384 window over the subsets of its unplaced digits with residue >= 1 (fixed at t = residue).
`--brute384` enumerates all 2^(r+1) children by the exact prime chain and compares the passing sets: **MITM set == brute set on all 14,325 words of the 1,335 run** (793 passing children).

Differences from `shadowcert.py` (all on the sound side): (a) the K = 192 window is applied to the shadow; (b) the level-384 prime cut is applied to V2(T, sn'), not to V,
and the copy-2 windows are attached to the branch whose V2 produced them; (c) words whose target tau is not 0 (shadow fails 193/769) are handled by the DP with their own target
instead of an assertion; (d) non-shadow survivors are lifted, not reported as BUDGET. `--faithful` reproduces `shadowcert.py` exactly (fixed V at 384, copy-2 window over all unplaced
digits, no K = 192 window, non-shadow survivors -> EXTRA); it exists for the comparison below.

## 2. Gaps in HSHADOW.md and what the data says (the coordinator's G1-G4)

- **G1 (level 384 is not covered by testing V).** Confirmed. The shadow's level-384 children depend on (T, sn'), and V2 = V1 - 2 Delta' modulo the four primes.
  The fixed-V step of `shadowcert.py` tests V and then lets digits sit at copy 2 in the window: those windows belong to branches whose prime residues were never tested.
  Reduced-system evidence (only the prime 3457 enabled at level 384, the 43 patterns): the full routine finds 220 surviving cosets, 124 of them non-shadow branches
  (T non-empty, sn' = 1); `tools/verify_points.py` re-checks a point of each of the 220 with Python big integers against every congruence of its branch (220 of 220 pass);
  the fixed-V variant reports 1,179 cosets, none of them one of these 124 branches. With all four primes the non-shadow branches die (0 survivors on the 43 and on the 1,335),
  so **verdict changes caused by G1: 0 of 43 and 0 of 1,335** (the fixed-V routine and the full routine give the same closed/class verdict on the 1,331 patterns where `--faithful` applies).
- **G2 (shadow residue check per word) is not a formality.** On 4 of the 1,335 patterns the shadow fails the level-192 primes for some words (16 words; tau = 65963 in every case):
  `3211264 222222277888 2 1411788`, `3211264 2222222247788 0 7411887`, `393216 222222244468 0 330812181`, `393216 2222222223488 0 330812181`. The true level-192 survivor there is a non-shadow child
  (S = one digit, sn = 1). `shadowcert.py` would stop at `assert co1 is not None`; the port tests the 8 DP candidates exactly, finds 16 child states alive after the K = 192 window, lifts them to 384 and
  closes all four patterns (3 CLOSED-cut, 1 CLOSED-sandwich). `--faithful` reports EXTRA on exactly these four.
- **G3 (content of Lambda'_a for every a).** Checked for a = 0..63 at start-up (`CONTENT` lines in `runs/shadow1335.txt`) and again per word (lattice equal to Lambda'_a, 768 | content, basis images trivial at 193 and 769):
  content(Lambda'_a) = 33862613400000000 = 2^9 * 3^2 * 5^8 * 7 * 11 * 41 * 59 * 101 for **every** a in 0..63 (a does not enter the content); 768 | content; 0 failures on 14,325 words.
  (The text of HSHADOW.md section 2 gives 2500 * m with m = 2^7 3^2 5^4 7 11 41 59 101 for a = 0: 2500 * m = 2^9 * 3^2 * 5^8 * ... = the value above.)
- **G4 (shadow passes the other five primes and the K = 192 window)** is tested per word, not assumed: `sh192dead` (shadow dead at the seven primes) and `win192dead` (dead at the window) are in every detail line.
  Totals over the 1,335: 16 words with the shadow dead at the primes (the G2 cases), 0 with the shadow dead only at the K = 192 window.

## 3. Verdict-for-verdict

### 3.1 The 1,335 final-stage sandwich patterns (`runs/shadow1335.txt`, `VERDICTS_1335.tsv`, `runs/compare1335.txt`)

Command (80 s CPU on a loaded machine, nice 10, one core):
`./cport_shadow shadow --lattice data/lattice96.txt --utable data/utable_u2.txt --cases data/cases_1335.txt --only data/only_1335.txt --levelprimes data/levelprimes.txt --diag --brute384 --stats runs/stats1335.tsv --tsv runs/shadow1335.tsv --dump runs/dump1335.jsonl --dump-surv runs/surv1335.jsonl --reps runs/reps1335.tsv`.
Inputs: the 1,335 patterns with status `sandwich` in the final-stage run of `FINAL-STAGE-run-U2.txt` (snapshot md5 a6911e81, copied to `data/snap/`).

| | old (`FINAL-STAGE-run-U2.txt`, per-pattern `sw/*.tsv`) | new (shadow certificate, U'' table `utable_u2.txt`) |
|---|---|---|
| closed | 1,335 (depth 1: 273, depth 2: 1,041, depth 3: 21) | 1,335 |
| class | CLOSED-sandwich at the depth shown | 1,153 CLOSED-cut (no coset survives level 384), 182 CLOSED-sandwich |
| per vertex | 42 vertices with sandwich patterns | counts match the old CLOSED-sandwich count on all 42 (`runs/pervertex.tsv`) |

Disagreements in closure: **0**. Class changes: every old pattern was closed by the sandwich at depth 1-3; 1,153 of them are closed with no surviving coset at level 384 depth 1
(the Lemma C / prime cut at level 384 kills them outright, a stronger statement than the sandwich), 182 keep one coset per word whose certified bound 10^238.1..10^239.4 digits exceeds U''
(smallest margin 110.8 orders, pattern `3211264 2222222222222778 0 330812181`: bound 10^239.29, U'' = 10^128.5; the old smallest margin was +4.93 orders).
Every old CLOSED-sandwich that the new routine calls CLOSED-cut is explained by the extra level-384 prime cut; none is open.
A >= 64 inputs: **0 of the 1,335** patterns come from an equation with A >= 64 (`tools/a64.py`: `tier0v2.two_adic_bound` of each (s, M); maximum 63).
117 patterns sit on vertex 393216, all from equations with A <= 63; the A >= 64 equation of that vertex (M = 2^15 3 4, A = 66) contributes no recorded open pattern,
so its old verdict (0 open) is the defect's output and is not a reference here; the 1,335 are an incomplete list of the true final-stage inputs for the seven affected vertices,
which a rerun with the fixed `lvlN` would extend.

### 3.2 The 43 hardest (`VERDICTS_43.tsv`)

| implementation | closed | CLOSED-cut | CLOSED-sandwich | verdict differences vs the others |
|---|---|---|---|---|
| `SANDWICH-full-U2.txt` | 43 (depth 1: 33, depth 2: 10) | | | closure agrees |
| `shadowcert.py` (SHADOWCERT-run.txt, 574 s) | 43 | 37 | 6 | 0 |
| C `--faithful` | 43 | 37 | 6 | 0 (alive counts 2, 4, 8, 3, 12, 8 and bounds 10^238.2..239.1 equal the Python lines) |
| C full | 43 | 37 | 6 | 0 (bounds 10^238.99..239.25; one coset per sandwich pattern) |
| blind Codex `certificate_blind.js` via the harness | 43 | 37 | 6 | 0 (47 of 47 representations agree) |

Fixed-V diagnostic against the full-branch result for the six sandwich patterns (cosets surviving the K = 384 window): fixed V 2, 4, 8, 3, 12, 8; full routine 1, 1, 1, 1, 1, 1.
The blind implementation's own diagnostic reports the same fixed-V counts (2, 4, 8, 3, 12, 8) and one branch each; dp_nonshadow_count is 0 on all 47 representations.
Wall: 0.3 s in C against 574 s in Python for the 43.

## 4. Planted negatives and mutants

| # | Test | Result |
|---|---|---|
| N1 | exhaustive child truth for the DP: 8 synthetic representations (k = 18), all 2^19 children built from the actual positions (e, e + 96, length nu + 96 sn), kept when congruent to V modulo 193 and 769 (`tools/planted_dp.py`) | correct DP == truth on 8 of 8 (41 solutions, 21 with the nu-shift) |
| N2 | mutant: nu-shift term dropped (`--mutant noNu`) | caught: 8 of 8 representations differ from truth |
| N3 | mutant: wrong modulus 193 * 773 (`--mutant wrongmod`) | caught: 8 of 8 differ |
| N4 | the same mutants on the real G2 patterns: correct run lifts 2 children per pattern; mutants lift 0 | caught; with the level-384 system reduced to {3457} the correct run keeps survivors (CLOSED-sandwich, 2 and 18 cosets) and both mutants report CLOSED-cut with 0 survivors |
| N5 | fixed-V level 384 (`--faithful`) under the reduced system {3457} | misses 124 non-shadow branches that are verified members of the relaxed system (section 2, G1) |
| N6 | independent point check: nearest point of every reported survivor coset, 2^a 3^b 7^c checked with Python integers against all level-96/192/384 prime congruences and the 96/192/384-digit tails (`tools/verify_points.py`) | 6 of 6 on the 43, 150 of 150 (random sample of the 1,335 survivors), 220 of 220 in the reduced system; the check refuses: the same points shifted by (1, 0) fail 6 of 6 |
| N7 | sandwich boundary: U set to the largest value the exact inequality still closes, and to that value + 1 (`runs/utable_boundary_*.txt`) | 6 of 6 sandwich patterns close at the boundary value; at +1, 5 of 6 are refused (1 still closes: its bound is larger than the others' sharing the same (k, a)) |
| N8 | table with every entry 10^400 (`runs/utable_inflated_400.txt`) | 0 of 6 sandwich patterns closed (6 OPEN) |
| N9 | `cport_shadow selftest` (inherited: nearest point 2000 cosets, 300 of 300 genuine S-units survive K = 96..480, 300 of 300 corrupted tails excluded, 60 of 60 own patterns) | PASSED (`logs/selftest_cport_shadow.txt`) |

Limit stated: a genuine S-unit with k <= 24 non-1 digits and 384 or more digits does not exist in the data, so "a genuine point is never certified" is tested as: every point of every reported
survivor coset satisfies all congruences (N6, positive), the checker rejects perturbed points (N6, negative), mutated DPs lose real members (N2-N5), and the sandwich comparison is exact at its boundary (N7, N8).
The REDTEAM-SANDWICH scripts (`rt_plant10adic.py`) are not in the repository; N6 is the analogue for the modular part (it checks the points of the reported cosets, it does not construct 10-adic words independently).

## 5. content(Lambda'_a)

`CONTENT a=0..63`: content = 33862613400000000 = 2^9 * 3^2 * 5^8 * 7 * 11 * 41 * 59 * 101, 768 | content for all 64 values, basis images at 193 and 769 trivial.
Runtime assertion: `cport_shadow shadow` dies before reading any case if any of these fails (`--no-assert` only prints), and checks every word's lattice against Lambda'_a.

Lean: not attempted (skipped, within the one-hour allowance it would not be finished). Assessment: stating "for every a, 768 | content(Lambda'_a)" needs the lattice Lambda'_a as a Lean object
(an intersection of the kernels of 20 prime congruences, 3^b 7^c == 1, plus the 5-adic and 2-adic kernels), a certificate that the computed basis generates it (determinant = index, containment by
modexp checks, and that the index equals the product formula), then `decide`/`native_decide` for the gcd. The numeric parts are cheap; the generation certificate is the work and needs Mathlib lattice-index
lemmas not found ready-made. Estimate: an afternoon, not an hour. The cheaper sufficient statement used by the certificate is the per-word check "basis maps to 1 modulo 193 and 769", a `decide` on two 2x2 integer matrices once a word basis is given.

## 6. Other deliverables

- `R_BY_K.md`: r, words and 2^(r+1) child counts by k on the 1,335.
- `NOTES-u2-k29.md`, `data/utable_u2_k29.txt`: U'' to k = 29, certified.
- `PH768.md`: level-768 primes and Pohlig-Hellman cost.
- `harness/`: see section 7.
- Files: `src/cport_shadow.c`, `cport_shadow.diff`, `Makefile`, `data/` (cases, only lists, levelprimes, U'' tables, snapshots), `runs/` (all outputs), `logs/`, `tools/`.

## 7. Harness for an external implementation (`harness/harness.py`)

Input per representation (JSON, one object per line from `cport_shadow shadow --dump F`, or an array): `id`, `modulus` (148417), `a`, `nu`, `min_digits` (384),
`digits` [{d, e}], `upper_digits` (the U'' integer), `words` [{id, fixed (digit indices at copy 0), offset [b, c], basis [[..], [..]]}]. This is the schema of `certificate_blind.js`.
The external program reads the JSON array on stdin and writes a JSON array of objects with `id` and `verdict` (CLOSED_CUT / CLOSED_SANDWICH / OPEN / NOT_APPLICABLE).

```
python3 harness/harness.py make runs/dump43.jsonl runs/patterns43.json
python3 harness/harness.py run runs/patterns43.json runs/blind43.json -- node ../codex-blind-shadow/certificate_blind.js
python3 harness/harness.py compare runs/blind43.json runs/reps43.tsv        # exit 1 on any disagreement
```
`runs/reps43.tsv` holds the C verdict per representation (`--reps`). Result on the 43: 47 of 47 representations agree.

## 8. Cross-checks that ran long

- `wordlift.py` (full children enumeration, independent algorithm) on the four G2 patterns (`runs/wordlift4.txt`, 1,341 s): words 39 / 86 / 2 / 2, alive at 192 = words, alive at 384 = 0 / 2 / 0 / 0,
  verdicts CLOSED-cut / CLOSED-sandwich (bound 10^239.1, U'' 10^106.9) / CLOSED-cut / CLOSED-cut: identical in class and word counts to the C port (bound 10^239.08).
- `certificate_blind.js` on the 1,335: stopped without output. The full array (2,655 representations) ran 35 min CPU and a subset with at most 7 unplaced digits per word ran 18 min; the blind code enumerates all
  2^(r+1) level-384 branches in BigInt, so no verdict-for-verdict result exists for it beyond the 43 (47 of 47 agree). Not completed; reported as skipped.
