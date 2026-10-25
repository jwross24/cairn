# Tier C induction on size: prediction, written before any computation (2026-10-24)

Scope of the claim being predicted: the three induction shapes of the lane brief (a nesting, b descent, c strong
induction on n with the corpus base) each fail at a named step, with a measured shortfall above 10^10, so the kill
criterion fires. Reading done before this file: LOOP-PROTOCOL.md, theta/NOTES.md, codex-theta-attempt.md,
CONDITIONAL.md (first 200 lines), HYPOTHESES.md 125-245, theta_07_sunit_census.py and out_07_300.txt, the head of
zf_below_1e4000.txt (columns: digits, a, b, c, tag; 8,807 rows). No arithmetic on S-units has been run in this lane.

## Paper predictions (to be checked by derivation, then by data)

PP1. Shape (b) is circular: for every prefix with s_j + g_j above the Baker separation length G*, the S-unit that
witnesses the exceptional prefix is the candidate M = 9y itself. Any witness M' different from M has
|M/(10^e M') - 1| >= exp(-C(4) log B) by Matveev, so it cannot lie within the candidate's own distance. No smaller
configuration is produced. Predicted G* for log10 B in [281, 402]: between 10^13 and 10^17 digits.

PP2. Shape (a) nests the same box. The prefix N_(j-1) is exceptional exactly when s_j exceeds about 4 log10 B, with
the same exponent box B. Nothing shrinks B, so the base case (corpus or census) is never reached by the step.

PP3. Shape (c) has no step: no map takes a size-n child to a smaller instance, so "no child below N" is never an
input to an upper bound on n. If a step with the Matveev/Yu multiplier per block existed, the iteration count from
the 6,885-digit corpus to log10 U is 17 at k = 31 (log10 U = 281.5) and 22 at k = 44 (402.1).

PP4. The per-prefix enumeration form (induction on the number of verified blocks j0, base case computed by
lattice reduction) costs about 10^4.1 lattice reductions per level and gains about 10^16.7 to 10^18.2 per level;
closing to the corpus needs j0 close to k, so the cost is above 10^100 against a budget near 10^12.

## Data predictions (falsifiable, on data not yet looked at)

DP1. Census of all 37,375,388 S-units 2^a 3^b 7^c below 10^300: the longest run of zeros in any decimal expansion
is between 8 and 11, and no run of 12 or more exists (the exceptional threshold 4 log10 B is about 11 at B = 2.1n+2).
Kill: any zero run of 12 or more.

DP2. Leading-digit divergence: among distinct census S-units, the longest common leading prefix is between 14 and 17
digits (birthday bound near 15), and no two share 18 leading digits. T10's bound of about 10^13.9 digits is therefore
looser than the census by about 10^12.7 or more. Kill: any pair sharing 20 or more leading digits.

DP3. Witness uniqueness: for every census zero run (s, g) with s+g >= 16, no other census S-unit shares the leading
s+g digits (up to 18). Shape (b) therefore has no non-trivial instance in the data. Kill: a counterexample pair.

DP4. Nesting does not transmit: among zero-free corpus children with at least 3 non-1 digits, the gaps g_(j-1) and
g_j (runs of 1s between non-1 digits) have Spearman correlation below 0.3 in absolute value, and the ratio
(s_j + g_j)/s_j has no bound that is independent of s_j: its maximum over children occurs at the smallest s_j.
Kill: correlation above 0.5.

DP5. The empirical per-block multiplier (s_j + g_j)/s_j over the census runs of g >= 4 is below 10^1.3 for s_j >= 3,
so the multiplier that depth 1 needs (10^1.3 to 10^2.6) holds on data with room to spare, while Matveev/Yu give
10^16.7 to 10^18.2. The gap is a proof gap, not a truth gap.

## Verdict predicted

Every shape fails at a named step with shortfall at least 10^14 (per-block constants) or 10^56 (enumeration cost).
Kill criterion fires: negative result, "do not retry without new data". Missing ingredient: an effective statement
that a decimal prefix of s digits with few non-zero digits is not approximated by a {2,3,5,7}-unit to better than
10^(-C s^theta) with theta < 1 (the theta lane's open item), or a map from a large child to a smaller instance.
