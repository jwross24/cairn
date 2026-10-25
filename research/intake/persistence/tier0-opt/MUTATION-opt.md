# Mutation testing of the optimized C passes (2026-10-19, Cairn)

Method: one defect per copy, built in /private/tmp/persist-mutation/m_<name> (lvl12) and m3_<name> (lvlN);
each copy's run_c.py execs its own binary (lvl12/lvlN resolved from HERE; lvl12 copy's scratch dir repointed
to its own). nice 19, 2 cores. tier0/ untouched.
"Verdict" = children / complete / open-pattern count / POSITIVE CONTROL LOST assertion / per-multiset open+sols.
"Counters" = the C pass's own stderr counts (c_stats), per-level survivor counts, and c_oracle sha256.
No-Claim: catching these mutants shows the controls are sensitive to these defect classes; it does not prove the engine correct.

## Baseline (unmutated tier0-opt/lvl12.c, 2 cores)
Controls: the 7 vertices of golden_run.sh (4:14, 14:27,72, 27, 98, 189, 294, 72:98,189,294,1161216), plus 16, 126,
1134, 13122 from MUTATION.md (all complete, open 0, children as known: 16 -> 28,128,144,224,441; 126 -> 729,972,1792;
1134 and 13122 -> none), total ~15 s. Long control: vertex 10800 equation M=(2,2,2,2,3,5,5,9): children
[11519532122112], 2 open patterns, bound 1324225949446888113636900864 (~1.3e27), 90 s. Whole vertex 10800 (17 multisets,
1.81e9 patterns): children [11519532122112], complete, 24 open patterns in total (the 2 above are this child's own
equation). Not run: 18144 (6.5e9 patterns; first 3 multisets alone took 600 s), 41472, 221184, 111132 (too slow at 2 cores).
The chat's list of eight vertex ids is not in a file; the set above is my reconstruction.
Full control pass per mutant: ~100 s (a mutant that loses a control aborts in 5-12 s).

## lvl12.c mutants (15)
| mutant | defect | caught by | time |
|---|---|---|---|
| a0 zero check deleted (open test) | `if(d==0){open=0;break;}` removed | EQUIVALENT: cntmg[0]==0, so `have[0]++ > 0` kills the same line; controls and oracle identical | 100 s |
| a1 zero skipped (open test) | `if(d==0) continue;` | verdict: NOT caught. Counters: c_stats differ on 11/12 controls; c_oracle 23/25 | 104 s |
| a2 zero skipped (exact test) | same, exact branch | NOT caught anywhere: controls, oracle, and 1370 equations (s<=20000, raw stdout+stderr) identical. Argued redundant: exact needs Y<10^3 (K=3) and Y agrees with the pattern number mod 11*13*37*101*9901 (>10^9), so a zero digit cannot pass; argument only | 101 s |
| b1 CRT v1 uses rep[0] | `v1+=ccrt*rp[0]` | control lost y=14, 27 (v4, v14, v72, v16, v126, 10800) | 10 s |
| b2 CRT modulus term off | last component `ccrt[c]+1` for v0 | control lost (v4, v14, v72, v126); v16 loses 28,128,224 | 92 s |
| c1 prefilter rejects rep0==0 | `crep>=0` -> `>0` | control lost (v14, v72, v16, v126, 10800) | 5 s |
| c2 prefilter accepts class 7 | `\|\|k==7` | verdict: NOT caught. Counters 11/12 controls; c_oracle 22/25 | 110 s |
| d1 y%p skips last prime | `i<npc-1` in zero test | verdict: NOT caught. Counters 11/12 (zero/prefilter-dead shift); raw stdout identical, only stderr counts differ | 102 s |
| d2 y%p test inverted to y==1 | | control lost (v4, v14, v16, v126, 10800); v72 loses 294,1161216 | 12 s |
| e1 exact n-residue off | `nY%L==(nu+1)%L` | control lost (v4, v14, v72); v16 loses 28,128,224 | 101 s |
| e2 split sign | `c=v2-k*U[2]` | v72 loses 294,1161216; control lost at 10800 | 11 s |
| e3 exact multiset check weakened | `!=` -> `>` | verdict: NOT caught. Counters 7/12; c_oracle 10/25 | 101 s |
| e4 position check off (open) | `pattern_has<1` -> `<0` | verdict: NOT caught. Counters 8/12; c_oracle 17/25 | 113 s |
| e5 digit contribution gd not gd-1 | | control lost (v4, v14, v72, v16, v126, 10800) | 9 s |
| e6 tail K capped at 2 | `if(K>2) K=2` | verdict: NOT caught. Counters 10/12; c_oracle 20/25 | 102 s |

