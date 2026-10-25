# X2 RESULT: what survives level 24 on the 228 gated equations

Written: Wed Oct 21 21:15:11 EDT 2026. Predictions: PREDICTIONS.md (md5 e3d4618bf8a45308896f400990d9445a, registered 20:44 EDT, unedited).
Calibration: the anchor test is exact big-integer arithmetic (every shadow re-verified by an independent integer identity, 32,056 of 32,056). The model comparison is Poisson with the model's own +-3% uncertainty folded in.
No-Claim: classification says nothing about closure.

## Verdict

1. **The relayed prediction fails.** Among level-24 descent survivors (D) at k >= 13 (10 equations, A < 64), 438 of 1,140 are shadows: 0.384 [Clopper-Pearson 0.356, 0.413]. The fraction is not >= 0.99. It is >= 0.99 only for k <= 8 (0.996 at k = 8, 0.989 at k = 9, 0.969 at k = 10, 0.903 at k = 11, 0.696 at k = 12-13, 0.362 at k = 15, 0.118 at k = 18). The 3 equations with A >= 64: 152 of 3,418 (0.045).
2. **Accidents are uniform at level 24.** Observed accident counts equal the uniform model: residue stage rho_R = 1.018 [0.979, 1.061] (37,783 observed vs 37,099 predicted, 225 equations); tail stage rho_T = 1.000 [0.930, 1.075] (2,182 vs 2,182.9). At k >= 13: rho_R = 1.020 [0.975, 1.068], rho_T = 0.947 [0.863, 1.040]. A suppression by any factor above 1.08 (pooled T) is excluded at 95%. The kill test (SUPPRESSED = upper bound < 0.8) did not fire at any stage or k. No crack in "accidents are uniform" appears here.
3. For anchor-first this means: at k = 13-18 the level-24 survivor set holds 976 accidents against 451 shadows (T stage, A < 64), and the accident count follows children x 3.777e-6 x tail pass rate to within 5%.

## Definitions used (as registered)

Pattern value V = R_nu + sum (d_j - 1) 10^{e_j}, residues in [0, 24). Shadow: y = V mod R_24 is nonzero and equals 2^a 3^b 7^c (equivalently y + kappa R_24 = V, OPEN-PATTERNS (†) at L = 24; kappa <= 28 <= 8k in all cases). Accident: no such y.
R = all level-24 residue survivors (OPEN + EXACT + tail-dead, from the instrumented copy). T = the engine's OPEN and EXACT lines. D = members of T still OPEN under pydesc.classify_batch with descent (what goes to level 48). k = number of non-1 digits. Counts are distinct (a, nu, canonical eps). All 228 equations run; none skipped.

## Table (A < 64 unless stated; rho = observed accidents / uniform-model prediction, 95% Poisson interval widened by the 3% model uncertainty; SUPPRESSED if upper < 0.8)

