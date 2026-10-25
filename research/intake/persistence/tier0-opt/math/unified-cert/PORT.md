# C port of the unified certifier: plan, cost model, differential test plan, and the k = 31 pattern experiment

Scope. This is a plan. No C has been written. Everything quoted as measured comes from `logs/` in this directory
(Python package, one niced core) or from the cited N1 lane logs. Anything labeled "estimate" is arithmetic on those
measurements, not a measurement.

Calibration. The k = 31 run in section 6 is a pattern-level experiment. A pattern that every node of which certifies is
"closed by the sandwich (U'')" at most, conditional on Lemma C, Matveev and Yu 2007 Theorem II, and the pattern list.
It is not a closure of vertex 128421199872, and nothing in it is PROVEN.

## 1. What is ported

| Python | role | C |
|---|---|---|
| `cert_cvp.expand_nodes` | digit-ordered depth-E node enumeration, linear extension from 12 digits | `uc_expand` on top of `cport.c` `cut_full`, `co_intersect` (already GMP) |
| `cert_dual.expand_nodes` | block-wise deep cut | `cport.c` `dc_stage` as it stands (the existing C port is this algorithm) |
| `cert_dual.system_from_node`, `z_box`, `check_mu`, `certify_tree`, `replay_tree` | Method A | `uc_dual_*` |
| `cert_cvp.block_problem`, `kernel_basis_and_particular`, `cvp_enumerate`, `nearest2d` | Method B | `uc_cvp_*` |
| `verify_record` (both) | replay checkers | `uc_verify_*`, plus the Python verifiers stay the reference |
| `run.py`, `planted.py`, `compare.py` | drivers | stay Python; the C binary reads node JSONL and writes record JSONL |

One new file pair, `ucert.c` / `ucert.h`, plus a `cport unified` subcommand wired into the existing option parser. The two
back-ends live in separate translation units (`uc_dual.c`, `uc_cvp.c`) that include only `ucert.h` (types, GMP helpers, the
node and record readers and writers) and the existing `Co` routines from `cport.c`. Neither includes the other.

## 2. Data layout

    typedef struct { int d, e; } Digit;
    typedef struct {
        int a, E, s, K;          /* s = 96 E, K = 96 D */
        mpz_t Y;                 /* tail mod 10^s */
        Co co;                   /* v0, u1, u2 as in cport.c */
        int nrem; Digit rem[64]; /* sorted */
        mpz_t N2;
    } Node;

- A system (Method A): `mpz_t M, beta, alpha[2]; mpz_t *omega; int *vd, *ve, *vt;` with `m` variables stored position-group
  contiguous so a group's min/max is a single pass.
- A lattice problem (Method B): row-major `mpz_t` matrices `basis[n][n]` (carried coordinates), `emb[n][n+G]`, `part[n]`,
  `target[n+G]`; all values are exact integers.
- Records are JSONL with decimal-string bigs, field for field the Python schema (`ucert-record-v1`), so the Python verifiers
  check C output unchanged and a C verifier checks Python output.
- Nodes stream one per line; a node is 1 to 3 KB (the coset vectors are up to 600 digits at E = 3).

## 3. The exact-integer LLL and enumeration choice

Measured basis for the choice (Python, `logs/uprime-*.jsonl`, `logs/tierc-*.jsonl`):

- Method B per node, exact integral LLL (gmpy2) plus rational Schnorr-Euchner, 6 to 16 dimensions: 3 to 300 ms
  (mean 2.6 ms at dimension 2, 40 ms at 8, 115 ms at 10, 155 ms at 12, 300 ms at 16).
- Method A per node: 11 ms mean, 55 ms max on the 43 patterns (fpylll LLL plus the exact interval test).
- Method B on sampled k = 31 nodes (E = 3): dimension 32 to 36 take 0.8 to 1.0 s, 47 to 53 take 3.4 to 6.7 s, 71 takes 24 to 32 s;
  time grows by about 6 per added 15 dimensions, consistent with a bignum-dominated cubic-to-quartic exact LLL.
- Node enumeration on the 43 patterns: Method A's block-wise deep cut 203 s (U'') and 471 s (U', k <= 9); Method B's
  digit-ordered search with linear extension 3.1 s and 3.5 s, a factor of 65 to 135 on identical node sets.

