# N1 lane notes: Boolean lattice reduction for the Baker-lattice sandwich (2026-10-21)

Nothing here is Lean-checked; nothing is PROVEN. Labels as in THEOREMS.md.

## Verdict in four lines

1. The linearization is real and exact (Theorem 1, PROVEN-ON-PAPER), but only for the TOP half of the depth: free variables at
   positions >= s make the congruence affine modulo precision 2 s and no better (Proposition 1.2). Depth D therefore costs
   enumeration of E = ceil((D + a/96)/2) blocks, then ONE lattice problem (polynomial in the number of variables) per base.
2. Per-pattern cost is NOT polynomial in q: it is (number of depth-E bases) x (poly LLL). For the Tier-C pattern of
   codex-deep-attempt.md (q = 31, 10 occupied classes) at D = 6 that is 440,640 certificates in place of 5.57e10 cuts (1.3e5 times
   fewer), run end to end in 3.8 hours of one Python core (section 6): all 440,640 bases certified, 0 failures. For k = 44 the certificate needs E = 5 (D = 10), 1.1e11 bases: out of reach.
3. The certificate is a sound one-way gate: 0 false closures in 57 + 8 + 12 planted tests and on 173 bases below the first closing
   depth; it closes all 43 SANDWICH survivors with a single multiplier per base (no branching).
4. The exact-minimum mode reproduces the C-port oracle on all 145 (pattern, representation, depth) rows of the 43 survivors:
   integer nearest norms and labeled sub-coset counts identical, zero disagreements.

## Files (all new, in this directory)

THEOREMS.md, PREDICTION.md, ADVERSARIAL.md, this file. Code: n1lib.py (Theorem 1 system builder, base enumeration),
n1solve.py (exact minimum: LLL/BKZ + Fincke-Pohst), n1cert.py (dual-multiplier certificate, branch and bound, gap),
n1diff.py (differential vs the C-port oracle), n1ref.py (vs tier0/deepcut.py), n1close.py (certificate verdicts on the 43),
n1neg.py, n1plant.py, n1genuine.py, n1gap.py (controls), n1tier.py / n1cost.py (exact class-DP counts of bases),
n1scale.py, n1tierc.py, n1grid.py, n1full.py (Tier-C experiments and the full family run), n1p5.py (minimum statistic).
Frozen inputs: /private/tmp/n1work (runall_final.jsonl, trees_c.jsonl, DEEPCUT-run-final-d1.txt, and the prefix of trees_mac.jsonl
that has md5 0fe595f8..., because the live file kept growing); oracle = the C port rerun on them
(/private/tmp/n1work/oracle; reproduces tier0-opt/cport/SANDWICH-full.txt row for row, 43 of 43 CLOSED). Copies of every log are in logs/ here; the originals are in /private/tmp/n1work (diff_all.log, ref.log, close.log, neg.log, gap.log, plant_small.log, genuine.log, grid_E3.log,
tierc_*.log, k44_*.log, p5.log, family_*.log, liftcheck.log).
Run with `PYTHONDONTWRITEBYTECODE=1 nice -n 10 uv run --no-project --with fpylll --with cysignals --with sympy --with gmpy2
python <script>`. fpylll 0.6.4 installs and works (it needs cysignals as well). The MPFR float type has no Python enumeration
callbacks, so the exact-minimum mode uses a Fincke-Pohst enumeration written here (doubles after exact rational
Gram-Schmidt; radius inflated by 1e-7; every leaf re-verified by exact modular exponentiation).

## 1. Differential test (P1) on the 43 SANDWICH survivors

Mode: enumerate depth-E bases with the same cuts as deepcut.deep_cut, then solve the remaining D - E blocks as one linear
system (Theorem 1) by lattice reduction plus enumeration. Compared with the oracle's per-(pattern, representation, depth) TSV:
- 43 of 43 keys, 145 (key, representation, depth) rows (depth 1: 47, 2: 47, 3: 40, 4: 11);
- minimum squared nearest norm equal as an integer on every row; labeled sub-coset count equal on every row (the count is
  the class DP of n1diff.class_count_labeled times base multiplicities);
- exact leaf re-check failed on 0 of all enumerated leaves (Theorem 1 exactness at scale);
- E = exact_E(D, a) = 1 (D <= 2, a = 0), 2 (D = 3, 4 with a = 0; D = 2 with a > 0), 3 (D = 4, a > 0);
- 73,246 sub-cosets resolved with 6,605 enumeration nodes (the largest row: 34,476 sub-cosets from 12 bases with 800 nodes).
Zero disagreements (P1 holds). The registered check against tier0/deepcut.py itself (n1ref.py) covers the 11 depth-2 DEEPCUT
survivors: 28 comparisons (representations and the two copies of the list in DEEPCUT-run.txt), bounds equal to 1e-9
in log10 digits, survivor counts equal, 5 closed representations also closed here. 0 mismatches.

