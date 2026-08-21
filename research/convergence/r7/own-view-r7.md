# Own view — guard round 7 (written before opening any seat file)

Plan read: plan-r6.md in full (1592 lines). Bar: demonstrable defects only.

1. **Waiver storage is stated two ways (§4).** The gate-bundle list names "the waiver
   registry" as a field of the content-addressed bundle "whose hash is pinned at deployment";
   the human-path paragraph says a waiver "enters the system through one route" — the
   operator-owned attestation file mirrored as a substrate row, read by "the waiver check".
   A runtime-issued waiver cannot live in a pinned bundle without a re-pin, so one of the two
   is wrong. Likely fix: the bundle holds the *waivable-check set* (policy); waivers are
   attestation records. Severity LOW (wording; the human-path mechanism already governs).

2. **Human-queue close rule has no clause for advisory classes (§10 vs §6/§4/§7/§15).**
   "An item closes only by a human-path record (§4) or by its blocker clearing", yet
   `clock_inconclusive`, `shape_departure`, `cost_drift`, `audit_shortfall`, `leaked` park no
   branch and no human-path record kind closes them. As written they never close, and queue
   depth/age is a drift-monitor input. Fix: advisory items close when the condition that
   raised them is superseded (a later verdict on the rung, an audit record at target, the
   leaked obligation reaching a terminal status, the alarm clearing) or by an attributed
   acknowledgment through the human path. Severity LOW–MED.

3. **Clock-tolerance inequality is checked at plan load against a run-measured radius
   (§6 (3)).** "the ladder plan's clock tolerance times that ratio must stay below the KEEP
   band's excess over 1 (`2·radius`...) — a plan failing that inequality refuses to start"
   — but `radius` is the A/A arm's measured CI radius, known only after the rung runs. The
   moment and the operand must be named: at plan load against the radius the plan's trial
   count and sd assumption imply; per rung against the measured radius, a failing rung being
   INCONCLUSIVE. Severity LOW–MED.

4. **Tier-gate refusal list omits the ≤ 50-bit ladder-rung exception (§5).** "refused ...
   when the declared tier is lower than the tier the bundle's boundary table assigns its
   production cost" versus "The ladder's distribution rungs (§6, ≤ 50 bits) are Tier-1 —
   admitted on the Tier-1 ticket whatever tier the boundary table would assign". A fresh
   implementer of the predicate paragraph refuses the rung. Severity LOW (cross-reference).

5. **Tier-gate gaming residual: sharding across minted keys.** The cumulative edge is per
   hypothesis key; jittered-region objects on one method are `Allowed` by the preflight
   (the sub-region rule applies to promoted holders only), so a Tier-2-scale computation
   sharded across many keys never crosses any edge. Purpose defeated in compute only: no
   KEEP ⇒ no STRONG-EMPIRICAL, no ticket; bound is the orchestrator's total grant and the M3
   junk-family bar. Candidate for open question rather than a new mechanism.

Also noted (lesser): a Tier-2 formalization run refused for want of a `review_verdict` has no
stated route to a `statement_review` queue item (M2's workflow routes *green* artifacts; the
Tier-2 path needs the review before green); §3 "entropy commitment for that rung" vs §6
"nonce per run" wording.
