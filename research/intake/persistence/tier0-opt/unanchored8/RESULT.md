# The 8 unanchored level-96 open patterns of 1161216 and 11239424

P = /Users/jwross/Documents/cairn/research/intake/persistence. All outputs are in `P/tier0-opt/unanchored8/`. Nothing under `tier0/`, `tier0-opt/cport/`, `cport-shadow480w/` or `kt-audit-l12/` was written (the Python imports `lattice`, `descent`, `dlog` from `tier0/` read-only with `sys.dont_write_bytecode`). No git, no make. Every compute process ran under `nice -n 10`, one at a time.

No-Claim: these verdicts are conditional on Lemma C, Matveev, Yu 2007 Thm II and the pattern list; nothing here is PROVEN and nothing is Lean-checked.

## Answer

Lemma C depth 1 (the cut) applies to an unanchored pattern, and all 8 are closed by it. The sandwich is not needed for them. The level-480 shadow does not apply to an unanchored pattern; its input is the anchor's identity, and the generalization was not derived (see (1) and Seams).

## Which 8

`items.py` recomputes the `run_c.py:92-112` admissibility test (Babai nearest point `(b0, c0)` with `b0 >= 0`, `c0 >= 0`, `max(b0, c0) < hypot(u1)/2`) on every item of `eqs[i].open_patterns.items` of the two vertices (18,069 items). Exactly 8 fail: 5 on 11239424, 3 on 1161216, which is the `open` minus `exceptional` surplus. In every one of the 8 the nearest point has one negative coordinate, so it is not a candidate.

## Verdicts (per pattern)

Lattice rows are `trees_mac.jsonl` (md5 3382a57f8934f6b20878b343a00bf6e4). "digit floor" is log10 of the digit lower bound that holds for every coset point, `digits_bound` of the exact nearest norm (`uncut.py`). Cases = depth-1 cases not removed by the distinct-position rule. Both implementations agree on case counts and verdict.

| # | vertex | equation | a | nu | k | nearest point | digit floor (log10) | depth-1 cases | survivors | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 11239424 | 2222222222227778 | 1 | 8 | 16 | b0 >= 0, c0 < 0 | 24.285 | 6912 | 0 | closed by the cut |
| 2 | 11239424 | 2222222222227778 | 1 | 8 | 16 | b0 >= 0, c0 < 0 | 24.285 | 5760 | 0 | closed by the cut |
| 3 | 11239424 | 2222222222227778 | 1 | 8 | 16 | b0 >= 0, c0 < 0 | 24.285 | 4320 | 0 | closed by the cut |
| 4 | 11239424 | 222222222444777 | 8 | 9 | 15 | b0 < 0, c0 >= 0 | 27.765 | 6144 | 0 | closed by the cut |
| 5 | 11239424 | 222222222444777 | 8 | 9 | 15 | b0 < 0, c0 >= 0 | 27.765 | 6144 | 0 | closed by the cut |
| 6 | 1161216 | 22222222233667 | 9 | 7 | 14 | b0 >= 0, c0 < 0 | 27.061 | 1296 | 0 | closed by the cut |
| 7 | 1161216 | 22222222233667 | 9 | 7 | 14 | b0 >= 0, c0 < 0 | 27.061 | 512 | 0 | closed by the cut |
| 8 | 1161216 | 22222222233667 | 9 | 7 | 14 | b0 >= 0, c0 < 0 | 27.061 | 720 | 0 | closed by the cut |

Full item data (v0, positions) are in `cases8.txt`; the Python run is `run_unanchored.out`, the C run `cases8.out`.

Items 4 to 8 close largely because every admissible depth-1 case fails `v2(L) = a` (planted search below found no admissible case with `v2(L)` equal to the recorded `a`); items 1 to 3 close by the three congruences of `cut_coset`. I did not separate these mechanisms further.

No sandwich verdict and no shadow verdict is reported for any of the 8, so no row is labeled "closed by the sandwich (U'')". Labels "open" and "not applicable" apply to none of the patterns under the cut.

## (1) What each certificate uses the anchor y for

