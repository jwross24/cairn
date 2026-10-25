# Lane 2 RESULT: breaking the 12 -> 24 lift, or proving it is the wall

Reference: tier0/lvlN (fixed, md5 20e091fc) re-run on all 228 level-24 equations (logs/ref228.jsonl, 1050 CPU-s); its sorted-line sha256 equals the join24swap pinned reference on 228/228.
Baseline "join24" = join24swap/lvlN (md5 b43dad7d, source lvlN.c 54db62e8): identical to the reference on 228/228 here too; 63.5 CPU-s in this session (59.4 in its gate).
All variants share one source, src/lane2.c (join24 source + runtime switches, build `cc -O3 -march=native`; mutants with -DJOIN_MUTANTS); idea-specific code in ideaC/c_window.inc and ideaE/e_dp.inc.
Differentials: sorted OPEN/EXACT lines (sha256) plus children/open/exact counters, 228 equations incl. the 3 with A >= 64 (their parents come from the unaudited level-12 output; both sides read the same parents file, so the differential is unaffected, the equations' own scientific status is).
CPU = rusage at nice 10 on a machine at load 35-65: single-pass ratios carry +-15%.
No-Claim: nothing here closes a vertex; nothing is swapped into tier0/ or the engine.

## 1. Scoreboard (speedup = CPU(join24) / CPU(variant); identical = survivor sets byte-identical to lvlN)
| variant | identical | total 228 | heavy 12 | min-of-3 on 3 heavy equations | prediction (PREDICTIONS.md) | verdict |
|---|---|---|---|---|---|---|
| L0 (join24 source rebuilt, all switches off) | 228/228 | x1.03 | x0.99 | x0.99-1.05 | - | control |
| E0 table-driven setup + lazy decode | 228/228 | x1.27 | x1.26 | x1.31-1.49 | engineering, not an idea | - |
| (a) cascade (chain + 137 bitmap), alone | 228/228 | x1.08 | x1.06 | x1.06-1.08 | H x1.3 [1.1,1.8]; T x1.2 [1.05,1.5] | MISSED on H (below range, kill rule < 1.10 triggers: dead as a stand-alone), HELD on T |
| (a)+E0 | 228/228 | x1.43 | x1.41 | x1.47-1.62 | | |
| (b) forced single keys (src/lane2_mut) | n/a | - | - | key 73: x0.78-0.93; 137: x0.11-0.12; 99990001: x0.02-0.03; (73,137): x0.84-0.98; (73,p3): x0.01-0.03 | forced 73 >= 1.5x slower [1.5,20] | MISSED (only 1.1-1.3x slower: the default already picks 73 on 68% of parents); default beats every forced key: HELD. Wagner: not implementable (KILLED by literature, below) |
| (c) 10-adic window before the residue test, alone | 228/228 | x1.63 | x1.64 | x1.57-1.71 | x0.5-1.05, kill if < 1.15 | **MISSED: the idea works** (tail-dead counter drops on 212 equations by design; sets identical) |
| (c)+E0 | 228/228 | x2.19 | x2.29 | x2.14-2.59 | | |
| (d) direct 12 -> 48 | measurement | - | - | - | level-48 stage <= 5% of 24+48 CPU; indices 4/48/900, joint 3.94e12 = 88 x ... | share MISSED (58%, below); index/coset numbers HELD; see section 4 |
| (e) DP + backtracking, key 73 (73 states) | 228/228 | x0.82 | x0.75 | x0.76-0.89 | H x0.5 [0.2,1.2] | HELD |
| BEST = (c)+(a)+E0, W_CAND = 40 | 228/228 | **x2.37** | **x2.89** | **x3.14-3.58** | <= 4x on H, <= 3x on T | HELD; **100x not reached** |
| BEST + (e) | 228/228 | x0.94 | x0.90 | | | no gain |
| DH (Dimitrov-Howe discipline: E0 + (a) + tuned weights + balanced/unbalanced switch at C0 < 600) | 228/228 | x1.41 | x1.56 | x1.62-1.77 | x1.5 [1.2,2.0] | HELD; switch alone: DH0 (no switch) x1.51, i.e. the switch changes total by -7%, inside the noise band |
| LA (LIFT-ADDITIVE: DP over Z/10001, 73*137 by CRT, bitset) | 228/228 | x0.87 | x0.92 | x1.00-1.06 | x0.9 (0.4-2.0) heavy, x0.8 (0.3-1.5) total | HELD |
Heavy 12 = the 12 equations with most children (45.4 of 63.5 CPU-s). The three minimum-of-3 equations: 9437184_222222222228889 (118,774 parents), 3211264_222222222222222277, 393216_222222222222222223.
Best gate evidence (BEST, all 228 sets identical): logs/eval_BEST.jsonl (identical = true on 228/228); planted mutants (logs/mut_BEST_*.jsonl, scripts/mut_summary.py):
M1 (drop odd-indexed allowed key residues) caught on 202 of 216 equations with output, the other 14 caught under a forced key set (14/14); M2 (2^a -> 1 in the key target) caught on 212 of 216, the other 4 are
one-line equations whose surviving parent has a = 0 (equivalent mutant; the same 4-5 equations are uncaught for join24 itself, L0_M2); window mutant CMUT2 (look the window slot up at residue i+1) caught 216/216 (the first window mutant, CMUT, caught only 50: weak, kept in logs as such);
chain mutant AMUT (exponent 143 for 144) caught 216/216. 12 equations have no output line (vacuous). DH: M1 is caught on only 94 equations because parents routed to plain enumeration never run the join (13 more under forced keys): the DH gate would need its mutant planted in the plain path as well.

## 2. Best x-factor over join24
**x2.37 on the 228 (63.5 -> 26.8 CPU-s), x2.89 on the 12 heaviest, x3.1-3.6 minimum-of-3 on three heavy equations, byte-identical survivor sets and the required mutants caught.**
Where BEST stands per parent on 9437184_222222222228889 (1.19 s, 118,774 parents, 10 us each): table setup and hash build 0.45 s, probes 0.20 s, candidate tests 0.62 s (stub runs, LANE2_STUB).
Measured scaling (MODELED beyond C = 6.5e4 children per parent): ns/child = e^2.68 C^-0.30 for BEST against e^2.71 C^-0.19 for join24, so the ratio grows to about x3.8 at C = 3e5 and x4.8 at C = 2e6 (Tier B means).

## 3. Why not x100: the measured statement (level-24 lattice content)
Exact content (MEASURE.md): the image of Lambda_12 has order 2 at 73 (index 36), 34 at 137 (index 4), 111,100 at 99990001 (index 900); jointly 3,777,400 allowed residue vectors of 9.79e11 (index 259,200 = 128 x 81 x 25, the 2-part being the strongest kill, 0.9924).
Only 73 is a pure congruence on Delta (2 residues; measured at most 2 distinct Delta mod 73 among the passers of any parent). The full coset has 3.78e6 elements, more than the children of a parent (4e3-6.5e4 on the 228, 3e4-9e5 at Tier B), so a key/hash join over the full coset costs at least min(C, sqrt(C K)) with K = 3.78e6 and never wins on the 228.
What is left is a join on (73) or (73,137): its candidate stream is 2.8% / 0.69% of the children, each needing a 99990001 character (about 25-60 ns after BEST); the p3-keyed join needs K = 111,100 probes per list entry. After BEST, per parent: 4 us setup + 2 us probes + 5 us candidates at C = 1.4e4.
Floors: (i) 2.645e6 parents x >= 2 us of parse + target + list setup = 5.3 s, i.e. no per-parent method can exceed x12 on the 228 (63.5 s); (ii) an output-sensitive method would need the children that pass the coset test: 135,155 of 2.718e10 (5.0e-6), but no algorithm that finds them without testing the 0.7-2.8% key candidates is known: the allowed set is a union of multiplicative cosets, not an additive structure, which is the situation where the bitset DP is optimal (literature below).
So x100 is not available at the sizes of the 228. The structure that did help is not additive: it is the 10-adic window, a word-local necessary condition on the shift bits that removes 67% of A-indices and 8% of parents before any residue is computed.

## 4. Idea (d) and the overlap with X3
Exact (scripts/lattice_content.py, lattice_content2.py), reported as a Lane 2 by-product; it overlaps the chat's X3 (content of Lambda_L): Lambda_12 images at the level-48 primes 17, 5882353, 9999999900000001 have indices 4, 48, 900 (joint 172,800); joint with level 24: index 3.94e12 (= 88 x 259,200 x 172,800), image order 2.34e23.
Lambda_24 (parent lattice of the level-48 stage): indices 8, 48, 39,600, joint 15,206,400. Direct 12 -> 48 enumerates 4 prod C(m+3,3) children per parent: 3.98e15 over the 228, i.e. 1.4e5 times the 2.72e10 level-24 children plus 5.8e8 level-48 children of the staged route (scripts/direct48_children.py), so it cannot compete; the coset is too large to hash.
With join24 the 214 level-48 equations cost 82.6 CPU-s against 59.4 for the 228 level-24 equations (gate.jsonl): after the 12 -> 24 speedup the 24 -> 48 stage is 58% of the lift CPU (the registered prediction of <= 5% was wrong because join24 made level 24 cheap, not because level 48 got dear). Lambda_24 has image order 2 at 17 (a congruence with 2 of 16 residues): the same window/DP structure applies there and is the next candidate (not built here).

## 5. Dimitrov-Howe discipline vs LIFT-ADDITIVE (relay item)
Read first: arXiv:2105.06440 (abstract + ar5iv text; the PDF was not machine-readable): moduli chain M_i, primes p = 1 mod 2^a 3^b chosen so the orders of 2 grow by 1 or 2 per stage, stage lifts of the surviving solutions, unbalanced stage (enumerate prod #A_j tuples, discrete-log test) when the number of target lifts exceeds that product, otherwise balanced MITM on sorted lists keyed mod M_i, stop when all powers are determinate.
Mapping and measured outcome: in the level-24 lift the stages are the primes 73 / 137 / 99990001; the first is balanced (join), the last is unbalanced (chi = 111,100 > children per parent); between stages a surviving child has no new freedom, so the chain reduces to join + filters and the order-ratio and determinate-stop devices have no counterpart.
DH (the same stage order, tuned weights, per-parent balanced/unbalanced switch): x1.41 total / x1.56 heavy, all of it candidate-stage engineering, identical sets.
LA (LIFT-ADDITIVE, DP over Z/10001 implemented as a 10001-bit cyclic bitset, 157 words per layer): x0.87 / x0.92; faster than join24 only above C about 7e4 (fit: ns/child e^4.47 C^-0.36, i.e. x1.5 at C = 3e5, MODELED); BEST is faster than LA at every C in range (0.34 vs 0.88 ns at 3e5).
LIFT-ADDITIVE.md's cost table compares against 6.1 us/child divided by 9; the measured join24 is 1.6-3.4 ns/child, so its x3 at q = 13 and x30 headline are not reproduced (measured x0.9-1.0 at C = 4e3-6.5e4). Its mechanism (the shift-bit congruence/DP, validated there against brute force) is correct: LA matches lvlN on 228/228.
Skipped: the 10-adic-cut variant of LA (its allowed sets shrink 137 to 17 and p3 to 22,220 residues; that changes the candidate density by at most x2 and not the DP cost, which dominates); the literal word-per-state DP (the ~1 ms/parent reading, P-LA2) was not built.
Literature recorded as given by the coordinator (not tested here): the bitset DP is O~(m)-optimal (Axiotis et al.; Cardinal-Iacono); k-tree/Wagner provably does not apply because the coset condition is not prefix-linear. Idea (b)'s registered prediction is unchanged; status KILLED by literature, with the forced-key timings above as cheap empirical confirmation: no single key beats the cost-model mixture.

## 6. COSTMODEL verdict (details COSTMODEL.md)
The chat's reading is wrong by about 10^7: lifted level-12 parents are OPEN survivors (2.9e11 at Tier B, not 2e15), each with about 4e5 (not 1.07e9) children at k = 29, 8e16 children, 1.2e8 core-seconds at join24 speed. The lift is not Tier B's wall. Exact ledger correction: COSTMODEL.md section 5.

## 7. Prediction scoreboard summary
M1-M5 HELD. I-series: (a) MISSED on H / HELD on T, (b) MISSED (magnitude) / HELD (default best), (c) MISSED (opposite sign: x1.6-2.2), (d) MISSED (share 58%) / HELD (indices), (e) HELD, composite HELD, 100x NOT MET. Addendum: P-DH1 HELD, P-DH2 HELD (inside noise), P-LA1 HELD, P-LA2 skipped, P-LA3 HELD (modeled), P-DH3 HELD.
C-series: C1 HELD (2.6e-8 at k = 29), C2 HELD (4.1e5), C3 MISSED at the edge (7.8e16 children vs [1e17,1e19]; interval 4.7e16-2e17 overlaps; 1.2e8 core-seconds vs [1.5e8,3e10]).

## Files
PREDICTIONS.md (md5 26caa988 at completion; the addendum is at its end), MEASURE.md, COSTMODEL.md, RESULT.md, ideaA..ideaE (READMEs), ideaC/SPEC.md (blind re-implementation spec of BEST), ideaC/c_window.inc, ideaE/e_dp.inc, src/ (lane2.c, join_prof.c, measure.c + helper), scripts/, logs/ (eval_*.jsonl, mut_*.jsonl, timing.jsonl, measure.jsonl, ref228.jsonl, costmodel_l2.txt).
