# Kill-ladder profiles (ladder.py), 2026-10-19/20

Survival fraction of a random residue pattern at level L = |image of the digit-prime exponents in ∏(Z/p)^*| / ∏(p−1),
computed exactly as |det(kernel lattice)| (no enumeration). Column 2: all S-units (bounded exponents free);
column 3: free primes only with the bounded exponents fixed (the engine's lattice group). Observed base-10
level-12 survival 1/40 = column 3 × (A+1 ≈ 12 bounded tuples) — the model is calibrated.

Base-8 prediction, made BEFORE the run (23:52 EDT): 70 vertices incl. 7 roots; 1.12×10^9 level-12 patterns in total,
dominated by s=826875 (4.7e8), 972405 (2.7e8), 455625 (2.0e8); ~5 h single-core Python at 15 µs/pattern;
expected open-at-12 ≈ 2.3e-3 × 3 bounded tuples × patterns before the a-split and tail test.

```
base 6: digit primes [2, 3, 5], bounded [2, 3], free [5]
  L primes of b^L-1 outside digit primes              surv(all S-units)  surv(free, 1 bounded tuple)
  6 7 31 43                                                   1.000e+00                    5.556e-03
  8 7 37 1297                                                 3.333e-01                    5.144e-04
  9 19 43 2467                                                5.000e-01                    9.259e-03
 10 7 11 101 311                                              5.000e-01                    2.500e-03
 12 7 13 31 37 43 97                                          2.315e-03                    6.430e-06
 14 7 29 197 55987                                            7.143e-02                    4.252e-04
 15 43 311 1171 1201                                          1.250e-01                    2.137e-05
 16 7 17 37 1297 98801                                        2.083e-02                    2.009e-06
 18 7 19 31 43 2467 46441                                     3.858e-04                    7.144e-07
 20 7 11 37 101 241 311 6781                                  6.944e-05                    5.787e-08
 24 7 13 31 37 43 97 1297 1678321                             3.827e-07                    4.922e-12
```

```
base 8: digit primes [2, 3, 5, 7], bounded [2], free [3, 5, 7]
  L primes of b^L-1 outside digit primes              surv(all S-units)  surv(free, 1 bounded tuple)
  6 19 73                                                     1.000e+00                    1.000e+00
  8 13 17 241                                                 1.000e+00                    3.333e-01
  9 73 262657                                                 2.500e-01                    8.333e-02
 10 11 31 151 331                                             5.000e-01                    5.000e-02
 12 13 19 37 73 109                                           8.333e-02                    2.315e-03
 14 43 127 337 5419                                           5.000e-01                    1.190e-02
 15 31 73 151 631 23311                                       2.778e-02                    1.852e-03
 16 13 17 97 241 257 673                                      2.604e-03                    1.085e-04
 18 19 73 87211 262657                                        4.167e-02                    1.543e-03
 20 11 13 31 41 61 151 331 1321                               5.556e-05                    9.259e-07
 24 13 17 19 37 73 109 241 433 38737                          3.349e-07                    9.303e-09
```

```
base 9: digit primes [2, 3, 5, 7], bounded [3], free [2, 5, 7]
  L primes of b^L-1 outside digit primes              surv(all S-units)  surv(free, 1 bounded tuple)
  6 13 73                                                     1.000e+00                    1.000e+00
  8 17 41 193                                                 5.000e-01                    5.000e-01
  9 13 19 37 757                                              5.000e-01                    8.333e-02
 10 11 61 1181                                                5.000e-01                    5.000e-02
 12 13 41 73 6481                                             1.000e+00                    1.250e-01
 14 29 547 1093 16493                                         1.429e-01                    3.571e-02
 15 11 13 31 61 271 4561                                      2.083e-03                    6.944e-05
 16 17 41 193 21523361                                        2.500e-01                    3.125e-02
 18 13 19 37 73 757 530713                                    2.315e-03                    1.286e-04
 20 11 41 61 1181 42521761                                    2.500e-02                    1.250e-03
 24 13 17 41 73 97 193 577 769 6481                           7.064e-08                    1.472e-09
```

```
base 10: digit primes [2, 3, 5, 7], bounded [2, 5], free [3, 7]
  L primes of b^L-1 outside digit primes              surv(all S-units)  surv(free, 1 bounded tuple)
  6 11 13 37                                                  1.000e+00                    2.500e-01
  8 11 73 101 137                                             1.000e+00                    4.167e-02
  9 37 333667                                                 1.000e+00                    8.333e-02
 10 11 41 271 9091                                            5.000e-01                    1.000e-02
 12 11 13 37 101 9901                                         1.000e-01                    2.083e-03
 14 11 239 4649 909091                                        5.000e-01                    3.571e-02
 15 31 37 41 271 2906161                                      2.500e-01                    2.778e-04
 16 11 17 73 101 137 5882353                                  6.250e-02                    3.255e-04
 18 11 13 19 37 52579 333667                                  2.778e-02                    4.287e-05
 20 11 41 101 271 3541 9091 27961                             1.667e-04                    2.778e-07
 24 11 13 37 73 101 137 9901 99990001                         1.736e-04                    8.038e-09
```

```
base 12: digit primes [2, 3, 5, 7, 11], bounded [2, 3], free [5, 7, 11]
  L primes of b^L-1 outside digit primes              surv(all S-units)  surv(free, 1 bounded tuple)
  6 13 19 157                                                 1.000e+00                    5.000e-01
  8 13 29 89 233                                              1.000e+00                    2.500e-01
  9 37 157 80749                                              1.000e+00                    2.500e-01
 10 13 19141 22621                                            1.000e+00                    8.333e-02
 12 13 19 29 157 20593                                        1.667e-01                    2.083e-02
 14 13 211 659 4943 13063                                     1.000e+00                    3.571e-02
 15 61 157 661 9781 22621                                     8.333e-02                    1.389e-03
 16 13 17 29 89 97 233 260753                                 3.125e-02                    4.883e-04
 18 13 19 37 157 1657 1801 80749                              6.944e-03                    1.072e-05
 20 13 29 19141 22621 85403261                                1.000e+00                    4.167e-03
 24 13 19 29 89 157 193 233 20593 2227777                     1.302e-03                    4.521e-06
```


Reading: base 10's level 12 is not unusual — every base has a level whose primes give a sudden rank gain
(base 6: 12 (13·31·37·43·97: 2.3e-3); base 8: 16 or 20 (2.6e-3 / 5.6e-5); base 9: 15 (2.1e-3); base 12: 18 (6.9e-3)).
The choice is the balance of L^{q+1} patterns against survival; for q ≤ 10 level 12 then 24 is right in every base,
for base-9/12 vertices with q ≈ 27–31 no level is cheap enough (same frontier phenomenon as base 10).