- Lemma C (`tier0/deepcut.py`): y supplies (i) the coset base point, `fct = factor237(y)`, `co0 = Coset((fct[1], fct[2]), Lam.u1, Lam.u2)` (lines 152-153); (ii) the representations, `all_representations(M, y)` (line 154), used only because the stored anchored keys carry `nu = eps = -` (`stage_io.py` `full_key`); (iii) the single checked point named in the docstring ("Any candidate y' != y", line 6) and in PAPER 3.6: "every point of C other than one checked point gives a candidate with at least 192 digits". y is a base point and a separately excluded point. Nothing else in `deep_cut` reads y: it takes `(co0, a, rep, depth, maxcases)` and builds `L` from the representation alone (`deepcut.py` `deep_cut`, `cut_coset(co, a, L, K)`).
- cport deepcut and sandwich (`cport/cport.c`): same use. `factor237(c.y)` and `co_babai` give the coset (lines 894-897 deepcut, 1043-1045 sandwich), `filtered_reps` enumerates representations from y (lines 837, 900, 1047). The sandwich's upper bound G(k, a) and its lower bound (nearest norm of the surviving sub-cosets) use no y.
- Level-480 shadow (`cport-shadow480w/src/cport_shadow480w.c`): y is load-bearing beyond a base point. The wrap `w = (V - y)/R_96` is computed at line 2580 (`g_y` set at 2852 and 2874), the program stops when `V - y` is not a nonnegative multiple of `R_96`, and the per-word `tau` is compared with `-w/9` at the seven trivial-image primes. This rests on the anchor-witness lemma (`tier0/HSHADOW.md` section 8; PAPER 3.10'): `2^a 3^b 7^c = y` modulo every prime, so the shadow is the anchor's identity continued. An unanchored pattern has no such y.

## (2) Soundness argument for an unanchored pattern

For the cut: the argument needs (A) the coset, (B) the representation, and (C) the premise that every point of the coset that yields a candidate has at least 192 digits.

- (A) The coset is the one the sweep recorded (`open_patterns.items[i].v0, u1, u2`). For anchored items it equals the anchor-based coset: the lattice rows match, and the per-representation verdicts and case counts of the control (below) equal the anchor-based run's rows for 3 of 3 anchors. `u1`, `u2` are Lagrange reduced for the 8 (`reduced True` in `run_unanchored.out`), and the nearest point was cross-checked against a +-40 window (assertion in `run_unanchored.py`).
- (B) The representation is `(nu, [(d_j, e_j)])` with digits `sorted(M)` paired with the recorded `eps` (canonical form: digits ascending, positions ascending within a digit). I checked this reading against y-derived data: for the 3 control anchors the recorded `(nu, eps)` of the matching items is among `all_representations(M, y)` where Python enumerated it (1 of 1 for 1161216 22222222222799; the other two controls ran in C only). `cport_coset` orders the positions by `(e, d)` while `uncut.py` keeps M order; both give the same case counts and verdicts on all 8 and on the control items.
- (C) `digits_bound` takes the exact nearest norm of the coset, `nn`, and every point of the coset has `hypot >= sqrt(nn)`, so every candidate (both coordinates nonnegative) has `max(b, c) >= sqrt(nn/2)` and at least `sqrt(nn/2) * log10(3)` digits (`deepcut.py` `digits_bound`, docstring). For the 8 this is 10^24.3 to 10^27.8 digits, far above 192. The nearest point has a negative coordinate in each of the 8, so it is not a candidate at all. Hence no checked point is needed: the anchored premise "all but one point" holds with the empty exception, and the `L_S` congruences apply to every candidate. If instead the nearest point were admissible with small norm it would be an anchor, which is the other branch of `run_c.py:92-112`.

A pattern with no admissible Babai point therefore has a sound Lemma C certificate, conditional on Lemma C as written, on the Babai exactness for a Lagrange-reduced basis (REDTEAM-SANDWICH 6, not re-derived), and on the pattern list.

For the sandwich: same coset and representation, so the same argument carries over. I did not build or run it for unanchored input (no input needed it), so no claim is made about `cport sandwich` on unanchored cosets.

For the level-480 shadow: not applicable, because its wrap target and its shadow come from y. A generalization would compute `T_p = 2^a 3^{b0} 7^{c0}` mod p at the seven trivial-image primes from the nearest coset point and test each word child against `T_p`. That is a new certificate, not derived or validated here, and I did not build it.

## (3) Commands

```
cd P/tier0-opt/unanchored8
nice -n 10 uv run --no-project --with sympy python -I items.py                  # the 8, admissibility
nice -n 10 uv run --no-project --with sympy python -I run_unanchored.py > run_unanchored.out   # Python cut on the 8
nice -n 10 uv run --no-project --with sympy python -I mk_cases8.py              # cases8.txt
nice -n 10 clang -O2 -std=gnu11 -Wall -Wextra -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function -I/opt/homebrew/include -o cport_coset cport_coset.c -L/opt/homebrew/lib -lgmp -lm
nice -n 10 ./cport_coset deepcut --lattice ../cport/data/lattice96.txt --cases cases8.txt --depth 1 --maxcases 5000000 --tsv cases8.tsv > cases8.out 2> cases8.err
nice -n 10 uv run --no-project --with sympy python -I mk_control.py             # control_anchored.txt, control_items.txt
nice -n 10 ./cport_coset deepcut --lattice ../cport/data/lattice96.txt --cases control_anchored.txt --depth 1 --maxcases 5000000 --tsv control_anchored.tsv > control_anchored.out 2> control_anchored.err
nice -n 10 ./cport_coset deepcut --lattice ../cport/data/lattice96.txt --cases control_items.txt --depth 1 --maxcases 5000000 --tsv control_items.tsv > control_items.out 2> control_items.err
nice -n 10 uv run --no-project --with sympy python -I mk_planted.py             # cases8_planted.txt
nice -n 10 ./cport_coset deepcut --lattice ../cport/data/lattice96.txt --cases cases8_planted.txt --depth 1 --maxcases 5000000 --tsv cases8_planted.tsv > cases8_planted.out 2> cases8_planted.err
nice -n 10 uv run --no-project --with sympy python -I verify_extra.py
```

`cport_coset.c` is `cport/cport.c` (md5 29105783f886919f0b4cada75a62c8c5) with two added case forms for the `deepcut` command only: `s M a b,c nu eps` (coset given by a base point, representation built from `nu` and `eps`) and `s M a Y@b,c - -` (anchor Y for the representations, coset taken from the record). The anchored forms are unchanged.

md5 (inputs, tools, outputs):

```
3382a57f8934f6b20878b343a00bf6e4  tier0/trees_mac.jsonl (48.6 MB, mtime Oct 22 21:26:52 2026; equals the final13 snapshot)
010c8bacd3b5b612c11473a3b95a87d3  cport/data/lattice96.txt
09c4b6ce642d1624a34d6ebef6223a8b  tier0/deepcut.py
84da334d3a682f38d87c2a9ce2899eec  tier0/descent.py
6c8a04e71bf674fce0f52dd185ee58a9  tier0/lattice.py
084f18a7f8af9aac344afe2d17d12acd  tier0/dlog.py
b95707a1983b6fc6e5c330d90dcfbdbc  cport/cport (not run; reference)
29105783f886919f0b4cada75a62c8c5  cport/cport.c
bdfae2c9ee58dad5f5097233e1ebf367  cport-shadow480w/src/cport_shadow480w.c (read only)
565f256f88fab83908b2f643fc212f28  final13/d1/pattern_status.json
a1d0376bff93ffaa69d2533baa7243ee  final13/shadow/s480w.tsv
1330a6c90c590c28d67619f699d0fd57  unanchored8/cport_coset
f23e024ec878cbcf1c277daf66fb612b  unanchored8/cport_coset.c
536e6c8498ddb1c49c1ec708cba832fd  unanchored8/uncut.py
3649d96cf671752d805907c04b9172b7  unanchored8/items.py
a9510484906e5f6612ce5ba05701faab  unanchored8/run_unanchored.py
bacf60b02643d0e3675abde1f66d643c  unanchored8/mk_cases8.py
44d920338ac440f77bf4535336459011  unanchored8/mk_control.py
4778b23695f3b9d575d13459076f3eb4  unanchored8/mk_planted.py
bb7cb3f8ab02d5ca8ccba82ef4efe866  unanchored8/verify_extra.py
f3aa919d72a72d29ca4d87f4e5f3f43d  unanchored8/cases8.txt
c36e5117747811d5b812cea2f8edbcee  unanchored8/cases8_planted.txt
5b66fd2ececed80988fe9b3741877c92  unanchored8/control_anchored.txt
5fb1299ca30ce5ee0f188125c2b67e6d  unanchored8/control_items.txt
```

## Planted negative

The U-inflation negative (`final13/mk_inflated.py`) gates a sandwich closure. This result reports none, so there is no sandwich closure to flip and that table is empty (not run).

The gate actually used is the cut. Its planted negative (`mk_planted.py`): for each of the 8, take an admissible depth-1 case `L` of the pattern for which `v2(L) = a'` and `5 does not divide L`, solve `2^a' 3^b 7^c = L (mod 10^96)` over all of Z^2 with `cut_coset`, and use that base point with the same lattice. The coset then contains a point satisfying the case, so the cut must not close it. `a' = a` where an admissible case exists with the recorded `a` (patterns 1 to 3); for the other 5 no admissible case has `v2(L) = a`, so `a'` is the smallest alternative (0 for patterns 4 and 5, 2 for 6 to 8).

| # | real (C, `cases8.out`) | planted (C, `cases8_planted.out`) |
|---|---|---|
| 1 | CLOSED | survives, bound 10^(10^71.29) digits |
| 2 | CLOSED | survives, bound 10^(10^71.29) digits |
| 3 | CLOSED | survives, bound 10^(10^71.35) digits |
| 4 | CLOSED | survives (a' = 0), bound 10^(10^71.93) |
| 5 | CLOSED | survives (a' = 0), bound 10^(10^71.85) |
| 6 | CLOSED | survives (a' = 2), bound 10^(10^72.07) |
| 7 | CLOSED | survives (a' = 2), bound 10^(10^72.07) |
| 8 | CLOSED | survives (a' = 2), bound 10^(10^72.07) |

8 of 8 flip from closed to not closed. The Python implementation also flipped the first 2 (survivors 252 and 24; `run_planted_py_partial.out`); I stopped it after the third item because it ran for over 50 minutes under load, and used the C implementation for the table.

## Positive control

The brief asks for 3 anchored patterns of "the same equations" that final13 closed. The three target equations hold no anchored pattern (their `open` equals the unlisted count), so I took anchored patterns of the same two vertices with the same pipeline path (coset from the record, not from y), k = 14 to 15, with one recorded depth-1 survivor to test the other direction. `status` is `final13/d1/pattern_status.json`.

| anchored key | final13 depth-1 status | coset-from-record, all representations (C, `control_anchored.out`) | per-rep (closed, cases) equals final13 `d1/deepcut_*.tsv` rows |
|---|---|---|---|
| 1161216 22222222222799 14 11519532122112 | cut1 | CLOSED (1 rep, 2880 cases) | yes |
| 11239424 222222222247778 8 952342272 | cut1 | CLOSED (8 reps, 28672 cases) | yes |
| 1161216 22222222223679 1 44471322 | survivor (`unrun`) | not closed (12 reps, 18088 cases, bound 10^(10^72.10)) | yes |

Verdicts match 3 of 3. Item-level (nu, eps from the record) controls, Python (`mk_control.py` output) and C (`control_items.out`), agree on 6 of 6 items: CLOSED, CLOSED x3, SURVIVOR, CLOSED, with equal case counts for the C rows. The two cut1 anchors and the survivor are all depth-1 cut verdicts; none of the three is a sandwich verdict, so the control does not exercise the sandwich or the shadow.

## Seams

- The cut verdicts rest on reading `eps` as the level-96 positions of the digits `sorted(M)` in canonical order. The evidence is 1 of 1 Python membership of the recorded `(nu, eps)` among `all_representations(M, y)` (the other two control anchors had Python enumeration abandoned as too slow, `run_control_py_aborted.*`) and case-count equality with the anchored C rows. It is not checked against sweep code that writes `eps`.
- The unanchored status is by recomputation of the `run_c.py:92-112` test on the stored items. I did not compare the 18,061 admissible items against the listed `exceptional` entries one by one; the counts agree (8 = open minus listed).
- Closure by the cut assumes Lemma C as stated, including the Lagrange-reduced Babai exactness (not re-derived) and the claim that the digit floor holds for all coset points. The 8 nearest points have one negative coordinate; the floor is the weaker norm-based bound, not the bound for the nonnegative quadrant.
- I did not run the sandwich or the level-480 shadow on any unanchored input. The generalization of the shadow noted in (2) is a proposal only.
- For patterns 4 to 8, no admissible depth-1 case has `v2(L) = a`; whether the sweep's earlier levels should already have removed them was not investigated.
- The final-stage vertex flags (`final_stage.py` lines 231 and 246) still print `RECORD-MISMATCH` for both vertices; I did not alter that tool. Whether the two vertices count as closed also depends on the final13 seams (the shadow-new cases and the 3281116734-style pre-fix issues for those two vertices), which are untouched here.
- The Python cut on the 16-digit patterns took 18 to 28 s each; the first control attempt in Python (all representations) was stopped after more than 30 minutes and the C implementation was used for the control. Aborted scripts are kept: `run_control_py_aborted.py`, `run_planted_py_partial.py`.
- A no-op `python3` heredoc was executed once by mistake (it printed one word and touched no file). Every analysis script ran with `uv run --no-project python -I` from a file.
- Stray files I created and did not delete: `dump_items.py`, `pick.py`, `status_peek.py`, the aborted Python runs above.
