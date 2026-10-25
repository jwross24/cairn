# lvl12 KT/P2A gate (workspace tier0-opt/kt-audit-l12/)

Verdict: do NOT swap in the two-change KT[512] build (`lvl12_fix1`). It drops true survivors and fails ASan.
Swap in `lvl12_fix2` (KT[512] + A>=512 abort + P2A[512] + init_tail loop bound `a<=A`), after the owner accepts the
four-change diff below. Production `tier0/lvl12` (md5 078d8908354f7c71acac39faeb4cb1b8) is wrong on every A >= 64
equation: it adds spurious survivors on all of them and drops true survivors on A >= 68.

## 1. Mechanism (production lvl12, source tier0/lvl12.c md5 850e43b373f8efb0484c37c2da1f53a5)

Rebuilding the source with `cc -O3 -march=native` gives the production code (`otool -tv` of the rebuild vs
tier0/lvl12: identical except the header line; only the LC_UUID differs).

Layout from a `-g` build of the same source (`lldb p/x &KT`, `lldb_addrs.txt`): `cidx` ends at KT, `KT` is
0x...db90..dc90, and the next 256 bytes are `fld_a[MAXF][MAXP]` (8x8 int). ASan on the production source:
`global-buffer-overflow ... 0 bytes after global variable 'KT' ... lvl12_orig.c:78 in read_cfg`.

Order of events in main: `read_cfg` writes KT[0..A] (KT[64..A] land in fld_a), then `init_syn` runs
`memcpy(fld_a[nf],ann[u],...)` and overwrites KT[64..71] with the annihilator vector. That vector is
(0,1,0,0,3,0,0,0) on every one of the 47 A >= 64 cfgs examined (`prod_kscan.txt`), so the K that `tail_test` reads (line 155) is:

| a0 | 64 | 65 | 66 | 67 | 68 | 69 | 70 |
|---|---|---|---|---|---|---|---|
| K read (prod) | 0 | 1 | 0 | 0 | 3 | 0 | 0 |
| true K (cfg) | 3 | 3 | 3 | 3 | 3 | 3 | 3 |

(debug copy = same source with prints only, `lvl12_dbg.c`; `prod_kscan.py` over all A >= 64 cfgs, output in
`prod_kscan` run of this session; `dbg_out.txt` for 393216.) Consequences:
- K = 0 takes the `K<1` branch: OPEN printed with no tail test (spurious survivors).
- K = 1 runs a one-digit tail test (weaker than the true 3-digit test; spurious survivors).
- `P2A[64]` is declared `static ull P2A[64]` and `init_tail` fills only a < 64 (line 40, `a<64`). `tail_core` reads
  `P2A[a0]` for the K==3 / lam==100 path (line 119) with a0 up to A. Debug copy shows P2A[64..67] = 2,4,4,4, not
  2^a mod 1000 = 616,232,464,928. At a0 = 68 the aliased K is 3, so the table path runs with garbage P2A and
  drops true survivors (a = 68 only; K = 0/1 slots never read P2A because lamc is 0 for K = 1 and K<1 returns early).
- Line 263 (`init_tailfast`) and line 292 (`init_surv5`) already disable the fast paths for A >= 64, so they are not in play.
- Line 155 can reach a0 = A (loops `a0<=A` in `finish`), so a0 reaches 64..A.

Effect on the computation: K does change after the overrun (3 -> 0/1/3-with-garbage), unlike lvlN where K was intact.

## 2. Builds (same flags `cc -O3 -march=native`)

- `lvl12_fix1.c` = tier0/lvl12.c + exactly: `static int KT[64]` -> `KT[512]`; line 78 prefixed with
  `if(A>=512){ fprintf(stderr,"A=%d exceeds KT capacity\n",A); exit(12);}` (diff in session; two changes). md5 of binary 129dc3e1d146fbcefef348ad0d85d0c1.
- `lvl12_fix2.c` = fix1 + `static ull P2A[64]` -> `P2A[512]` + `for(int a=0;a<=A && a<64;a++)` -> `for(int a=0;a<=A;a++)` (line 40).
  Two more changes. md5 of binary e547259ef483d1cfc5bf8f86d3d0ccee (the md5 differs per link because of LC_UUID; code is deterministic).

