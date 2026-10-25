# PREDICTION (written before any compute in this directory)

Read before writing: the two RESULT.md files, the k histogram of tierc-rank/r2w0_pooled_pat.jsonl (khist.py: k = 30 to 33 hold 9.4% of the wrap-0 patterns, k = 34 none among 25,082).

1. Survivor sampling. Survival rate per wrap-0 pattern at k >= 30 is lower than or equal to the 2e-4 of k = 25 to 29 (more digits make a depth-1 cut harder to survive? not established; the 5 observed survivors have k = 25 to 29 only). Expected: 20 to 40 new survivors from the sampling budget, of which 2 to 8 with k >= 30, none with k = 34.
2. Expected closures. k <= 29 survivors: closed by the sandwich (U'') at default or raised caps, matching the 5/5 of tierc-r2shadow. k = 30 and 31: closed by the sandwich with raised caps for about half, the rest BUDGET (8 GB or 2 CPU-hours). k >= 32: mostly BUDGET. Open: 0. Closed by the cut: 0 (they are depth-1 survivors).
3. Expected CPU seconds by k (median): k 25 to 26: 1; k 27 to 28: 10; k 29: 600; k 30: 6e3; k 31: 3e4 (BUDGET lower bound 7.2e3); k 32 and above: BUDGET. Growth about 10 times per unit k beyond 28.
4. Expected bill: heavy tail dominated by k >= 30. Central 1e3 core-years, 95% interval [30, 2e4], BUDGET cases entering as lower bounds so the upper end is open-ended. On 1000 rented cores the central figure is about 1 year; on 10 cores 100 years.
5. Controls: the 5 earlier survivors reproduce their verdicts under the new table; the inflated table (10^400) gives open on every tested survivor, zero closures.
6. Table extension: mk_utable_u2.py with --kmax 34 reproduces the k <= 29, a <= 24 rows of utable_u2_k29.txt exactly; it may fail or be slow for large a at k >= 30.
