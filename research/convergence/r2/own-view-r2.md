# Own view, round 2 (written before opening any seat file)

Plan under review: `plan-r1.md` (v3). Five weaknesses a fresh implementer would hit, in
the order I would fix them.

1. **§5 / §6 — the Tier-2 ticket for the 60-bit rung is circular.** §5 says the Tier-2
   ticket for an algorithmic claim is "a ladder result table with verdict KEEP"; §6 (2b)
   says the 60-bit rung is Tier-2 by its declared profile and that the verdict is REJECT
   when the in-sample fit misses out of sample — so KEEP is defined to need the 60-bit
   rung, and the 60-bit rung needs a KEEP table to be admitted. The ≤ 50-bit table has
   no named verdict of its own. Fix: a typed ladder verdict with a distinct in-sample
   value (e.g. `KEEP_IN_SAMPLE`) that is the ticket for the 60-bit rung and for nothing
   else; final `KEEP` requires the out-of-sample rung and is the ticket for every other
   Tier-2 launch. Severity MED (a gate predicate a fresh implementer cannot build as
   written; not a weakening of the ladder).

2. **§13 M1 — "no matched true advance is rejected" names no positive fixture.** The
   planted corpus (a)–(i) is all negatives. Random prime-order ladder curves admit no
   structural attack, so the positive control must be one that beats plain rho on the
   ladder's own terms: rho with the negation map (≈ √2 fewer group operations, same
   memory) is a known-answer positive fixture the KEEP band must pass at 10² trials.
   Without a named positive the M1 bar is one-sided and a gate that rejects everything
   passes it. Severity MED.

3. **§7 / §13 — `justify` is in the M0 schema but the evidence node it reads has no
   typed shape.** The max-class map is given (green Lean → PROVEN, ladder + repro →
   STRONG-EMPIRICAL, …) but not the record `justify` inspects: evidence kind, target
   statement hash, declared population / assumptions / model, producer's own tag, and
   the lattice order it returns a violation from. An M0 implementer cannot write
   `justify` from the plan. Severity MED (self-containment).

4. **§13 M0 — the tier gate and the gate-bundle pin are built at M0 but no "done when"
   exercises them.** The M0 done-when tests the verifier (positive, two negatives,
   forced crash) and substrate hashing, but no `TierRefused` record is produced and no
   bundle-hash mismatch is shown to fail closed. Two mechanisms at M0 have no
   demonstrable property (rule 10b orphan test at the milestone level). Severity MED.

5. **§6 — the gate-owned instance-maker's hidden entropy is asserted, not constructed.**
   "Entropy the worker never sees before committing its method" needs a seed derivation
   an implementer can write: a gate-side nonce drawn after the method's content address
   is recorded, per-trial seed = H(nonce ‖ method hash ‖ size ‖ trial index), nonce and
   seeds recorded in the result table so every trial replays afterward. The §13 exemplar
   `toy_curve(bits, seed)` takes a seed, so the seam is exactly one line. Severity
   LOW–MED.

Also noted, lower priority: §3 recipe key names a `container-digest` but the M0 build
machine runs no container (the §7 macOS fallback is development-only), so the key needs
a defined value for "no container" (toolchain manifest digest under its own tag);
§7's spot-check bound at `f = 0.01, bits = 20` is `l ≈ 1.4 × 10³` per stratum, which
exceeds any plausible Tier-2/3 population, so that stratum is audited exhaustively and
the plan should say so rather than let the formula be applied blind.