fix2 correctness basis (read, not assumed): for all 51 A >= 64 cfgs, a fix2 debug copy (prints only) shows KT[a] == 3 and
P2A[a] == pow(2,a,10^KT[a]) for every a <= A (`oracle_p2a.py`: checked 51, bad 0). With those two inputs correct, the a >= 64
path is the same code as the a < 64 path.

## 3. Differential, full sorted output lines (`runs/*.sorted.gz`, `runs.jsonl`, `compare.txt`, `compare.json`)

Command shape per run (cfg exactly as run_c.py: `export(M, path)` from tier0/export_cfg.py, then
`lvl12 cfg 0 12 bs`, BRANCHSPLIT on): sorted with `LC_ALL=C sort`, sha256 of the sorted stream, set differences by merge.
Production side is a pinned copy `lvl12_prod_pinned` (md5 078d8908...).

Controls, A < 64 (prod = fix1 = fix2, sha256 identical, rc 0): 139968_233334666 (A56, 10,020 lines), 393216_...223 (A58, 99,806),
1417176_23333333669 (A61, 55,283), 3211264_...277 (A60, 436,870).

A >= 64, all 12 nu, full output (lines: prod / fix1 / fix2; fix2\prod; prod\fix2; fix2\fix1):
| equation | A | prod | fix1 | fix2 | fix2\prod | prod\fix2 | fix2\fix1 |
|---|---|---|---|---|---|---|---|
| 393216 2^15·3·4 | 66 | 2,858,343 | 470,870 | 493,449 | 0 | 2,364,894 | 22,579 |
| 3779136 233333334666 | 64 | 1,981,162 | 338,084 | 343,200 | 0 | 1,637,962 | 5,116 |
| 2939328 23333346667 | 65 | 3,472,789 | 559,960 | 577,539 | 0 | 2,895,250 | 17,579 |
| 331776 22222222233338 | 65 | 4,201,366 | 1,128,918 | 1,163,628 | 0 | 3,037,738 | 34,710 |
| 11239424 ...777 (15x2) | 64 | 4,056,812 | 1,317,572 | 1,337,945 | 0 | 2,718,867 | 20,373 |
| 69441624 33333333334677 | 67 | 12,011,356 | 235,555 | 249,532 | 0 | 11,761,824 | 13,977 |
| 1492992 222222222223399 | 67 | 15,271,104 | 2,133,735 | 2,271,772 | 0 | 12,999,332 | 138,037 |
| 46294416 3333333346677 | 64 | 5,888,384 | 558,897 | 567,523 | 0 | 5,320,861 | 8,626 |
| 11239424 2222222222227778 | 64 | 8,440,846 | 2,722,445 | 2,764,491 | 0 | 5,676,355 | 42,046 |
| 3779136 22223333333366 | 65 | 11,450,175 | 2,767,056 | 2,855,362 | 0 | 8,594,813 | 88,306 |

In every row fix1\fix2 = 0, all differing lines have a >= 64, and the a < 64 lines are identical across the three builds.
The recorded level-12 counts for 393216 (2,858,343) and 11239424 (4,056,812) equal the production numbers above.

A >= 68 equations (production reads K = 3 with garbage P2A at a0 = 68), nu in [0,3) and [3,6) only:
| equation | A | nu | prod | fix2 | fix2\prod (all a = 68) | prod\fix2 |
|---|---|---|---|---|---|---|
| 69441624 23333333336677 | 70 | 0-2 | 15,604,004 | 645,361 | 8,920 | 14,967,563 |
| 69441624 23333333336677 | 70 | 3-5 | 15,595,634 | 652,009 | 9,080 | 14,952,705 |
| 1492992 222233344666 | 68 | 0-2 | 12,101,545 | 1,402,616 | 20,602 | 10,719,531 |
| 1492992 222233344666 | 68 | 3-5 | 12,036,926 | 1,336,050 | 18,858 | 10,719,734 |

Independent check (Python, `tailcheck.py`, `dropcheck.py`; K = 3 digit rule from 2^a·3^b·7^c mod 1000 against the pattern):
- 393216: all 493,449 fix2 lines tail-alive (0 violations); all 22,579 fix2\fix1 lines tail-alive (true survivors that fix1 drops);
  300,000 sampled prod\fix2 lines all tail-dead.
