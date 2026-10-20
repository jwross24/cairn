# Audit of "Tier 0 of the antecedent tree A_4 is closed" — independent re-implementation

Everything here was built from `RESULT.md` ("Method") and `known_children_A4.json` only; no original
code was read. All code, logs and results are in `/home/claude/audit_out/`.

## Verdicts

| vertex | verdict | my children | expected | my final level | theirs |
|---|---|---|---|---|---|
| 4   | **CONFIRMED** | 14 | 14 | 12 | 24 |
| 14  | **CONFIRMED** | 27, 72 | 27, 72 | 12 | 12 |
| 27  | **CONFIRMED** | none | none | 12 | 12 |
| 72  | **CONFIRMED** | 98, 189, 294, 1161216 | 98, 189, 294, 1161216 | 48 | 48 |
| 98  | **CONFIRMED** | none | none | 12 | 12 |
| 189 | **CONFIRMED** | none | none | 12 | 12 |
| 294 | **CONFIRMED** | none | none | 24 | 24 |

CONFIRMED = my independent implementation of the described method closes every digit-multiset
equation of the vertex (no OPEN pattern remains after the last level reached) and the children it
recovers are exactly the expected ones. Two independent brute forces agree (see §4).

Both lemmas (steps 5 and 6) are correct as stated; see `LEMMAS.md`. Step 6 is weaker than the prose
suggests (it is vacuous when a < K* and can never close a pattern by itself), but nothing in the
theorem depends on the prose.

## 1. What was implemented (and the choices the description forced)

Files: `lattice.py` (exact 2-D coset arithmetic + brute-force self-test), `dlog.py` (Pohlig–Hellman
+ BSGS, every log asserted by re-exponentiation), `engine.py` (steps 1–7), `run_tier0.py` (driver),
`brute.py` (task 4), `controls.py`, `trace.py`, `trace2.py` (positive-control tracing).

Step 1, 2-adic bound. Implemented literally: for k = 1, 2, … look for a string of j ≤ k digits over
{1} ∪ M (each non-1 digit at most its multiplicity), left-zero-padded to k digits, divisible by 2^k;
A = first k with no such string, minus 1. Results for the 19 multisets:
{4}:2 {2,2}:6 | {2,7}:6 | {3,9}:0 {3,3,3}:0 | {8,9}:3 {2,4,9}:16 {2,6,6}:12 {3,3,8}:3 {3,4,6}:9
{2,2,2,9}:15 {2,2,3,6}:14 {2,3,3,4}:16 {2,2,2,3,3}:13 | {2,7,7}:8 | {3,7,9}:0 {3,3,3,7}:0 |
{6,7,7}:9 {2,3,7,7}:13. The per-vertex maxima 2,6 | 6 | 0 | 8 | 0 | 13 | 16 are the eight numbers
the description lists. *Choice:* "zero-padding for short numbers" was read as "the whole number y may
have fewer than k digits"; the padded part is zeros, the number itself has no zero digit.
*Observation:* the bound is sound but loose: A({2,4,9}) = 16 comes solely from the 7-digit number
1114112 = 2^16·17; for y with ≥ 8 digits the true bound is 12. Harmless.

Step 2, residue patterns. Verified that the listed primes are exactly the primes of 10^L − 1 outside
{2,3,5,7} that are new at each level (factorizations in the log). *Choice:* a pattern is
(a, n mod L, multiset of (digit, e mod L)) — a is part of the pattern because the right-hand side
log(y_p) − a·log 2 depends on it. The level-12 count for ordered arrangements of {2,2,2,3,3} would be
14·12·12^5 = 4.18×10^7, matching the description's 4.2×10^7; the multiset count is 4.77×10^6.

