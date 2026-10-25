# Spec of the best variant (BEST = window pruning + table-driven setup + small-prime bitmap + cofactor chain), for a blind re-implementation

Goal: reproduce the OPEN/EXACT lines of tier0/lvlN (md5 20e091fc) for Lold = 12, Lnew = 24 on the cfg/parents format of tier0/lvlN.c, byte-identical after sorting.
The reference semantics are the source of lvlN.c (the only authority); this document names the algorithm, not the format. The join (meet-in-the-middle on key residues) is
join24swap/lvlN.c; the additions below are necessary-condition filters or arithmetic replacements, so correctness only needs "never discard a child that lvlN would emit".

## Notation (level 12 -> 24)
Parent: (a, nu, e_1..e_q, b, c). Digits d_j >= 2 grouped by value; equal (d, residue) form a SLOT s with multiplicity m_s; a child chooses k_s in 0..m_s lifted copies (residue + 12) and nu or nu + 12.
Child value mod each new prime p in {73, 137, 99990001}: y_p = R_nu' + sum_s (d_s - 1) ((m_s - k_s) 10^{r_s} + k_s 10^{r_s + 12})  (R_n = repunit). A child survives the residue test iff for every l-component
(cfg "components") the vector of logs lies in the image set; otherwise dead. Survivors get t = (t1, t2) by CRT; the tail test (Y = 2^a 3^{b'} 7^{c'} mod 10^K, K = KT[a]) decides OPEN/EXACT.

## 1. Window pruning (the part that produced the factor; ideaC/c_window.inc)
(b', c') = (b, c) + t1 Uold[0] + t2 Uold[1]; Y depends on t only through t1 mod T1p, t2 mod T2p with T1p = lam / gcd(lam, gcd(Uold[0][0], Uold[0][1])), lam = lcm(4 5^{K-1}, 2^{K-2}) (500 for K = 4;
T1p = T2p = 5, 25 classes). For each class compute Y mod 10^K from tables of 3^e, 7^e (e < lam) and 2^a. A class is DEAD if some digit of Y among the K lowest is 0, if the number of digits equal to d >= 2 exceeds the multiset
count of d, or if some non-1 digit d_i at position i has no slot (d_i, residue i) in the parent. A live class has a requirement set R = { slots (d_i, i) : d_i >= 2, i < K }.
A child with window lift pattern k passes the class iff every slot in R has k_s < m_s (an unlifted copy remains at residue i, because the tail test counts digits d at position i against the child's digits at residue i, and a lifted copy sits at i + 12).
A child can only survive if SOME live class passes. Slots with residue < K are put first in the slot order (least significant mixed-radix digits of the A half). For every A-index whose window pattern (window slots assigned
to the B half are assumed unlifted, i.e. optimistic) passes no live class, skip all probes of that A-index; if no pattern passes, skip the parent (children are still counted: sum of 2 * prod(m_s + 1)).
Measured: 67% of A-indices skipped and 8% of parents skipped on 9437184_222222222228889. Only the survivor SET is unchanged; the tail-dead counter drops (those children never reach the tail test), so compare open/exact counters and the sorted lines.

## 2. Table-driven setup (E0)
a) T_p = 2^a 3^b 7^c mod p for the key primes from exp tables of the generator (exponent X = a L2 + b L3 + c L7 mod p-1 is already computed for the component offsets): one table lookup.
b) Slot contributions contrib[s][k][p] by repeated addition of (c1 - c0) mod p; half lists by an odometer with a carry correction (no division). c) Targets T_p * K_j by 64-bit modulo, not 128-bit.
d) A candidate carries only (A-index, B-index); its digit residues are decoded when it reaches the full test; residues y_p = base + a + b with two conditional subtractions.

## 3. Small-prime bitmap and cofactor chain (A)
Per parent build a 137-bit bitmap of T_137 K_137 and drop a candidate whose y_137 is outside it (after the zero test). For 99990001: z = y^1111 (11-bit exponent, 4 candidates interleaved), 5-part element z^144, test the 625-component first
(kills 96%), then the 2- and 3-parts from z^5625, z^10000; everything surviving runs the unchanged full test.

## 4. Key choice
Cost model of join24swap with W_CAND = 40 (candidates are cheaper after 2-3): choose the key set (73, 137, (73,137) ...) minimizing 20 na K + 10 (na + C/na) + W_CAND C sacc.

## Gate (same as join24swap/gate.py)
Differential on 228 equations (sorted-line sha256 plus open/exact counters, level 24); planted mutants: (M1) drop the odd-indexed allowed key residues, (M2) replace 2^a by 1 in the key target, (CMUT2) look up the window slot at residue i+1.
Both mutants must change the output on every equation that has at least one output line (M1 needs the forced key sets; 4 one-line equations with a = 0 parents are equivalent for M2).
