# PREDICTION (TB-ANCHORED), written before any compute

Timestamp: 2026-10-24 15:59 EDT (date -u appended below). Nothing in this directory has been executed except `tar xzf` of the census and file reads.

Registered chat prediction under test: depth-1 survival 0.2% +- 0.05 on 71663616, zero wrap >= 1 survivors, every survivor CLOSED-cut at 480/1152 or closed by the sandwich at >= 10^300, none open.

My own predictions (vertex 71663616 = 2^15 * 3^7, anchored census 2.999e8 patterns, k_digits 9..22):

1. Algebra: with 9V = 9y + w(10^96 - 1) - (10^nu - 1), the congruence 10^nu + 9 S_U + w == 0 reduces to L == y (mod 2^(a+9) 5^5) with L = R_96 + sum over the fixed set F; it depends only on digits at positions e < a+9. Survival is therefore a property of the low-position configuration, and the wrap enters only through which low digits the representation has.
2. Survivor count (all patterns, exact enumeration): 0.15% to 0.45% of 2.999e8, central 0.25%, i.e. 7.5e5 [4.5e5, 1.35e6]. The chat sample was drawn with at most 30 patterns per hit and hits weighted by count, so it under-weights the large hits; I expect the exact rate to differ from 0.20% by up to a factor 2 in either direction. The registered 0.2% +- 0.05 has about 40% chance of containing the exact rate.
3. Wrap >= 1 survivors: not zero in the full enumeration. 0/53,279 sampled gives a 95% upper rate of 5.6e-5, but 3.0e8 patterns of which 6e7 are wrap >= 1 could carry 10^2 to 10^3 survivors. Probability that the exact count is exactly zero: 20%.
4. Congruence versus exact cut (wordlift.depth1_words, the reference I can actually run; d5b_depth1.py's libraries anchorlib and sandwich_lite are not on disk): 0 disagreements on >= 20,000 patterns, 90% confidence.
5. Verdicts: all survivors closed (cut or sandwich) for the shadow-level certificates; at k <= 22, a majority (60-90%) CLOSED-cut, remainder sandwich with U'' about 10^150 to 10^200 against bound 10^301. Open: 0 expected; probability any survivor is open 5%. BUDGET: under 1% at 2 CPU-h / 3 GB.
6. CPU per survivor (cport_r2c, default caps): median 0.3 s, mean 2 s [0.5, 10], right-skewed; cost grows with k (k <= 24 bin of the Tier C bill: mean 1.5 s, median 1.0 s).
7. Bill: survivors 7.5e5 x 2 s = 1.5e6 CPU-s = 17 core-days for 71663616 [3, 90]; the 24 CPU-h budget cannot cover all survivors, so a uniform sample is required. All 13 vertices: 1.71e10 patterns x 0.25% = 4.3e7 survivors x 2 s = 8.6e7 CPU-s = 1,000 core-days [150, 5,000] = 100 days on 10 cores. The SPRINT-TIERBC claim "days on the Mac" for the certificate stage is, in my prediction, wrong by a factor 10 to 100 (months).
8. Failure modes: (a) cport_r2c rejects or mishandles c = 0 patterns (no factor 7) or wrap >= 1 representations; (b) exact enumeration counts per (y,k,nu) disagree with the census counts (then the DP port is wrong; stop); (c) cost dominated by a few high-k outliers (BUDGET lower bounds); (d) survivor density concentrated in few low configurations with huge completion counts, so uniform sampling over patterns is dominated by those y.
Sat Oct 24 19:59:11 UTC 2026