Step 3, lattice. `Coset.cut` intersects a coset with one congruence αb + βc ≡ r (mod m) by a
unimodular change of basis (exact; Lagrange-reduced). Unit test: 300 random systems of 1–5
congruences with moduli ≤ 30, compared with brute force on a box (membership), plus the basis and
representative are checked against the system and the index against the solution density
(`python3 lattice.py`). The ℓ-primary prefilter was re-derived (a subgroup H of a finite abelian group
is ⊕ of its ℓ-parts and π_ℓ(H) = H_ℓ, so r ∈ im φ iff π_ℓ(r) ∈ im φ_ℓ for every ℓ) and implemented
with numpy lookup tables; every prefilter survivor is recomputed exactly (assert non-empty), and
~2000 prefilter rejects per multiset are sampled and verified empty by the exact lattice. No
disagreement in any run.

Step 4, lifting. n and each unpinned (d, r) lift to r or r + L; identical pairs are lifted as a
multiset (k + 1 choices rather than 2^k). Pinned digits (exact positions from steps 5/6) do not lift.

Step 5, pinning. K* computed as in the description (basis test mod 5^K and mod 2^{K−a}); Y is
computed from the representative and *asserted equal* at v + β⁽¹⁾ and v + β⁽²⁾. *Choices:* (i) the
n ≤ K* branch takes n = number of digits of Y and requires n ≡ n₀ (mod L); (ii) in the n > K* branch
each non-1 tail digit at position i must be matched injectively to an unpinned pair (d, i mod L),
which is then pinned (consumed); a zero tail digit or an unmatched digit kills.

Step 6, descent. As in `LEMMAS.md`: t = v₂(9Y − 10^{K*}); if t = a the pattern is OPEN (silent);
else enumerate m ∈ [K*, t]: either n = m (requires m ≡ n₀ mod L, m > K*, no unplaced digit; y is
then exact and is verified) or a digit d with pattern residue ≡ m (mod L) sits at m; the extended
tail Y' (ones at K*..m−1, d at m) cuts the coset via 2^a3^b7^c ≡ Y' (mod 10^{m+1}) (5-part: one
congruence mod 4·5^m; 2-part: divisibility only if m+1 ≤ a, else a parity congruence and one mod
2^{m+1−a−2}), then recurse. OPEN sub-patterns (with their cut cosets and pinned digits) are what gets
lifted to the next level. *Choice:* the description's "each inherits the coset" does not say whether
the level coset or the descent-cut coset is inherited; I inherit the cut one (sound, since the cut
encodes the case assumptions that define the sub-pattern).

Step 7. A multiset is closed when no pattern is OPEN after level 96 (or earlier if none is left).
Children are only credited when recovered under a pattern they actually match (a, n mod L, residues,
pinned positions, coset membership); a genuine child hit from an unrelated pattern is logged as
"stray" and not credited (it happened for 162 under vertex 12 and 432 under vertex 24 — both were
also recovered under their own pattern).

## 2. Results on the seven vertices (`tier0_results.json`, `tier0_log.txt`)

Columns: A = 2-adic bound; L12 = patterns / non-empty cosets / still open after step 5+6;
later levels = lifted / non-empty / open.

