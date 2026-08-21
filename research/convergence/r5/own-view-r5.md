# Own view, round 5 (written before any seat file was opened)

Plan under review: `plan-r4.md`. Five weaknesses, ranked by what a fresh implementer would be unable to build or would build two ways.

## 1. The in-sample model-fit predicate is undefined (§6 steps 2, 2c; §13 M1 fixture (a)) — MED

§6 (2c) makes "an in-sample ... miss of the pre-registered model" a REJECT predicate and "model fits in sample" a KEEP_IN_SAMPLE condition, and M1 fixture (a) is caught by exactly this predicate ("the catch is the in-sample model-miss REJECT"). The out-of-sample check has an explicit band (`1 ± 2·√(radius² + (sd₆₀/(mean₆₀·√m))²)`); the in-sample check has none. Step (2) says "the sorted-distribution shape compared to the claimed model" without a statistic, a fit method for the declared free parameters, or a tolerance. An implementer must invent what "fits" means at 30/40/50 bits, and two implementers will invent different things. The ladder plan lists "tolerances of step (3)" but no step-(2) tolerance. The fix is a per-rung band of the same form as the 60-bit one (each ≤ 50-bit rung's measured mean inside `1 ± 2·√(radius² + (sd_s/(mean_s·√n))²)` of the model's prediction after the declared free parameters are fit on those rungs), named in the ladder plan, so that fixture (a) is decidable as written.

## 2. The Tier-3 ticket contradicts the "+1" rule, and a ladder table has no tier (§5, §6 2c) — MED

§5 refuses a launch "when the declared tier exceeds the ticket's tier by more than one" and says "each tier's admission ticket is a result from the tier below". §6 (2c) says KEEP "is the ticket for ... any Tier-3 request built on the claim", and §5's lattice says "Tier 3 adds the justification, certificate plan and sign-off". A KEEP table's rungs ran at Tier 1 (≤ 50 bits) and the 60-bit rung "is tiered by its declared profile" — Tier 1 compiled, Tier 2 interpreted. The plan never defines the tier of a multi-rung table node, so whether a Tier-3 request holding KEEP is refused by the +1 rule depends on whether the 60-bit rung happened to run compiled. Either the ticket for Tier 3 is a Tier-2 result (which kind? undefined for an algorithmic claim) with KEEP checked transitively, or the +1 rule is stated against a defined table tier. Resolve one way.

## 3. The retry predicate of a `measured` REFUTED entry has no author and no default (§4, §6 5, §7) — MED

Every REFUTED entry carries a `retry predicate`; the `implementation` kind's predicate is defined (a certified new revision); `formal` is permanent by nature. A ladder REJECT "moves the claim version to terminal status refuted" and writes a measured entry — but the plan never says who writes its retry predicate or what it says. The preflight's `Blocked`/`Allowed` answer turns entirely on this field, so M2's fixture "a refuted hypothesis key is Blocked unaided" is not buildable without a rule. The null-control path already names the one gate-owned way a measured entry is re-opened (a gate-owned re-measurement under the current ladder plan returning a verdict other than REJECT); the default predicate for a measured entry should be exactly that, written by the gate that produced the table, with the worker never authoring it.

## 4. The per-rung memory cap is the BSGS table at that size, which is 2¹⁵ entries at 30 bits (§6 step 2, step 4) — LOW/MED

The cap is "fixed in the ladder plan as the BSGS table for that size (≈ 1 GB at 50 bits)" and "every rung must pass". At 30 bits BSGS holds 2¹⁵ ≈ 3×10⁴ entries; at 40 bits 2²⁰. A method with an honest, pre-registered constant memory model of, say, 2²⁰ entries (precomputation-style methods are a real class) is REJECTed at the 30-bit rung by "memory cap exceeded" though its memory model holds at every rung and it is under the cap at 50 and 60 bits. The cap exists to refuse a method that spends BSGS-scale memory at the size where that matters (the 50-bit floor); at the small rungs the memory-model check carries the anti-fabrication load. A floor on the cap (the ladder plan's, e.g. the 40-bit table) or applying the BSGS cap at the 50/60-bit rungs only would remove a false REJECT of an honest memory model without weakening the 50-bit floor.

## 5. Two wording gaps a gate author would trip on — LOW

(a) §5's ticket is "the most recent admissible substrate node of the kind the tier requires"; for Tier 2 the kind is "a ladder result table with verdict KEEP". If the verdict is part of the kind, a later INCONCLUSIVE or REJECT table on the same key does not displace an older KEEP ticket; the intent (a REJECT refutes the branch) is reachable only through §7's terminal status, which the tier gate does not read. State that "most recent" ranges over all ladder tables for the key and the verdict rule is then applied. (b) §8 says a flagged attack holds "no ticket above Tier 1 until the declaration exists"; §5 says Tier 1's own ticket requires "the §8 presence check passed". Both are right but read together they suggest a flagged attack may run Tier 1 — say in §8 that an absent declaration is no Tier-1 ticket either, and `accept_for_tiering` is what opens tiers above 1.

## Not listed (considered and judged minor or handled)

- Escrow reservation/release has no fixture in any done-when (M0 schema builds it; nothing exercises release) — LOW, process-light to add to M1.
- M2 fixture "a proposal differing from a REFUTED entry only in implementation revision is Blocked" is true for `measured` and `formal` entries, not for `implementation` entries — say "measured".
- A KEEP ticket recorded under an older gate-bundle pin (older baseline revision) stays a ticket; spend-only exposure, not a truth leak.