Negative control (n1neg.py, neg.log): the same system with E smaller than the exactness threshold. D = 2, a > 0, E = 1: the
relaxed system has 3 to 4 enumeration nodes and returns the exact minimum (P2 holds in this mild regime). D = 3, E = 1
(K = 288 > 2 s = 192): the enumeration did not finish in 50,000,000 nodes (and again not in 400,000) where the exact system needs
5. So the limit 2 s is not a bookkeeping point: the relaxation has about 10^96 spurious solutions.

## 2. The certificate decides the 43 (n1close.py)

For each survivor, each representation, at the C port's first closing depth D*: build all depth-E bases, form the system, run the
dual-multiplier search (LLL on the multiplier lattice, exact interval test, branch and bound if needed) with the Baker bound
U(k, a) of the oracle's utable.
- 43 of 43 patterns closed by certificates alone; 47 (representation, depth) cases with variables, 395 bases, 395 certified, 356
  LLL calls (never any branching); smallest predicted slack 8.8 digits (k = 9).
- The same procedure at depth D* - 1 (where the oracle says open): 47 cases, 173 bases, 0 certified. A planted negative in the
  sense that every one of these contains a genuine solution of the system inside the disc.
- n1gap.py: for 28 bases the largest certified radius^2 is within a factor 2 (25 bases) or 4 (3 bases) of the exact minimum
  nearest norm: the single-multiplier certificate is almost sharp when slack is large.

## 3. Planted points (P3)

- plant_small.log (4 patterns, E < D): 57 sub-cosets planted at their own nearest norm, 0 certified (0 false closures); radius^2 =
  4 x (true minimum): 0 of 21 certified; radius^2 = true minimum - 1: 0 of 21 certified (the certificate is not sharp to the last
  unit, see the gap result).
- Tier-C scale (tierc_plant_E3.log; E = 3, D = 6, K = 576, U = 10^281.51): 8 random admissible placements x*, exact nearest norm
  by cut_coset at K = 576 (624 to 626 digits); at radius^2 = that norm 0 of 8 certified (branch and bound visited 13 to 79
  nodes, all failed); at radius^2 / 10^12 8 of 8 certified. The gate says yes and says no.
- Genuine S-units (genuine.log): 12 S-units 2^a 3^b 7^c (arbitrary digits, zeros allowed) with a up to 9, b about 900-1400, c about 500-900
  placed as patterns with their own digits (m = 83 to 338 Boolean variables, (E, D) = (1,2), (2,3), (2,4), including the
  relaxed cases a > 0): the genuine (z, x) satisfies the Theorem 1 congruence in 12 of 12, satisfies the exact residue check
  in 12 of 12, and the certificate does not certify at its radius in 12 of 12.

## 4. Tier C (the pattern of codex-deep-attempt.md: q = 31, classes 0..9, y = 3^3 7^10, a = 0)

