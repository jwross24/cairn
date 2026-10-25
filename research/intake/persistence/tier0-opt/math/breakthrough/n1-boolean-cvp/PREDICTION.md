# N1 predictions, registered 2026-10-21 01:08 EDT

Honest ordering note: the first two patterns (14336/47888 and 28672/{247888,444788}, 13 of 43 keys at D <= 3)
had already been run through the exact-mode prototype when this file was written and showed 0 disagreements;
the 30 remaining keys, every k >= 9 key, every relaxed-E run and every scaling and certificate experiment below
had not been run. The predictions below are for those.

## P1 (differential, exact mode)

Exact mode = enumerate depth-E bases with deepcut's own cut, then solve the last D-E blocks as ONE linear
system with lattice reduction plus Fincke-Pohst enumeration, E = smallest E with 192E - a >= 96D.
For every (key, representation, depth) row of the frozen C-port oracle (`oracle/sw/*.tsv`, which reproduces
tier0-opt/cport/SANDWICH-full.txt row for row, 43 of 43 CLOSED):

- the minimum squared nearest norm equals the oracle's integer `nn` exactly;
- the labeled sub-coset count (sum over bases of multiplicity times the class-DP count of high placements)
  equals the oracle's last `stats` entry exactly;
- every enumerated leaf passes the exact modular re-check (inexact = 0), i.e. Theorem 1's linearization is exact;
- zero disagreements, hence the 43 verdicts and 43 minimum bounds coincide.

Falsifier: any row with nn_eq or cnt_eq False, or inexact > 0.

## P2 (relaxed E)

With E smaller than the exact-linearization threshold (a > 0, D even), the linear system is a superset
(2-adic modulus 2^(s-a) instead of 2^(K-s)). Prediction: relaxed minimum <= exact minimum,
equal after the exact leaf filter (leaf re-check on), and no verdict changes.

## P3 (planted points)

For random admissible placements x* and the exact nearest point of their sub-coset (radius^2 := its norm), the
certificate search NEVER certifies (0 false closures), at small and at Tier-C size; with radius^2 lowered by 10^6
the certificate does certify in a majority of trials (the gate can say yes). Falsifier: a certified planted point.

## P4 (Tier C, heuristic information budget)

Single-multiplier certificate exists iff 96*h_blocks > 2*log10(Z) + sum over position-groups of log10(2g/...) where
Z = box half-width of z (about U / |shortest vector of Lambda_E|). Using |Lambda_E| shortest = 10^(72+48(E-1)):

- k = 31, log10 U = 281.51: slack(E) = 192E + 48 - 2(log10 U + 0.5) - 3 - S, S about 44 for 30 groups:
  E = 3 (D = 6): slack about +13 digits, so certificates found for most bases (prediction: >= 80 percent of
  sampled bases, one LLL each);  E = 2 (D = 4): about -179, so none.
