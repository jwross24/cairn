# ROOT-SIEVE: anchor-free additive conditions on level-12 patterns

Directory: `P/tier0-opt/rootsieve/` (P = `/Users/jwross/Documents/cairn/research/intake/persistence`). Nothing under
`P/tier0/` or another lane's directory was edited; `lvl12.c` was copied to `lvl12_r2.c` before modification.
Prediction registered before any compute: `PREDICTION.md` (5% for 100x or more, 60% partial, 35% dead).

## 0. Verdict: PARTIAL, and short of 100x by a factor of five or more

| quantity | value | label |
|---|---|---|
| Best anchor-free additive condition | rank: 3 divides x (digit sum, a function of nu and the multiset) and 7 divides x (a function of nu mod 6 and the classes mod 6) | derived on paper, checked on 1,042 planted solutions and 137,292 recorded open@96 items |
| Cut of the enumeration (hot loop) if only rank-2 patterns are enumerated | 21.00x exactly in pattern count (4.7616% of patterns, interval [4.7595, 4.7637]%); realized 6.2x to 15.6x in wall time on four Tier A multisets by a direct kernel change | counts exact, times measured, kernel not tuned |
| Cut of level-12 survivors by the same condition | 19.69x [19.63, 19.75] on residue survivors; 20.38x [19.99, 20.79] on tail-open patterns | measured on 4.0e8 uniform patterns of the Tier C vertex |
| What the cut costs | the rank-0 and rank-1 streams still hold 2.13% [1.86, 2.44] of the final open parents (203 of 9,529); no kernel for them exists | measured share, kernel unbuilt |
| Second condition, new | 2-adic divisibility chain over the low classes, capped at the digit count: 2.09x [2.05, 2.13] on the open parents | derived on paper, checked on 1,042 plants and 137,292 items; applies after the V test, so it does not touch the hot loop |
| Anything giving 100x or more | none found | every other candidate is vacuous or needs V; see section 2 |

The rank condition is already in the survivor path (`P/tier0-opt/branchsplit`, `P/tier0-opt/math/r1-branch-split`, 19-20x
measured there; the production `lvl12` runs now take a `bs` argument). This lane adds: (i) the same cut measured on the
Tier C vertex itself with intervals, (ii) the observation that it can be moved into the enumeration order (21x in
pattern count), (iii) the chain condition, (iv) the proof that no other V-free condition exists at level 12.
A sound filter with a measured cut factor is a cost reduction, not a closure.

## 1. Why the pattern representation limits what can bite

A level-12 pattern fixes nu = n mod 12, the digit values, and the classes e mod 12. A condition on x can be evaluated
from the pattern alone only if it is a function of that data. Of the additive facts about x:

- x mod 3 is the digit sum mod 3, n + sum(d_j - 1), needing n mod 3 only. Function of the pattern. Gives 3 | x or not.
- x mod 7: 10 has order 6 mod 7 and 6 divides 12. Function of the pattern. Gives 7 | x or not.
- x mod 9, 27, 81, 243, 729 and mod 49, 343: not functions of the pattern. They need n mod 9.. and positions mod 3^(j-2)
  and mod 42.. The reachable set over all lifts of a pattern is the full class mod 3 (resp. mod 7). Measured on 400
  rank-2 survivor patterns, moduli 27, 81, 243, 729, 49, 343, 27*49, 81*343: zero reachable in 400 of 400 for every
  modulus; the mean reachable-set fraction is exactly 1/3 and 1/7 (so the only information is the residue mod 3 and mod
  7). Negative control: patterns with 3 not dividing x, modulus 27: zero reachable in 0 of 400. (`reach.py`,
  `reach_main.out`.)