| s | multiset | A | L12 | L24 | L48 | children | status | max K* |
|---|---|---|---|---|---|---|---|---|
| 4 | {4} | 2 | 432 / 3 / 0 | | | 14 | closed | 3 |
| 4 | {2,2} | 6 | 6552 / 14 / 0 | | | | closed | 3 |
| 14 | {2,7} | 6 | 12096 / 37 / 0 | | | 27, 72 | closed | 3 |
| 27 | {3,9} | 0 | 1728 / 5 / 0 | | | | closed | 3 |
| 27 | {3,3,3} | 0 | 4368 / 5 / 0 | | | | closed | 3 |
| 72 | {8,9} | 3 | 6912 / 15 / 1 | 2 / 1 / 0 | | 98, 189 | closed | 4 |
| 72 | {2,4,9} | 16 | 352512 / 542 / 1 | 2 / 1 / 0 | | 294 | closed | 4 |
| 72 | {2,6,6} | 12 | 146016 / 208 / 0 | | | 1161216 | closed | 5 |
| 72 | {3,3,8} | 3 | 44928 / 65 / 0 | | | | closed | 3 |
| 72 | {3,4,6} | 9 | 207360 / 289 / 0 | | | | closed | 3 |
| 72 | {2,2,2,9} | 15 | 838656 / 1426 / 0 | | | | closed | 4 |
| 72 | {2,2,3,6} | 14 | 2021760 / 3677 / 5 | 76 / 1 / 0 | | | closed | 4 |
| 72 | {2,3,3,4} | 16 | 2291328 / 4101 / 1 | 4 / 1 / 0 | | | closed | 4 |
| 72 | {2,2,2,3,3} | 13 | 4769856 / 7905 / 2 | 12 / 1 / 1 | 8 / 1 / 0 | | closed | 8 |
| 98 | {2,7,7} | 8 | 101088 / 153 / 0 | | | | closed | 3 |
| 189 | {3,7,9} | 0 | 20736 / 39 / 0 | | | | closed | 3 |
| 189 | {3,3,3,7} | 0 | 52416 / 93 / 0 | | | | closed | 3 |
| 294 | {6,7,7} | 9 | 112320 / 235 / 1 | 6 / 0 / 0 | | | closed | 3 |
| 294 | {2,3,7,7} | 13 | 1886976 / 2988 / 1 | 16 / 0 / 0 | | | closed | 3 |

Wall time: all seven vertices in about 6 s total on one core (vertex 72: 4 s). No multiset came
near the 30-minute limit. The description's 17 minutes for vertex 72 is a cost of enumerating
ordered arrangements and resolving each pattern individually; it is not evidence of anything.

The known child 1161216 = 2^11·3^4·7 is recovered by the descent exactly as the description says:
at level 12 its pattern has K* = 5, Y = 61216, t = v₂(9·61216 − 10^5) = 7 ≠ a = 11, so the next event
lies in [5, 7]; the case "n = m = 7" gives y = 1161216 exactly, and the cases m = 5, 6 die.

## 3. Positive controls (`controls.py`, `controls_log.txt`, `controls_results.json`)

Beyond the seven vertices I ran the engine on every vertex s = 2^α3^β7^γ with α+β+γ ≤ 7 that has a
known child with ≥ 4 digits (37 vertices; the known children come from my own enumeration of all
zero-free elements of S below 10^40). Invariant checked: **the engine never declares a multiset
closed while missing one of its known children**, and every known child whose multiset is closed is
recovered under its own pattern. At the time of writing 30 of the 37 vertices had finished
(6, 8, 12, 18, 24, 42, 48, 54, 96, 108, 112, 126, 128, 144, 162, 168, 192, 216, 224, 288, 336, 432,
648, 756, 784, 972, 1008, 1176, 1372, 1458; plus 2646 in an earlier run): 103 known children covered,
92 recovered exactly under their own pattern, 11 left in OPEN multisets, **0 violations**
(`python3 check_controls.py` re-checks this from `controls_log.txt`; the remaining q = 7 vertices
keep appending to that log). The known children that are *not* recovered
(e.g. 111132 under 6, 177147 = 3^11 under 1372, 122472 under 224, 214326 under 288) all sit in
multisets the engine leaves OPEN: in each case a < K* so step 6 is silent, exactly as the addendum
says for its 27 open patterns. This is consistent with the authors' account and is not a defect of
the theorem about the seven Tier-0 vertices.

This control caught a real bug in *my* first implementation (the new digit's contribution to the
extended tail was (d−1)·10^m instead of d·10^m), which had made vertex 8 "closed" while missing
14112. After the fix all controls pass. The authors' own report of a defect in the "n = m" case is
exactly the kind of error this control detects; both show that the positive control is load-bearing
and should be run on every vertex, not only the seven.