- A >= 68 slices: every fix2\prod line has a = 68 and is tail-alive; 0 violations on all fix2 lines; sampled prod\fix2 lines tail-dead.

Reading: for A in 64..67 production is a strict superset of the correct output (spurious survivors only, no drops);
for A >= 68 production also drops true survivors at a = 68. fix1 drops true survivors on every A >= 64 equation tested.

## 4. ASan (`asan_run.py`, `asan_*.err`; `cc -O3 -march=native -g -fsanitize=address -fno-omit-frame-pointer`)
Equation 393216 M=2^15·3·4 (A=66), nu in [0,1):
- production source: abort, global-buffer-overflow 0 bytes after 'KT' (size 256), lvl12_orig.c:78 in read_cfg.
- fix1: abort, global-buffer-overflow 16 bytes after 'P2A' (size 512), lvl12_fix1.c:119 in tail_core.
- fix2: rc 0, no ASan report, 8 OPEN lines.
fix2 also on 69441624 M=2^2·3^9... (cfg 69441624_23333333336677, A=70), nu in [0,1): rc 0, stderr holds only the stats line (12,262,423,680 patterns), no ASan report, 52 OPEN lines (`asan_fix2_A70.err`).

## 5. Not verified
40 of the 50 A >= 64 equations (19 known + 31 pending-list entries, deduplicated to 50) were NOT rerun in full; they are listed
in `unverified.txt` with a time estimate (about 167 core-hours for prod + fix2 at the ~7e7 patterns/s/worker measured under load 25-40).
Two of the 40 are partial (nu 0-5 of 12 compared): 69441624_23333333336677 (A70) and 1492992_222233344666 (A68). None is reported as passing.
- 10 equations have A >= 68 and are exposed to the a = 68 drop; only the two partial ones above were observed. The mechanism (K read = 3 at
  a0 = 68 with garbage P2A) applies to all ten: the rows with A=68..70 in `unverified.txt`.
- The four largest cfgs (46294416_22223333337799, 46294416_2223333367799, 9483264_222222223334777, 9483264_22222233344777) were generated
  last and never queued.
- fix2 completeness (no true survivor dropped) rests on the structural argument in section 2 plus the Python tail check on the
  fix2\prod and fix2\fix1 lines; no independent full re-derivation of level 12 (e.g. the pure-Python engine) was run on an A >= 64 equation.
- ASan was run on nu in [0,1) only. Nothing was run with fix2 on a downstream level (lvlN already fixed).
- tier0/lvl12.c lines 163-170 `static unsigned short DC[10][64][8]` and `pattern_has[10][64]` are indexed by residue < L = 12, not by a; not changed.
- Pre-existing issue kept out of scope: the `K` array clamp `if(K>18)` and the K=1 path's use of LAMK[1]==0 (slow-path powmod) were read, not run on a >= 64 data.


## 6. Swap (the owner runs it; nothing was copied into tier0/)
Backups already taken: `backup-pre-swap/lvl12` (md5 078d8908...) and `backup-pre-swap/lvl12.c` (md5 850e43b3...).

```sh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0 && \
[ "$(md5 -q lvl12)" = 078d8908354f7c71acac39faeb4cb1b8 ] && [ "$(md5 -q lvl12.c)" = 850e43b373f8efb0484c37c2da1f53a5 ] && \
cp -p ../tier0-opt/kt-audit-l12/lvl12_fix2 lvl12.swapnew && mv lvl12.swapnew lvl12 && \
cp -p ../tier0-opt/kt-audit-l12/lvl12_fix2.c lvl12.c.swapnew && mv lvl12.c.swapnew lvl12.c && \
md5 -q lvl12 lvl12.c
```
The base-10 sweep (run_trees_c_v2.py via run_c.py) execs tier0/lvl12 per equation, so it picks the new binary up at its
next equation; equations whose level-12 ran before the swap on an A >= 64 equation are suspect (every such level-12 output
is a superset of the correct one for A <= 67 and can also miss true survivors for A >= 68).