- x mod 2^m, 5^m, i.e. the low digits: positions are known mod 12 only, so the window is a statement about classes
  0..m-1, and it is conditional. Without V the all-ones window with alpha = 0 (x odd, last digit 1) is always admissible
  (111 mod 8 is a unit, 111 is coprime to 5), so no prefix of low classes can be pruned: P(pruned) = 0 exactly. The window
  bites only given a, and a mod 12 is read off V by the multiplicative test.
- The 5-adic part: 3 is a primitive root mod every 5^s, so x mod 5^s is unconstrained by itself. With the coset, b is
  known mod 9900 and c mod 900, which fixes x mod 5^3 and no further (the order of 3 mod 5^4 is 500, and 500 does not divide
  900). That is the K = 3 tail the kernel applies, and it needs V.
- Theorem F, Lemma C, the 10-adic descent: they act on actual positions below a + 9 or 5, which a class mod 12 does not
  give. They apply from level 96 (positions mod 96 against windows below 96) and are outside what a level-12 pattern can
  state.

The multiplicative test is silent on 3 and 7 (the prime set excludes them), so the rank condition is independent of
it: among residue survivors the rank shares are 57.0 / 38.0 / 4.8% (4,617,509 / 3,076,995 / 384,152), the same as among all
patterns.

## 2. Candidate conditions

| condition | function of the pattern? | selectivity | independent of the level-12 test? | verdict |
|---|---|---|---|---|
| rank, 3 divides x (via nu and the multiset) | yes | with 7: 21.00x in pattern count | yes (shares equal among survivors) | live, partial |
| rank, 7 divides x | yes (last class) | see above | yes | live, partial |
| (b, c) coset must contain b = 0 / c = 0 for the absent prime | needs V | 0.85% of rank-1 survivors pass, 7 of 4.6e6 rank-0 | the filter that realizes the 19.7x | in production already |
| 2-adic chain, window min(a, q) | needs a (hence V) | 2.09x on open parents, 3.6x on bare rank-2 survivors | close to independent of the K = 3 tail: of 731 sampled rank-2 survivors 203 pass the chain alone (27.8%), 20 pass the tail alone (2.7%), 10 pass both (independence predicts 5.6) | live for the lift, 0 for the hot loop |
| a-first enumeration with window pruning (the quantifier swap) | a0 = 0 class has no window | none | n/a | dead: a0 = 0 holds 1/12 of the survivors and needs the full enumeration, the other classes add work |
| x mod 9, 27, 49, ... | no | 1.0x | n/a | dead (section 1) |
| last digit not 5, x mod 125 | needs V | inside the tail | no | already applied |
| archimedean (length against exponents) | no | vacuous: n is free mod 12 and the lattice has finite index | n/a | dead |
| Theorem F, Lemma C | needs positions | not available at level 12 | n/a | dead for level 12 |

Do not retry any of the dead rows without new data: each is a statement about what a class-mod-12 pattern determines, and
that statement is settled by section 1.

## 3. Measurements

All on the Tier C vertex 3416267673274176 = 2^6 3^27 7: 306 multisets, 17,240,008,221,052,531,200 level-12 patterns
(equal to FRONTIER.md and to the exact census in `tierc-rank`). Sampler `rs.c` (copy of the `lvl12.c` residue, coset and
tail code; patterns drawn uniformly: multiset by pattern count, classes by stars and bars). Interval: Wilson 95%.

4.0e8 samples (`rs_main.out`, `stats.out`):