- k = 44, log10 U = 402.12: E = 4 (D = 8): about -56, so none found; E = 5 (D = 10): about +115, found.
- Therefore the lattice step removes only the top floor(D/2) enumerated blocks: total cost = (number of depth-E
  bases) x (one LLL of dimension about #types x (D - E)), E about D/2.
- Depth-E base count for the Tier-C pattern of codex-deep-attempt.md: E = 3 between 3e5 and 3e6.

## P5 (registered 01:46 EDT, before any analysis of the minimum-bound statistics; the 132 differential rows already exist but
## their nn values have not been compared with this formula)

Minimum over the N unlabeled sub-cosets of the nearest-point squared norm behaves like the minimum of N independent
samples of the covering distribution of a 2D lattice of covolume V_D: nn_min = V_D / (pi N) within a factor of 10^(+-0.7)
(one-sigma of the minimum of N exponentials is 0.43 decades; a lattice coset's nearest-point norm is not exactly
exponential, so +-0.7 is the registered band). V_D is the covolume of the depth-D sub-coset lattice (its index in Z^2),
read from the cut. Consequence for the lane's targets: the usual quoted lower bound 10^(72 + 48 (D - 1)) digits must be
reduced by 0.5 log10(N_D) digits. For the Tier-C pattern of codex-deep-attempt.md (a = 0) I predict that depth D = 6
closes k = 31 (bound about 10^(300 +- 3) against log10 G' = 281.5) and that D = 8 does NOT close k = 44 (about 10^(396 +- 4)
against 402.1; D = 9 does), because N_8 is larger than 10^25 there. Falsifier: the fitted residual of log10(nn_min) against
log10(V_D / (pi N)) outside +-0.7 for more than 15 percent of the 132 rows, or exact counts N_D inconsistent with
the stated orders.

## Registered 04:09 EDT, after the P1-P4 runs reported in NOTES.md and before the runs below

P4 outcome so far (not part of this registration): 66 of 66 sampled Tier-C bases at E = 3 certified by one LLL each;
the registered slack (+13) used 30 position groups, but no base has more than 24 (digits consumed in blocks 0-2 shrink
the group count), so the measured predicted slack is +25 to +46.

P6 (incremental lift). Theorem 1 applied to a fixed filling x, with K = s + 96 <= 2 s - a, produces the refined coset
without any discrete logarithm. Prediction: for the Tier-C pattern (a = 0), depth-1 -> 2 and depth-2 -> 3 lifts equal the
cut_coset results (same lattice, same coset) on every one of 12 x 6 + 4 x 3 x 6 = 144 sampled children (n1full.py liftcheck).
Falsifier: any inequality.

P7 (a full family). The first 400 bases (depth 3) of block-0 survivor number 4 of the Tier-C pattern are all certified at
D = 6 with log10 U = 281.51: 400 of 400, and the per-base cost (lift + system build + LLL) stays below 0.1 s in Python.
Falsifier: any uncertified base or a per-base cost above 0.1 s.

P8 (min-bound statistic, P5 recalibrated). Under the exponential model for one coset's nearest-point squared norm,
log10(nn_min / (V_D/(pi N))) has mean -0.25 and standard deviation 0.56 (for N = 1 it has the same law), so about 81
percent of rows fall within +-0.7 of zero and about 95 percent within +-1.3; the P5 falsifier (more than 15 percent
outside +-0.7) therefore sits at the edge of its own model. The test is applied to the 132 rows as: mean in [-0.45, -0.05],
sd in [0.4, 0.8].

## Outcomes (04:50 EDT; details in NOTES.md)

- P1 held: 43 of 43 keys, 145 rows, integer nn and labeled counts equal, 0 inexact leaves.
- P2 held in the mild regime (D = 2, a > 0, E = 1: same minimum, 3 to 4 nodes). For E < D/2 the relaxation is not just inexact but
  infeasible (D = 3, E = 1: enumeration unfinished at 50,000,000 nodes, exact system 5 nodes).
- P3 held: 0 false closures (57 + 21 + 21 small, 8 + 8 at Tier-C scale, 12 genuine S-units); the gate certified at radius^2/10^12 in 8 of 8.
- P4 held in direction: E = 3 certified 66 of 66 (registered at least 80 percent), E = 2 none; k = 44: E = 4 none, E = 5 yes. The
  registered numbers were off for the right reason: slack +13 assumed 30 groups, bases have at most 24, measured predicted slack +25 to +46;
  N_3 = 4.41e5 inside the registered [3e5, 3e6].
- P5 half held: the V_D/(pi N) form is right, the registered band is slightly off (mean -0.47, sd 0.54, 24 percent outside +-0.7 against the
  registered 15); N_8 > 10^25 was wrong (2.8e13), the D = 6 closes / D = 8 does not close k = 44 conclusion survives (401.5 vs 402.12).
- P6 held: 144 of 144 lifted children equal the discrete-logarithm cuts.
- P7 held and was exceeded: the 400 first bases certified at 45 ms each; the full run then certified all 440,640 depth-3 bases (six families) at 30.8 ms each, 0 failures.
- P8: mean -0.47 (registered window [-0.45, -0.05]: missed by 0.02), sd 0.54 (window [0.4, 0.8]: met).
