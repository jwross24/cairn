# Review of plan-r0.md

## 1. Ladder trial count contradicts its own tier budget at 60 bits · HIGH · §6

**Component:** the small-scale ladder (§6), compute tiers (§5).

**Cost:** one sentence of clarification; no new mechanism.

**Evidence:** The plan states Tier-1 is "one core, minutes" and "the ladder is Tier-1." It also mandates "at least 10² independent trials per size." At 60 bits, a single rho run is ~1.25√n ≈ 1.3×10⁹ group ops. In PARI, group ops on a 60-bit curve run at roughly 10⁵–10⁶/sec, so one trial is ~10³–10⁴ seconds. One hundred trials is ~30–300 core-hours. That is Tier-2 ("many cores, hours"), not Tier-1. The plan's own §5 says "Fail here → never see another core," implying the ladder is the Tier-1 gate, but the 60-bit bar as written cannot be met at Tier-1. STRONG-EMPIRICAL (arithmetic: √(2⁶⁰) ≈ 1.15×10⁹; PARI benchmark range is well-established).

**Rationale:** A fresh implementer reading §6 will either (a) run 100 trials at 60 bits, blow the Tier-1 budget, and conclude the system is broken, or (b) skip the 60-bit bar and lose the completion check that catches methods that scale on paper but don't finish. The fix: the 10²-trial distribution gate applies at sizes where distribution comparison is the decision (30–50 bits); at 60 bits the gate is completion + a single ballpark ops count, because the point at 60 bits is "it finishes and is in the right order of magnitude," not "we have a distribution fit."

```diff
--- a/plan-r0.md (§6, point 2)
+++ b/plan-r0.md
- (2) It gates on distributions, not runs: at least 10² independent trials per size (for
- rho the standard deviation is ≈0.5× the mean, so a single run calibrates nothing), the
- sorted-distribution shape compared to the claimed model, and an A/A null arm whose CI
- radius sets the decision band (a speedup is KEPT only if the whole claim CI clears
- `1 + 2·radius`, floor 1%; otherwise INCONCLUSIVE or REJECT).
+ (2) It gates on distributions, not runs: at least 10² independent trials at 30/40/50
+ bits (for rho the standard deviation is ≈0.5× the mean, so a single run calibrates
+ nothing), the sorted-distribution shape compared to the claimed model, and an A/A null
+ arm whose CI radius sets the decision band (a speedup is KEPT only if the whole claim
+ CI clears `1 + 2·radius`, floor 1%; otherwise INCONCLUSIVE or REJECT). At 60 bits the
+ gate is completion (the method must finish) plus a single measured ops count in the
+ claimed ballpark — 10² trials at 60 bits is Tier-2 compute, not Tier-1, and the
+ distribution gate has already done its work at 50 bits.
```

## 2. M0 done-when doesn't exercise the verifier end-to-end · HIGH · §13

**Component:** M0 milestone, Tier-0 verifier (§4, §13).

**Cost:** extends M0 done-when by one step; no new component.

**Evidence:** M0 lists "Tier-0 verifier" as a deliverable but the done-when says only "it runs one skill on a 40-bit toy curve end to end, and the result is a hashed, self-tested, cost-tagged substrate node." The exemplar skill `toy_curve` generates a curve; it does not solve or verify a DLP. The verifier (`xP == Q`) is the load-bearing gate, and M0 is where "get it right once" is supposed to happen. If M0 doesn't close the loop — generate curve, pick x, compute Q = xP, verify xP == Q, store the verified node — then the verifier is untested at M0 and the first real exercise is M1, where it's needed to catch planted-false advances. PROVEN-in-source (the plan's own §13 lists the verifier as an M0 deliverable but omits it from the done-when).

**Rationale:** M0's purpose is to prove the substrate shape works end-to-end. "End-to-end" for a DLP harness must include the verifier, or the shape is missing its most important vertex.

```diff
--- a/plan-r0.md (§13, M0)
- *Done when:* it runs one skill on a 40-bit toy curve end to end, and the
- result is a hashed, self-tested, cost-tagged substrate node. Everything else plugs into
- this shape — get it right once.
+ *Done when:* it runs one skill on a 40-bit toy curve end to end, **then closes the
+ loop**: picks a random `x`, computes `Q = xP` via the same skill or a second skill,
+ runs the Tier-0 verifier (`xP == Q`), and stores the verified pair as a hashed,
+ self-tested, cost-tagged substrate node. Everything else plugs into this shape —
+ get it right once, including the verifier.
```

## 3. No-go checklist is a declaration tripwire, not a mechanical gate — acknowledge this · MED · §8

**Component:** no-go checklist (§8), gate layer (§4).

**Cost:** one clarifying sentence; no new mechanism.

**Evidence:** §4 lists the no-go checklist among "Gate layer (mechanical, immutable)." §8 says "must state how it evades all three or be flagged." The mechanical part is presence-of-declaration (did the worker fill out the form?); the content — "does this attack actually exploit curve-specific structure?" — is not mechanically checkable and is left to the Librarian/Skeptic. Calling it "mechanical" when half of it is a declaration risks the same name-vs-mechanism gap §7 warns about for statistical monitors. CONJECTURE (the three obstructions are PROVEN-in-source; the claim that the checklist as implemented is only a declaration is a design observation).

**Rationale:** §7 explicitly warns that "a name promising more than the mechanism delivered, then read as permission" is the documented failure mode for statistical gates. The same risk applies here: calling the checklist "mechanical" when its content verification is delegated to workers could let a worker's self-declaration pass as gate enforcement. The fix is to name the two layers honestly: the presence check is mechanical; the content is verified by the Librarian and Skeptic, not by the gate itself.

```diff
--- a/plan-r0.md (§8)
- Any proposed attack on the target must state how it evades all three or be flagged
- almost-certainly-broken:
+ Any proposed attack on the target must state how it evades all three or be flagged
+ almost-certainly-broken. The gate is mechanical only in the presence dimension (a
+ missing or empty declaration is an automatic flag); the *content* — whether the
+ stated evasion actually holds — is verified by the Librarian and Skeptic, not by
+ this gate alone:
```

## 4. Foundations auditor sampling should be tier-aware · MED · §7

**Component:** standing foundations-auditor (§7).

**Cost:** one clause; no new component.

**Evidence:** The auditor's sampling bound `l ≥ ln(2^bits)/ln(1/(1−f))` is correct for uniform sampling (PROVEN-in-source, standard concentration bound). But re-verifying a substrate node means re-running its recipe. A Tier-0 node costs milliseconds; a Tier-2 node costs hours. Uniform sampling across all nodes spends most of its budget re-running cheap nodes and may never touch the expensive ones that carry the most downstream weight. STRONG-EMPIRICAL (the cost differential between tiers is stated in §5).

**Rationale:** The auditor's value is catching rot in load-bearing premises. A Tier-2 node that 50 downstream claims depend on is higher-value to re-verify than a Tier-0 leaf nobody cites. The sampling should weight by tier (sample lower tiers more frequently because it's cheap) and by dependency fan-in (