| statistic | count -> count | cut | 95% interval |
|---|---|---|---|
| residue survivors -> kept by rank | 8,078,656 -> 410,269 | 19.69x | [19.63, 19.75] |
| residue survival rate | 1 in 49.51 | | matches dpcount (1/49.5) |
| tail-open patterns (any a up to 118) -> kept | 194,238 -> 9,529 | 20.38x | [19.99, 20.79] |
| (a, pattern) lines, a up to 60 / 118 / 160 | 41,066,632 / 80,114,575 / 108,388,446 -> 1,966,361 / 3,835,718 / 5,189,496 | 20.88x / 20.89x / 20.89x | [20.86, 20.91] / [20.87, 20.91] / [20.87, 20.90] |
| tail-open lines, a up to 60 / 118 / 160 | 327,872 / 643,157 / 871,224 -> 15,897 / 31,202 / 42,113 | 20.62x / 20.61x / 20.69x | [20.3, 20.9] / [20.4, 20.8] / [20.5, 20.9] |
| rank-2 share of patterns | 4.7616% | hot loop 21.00x | [20.99, 21.01] |
| final open parents outside rank 2 | 203 of 9,529 (all rank 1; rank 0: 0) | | 2.13% [1.86, 2.44] |
| chain pass among the 9,529 open&kept patterns | 4,561 | 2.09x | [2.05, 2.13] |

The cut does not depend on the unknown true A: it is 20.9x at A = 60, 118 and 160. A = 118 is the lower bound found by
dpcount; the true A for these multisets is larger.

Parents for this vertex: open&kept patterns 4.11e14 [4.03e14, 4.19e14] (rate 2.38e-5 of patterns); 1.97e14 after the chain.

Sampler cross-check against the production kernel: for multiset 2,4,6^4,7^3 (8.59e8 patterns, vertex shape of Tier A)
all 154,110 OPEN lines of the unmodified `lvl12` are reproduced as open by the sampler's test (154,110 of 154,110), of
which 7,651 are rank 2 (`xval.out`).

### Hot-loop kernel (`lvl12_r2.c`, compiled with `-DR2`)

Enumerates only patterns with 3 | x (nu restricted, 4 of 12 values per multiset) and 7 | x (the last digit's class is
solved from V mod 7: at most two of 12 classes). Four Tier A multisets, best of three, user CPU on a loaded machine
(`bench.out`):

| multiset | patterns baseline -> stream | wall ratio | open + exact lines, baseline restricted to rank 2 vs stream |
|---|---|---|---|
| 2,3,7^3,8^2 | 49,061,376 -> 2,336,256 (21.00x) | 12.7x | 187 = 187, identical |
| 3,4^2,7^3,8 | 49,061,376 -> 2,336,256 (21.00x) | 15.6x | 55 = 55, identical |
| 4,6^4,9^3 | 71,547,840 -> 3,407,040 (21.00x) | 6.6x | 247 = 247, identical |
| 2,4,6^4,7^3 | 858,574,080 -> 40,884,480 (21.00x) | 6.2x | 7,651 = 7,651, identical |

The pattern count falls by exactly 21.00x; the wall time falls by less because the recursion overhead per visited leaf
rises. Extrapolating to Tier C shapes (k = 17 to 34, large groups) is not measured: the two multisets with large
groups gave 6.2x and 6.6x. At 8 ns per pattern the full enumeration is 4,370 core-years; the rank-2 stream is 208
core-years at the 21x bound and about 700 core-years at 6.2x. The rank-0 and rank-1 streams are extra: 2.13% of the
final open parents, no kernel built. A join of a dense bitmap over Z/P against the target set (about 1.6e6 residues
for rank 1: the cosets 2^a<3> for a up to 160, each of size 9,900) would cost roughly the number of outputs; that is an
estimate from counting, not a measurement.

## 4. Soundness and planted negatives

Soundness of the rank filter is a theorem: 3 not dividing x forces b = 0, 7 not dividing x forces c = 0, and the
coset test asks whether (b, c) = 0 on the absent axis lies in the coset (derived on paper; the same argument as
`r1-branch-split/REPORT.md`, whose lattice test `rs.c` copies). Checked on:

- 1,042 planted solutions: every zero-free x = 2^a 3^b 7^c below 10^120 with at least four digits and digits in
  {1,2,3,4,6,7,8,9} (10 pure powers of 2, 236 with one odd prime, 796 with both). Every plant is kept at its true a,
  open and kept: 1,042 of 1,042.