## 4. Brute force (`brute.py`, `brute_results.json`)

(a) Every y of each equation's shape (digits exactly M plus ones) with ≤ 24 digits, tested directly
for membership in S: 4.5 million numbers for vertex 72 alone. (b) Independently, all 2^a3^b7^c
below 10^60 (so ≤ 60 digits), grouped by digit product. Both give exactly the expected table:
4 → {14}; 14 → {27, 72}; 27 → ∅; 72 → {98, 189, 294, 1161216}; 98, 189, 294 → ∅. They agree with
`known_children_A4.json` and with my engine's output.

## 5. Findings

1. **Both lemmas hold.** Proofs in `LEMMAS.md`. No missing hypothesis makes either false. Two
   implicit hypotheses: the coset must be the exact solution set (so the lattice step must be exact
   and discrete logs verified — the description does say this), and step 6 needs n ≥ K* (handled
   by the exact n ≤ K* branch).
2. **Step 6 is silent whenever a < K*** (t = a automatically), and an active descent always ends in
   silence once the known tail is longer than a, so step 6 never closes a pattern on its own; closure
   comes from the tail test, an empty coset, or an exact candidate. The sentence "This resolved every
   pattern that plain lifting left open" is true for these seven vertices but is not a property of the
   lemma. The addendum's open patterns are the general case.
3. **Description imprecisions (not errors):** "two linear congruences" for the tail cut is really
   one mod 4·5^{K−1}, one parity, one mod 2^{K−a−2}, and the 2-adic one must be applied to Y'/2^a
   mod 2^{K−a} (nothing at all if K ≤ a). The extended-tail digit contributes d·10^m. The n = m case
   must be enumerated. Which digits may sit at m is constrained by the residue pattern.
4. **Final level for vertex 4:** mine 12, theirs 24. My step-5 tail test (consume matched digits,
   kill on unmatched residue class, exact-candidate branch) closes both multisets of 4 at level 12;
   their table says they needed level 24. Not a contradiction, but it means their step 5 is weaker
   than my reading of the description, or the descent was not applied at level 12.
5. **Pattern counts in their table are for ordered arrangements** (4.2×10^7 = 14·12·12^5 for
   {2,2,2,3,3}); the addendum's switch to multisets reduces this to 4.8×10^6 as I observe.
6. **K* saturates** (max 8 in all runs; typically 3–5 even at level 96 with coset index ~10^56),
   consistent with their "K* stuck at 5". Consequence: for vertices outside Tier 0 the method cannot
   recover long children exactly unless a ≥ K*; the addendum's Babai-rounding argument is what
   handles those, and it was not part of this audit.
7. **Prefilter/lattice equivalence** verified on every survivor (assert) and on ~2000 sampled rejects
   per multiset; **discrete logs** all verified by re-exponentiation; **lattice** unit-tested against
   brute force on 300 random systems; **Y constancy** on the coset asserted at every pinning.
8. The 2-adic bound of step 1 is loose for large multisets (finding in §1) — harmless, cost only.
9. Nothing about the Corollary (persistence) was checked beyond noting its chain argument is
   consistent with the child table.

## 6. Reproduce

```
cd /home/claude/audit_out
python3 lattice.py                 # lattice self-test vs brute force (300 systems)
python3 dlog.py                    # discrete logs on all 20 primes + 5-adic/2-adic groups
python3 run_tier0.py               # seven vertices -> tier0_results.json, tier0_log.txt  (~6 s)
python3 brute.py 24                # task 4 -> brute_results.json                        (~12 s)
python3 controls.py $(cat control_vertices.txt) > controls_log.txt   # positive controls (long)
python3 check_controls.py          # verify the control invariant from the log
python3 trace.py 1161216 14112     # trace a known child through level 12 (coset, K*, Y, descent)
python3 trace2.py 111132 177147    # trace a child through all four levels
```
