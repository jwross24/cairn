# Registered prediction (written 2026-10-20 21:00 EDT, before any differential run)

P1. On every open pattern (vertex, multiset, 2-adic exponent a, anchor y, recorded (nu, eps) when present) in
runall_final.jsonl, trees_c.jsonl and trees_mac.jsonl as they stand now, the per-anchor method returns the same
CLOSED / OPEN verdict as tier0/deepcut.py at depth 1 (D = 1), per representation and per pattern. Disagreements: 0.

P2. The depth-1 verdict of an anchor (y, a) depends on a case only through L mod (5^5 * 2^(a+9)); the exact
acceptance test is L == y (mod 5^5 * 2^(a+9)), i.e. the image of Lambda_96 in (Z/5^96)^* x (Z/2^(96-a))^* is the
full kernel of reduction mod 5^5 and mod 2^9 (after dividing out 2^a).

P3. Planted genuine S-units (placed as patterns on a shared anchor, at the anchor's own coset point) are never
killed: 0 false kills.

P4. Per-anchor time is at most 100x the per-pattern time of deepcut (the HYPOTHESES.md bound). Expected far
below: per-pattern cost at least 100x lower than deepcut's, because no discrete logarithm is evaluated.
