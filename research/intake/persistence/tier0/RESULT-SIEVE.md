# The zero-free S-unit sieve to 10^6884 — certification of Corollary C1(b)'s premise

*Chat session, 2026-10-21, run 18:58–23:27 EDT across nine reboots of the cloud box. Code `zfsieve_chat.c` (10-adic sieve),
`zfsieve_check.py` (exact check). Status: COMPLETE. Calibration: an exact finite computation; its independent counterpart is
Chaffin's 2016/2019 enumeration (OEIS A003001; all 2^a3^b7^c below 10^{20000}) and Cairn's gated zfsieve.*

## 1. What is computed

Every (a, b, c) with 10^{79} ≤ 2^a 3^b 7^c < 10^{6885} (generous float bounds; 4.5×10^{11} triples) is visited in
the order c, b, a with the value kept modulo 10^{36} and 10^{108} in base-10^6 limbs (doubling along a, ×3 along b,
×7 along c from scratch per c for resumability). A triple is rejected as soon as a digit 0 appears among its lowest
min(M, n−2) genuine digits (n from logs; the −2 guards the float boundary). Survivors (≈ 1.2×10^{−5} of the triples)
are checked exactly: lowest 600 digits by modular exponentiation for n ≥ 602, otherwise the full integer; a survivor
of that is converted in full and tested for the digit 0 anywhere.

Control: with bounds [1, 10^{80}] the same binary plus the exact check returns exactly the 8723 corpus elements below
10^{80} (`ctrl80.txt`; the corpus `zf_below_1e4000.txt` is known to agree with brute force there). Positive
control inside the main run: every corpus element with ≥ 80 digits (84 with 81–140 digits, 7 with exactly 80) is found
(`found.txt`, 91 entries, all corpus elements).

Resumability: the box rebooted 9 times during the run; each worker (c even / c odd) resumes from its last `DONE c`
line and re-runs the interrupted c from scratch; torn output lines from a reboot are skipped by the checker (their
c-value is re-emitted whole).

## 2. Result

Workers reached c = 8146 (even class) and c = 8145 (odd class) at 23:27 EDT; every c ∈ [0, 8146] has a DONE
line (8147 of 8147, parity-correct), 448,299,085,464 triples visited (the exact count of (a, b, c) with
10^{79} ≤ 2^a3^b7^c < 10^{6885} under the float bounds; the [10^{80}, 10^{6883}) count is 447,908,543,193);
stage survivors checked exactly: 5693747 lines over the whole run (including the re-emitted segments of interrupted c-values) (every one
with ≥ 602 digits had a 0 among its lowest 600 digits; none needed the full conversion beyond the corpus range);
zero-free S-units found: the 91 corpus elements with 80–140 digits and nothing else. **No zero-free {2,3,7}-unit
with more than 140 digits exists below 10^{6884}.** sha256 (first 16 hex): out_0.txt 518d328aab03cca6,
out_1.txt f27820a5343d12b0, found.txt 2ea23b926507138f.

## 3. Consequence

Corollary C1(b) of CONDITIONAL.md needs the corpus below 10^{6883} to add no vertex to T_6 or T_8. It adds no
element at all above 140 digits (this run; Chaffin's run to 10^{20000} independently), so C′ = C and T′_Δ = T_Δ.
Hence, with Theorem C:

**Theorem D (conditional on RST[1]).** Every positive integer with multiplicative digital root 2, 4, 6 or 8 has
persistence at most 6, 5, 8, 6 respectively. With BCGN's theorem for the odd roots, every integer whose orbit does
not end at 0 has persistence at most 8.

What this does not touch: root 0 (Z′; REDUCTION.md).
