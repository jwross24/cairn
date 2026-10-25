# H1 lane notes (registered before any run)

Registered 2026-10-20 ~21:00 EDT, before running classify_open.py.

Prediction P1 (data): classify_open.py over the three files reports at least 299 distinct open
triples, no NOT-S-UNIT and no ZF-OTHER; the exact-identity check (run_exact, which the CLI does not call)
reports 0 NO EXACT IDENTITY.

Prediction P2 (mechanism): the exact identity is equivalent to the full congruence y = V mod R_96, so it
carries no information beyond "an S-unit of size < R_96 lies in the coset"; the lattice gives no pigeonhole
(index 2.8e56 vs about 1e4 S-units below 10^98 per a). Anchoring of every open pattern is therefore a
statement that no random coset hit exists, true iff (patterns per equation) x (density) is far below 1.
Predicted: summed expected random hits over the recorded equations is < 1e-3; it exceeds 1 for q >= ~22.

Outcome: P1 true for counts (3154 distinct triples, 6990 recorded open patterns, 0 failures) but the 1.1e9 anchor
height cap is stale (max 1.0e14). P2 true that sum mu < 1e-3 (2e-13); my guess of crossover q ~ 22 was low, the
computed crossover is q ~ 26-30 depending on digit shape.

## Level-48 decisive test, registered before the run (2026-10-20 ~21:25 EDT)

Target: s = 124416, M = 2^9 3^5 (q = 14), levels 12, 24, 48, 1 core, nice 10.
Quantity: number of level-48 coset survivors that are accidents (nearest coset point with max(b,c) > 200, no small S-unit),
versus anchored (nearest point small and run_exact finds the identity).

Uniform-residue accident model: raw N_48 * rho_48 = 499.5 (N_48 = 9.45e17, rho_48 = 5.286e-16 from index/phi). Corrections:
x0.73 for |H|/Q instead of |H|/phi, x(0.09 to 0.14) engine filter factor measured at levels 12 and 24 for q >= 10.
Registered prediction, accident picture: 42 accidents (plausible 20 to 100, Poisson sd ~6.5 plus a factor-2 systematic).
Anchoring picture: 0 accidents.

Retrodiction already in hand (not the run): 7 sibling equations (q = 13-14, trees_mac) have 46 level-48 survivors, and the level-96
survivor count equals the level-48 count in each, so 0 are accidents; the same calibrated model predicts 31 accidents there
(raw 422). If that reading is right the test is expected to show ~0 and the uniform model overstates, because the children of
level-12/24 survivors are far fewer than the uniform domain (477 per survivor observed vs ~4300 average). Chain prediction using
observed domain sizes: <= 0.3 accidents. My best single guess is therefore 0 observed, with the uniform picture's 42 as the
refutable alternative.
(Clock correction: the registration above was written at 21:10 EDT, not 21:25; run started 21:10.)

Result of the level-48 run (21:15 EDT, 298 s wall, 1 core, nice 10): s = 124416, M = 2^9 3^5, A = 49.
Level 12: 8,803,791,360 patterns, 4,544,237 survivors. Level 24: 3,510,549,840 children, 1,097 survivors. Level 48: 13,874,912 children,
17 survivors, all engine-OPEN. All 17 anchored (Babai point small, exact identity found by run_exact): anchors 2*3^8 = 13122,
2^2*3^4*7^3 = 111132, 2^2*3^14*7 = 133923132. Accidents observed: 0. Registered accident-picture prediction: 42 (20 to 100); observed 0.