| k | eqs | children | R | R shadows | R accidents | E_R | rho_R [95%] | T | T shadows | T accidents | E_T | rho_T [95%] | D | D shadows | D accidents | D shadow frac [CP 95%] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 2 | 336 | 4 | 4 | 0 | 0.0 | 0.000 [0.000, 2996.402] CONSISTENT | 2 | 2 | 0 | 0.00 | 0.000 [0.000, 230171.058] CONSISTENT | 2 | 2 | 0 | 1.0000 [0.1581, 1.0000] |
| 6 | 8 | 5224 | 15 | 15 | 0 | 0.0 | 0.000 [0.000, 192.724] CONSISTENT | 5 | 5 | 0 | 0.00 | 0.000 [0.000, 6853.004] CONSISTENT | 5 | 5 | 0 | 1.0000 [0.4782, 1.0000] |
| 7 | 22 | 295724 | 382 | 381 | 1 | 1.1 | 0.895 [0.022, 5.142] CONSISTENT | 115 | 115 | 0 | 0.04 | 0.000 [0.000, 87.698] CONSISTENT | 108 | 108 | 0 | 1.0000 [0.9664, 1.0000] |
| 8 | 32 | 6299936 | 1928 | 1900 | 28 | 23.8 | 1.177 [0.759, 1.753] CONSISTENT | 819 | 816 | 3 | 1.12 | 2.670 [0.535, 8.046] CONSISTENT | 778 | 775 | 3 | 0.9961 [0.9888, 0.9992] |
| 9 | 49 | 73544896 | 5045 | 4741 | 304 | 277.8 | 1.094 [0.946, 1.262] CONSISTENT | 1789 | 1771 | 18 | 13.79 | 1.305 [0.751, 2.126] CONSISTENT | 1702 | 1684 | 18 | 0.9894 [0.9833, 0.9937] |
| 10 | 52 | 643707814 | 11598 | 9123 | 2475 | 2431.5 | 1.018 [0.950, 1.092] CONSISTENT | 3777 | 3653 | 124 | 120.01 | 1.033 [0.834, 1.270] CONSISTENT | 3569 | 3459 | 110 | 0.9692 [0.9630, 0.9746] |
| 11 | 33 | 2465169952 | 19190 | 9801 | 9389 | 9311.7 | 1.008 [0.959, 1.061] CONSISTENT | 4261 | 3786 | 475 | 470.39 | 1.010 [0.894, 1.139] CONSISTENT | 3931 | 3551 | 380 | 0.9033 [0.8937, 0.9124] |
| 12 | 17 | 2677908756 | 13916 | 3565 | 10351 | 10115.3 | 1.023 [0.974, 1.075] CONSISTENT | 1717 | 1131 | 586 | 547.22 | 1.071 [0.957, 1.197] CONSISTENT | 1525 | 1062 | 463 | 0.6964 [0.6726, 0.7194] |
| 13 | 5 | 697604216 | 3427 | 751 | 2676 | 2635.1 | 1.016 [0.949, 1.087] CONSISTENT | 348 | 222 | 126 | 151.29 | 0.833 [0.674, 1.022] CONSISTENT | 313 | 217 | 96 | 0.6933 [0.6389, 0.7439] |
| 15 | 2 | 1822366272 | 7713 | 660 | 7053 | 6883.7 | 1.025 [0.972, 1.081] CONSISTENT | 637 | 192 | 445 | 465.38 | 0.956 [0.844, 1.082] CONSISTENT | 514 | 186 | 328 | 0.3619 [0.3203, 0.4051] |
| 17 | 1 | 87692932 | 380 | 39 | 341 | 331.2 | 1.029 [0.896, 1.180] CONSISTENT | 33 | 2 | 31 | 26.35 | 1.177 [0.776, 1.722] CONSISTENT | 24 | 1 | 23 | 0.0417 [0.0011, 0.2112] |
| 18 | 2 | 1346900798 | 5259 | 94 | 5165 | 5087.7 | 1.015 [0.959, 1.076] CONSISTENT | 409 | 35 | 374 | 387.30 | 0.966 [0.845, 1.102] CONSISTENT | 289 | 34 | 255 | 0.1176 [0.0829, 0.1605] |
| k<=12 (A<64) | 215 | 5866932638 | 52078 | 29530 | 22548 | 22161.3 | 1.017 [0.975, 1.063] CONSISTENT | 12485 | 11279 | 1206 | 1152.58 | 1.046 [0.959, 1.141] CONSISTENT | 11620 | 10646 | 974 | 0.9162 [0.9110, 0.9212] |
| k>=13 (A<64) | 10 | 3954564218 | 16779 | 1544 | 15235 | 14937.6 | 1.020 [0.975, 1.068] CONSISTENT | 1427 | 451 | 976 | 1030.32 | 0.947 [0.863, 1.040] CONSISTENT | 1140 | 438 | 702 | 0.3842 [0.3559, 0.4132] |
| all (A<64) | 225 | 9821496856 | 68857 | 31074 | 37783 | 37098.9 | 1.018 [0.979, 1.061] CONSISTENT | 13912 | 11730 | 2182 | 2182.90 | 1.000 [0.930, 1.075] CONSISTENT | 12760 | 11084 | 1676 | 0.8687 [0.8627, 0.8745] |
| A>=64 (3 eqs, separate) | 3 | 17356821196 | 66298 | 982 | 65316 | 65562.2 | 0.996 [0.960, 1.035] CONSISTENT | 5279 | 187 | 5092 | 5210.75 | 0.977 [0.923, 1.035] CONSISTENT | 3418 | 152 | 3266 | 0.0445 [0.0378, 0.0519] |

Descent pass rate of T accidents: d = 1,676 / 2,182 = 0.768 [0.750, 0.786] (RESULT-accidents 3(b) quoted 0.24-0.4; the descent removes less than that here). Tail pass rate of R accidents: 0.058; of R shadows: 0.378 (the tail test kills 62% of shadows, which the engine output alone cannot show). Half-anchor diagnostic (J = 1..64): 0. Anchor exponent a' = engine a: 0 mismatches of 32,056 shadows.
The 3 A >= 64 equations (level-12 output under audit in kt-audit-l12), reported only on their own row: 9437184_222222222222222222229 (k 21) R accidents 10,732 vs 10,778; 9437184_22222222222222222266 (k 20) 31,154 vs 31,030; 9437184_2222222222222222289 (k 19) 23,430 vs 23,755; T accidents 845 / 2,513 / 1,734 vs 858 / 2,530 / 1,822. They match as well, conditional on the level-12 parents being correct.