Inference, not measured: once entries have 500 to 1000 bits and the Gram data has 10^4 to 10^5 bits, bignum multiplication
dominates, and GMP is already the engine under gmpy2. A C rewrite of Cohen's integral LLL would then buy roughly 1.2 to 3 times,
not 100 times. The first C task is to measure this on the 200-node sample.

Decision:

1. Reduction is untrusted. Both back-ends call fplll (C++, floating point, `LLL` with transformation matrix) to produce a reduced
   basis, and the verdict never depends on it being reduced. Method B checks exactly that the returned transformation is
   unimodular and that the reduced rows still satisfy the congruence (the same checks `cert_cvp.verify_record` runs: rows satisfy
   the congruence, determinant equals the lattice index, embedding of the carried rows equals the recorded vectors).
2. Method A's multiplier is an integer found by fplll; the verdict is the exact interval test in mpz (about 3 m big-integer
   multiplications and a handful of comparisons).
3. Method B's enumeration is exact: fraction-free Gram-Schmidt data (the integral representation d_i, lambda_ij of Cohen
   2.6.7, no mpq), center and bound comparisons cross-multiplied in mpz. Floating point appears nowhere in a verdict.
4. A pure-GMP Cohen LLL (a port of `cert_cvp.lll_integral`) is kept as the cross-check reduction (`--red exact`), used on
   every node in the differential run and on a 1-in-1000 sample of the production run.

Dimension limit to measure first: exact Gram-Schmidt in Method B at dimension 2 + f + G with f near 30 and entries of 288 to
480 digits. section 6 records the measured Python time on sampled k = 31 nodes; if it is more than a few seconds per node,
Method B certifies a stratified sample of the 440,640 nodes plus every node on which Method A fails, and Method A certifies
all of them.

## 4. What is shared and what is duplicated

Shared in C (trusted by both): GMP wrappers, `Co` arithmetic and `cut_full` from `cport.c`, the JSONL readers, `exact_E`,
`rho2`, the final modular-exponentiation check of any returned point.

Duplicated, never shared (the contract of SPEC.md section 6): the linear-system builders, the node enumerators, the reduction
call sites, the enumeration or interval test, the nearest-point routine on variable-free nodes. In C that is two source
files with no common non-trivial function; a grep gate in the build (`scripts` check, below) refuses an `#include` of one
back-end file by the other.

## 5. Differential test plan (the C port is accepted only when all of these pass)

1. Node sets: C `uc_expand` against Python `cert_cvp.expand_nodes` and `cert_dual.expand_nodes` on the 88 representations of the 43
   patterns (U'' depths) and the 186 oracle rows of the old U' table, comparing `node_digest` lists (tail, remaining
   digits, Hermite normal form of the coset).
2. Verdicts and exact minima: both C back-ends against `logs/u2-*.jsonl` (100 rows) and `logs/uprime-*.jsonl` (all rows run): status
   equal, `min_nn` equal as integers where both compute it.
3. Planted negatives: the `planted.py` suite replayed with the C binaries (sub-coset nearest points of random admissible
   words, the all-ones word, the at-minimum and below-minimum radii, synthetic genuine S-units with a up to 9 and D up to 4).
   Required: every planted case refused by both C back-ends; below-minimum certified by Method B.
4. Cross-verification: C records verified by the Python verifiers and Python records verified by the C verifiers.
5. Mutant gates: the six mutants of `tests/mutants.py` ported to the C source (off-by-one interval, narrowed z box, group terms
   dropped, enumeration without side candidates, quartered radius, lattice missing the modulus row); the suite must refuse each.
6. Sanitizers: the differential run under ASan and UBSan on 3 representations.
7. k = 31 sample: 200 random E = 3 nodes certified by C Method A, C Method B and Python Method A with equal verdicts; the
   full run in section 6 only starts after that.

## 6. The k = 31 pattern experiment

Pattern. The Codex pattern of `codex-deep-attempt.md` as used by the N1 lane: anchor y = 3^3 7^10 = 7626831723 (a = 0, b = 3,
c = 10), 31 special digits in classes 0 to 9 (`ucert/tierc.py` `TIERC_CLASSES`), Tier-C vertex 128421199872. One pattern, one
representation. No other anchor or representation of that vertex is touched.

Depth and nodes. With a = 0 the exact range gives E = 3 for both D = 5 (K = 480, h = 192) and D = 6 (K = 576, h = 288); E = 2
covers only D <= 4. The node count is N_3 = 440,640 (class DP of the N1 lane, families 93,312 / 46,656 / 93,312 / 82,944 /
41,472 / 82,944). A node enumerator that returns a different number has lost or invented a node, and that is a failure of the run.