- 137,292 recorded open@96 items from 23 vertices of `trees_mac.jsonl` (29,543 rank 1, 107,749 rank 2; the record holds
  no rank-0 item): kept 137,292 of 137,292.
- The 154,110 production OPEN lines above.

Planted negatives (a deliberately wrong congruence must remove known open patterns; `soundness.out`):

| mutant | plants lost | recorded open@96 items lost |
|---|---|---|
| 3-adic branch inverted | 942 of 1,042 | 132,037 of 137,292 |
| 7-adic branch inverted | 886 of 1,042 | 113,004 of 137,292 |
| b shifted by one | 100 of 1,042 | 5,255 of 137,292 |

Chain condition (`chain.py`, `chain_sound.py`). Statement: for a line with exponent a and q non-1 digits, set w = a if a
is less than q (the number has more than a digits, so position a exists and the exactness bit applies) and w = q
otherwise (n is at least q, so positions 0 to q-1 exist and only divisibility by 2^q is asserted). With u_0 = 0 and
u_(p+1) = (u_p + c_p 5^p)/2, a digit c_p at position p must have the parity of u_p for every p below w, drawn from 1 or
a pattern digit of class p mod 12, each pattern digit used once; for a less than q the digit at position a must have the
opposite parity. The window must be capped at q: an uncapped window (all positions up to a assumed present) rejects 414
of the 1,042 plants, which are true solutions with fewer digits than a. With the cap: plants 1,042 of 1,042 feasible,
open@96 items 137,292 of 137,292 feasible. Planted negative (one non-1 digit moved to another class, a at least 3):
rejected 353 of 888 plants and 10,990 of 55,132 items. Whether levels 24 to 96 already remove the same parents before
doing lift work is not measured; the 2.09x is a cut of level-12 parents.

## 5. Where the cost sits (projection, not measured here)

Using LIFT-ADDITIVE.md unit costs (floor of about 1 ms per level-12 parent for the 12 to 24 step, 0.9 s at q = 22, 110 s
at q = 29): 4.11e14 parents at 1 ms is 13,000 core-years, 6,200 after the chain. The parents of the lift stage exceed
the hot loop even before the q-dependent cost is applied. A 21x cut of the enumeration moves 4,370 core-years to
208 to 700, and leaves the lift stage as the wall that dpcount and LIFT-ADDITIVE already name. The ratio of hot loop to
lift floor depends on the 1 ms figure and on parent counts from this lane's sampler (A up to 118); I did not run a lift.

## 6. Do not retry without new data

- A prefix-pruned enumeration keyed on low-class windows (2-adic or 5-adic) or on a-first ordering: the all-ones window
  with alpha = 0 is always admissible and a0 = 0 is one twelfth of the survivors.
- Any modulus other than 3 and 7 on the pattern value (9, 27, 49 and higher powers): the reachable sets are complete.
- Moving the rank condition expecting 100x: the pattern fraction is 4.7616% exactly, so 21.00x is the ceiling.
- Lemma C or Theorem F style congruences at level 12: they need positions.

## 7. Seams

- The sampler reproduces the kernel's residue, coset and K = 3 tail logic (154,110 of 154,110 OPEN lines of one
  multiset reproduced) but is a separate program; the Tier C kernel itself was not run. `a` is capped at 160 by the
  configuration; A = 118 is dpcount's lower bound.
- The hot-loop times are from four Tier A multisets with k = 7 to 9 on a machine at load average 44 to 51; user CPU,
  best of three.