Score: 7 caught by verdict; 6 caught only by counters/c_oracle; 1 equivalent (a0); 1 uncaught and argued redundant (a2).
Finding: every verdict-level escape is a permissive defect (extra survivors) that the Python descent/lift removes later.
Not an unsound result, but the eight-vertex controls cannot see it. The c_oracle sha256 check (already in check_golden.sh)
catches 5 of those 6 by stdout hash or counters; d1 changes only stderr counters, so the oracle must compare the `err`
field (build_and_test/check_golden do: cmp of the whole jsonl). Proposed standing control: always run c_oracle.
a2 has no catching control; a planted true solution with a zero digit cannot exist per the argument above.

## Task 3: K == 3 and np == 5 at level 12
Verified. np = len(primes_for_level(12, set())) depends only on L (export_cfg.py); the 5 primes give nc=4 components
with csize<65536, so fastp=1. KT[a] = ten_adic_K(Coset(0,0,U2)) with U2 = [[0,900],[9900,0]]. Over 3622 equations
(all s in 2^a3^b5^c7^d, s<=20000, every multiset): K==3 for all 83587 (equation, a) values, np==5, nc==4, one U2.
Instrumented run (abort on K!=3, LAMK[3]!=100, np!=5, !fastp, nc!=4 at every tail_test call) over 5 equations incl.
M=(2,2,2,2,3,5,5,9) (9.6e6 calls), (2,2,3,3,4,6), (2,2,2,2,3,3,6), (4,7,8,8,8,9,9), (3,3): no abort.
Comment added at tail_test in tier0-opt/lvl12.c (comment only; behavior unchanged). check_golden equivalent run in
/private/tmp/persist-mutation/gold (rebuilt lvl12, 7 vertices, eq6, c_oracle): SAME for all 9 files, rc=0.
Caveat: "K==3 for all a" is empirical over those equations, not derived.

## lvlN.c mutants (v3 engine; tier0/ copied at 21:5x EDT into v3base)
Gate per mutant: difftest.py on 72 / 6 / 224 / 162 (C pipeline vs NOCLIFT Python) plus vertex 10800
M=(2,2,2,2,3,5,5,9) C pipeline vs the recorded Python result (levels >= 48; see note). Baseline: 4 IDENTICAL,
10800: C 231 s vs Python 40 s, same open/sols/levels 48,96.
| mutant | defect | caught by | time |
|---|---|---|---|
| N1 tail zero skipped | `if(d==0) continue;` in open test | NOT caught by gate; lvlN counters differ (open 3 vs 2) | 217 s |
| N1b zero check deleted | | EQUIVALENT: cntm[0]==0 (same argument as a0) | 303 s |
| N2 linear-component CRT | `t2` uses `x1*s` | DIFFERENT on 6 and 224 (C per-level key differs from Python) | 3 s to detect |
| N3 mulmod128 no reduction | `a<<=1` without `if(a>=m) a-=m` | DIFFERENT on 6 and 224; 72, 162, 10800 identical | 3 s |
| N4 final reduction mod N removed | `t1=mod128(t1,N)` deleted | NOT caught; counters identical. Probably coset-invariant (tail depends on the coset only), argued not proven | 261 s |
| N5 Pohlig-Hellman CRT sign | `-` -> `+` | loud: `dlog verify failed p=99990001` (exit 5), plus DIFFERENT | 2 s |
| N6 lift drops all-lifted child | `k<=m` -> `k<m` | DIFFERENT on all 4 gate vertices and 10800 (level 48: 42 vs 3296) | 3 s |
| N7 drops n+L residue | `dn<2` -> `dn<1` | DIFFERENT on all 4; 10800 POSITIVE CONTROL LOST at level 24 | 3 s |
| N8 exact n-residue off | `(nu_cur+1)` | NOT caught; counters differ (exact 0 vs 1). Benign: run_c.py merges EXACT with OPEN lines | 275 s |
| N9 adjusted target sign for a*l2 | `-` -> `+` | DIFFERENT on 6, 224, 162; 10800 POSITIVE CONTROL LOST | 3 s |
| N10 tail K capped at 2 | | NOT caught; counters differ (open 3 vs 2, exact 0 vs 1) | 220 s |

Score: 6/11 detected by the gate (N2, N3, N5, N6, N7, N9); N1b equivalent; N4 argued equivalent;
N1, N8, N10 are permissive tail-test defects the Python classification absorbs, visible only in lvlN's stderr counters.
Proposed control: add lvlN's stderr counts (tail-dead / open / exact per parent file) to difftest's key.

Notes for chat: (1) difftest's per-level key reports DIFFERENT for the unmutated engine on the 14-digit control (level 12
OPEN 38821 vs 3147, level 24 16,213,008 vs 1,340,704) because the C path defers descent; open/sols/levels 48,96 agree. The
four standard gate vertices do not show it. (2) On that equation the C pipeline took 231 s against 40 s for Python.
(3) The gate does not compare the digit bounds or the coset representatives.