Shadows: 32,056 over 564 distinct anchors, all with <= 15 digits (19 with 3 digits, peak at 8-9 digits); kappa 0 for 25,110, 1 for 3,186, up to 28. Most frequent anchors: 750141 (1,164), 13122 (1,084), 1000188 (868), 330812181 (820), 1778112 (759), 14112 (705).

## Controls

- Planted anchored: 111132 with proper digits classifies shadow (y 111132, 2^2 3^4 7^3, kappa 0). 1,200 planted S-units (300 random below R_24 for each kappa 0, 1, 2, 3, patterns built from y + kappa R_24, including digits above the top): 1,200/1,200 recovered (y, kappa).
- Random patterns (random nu, eps, 5-20 digits): 0 of 100,000 classified shadow.
- False-anchor refusals: 5 x S-unit, 11, 0 and V = 0 mod R_24 all refused.
- Real shadows with one residue or nu shifted by 1 (40,000 trials): 267 (0.67%) remain shadows. The registered expectation (all accident) was too strong: these are patterns with elements at residues 22, 23, 0, 1 where wraps give kappa = 1-18 and a different small anchor (216, 1512, 756); each was recomputed as an exact identity. They concentrate at k = 9-12 (ctl3.py). The classifier is exact; the control shows perturbed shadows are not uniform random patterns.
- Instrument gate (all 228): lvlN_x2 OPEN+EXACT lines identical to join24swap/lvlN (b43dad7d) sorted sha256; DEAD lines = tail-dead counter; children equal; join24swap/lvlN identical to tier0/lvlN (20e091fc) sorted sha256. Planted negative: dropping one line from one output changes the sha (56efcb57a15d8f9e -> d0129305df2423d8), altering one character changes it (b8a7d229d85bcd10).

## Limits

- The model's tail-pass probability rests on the assumption that the child's position in the fiber is uniform for an accident; the agreement of 2,182 with 2,182.9 supports it but is one aggregate.
- The test covers the 228 equations (k 5-21, mostly k <= 12) from the h12 corpus parents; 215 of the 225 A < 64 equations have k <= 12.
- Python fallback counts inside classify_batch were not recorded.
- Level 24 only. Nothing here speaks to levels 48 and 96, where accidents in the Tier C vertices are forecast in RESULT-accidents Table 8.

## Files and md5 (P/tier0-opt/math/x2-survivors/)

PREDICTIONS.md e3d4618bf8a45308896f400990d9445a; model.py 65025053af7c52c3bc8ceb83c8572556; model_out.jsonl 7ec5d2cf94aff13f118ff13caf20c75f; model_table.csv 74eda782f22025f87818aaba8ad93bab;
run24.py bcc548e53348336720d81211d27bf94d; run24.log b1e28f753754d87743559a7500850a75 (a log written once; md5 as listed); classify.py 92bb1bbf636d1c8aa72deb21f31c455c; anchor.py cf13b86bfccc68cf3a4698fa4373b7b8;
aggregate.py fa82fef36fdffb5c9eaddb34e367fcec; controls.py dc25bdc49138067edeaddfadd06870b0; verify.py 6887b7e6970bc66618edcfe2e4acdf69; ctl3.py 6ccd135987107ebf16853be54c3c4b5d;
survivors.jsonl fe3927bfd32ec6cbb8dca7d73d4ba4b4 (135,155 rows); summary_by_eq.json ce13f39cef3a168b15a7af5a98a33aab; per_equation.json aba28385221920632d11c2e4c02d8ae9; table_by_k.md 599674974b04e56d79aa78c56e32f51f;
gate_instrument.json e373c9ec27b7890642ef474bdac135ea; controls_out.json 4c01b42cf13ec1d6cb46be8563b5502c; inst/lvlN_x2.c 85b3b3a951608765741294282f7781ef; inst/lvlN_x2 0e898aa6ec1062d90de4914f8904c6ae;
out/ (1,368 engine output files, md5 of the per-file md5 list) 798af4a82c25f492343d139e0e82185b.
Engines: join24swap/lvlN b43dad7d891e8a9e19ac7aec10fd042c; tier0/lvlN 20e091fc7eecabb906406dfd37bed87d (both verified at run time). CPU: model 2 min, engine runs about 40 min (nice 10, one core), classification 8 s.