- The separate rank-0/1 path is not built; the join cost is an estimate.
- The lift cost in section 5 is a projection from another lane's unit costs.
- Process deviations: two early read-only inspections used a bare `python3 -` heredoc instead of a script file run with
  `uv run --no-project python -I`; one 60-second foreground `sleep` was issued while waiting for the sampler; a short
  `plants.py` run overlapped the sampler for a few seconds (two compute processes); scripts used `uv run` with
  `--with sympy`, `--with gmpy2` or `--with numpy` where the imported tier0 modules or numpy needed them; `patch*.py`
  files are one-shot edit helpers that rewrote `rs.c`, `chain.py`, `reach.py` and the copy `lvl12_r2.c`. No file was
  deleted, nothing was staged or committed, and no process of another lane was touched.

## 8. No-Claim

A sound filter with a measured cut factor is a cost reduction, not a closure; it does not establish Hypothesis H.
Nothing here is PROVEN or Lean-checked; the statements are derived on paper and checked on the stated numbers of cases.

## 9. Commands and md5

All from `P/tier0-opt/rootsieve`, prefixed `PYTHONDONTWRITEBYTECODE=1 nice -n 10`; `PY` is `uv run --no-project python -I`.

| step | command |
|---|---|
| configuration | `PY gen_cfg.py 160` (needs `--with sympy --with gmpy2`) |
| sampler | `cc -O2 -o rs rs.c`; `./rs cfg_tierc.txt multisets_tierc.txt 400000000 20261024 dump_main.txt 0.002 > rs_main.out` (the binary of the main run was built from `rs_main_src.c`) |
| statistics | `PY stats.py > stats.out` |
| chain | `PY chain.py dump_main.txt > chain_main.out`; `PY chain_sound.py > chain_sound.out` |
| reachable sets | `PY reach.py dump_main.txt 400 > reach_main.out` (`--with numpy`) |
| plants and recorded items | `PY plants.py 120`; `PY openpat_in.py`; `./rs_check cfg_tierc.txt -check M < plants_in.txt` and `< openpat_in.txt` for M = 0 to 3; `PY verify_all.py > soundness.out` |
| hot loop | `PY gen_cfg2.py <digits> cfg_Ax.txt` for four multisets; `cc -O3 -march=native -o lvl12_base ../lvl12.c`; `cc -O3 -march=native -DR2 -o lvl12_r2 lvl12_r2.c`; `PY bench.py > bench.out` |
| cross-check | `PY xval.py > xval.out` |

md5 (`md5_outputs.txt` holds the full list):

| file | md5 |
|---|---|
| `PREDICTION.md` | 7612190ba94411230ba9b3e35c3bdc7c |
| `rs.c` / `rs_main_src.c` | 887a61636e28b216db7e044b98c4843d / aa7e69be480df4428cba1769c0353347 |
| `rs` / `rs_check` | 8be258291abddf1a551db6a7abe613e5 / 71ac9beca06dfab2a6fbf2cf68ce3ddb |
| `lvl12_r2.c` / `lvl12_r2` / `lvl12_base` | b4970cdb0682f743031428008ea0f3e9 / 40a581b978b269010cbdcd4671494312 / af8e1fa2bb37109a9425a5a3fe9a50ba |
| `rs_main.out` / `stats.out` | 404028f25cadd268d144d60c1d1ebfeb / 3c1bea1b40e5a2e2f7529922c5ac9ee8 |
| `chain_main.out` / `chain_sound.out` / `reach_main.out` | e2533d42d0ab38c7c9ef7a401006bd91 / cb823d84016f26161e77eee360c74f91 / 6d7584ae9ba0b8d25137e1d7e773cb28 |
| `soundness.out` / `bench.out` / `xval.out` | e73b2f48641dd6270b0f5a93952cd04e / 662380f8f75aed00d4c3928b62efd786 / 328254ef565ebf729282e1e8119c6c7d |
| `dump_main.txt` / `cfg_tierc.txt` / `multisets_tierc.txt` | eda75a5998713b9a0a75b62b6156df78 / 8137db6430934fcb6d1907495d3be17c / ed685255711b24ce39dec681c1e2e401 |
| `../lvl12.c` (input, unmodified) | 8f60d9840254d735cf9a422409489e94 |
