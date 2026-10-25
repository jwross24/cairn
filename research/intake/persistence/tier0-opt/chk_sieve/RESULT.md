# L1: chat zfsieve vs Cairn gated zfsieve6900 (second certification, computational, nothing PROVEN)

Scripts and raw outputs in this directory: counts.py/counts.out, compare.py/compare.out, recheck.py/recheck.out.
RESULT-SIEVE.md md5 verified 70483b0a412b256c1aa81b83c179a868.

## Statements (read from code)
- Same unit set: all (a,b,c) >= 0, y = 2^a 3^b 7^c, decimal, zero-free = no digit 0 anywhere.
- Chat: sieves 10^79 <= y < 10^6885 (generous float bounds, L0=80, L1=6884); control run covers y <= ~10^80. Claim "no zero-free above 140 digits below 10^6884" is a subset of what was sieved.
- Cairn zfsieve6900: all y < 10^6900 (dmax=6900, no lower cutoff). Strictly larger range; same statement on the overlap.
- Mismatch only in stated bound (10^6884 claimed vs 10^6885 sieved vs 10^6900 for Cairn); no definitional mismatch.

## Sets
- Cairn list: 8807 entries, all re-verified exactly (digits, zero-free), max 140 digits, none above 140; tier0 copy identical.
- Chat found.txt: 91 entries, all exact-verified, 80..140 digits. Cairn entries with >=80 digits: 91. Symmetric difference: empty; digit counts agree.
- Chat ctrl80 survivors (9902 lines) exact-checked: 8727 zero-free (4 have 81 digits, all in found.txt). ctrl80 (<=80 digits) vs Cairn (<=80 digits, 8723): identical. Union of ctrl80 and found.txt equals Cairn's 8807 exactly.
- Independent exact recheck of every chat stage survivor: 5,693,741 lines + 6 torn = 5,693,747 (matches RESULT-SIEVE.md); 5,689,277 unique triples; 5,685,382 rejected by low 600 digits, 3,895 full checks; zero-free = exactly the 91. Decompressed out_0/out_1 sha256 prefixes match the stated 518d328aab03cca6 and f27820a5343d12b0.

## Coverage count (exact, 48-bit fixed-point logs, each bound robust under +-1e-9 shift)
- [10^79,10^6885): 448,299,085,464 = DONE-line sum. Per-c counts match for all 8147 c in [0,8146], zero mismatches, no missing, no duplicate or conflicting c.
- [10^80,10^6883): 447,908,543,193 (matches RESULT-SIEVE.md).
- Cairn [1,10^6900): 451,235,888,800 (matches Cairn's tested count).

## Planted negatives
Dropping one entry from a copy of found.txt (planted_found_drop1.txt), one from Cairn's list, or adding a spurious entry: comparator reports each; unplanted control reports no difference.

## Cairn's own sieve
Complete, 96/96 chunks, exit 0 (COORDINATION.md 2026-10-21 17:55 entry). Nothing to finish.

## Seams
- I did not rerun either sieve; agreement is between two different sieve implementations' outputs (chat: low-digit 10-adic; Cairn: leading-digit window plus low 144 digits). Rejection correctness of the sieve stage is not independently re-derived, only its survivor set re-checked and the outputs compared.
- Chat's survivors list is trusted as written to disk; the 6 torn lines are consistent with the documented reboots.
- Cairn's leading-digit window ran on 53-bit double-double; its own gate (PARI sample, error 1.6e-30) is as reported by Cairn, not re-run here.
- Stated bound 10^6884 vs 10^6885 actually sieved: harmless but the paper should say which.
- Both share one methodology family (same triple enumeration idea), so convergence is not fully independent of that idea; the exact-count check covers the enumeration.