Exact counts (class DP, unlabeled, n1cost.py): depth-1 survivors 6 of 5184 fillings (matches Codex), depth-2 bases 3,072
(matches Codex's 3,072), depth-E bases N_E:

| E | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| N_E (= pure-enumeration sub-cosets at D = E) | 6 | 3.07e3 | 4.41e5 | 3.39e7 | 1.65e9 | 5.57e10 |

(pure enumeration at D = 7, 8, 9, 10: 1.4e12, 2.8e13, 4.6e14, 6.2e15). Registered range for N_3 was [3e5, 3e6]: 4.4e5 holds.
Synthetic q = 40 and 44 with the same class skeleton (extra 2s and 3s): N_4 = 3.4e8 and 5.9e8, N_5 = 4.9e10 and 1.1e11.

Certificate on sampled bases (tierc_*.log, k44_*.log, U from b3 REPORT):
- k = 31, log10 U = 281.51, E = 3, D = 6: 60 of 60 random depth-3 bases certified plus the 6 worst-case bases (blocks 1, 2 empty,
  24 groups, 27 to 30 variables); one LLL each, 0.01 to 0.06 s, predicted slack +25 to +46 (my registered +13 assumed 30 groups;
  no base has more than 24). E = 2 (D = 4): 0 of 2 certified, predicted slack -146.
- k = 44 synthetic (13 extra free digits, 40 groups), log10 U = 402.12: E = 4 (D = 8): 0 of 10 certified, plus the 6
  worst-case bases (200-node branch and bound cap), predicted slack -56 (the z-part alone uses 372 of the 384 digits of
  modulus); E = 5 (D = 10): 6 of 6 certified, slack +115, 0.3 to 0.9 s each with 65 to 75 variables. Prediction P4 holds
  in direction and value.
- Certificate-existence grid (grid_E3.log, base fixed, E = 3, up to 240 variables, 62 coordinates): found down to slack -49.5
  (D = 6, 60 groups), not found at -53 (D = 6, 90 groups) and below; the predicted-slack formula is conservative by about 50
  digits (one-sided group hulls, L1 body).

Per-base certificate time (n1grid, n1tierc; 61 points, m in [12, 240] variables, modulus 10^h with h in {192, 288, 480}):
t = exp(-29.05) m^2.12 h^3.24 seconds, rms log error 0.7 (a factor 2), fpylll LLL driven from Python, one core.
Lifting: Theorem 5 generates a depth-3 base in about 8 ms (vs 1.2 to 2.6 s for cut_coset; 144 of 144 children identical).
Building one system: about 14 to 29 ms (the first 400-base test: 45 ms per base in total; after caching g(u_i): 30.8 ms per base over the full run).

Cost summary for the pattern at k = 31 (log10 U = 281.51):
| route | work | time (one core) |
|---|---|---|
| pure enumeration at D = 6 | 5.57e10 cuts | about 1.1e8 s at the C port's 1.9 ms per sub-coset (3.4 core-years) |
| E = 3 lattice certificates (this lane) | 4.41e5 bases x 30.8 ms | 3.77 hours in Python, measured end to end (section 6) |
For k = 44 (log10 U = 402.12): E = 5 (D = 10) certificates, 1.1e11 bases x about 1 s: 3,000 core-years; pure enumeration at
D = 9 (the first depth where the min-bound statistic below passes 402): 4.6e14 cuts.

## 5. What closes, and the depth actually needed (P5/P8)

Minimum over N unlabeled sub-cosets: log10(nn_min) = log10(V_D / (pi N)) - 0.47 with standard deviation 0.54 (113 rows with
k <= 9, p5.log; for N >= 2 the same numbers: mean -0.46, sd 0.58; 76 percent of rows within +-0.7, 93 percent within +-1.3;
V_D = covolume of the sub-coset lattice, log10 V_1 = 146.2 and +96 per depth for a = 0). Registered P8 band (mean in [-0.45, -0.05]) is
missed by 0.02, and the registered P5 falsifier (at most 15 percent outside +-0.7) is exceeded (24 percent), so the registered
model is slightly mis-calibrated, not wildly. Using the calibrated rule on the Tier-C counts: the digit bound at D = 6 is
about 10^(306.8 +- 0.3) against 10^281.51, closing k = 31 with margin 25; at D = 8 the q = 31 structure gives
10^(401.5) against 10^402.12 (not closing, within the scatter), and any larger N_8 makes it worse; D = 9 gives 10^(449) and closes.
The prediction of P5 that N_8 > 10^25 was wrong (N_8 = 2.8e13 for the q = 31 skeleton), the conclusion (D = 8 fails to close k = 44
by a hair, D = 9 closes) stands. The quoted lower bound 10^(72 + 48 (D-1)) must be reduced by 0.5 log10 N_D + 0.2.

## 6. The full Tier-C family run (n1full.py family, logs family_0..5.log)

Every depth-3 base of the Tier-C pattern was generated by Theorem 5 (no discrete logarithms), turned into the D = 6 system
(blocks 3, 4, 5), and run through the certificate with log10 U = 281.51 (k = 31, a = 0, b3 REPORT):

| block-0 survivor family | 0 | 1 | 2 | 3 | 4 | 5 | total |
|---|---|---|---|---|---|---|---|
| bases (equal to the class-DP count) | 93,312 | 46,656 | 93,312 | 82,944 | 41,472 | 82,944 | 440,640 |
| certified / failed | all / 0 | all / 0 | all / 0 | all / 0 | all / 0 | all / 0 | 440,640 / 0 |
| seconds (one niced core, Python) | 2,960 | 1,319 | 2,510 | 2,885 | 1,266 | 2,634 | 13,574 |

30.8 ms per base on average (lift about 8 ms, system about 14 ms after caching g(u_i), one LLL about 6 ms). The per-family
base counts equal the independent DP counts of n1cost.py, so no child was lost (a lift that returned no coset would have
shown as a shortfall). Margin: 20 of 20 sampled bases still certify at log10 U = 282, 290, 296, 300 and 304 (the exact
minimum bound of a typical sub-coset is about 10^306.8), so the 2-decimal rounding of U in the b3 table is irrelevant.

Reading (STRONG-EMPIRICAL for the computation, conditional on Lemma C, Theorem U with its Bugeaud-Kaneko constant, and the
anchor/representation list being the one in codex-deep-attempt.md): the Tier-C pattern y = 3^3 7^10, nu = 2, with the
31-digit class multiset of codex-deep-attempt.md has no candidate other than its anchor with at most 10^281.51 digits, which
with Theorem U closes it. This is the first sandwich closure at k = 31. It is one pattern of one vertex; it is not a census
of the vertex 128421199872, and nothing here is machine-checked.