Ceilings. log10 U'' (31, 0) = 246.0183 (`mk_utable_u2.py --probe 31,0`, `logs/u2-probe-31.out`; the integer table entry is
produced by `mk_utable_u2.py --kmax 31 --amax 0` into this directory, with its md5 recorded before the run) and the earlier
log10 U' = 281.51 (b3 REPORT) as a stress ceiling.

Measured on sampled E = 3 nodes (`logs/tierc-samples*.jsonl`, nodes drawn by a random descent of the package's own enumerator;
15 to 23 undetermined digits per node, the sparse draws biased to empty blocks 1 and 2):

| D | ceiling | nodes | Method A | Method B | per-node time A / B (Python) |
|---|---|---|---|---|---|
| 5 | U'' 246.0183 | 5 | certified 5/5 | certified 5/5 | 0.02-0.10 s / 0.8-6.7 s (dimension 32 to 48) |
| 5 | U' 281.51 | 3 | refused 3/3 | refused 3/3, each with a point | 0.03 s / 2.1-2.6 s |
| 6 | U'' 246.0183 | 5 | certified 5/5 | certified 5/5 | 0.03-0.09 s / 3.4-32 s (dimension 47 to 71) |
| 6 | U' 281.51 | 3 | certified 3/3 | certified 3/3 | 0.02-0.03 s / 4.2-5.3 s |

All 16 certificates were accepted by the replay verifiers (0.02 to 0.4 s each). Eight planted words at k = 31 scale
(sub-coset nearest points at K = 480, 530 digits) were refused by both back-ends (`logs/tierc-planted.jsonl`). The
D = 5 / U' = 281.51 refusals are genuine: Method B returns an admissible union point inside the disc for those nodes, so
depth 5 does not close the pattern at the earlier ceiling on those nodes, while depth 6 does (the N1 lane's 440,640-node
result at D = 6, reproduced here on 3 nodes).

Experiment (what the C port runs, in this order):

1. Gate. Section 5 passes. The C node enumerator reproduces N_3 = 440,640 and the six family counts.
2. Run A. D = 5, ceiling U''(31, 0): Method A on all 440,640 nodes. Output `tierc_A_D5.jsonl`, one line per node: digest, verdict,
   record hash, system size, time. Estimate: 440,640 x about 10 ms = 1.2 core-hours in C (the fplll reduction is already native;
   Python spends 20 to 100 ms per node, 3.7 to 12 core-hours).
3. Run B. D = 5, same ceiling: Method B on all 440,640 nodes if the first 200 nodes average under 5 s, else on every node
   Method A fails plus a 1-in-50 digest-ordered sample (8,813 nodes). Python mean estimate at D = 5: about 2 s per node, 245 core-hours;
   the C gain is not measured (section 3 says the exact LLL gains little, so the speedup rests on fplll reduction plus
   fraction-free enumeration; band 5x to 50x, 5 to 50 core-hours). Output `tierc_B_D5.jsonl`, same schema.
4. Cross-check. Equal verdicts node by node between A and B on the common set; any disagreement is reported with both records.
5. Margins. 200 nodes, Method A, at log10 U in {246.0183, 255, 265, 275, 281.51} at D = 5, and D = 6 at 281.51: the
   largest ceiling at which depth 5 certifies is recorded per node.
6. Planted negatives at scale. 500 random admissible words on 50 nodes: radius equal to the word's exact nearest norm; both
   back-ends must refuse every one. One genuine S-unit with 31-digit pattern structure is planted per 10,000 nodes.
7. Optional D = 6 / U' = 281.51 run with Method A, which reproduces the N1 result with the new code.

Pass. Node count equals 440,640; Method A certifies every node and each record verifies; Method B agrees on its set; zero planted
word certified. Fail. Any node that neither back-end certifies is written out with B's witness point and is the headline result.

Label if it passes. The pattern y = 3^3 7^10 with the Tier-C digit multiset is "closed by the sandwich (U'')" at depth 5,
conditional on Lemma C, Matveev and Yu 2007 Theorem II, and the pattern/representation list. That is a pattern-level
experiment. It says nothing about the other anchors and representations of vertex 128421199872, which the census would need
(each with its own N_E, and the k = 44 type costs of the N1 lane for the harder ones), and nothing here is PROVEN.
