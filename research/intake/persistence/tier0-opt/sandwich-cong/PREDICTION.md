# PREDICTION (written before any compute in this directory)

Read before writing: HSHADOW.md sections 6-8, LIFT-ADDITIVE.md, DEEPCUT.md, both RESULT.md files, src/cport_r2.c run_rep480 / mitm480 / chain480, the "rep0:" lines of 679 recorded R2BILL runs (nT, |G|, compat, notshadow_alive).

Paper reasoning that precedes the numbers:
- A digit placed at copy t >= 1 contributes 10^(e+96t), which is 0 modulo 2^(a+v2+2) * 5^(v5+1) for every a in range, so the window side of depth D equals the depth-1 window side; depth never kills through the window (DEEPCUT already says "depth 2 never kills").
- The shadow child (every digit at residue 0) has V_child = V, so its modular coset is the anchor coset at every level, and its survival is membership of X/y in the 2,5-adic image of the level lattice: a congruence on the digits with the same shape as Theorem F.
- Every other child must satisfy Delta = tau modulo the product PT of the trivial-image primes: a modular subset-sum, solved by the meet-in-the-middle; it is not a closed form.

Odds (my own, before compute):
1. The SHADOW's survival at depth D (D = 5, level 480) is one congruence on the digits, agreeing with cport_r2 on every recorded representation (wrap 0): 85%.
2. The whole certificate (non-shadow children included) collapses to a chain of congruences evaluated without a subset-sum search: 5%. Reason: the non-shadow children are the solutions of a modular subset-sum with 10^13..10^18 candidates and PT about the same size; no digit-level closed form is known for those.
3. A chain evaluated in microseconds replaces cport_r2 for the verdict in a SOUND way (accidents excluded, not assumed absent): 5%. Evaluated for the shadow only, the verdict agrees on all recorded cases (notshadow_alive = 0 in all 679 recorded runs) but is not a certificate.
4. The certificate factors through (anchor, a) so one computation serves many survivors: 10%. Predicted dedup ratio of distinct (y, a, nu, digit multiset) keys to survivors: at most 1.3. The MITM depends on the unit multiset (d, e, m) and nu, not on the anchor alone.
5. A different, partial lever: restrict the subset-sum to children compatible with a depth-1 word (digits of the word forced to residue 0, a factor of up to 5 per forced digit). Odds it cuts the k >= 28 survivor cost by 10x or more: 35%.

Expected speedup on the anchored bill: 1x for the sound certificate with the lever in item 5 absent; 3x to 100x on k >= 28 if item 5 works; "microseconds per survivor" only for the unsound shadow-only verdict.

Revised bill prior: smallest Tier C vertex stays at 5.4 core-years [3.6, 7.8] unless item 5 works, in which case 0.3 to 2 core-years.
