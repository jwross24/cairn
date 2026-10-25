# What a complete proof of Sloane's conjecture requires — the exact reduction, and where this project stands

*2026-10-21 19:30 EDT, chat session. Sources: PAPER.md §1.1–2.1, BCGN (arXiv:2110.04263, fetched: odd targets
1, 3, 7, 9 have persistence ≤ 1 beyond the first product and target 5 has Ξ ≤ 5 — target 5 IS covered), Fonga
(arXiv:2608.27802, fetched: the 2-adic bound for fixed digit multiplicities, every base b ≥ 3), the corpus
`zf_below_1e4000.txt` (chain statistics below computed from it), CONDITIONAL.md. Calibration: §1–§2 are definitions
and elementary facts; §3 is the status; nothing here is a result on Conjecture Z (none is claimed).*

## 1. Chains

For N ≥ 10 write N → p(N) → p²(N) → … → Δ(N) (single digit). Every iterate after N is a product of digits, i.e. a
{2,3,5,7}-unit. Three ways the orbit ends:
- Δ ∈ {1, 3, 7, 9}: all iterates have only odd digits and no 5 — BCGN: persistence ≤ 2 (Ξ ≤ 1 after p(N)).
- Δ = 5: all iterates from the first with a 5 are odd multiples of 5 with odd digits — BCGN: persistence ≤ 5.
- Δ ∈ {2, 4, 6, 8}: every iterate p^j(N), 1 ≤ j < pers(N), is a zero-free {2,3,7}-unit ("zf S-unit"), and the
  last one is the single digit Δ. pers(N) = 1 + (length of the zf S-unit chain p(N) → … → Δ, counting Δ... ) — in
  the tree language, pers(N) = 1 + depth of p(N) in T_Δ, and max pers over the tree = 1 + max depth.
- Δ = 0: the orbit is N → y_1 → y_2 → … → y_m → z → 0 with y_1, …, y_m zf S-units and z = p(y_m) a
  {2,3,5,7}-unit that is not zero-free or has a 5 and an even digit. pers(N) = m + 2.
  (If instead z is a single digit 0, pers = m + 1; this only shortens.)

Elementary bound on chain shape: y_{j+1} = p(y_j) ≤ 9^{n_j}, so n_{j+1} ≤ 0.9543·n_j + 1 — a chain of length m
needs a top element with ≥ (n_m − 20)/0.954^{m} digits, and nothing more. Chains are not bounded by size arguments.

**Corpus facts (computed here).** Among the 8,807 zf S-units below 10^4000 (largest: 140 digits), the longest
zf-S-unit chain by terminal digit: Δ = 0: **9** (top 937638166841712, so persistence 11 — Sloane's record is a
Δ = 0 chain); Δ = 2: 5 (368947264); Δ = 4: 4 (128421199872); Δ = 6: 7 (3416267673274176); Δ = 8: 5 (1783627776).
Hence IF every zf S-unit is in the corpus, the maximal persistence is 11 (Δ = 0), 6, 5, 8, 6 for Δ = 0, 2, 4, 6, 8,
and Sloane's conjecture holds with the record 11.

## 2. The reduction

Sloane's conjecture (pers ≤ 11 for every N) is equivalent to the conjunction of
- (E) for Δ ∈ {2, 4, 6, 8}: the antecedent tree A_Δ equals the corpus tree T_Δ (then pers ≤ 8); it suffices that
  the 177 vertices of T_2 ∪ T_4 ∪ T_6 ∪ T_8 have no child outside the corpus (closure of every vertex), which is
  this project's subject; and
- (Z′) no chain y_1 → y_2 → … → y_10 of ten zf S-units with y_{j+1} = p(y_j) exists (equivalently: every zf S-unit
  that is the digit product of a zf S-unit, which is the digit product of a zf S-unit, … nine times, is a
  single digit or the chain breaks). Z′ is implied by Conjecture Z (every zf S-unit is below 10^4000, i.e. in the
  corpus): then every y_j is a corpus element and the corpus's longest chain is 9.
(Odd Δ are BCGN's theorem.) Z′ is strictly weaker than Z, but every attack on Z′ we know is an attack on Z: a chain
of length 10 has y_2, …, y_10 each a zf S-unit which is a digit product of a zf S-unit, and bounding those is
exactly the "children of a vertex" problem for the *infinite* family of vertices y_j outside the corpus. Z is the
statement that 2^a 3^b 7^c has a digit 0 once it exceeds 10^4000; it is of the same nature as the open conjectures
on the digits of 2^n (Erdős's base-3 conjecture; "2^n has a digit 0 for n > 86"), on which no method — Baker,
abc, large sieve — gives even a conditional proof. The project's standing rule that a claim of progress on Z is a
fabrication alarm is exactly right, and nothing in this file touches it.

## 3. Status of (E), honestly

- Unconditional: 138 of 177 vertices closed (Theorem 2 of PAPER.md); Tier A (15 vertices) is a Mac job of weeks
  to months; Tier B (13) and Tier C (6) are not reachable by the enumeration: the 12 → 24 lift costs ≈ 2^(k+1)
  children per level-12 survivor with ≈ 10^15 survivors at Tier B (cost model 2026-10-20 16:10, rates.json:
  sv12 ≈ 5×10^-3 of patterns at k ≈ 29) — ≈ 10^15 seconds even at a nanosecond per child. The shadow certificate
  (HSHADOW.md) removes the final stage's exponent, not the lift's.
- Conditional on RST[1] (CONDITIONAL.md, refereed 2026-10-21): (E) holds for T_2 and T_4 with the existing corpus,
  and for T_6 and T_8 once the corpus is extended to 10^6883 with no new vertex. **That extension is running now**
  (`/home/claude/zf/zfsieve.c`: 10-adic sieve of all 4.5×10^11 S-units in [10^80, 10^6884), control = exact
  equality with the corpus below 10^80, 8723/8723). If it finds no zf S-unit above 10^140, then:

  **Theorem (conditional on RST[1]).** Every positive integer with multiplicative digital root 2, 4, 6 or 8 has
  persistence at most 6, 5, 8, 6 respectively; together with BCGN, every integer whose orbit does not end at 0 has
  persistence ≤ 8.

  What remains for Sloane's conjecture in full is then Z′ alone — and that is where the record 11 lives.

## 3′. What is already known about Z′, and the constraint system of a 10-chain (Lane 3)

- **Peters 2023 (OEIS A003001 comment, fetched):** no number ≤ 2.67×10^30000 has persistence 12; the method enumerates
  the canonical digit strings (the smallest number with a given multiset: at most one each of the digits that can be
  merged, then 7s, 8s, 9s — eight regular expressions) up to 30,000 digits and iterates p. Since every S-unit
  y_1 = 2^a3^b7^c is p(N) for a canonical N with ≈ a/3 + b/2 + c digits, this verifies Z′ for every chain whose top
  satisfies a/3 + b/2 + c ≤ 30000 — far beyond the corpus (10^6884 ≈ a·0.3 + b·0.48 + c·0.85 ≤ 6884). So a corpus
  extension gives NO new unconditional bound on counterexamples (the 19:25 "corollary" is withdrawn); the corpus
  matters for the even trees only.
- **Constraints a 10-chain y_1 → … → y_10 must satisfy** (all elementary): (i) y_{j+1} = 2^{a_{j+1}}3^{b_{j+1}}7^{c_{j+1}}
  with a_{j+1} = n_2 + 2n_4 + n_6 + 3n_8, b_{j+1} = n_3 + n_6 + 2n_9, c_{j+1} = n_7 (n_d = count of digit d in y_j);
  (ii) y_j zero-free, so digits(y_{j+1}) ≤ 0.9543·digits(y_j) + 1 and ≥ 0.301·k_j (k_j = non-1 digits);
  (iii) under RST[1], Theorem C gives k_j ≥ √(n_j log n_j)/c for every chain element — a zero-free S-unit cannot be
  mostly 1s; (iv) Peters: a_1/3 + b_1/2 + c_1 > 30000. None of these bounds the length. The natural intermediate
  statement is
  **S1:** every zero-free S-unit y with more than 140 digits has p(y) that is not a zero-free S-unit (a digit 0, or
  a 5 next to an even digit, in p(y)).
  S1 is implied by Z (vacuously, if there is no such y) and implies Z′ (a 10-chain would need nine elements with
  zero-free S-unit products, all ≤ 10^140 by S1 and hence in the corpus, whose longest chain is 9). S1 is the
  weakest thing of this kind, and it is exactly as hard: p(y) is an S-unit whose exponent vector is the digit-count
  vector of y, and asking it to have a 0 is Z for that S-unit. No reduction below Z is visible; Lane 3's honest
  output is this paragraph.

## 4. Consequence for the project's direction

The honest target of further unconditional work is Tier A (closing it makes 153/177), and the honest target of
further mathematics is the hypothesis: can RST[1] be replaced by something weaker but still explicit (RST[β] lowers
the corpus height to 10^6491; plain abc with any explicit (ε, K) does not help; Baker's explicit abc gives 10^83+
digits)? Anything that promises Z, or a "complete solution", is outside what the mathematics allows today.
