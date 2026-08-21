## 1. Break the Tier-2 ladder admission circularity  
**Severity:** HIGH  
**Section:** §§5–6, §13 M1  
**Component improved:** Tier gate / small-scale ladder admission contract.

**Rationale:**  
The current plan makes a Tier-2 algorithmic launch require a Tier-1 ladder artifact with `verdict KEEP` (§5). But the ladder artifact’s `KEEP` verdict includes the 60-bit completion-and-extrapolation rung (§6), and that rung is explicitly Tier-2 work requiring tier-gate approval. Therefore the system needs a Tier-2 ticket before it can generate the Tier-2 evidence required for that ticket.

This is not merely implementation ambiguity: a strict implementation correctly refuses every 60-bit ladder launch. The fix is to distinguish:

1. a **Tier-2 validation admission ticket**, earned from the ≤50-bit ladder; from  
2. a **Tier-2 research ticket**, earned only after the 60-bit hold-out result passes.

This preserves cheap-before-expensive. It permits only the narrowly scoped 60-bit validation run—not arbitrary Tier-2 research—before the full KEEP result exists.

**Cost / failure surface:** One additional ticket type and a narrow-purpose constraint in the tier gate. The main failure risk is accidentally using validation admission as general Tier-2 authorization; prevent this mechanically with an allowed-purpose field.

**Evidence:** **PROVEN-in-source** as a dependency-graph correction: the current stated predicates form a cycle. The relevant mechanism evidence is the existing tier/ladder material in `research/PROPOSALS.md`; this revision does not add a research claim.

**Invariant check:** Does not alter gates, permit strategy to edit truth, or weaken calibration. It makes the existing tier gate executable.

```diff
diff --git a/plan-r1.md b/plan-r1.md
@@ §5 Tier gate predicate
- for Tier 2 on an algorithmic claim the ticket is a ladder result table with
- verdict KEEP (§6)
+ for Tier 2 on an algorithmic claim there are two distinct admission modes:
+ (a) `ladder_validation_60`: a narrowly scoped Tier-2 launch whose only permitted
+ purpose is the gate-owned 60-bit hold-out rung; its ticket is an admissible ≤50-bit
+ ladder table with a pre-registered model, completed A/A null arm, successful recovery
+ on every completed trial, and a provisional verdict `ELIGIBLE_FOR_HOLDOUT`; and
+ (b) `algorithmic_research`: any other Tier-2 algorithmic launch; its ticket is the
+ complete ladder artifact with verdict KEEP, including the 60-bit hold-out result.
+ The ticket records its permitted purpose, and the tier gate rejects a skill launch
+ whose declared purpose is not exactly that purpose.

@@ §6 Protocol (2b)
- The 60-bit rung is the completion-and-extrapolation rung...
+ The 60-bit rung is the completion-and-extrapolation rung. It may be launched only
+ under the `ladder_validation_60` admission mode of §5; that admission authorizes no
+ other Tier-2 work. The completed 60-bit artifact is then incorporated into the
+ complete ladder table, whose KEEP verdict is required for subsequent Tier-2
+ algorithmic research.

@@ §13 M1 Done when
- Adds the ladder protocol (§6) ...
+ Adds the ladder protocol (§6), including a planted test that a ≤50-bit
+ `ELIGIBLE_FOR_HOLDOUT` ticket authorizes exactly one gate-owned 60-bit hold-out
+ protocol and is rejected for every other Tier-2 skill or parameter sweep ...
```

---

## 2. Do not treat a finite-size loss as an asymptotic refutation  
**Severity:** HIGH  
**Section:** §§4, 6, 11  
**Component improved:** Dead-end ledger / ladder verdict semantics.

**Rationale:**  
The plan correctly says finite sizes do not establish an asymptotic (§6), but then says that an attack unable to beat BSGS at 50 bits “is refuted on the spot.” Those statements conflict for any hypothesis whose declared crossover is above 50 bits, or whose claimed advantage is asymptotic rather than a claimed 50-bit performance result.

A measured ladder run can permanently refute only the exact finite-domain hypothesis that was measured—consistent with §4’s otherwise strong rule that a broader blacklist needs formal evidence. A failed 50-bit performance threshold is valuable negative evidence, but must produce:

- `REFUTED` when the pre-registered hypothesis explicitly predicts passing that threshold at that domain; or
- `REJECT` for the requested promotion / `PARKED` with an explicit crossover or model-validation blocker when it does not.

Otherwise the ledger will incorrectly blacklist hypotheses that the plan itself admits have not been disproved.

**Cost / failure surface:** More precise hypothesis declarations: predicted finite-size performance and crossover must be explicit. This prevents workers from retroactively claiming an unspecified later crossover.

**Evidence:** **PROVEN-in-source** as a logical consequence of the plan’s own distinction between finite measurements and formal/asymptotic claims; see the existing ladder and ledger evidence records in `research/PROPOSALS.md`.

**Invariant check:** Strengthens the permanent-REFUTED boundary; does not weaken the ladder or permit evidence inflation.

```diff
diff --git a/plan-r1.md b/plan-r1.md
@@ §3 Hypothesis key
- {target family, claimed property or cost model (exponent, constant, crossover ...
+ {target family, claimed property or cost model (exponent, constant, declared
+ finite-size predictions and crossover, if any) ...

@@ §4 Ledger preflight
- A measured refutation reaches exactly the hypothesis object it was measured on ...
+ A measured refutation reaches exactly the hypothesis object it was measured on,
+ including its declared finite-size prediction. A failure at size s permanently
+ REFUTES an algorithmic hypothesis only if that hypothesis predicted the failed
+ threshold at s (within its pre-registered decision band). Failure of a hypothesis
+ that declares its crossover above s is evidence against its model fit and blocks
+ promotion, but is not an asymptotic blacklist; it is recorded as REJECT for the
+ requested ticket or PARKED with a model-validation blocker. A broader blacklist
+ needs a formal entry.

@@ §6
- A "subexponential attack" that can't beat baby-step-giant-step at 50 bits is
- refuted on the spot.
+ A method whose pre-registered 50-bit prediction requires beating the stated
+ BSGS floor and fails it is refuted on that measured hypothesis on the spot. A
+ method that did not predict a 50-bit advantage is not thereby asymptotically
+ refuted: it fails to earn a ladder KEEP verdict and must carry an explicit,
+ pre-registered crossover claim for any later reconsideration.

@@ §11 Negative-results map
- "approach X provably fails on prime-field curves, here's why"
+ "approach X provably fails on prime-field curves, here's why," or
+ "the pre-registered finite-domain performance hypothesis H failed on declared
+ family F and sizes S, here's the result"
```

---

## 3. Replace the rho-relative memory band with an explicit Pareto policy  
**Severity:** MED  
**Section:** §6  
**Component improved:** Ladder baseline comparison and acceptance metric.

**Rationale:**  
The current acceptance condition requires an operations speedup over O(1)-memory rho **and** says memory must “stay inside the same band.” Taken literally, any nontrivial-memory method fails regardless of its operations improvement, because rho’s memory baseline is constant. That makes the plan internally inconsistent with its BSGS comparison and with research on explicit time-memory tradeoffs.

The ladder should still reject “faster only by hiding an impractical memory explosion,” but it needs an operational resource policy. Compare work and memory separately, record both, and require declared Pareto improvement under a gate-owned memory budget. A method may qualify if it improves group operations without exceeding a fixed ladder memory cap, or if it improves a declared composite resource budget that is fixed before the run. It must never convert seconds into claimed group-operation gains.

**Cost / failure surface:** Requires a deterministic memory-accounting definition: peak resident memory alone is insufficient for distributed or external-table algorithms. Start at M1 with peak allocated algorithmic table bytes plus explicit spill/storage bytes; report RSS as diagnostic. This slightly broadens testing but prevents accidental exclusion of an important class of methods.

**Evidence:** **STRONG-EMPIRICAL-in-source**—the plan already recognizes BSGS/rho as distinct time-memory baselines; the relevant supporting material should be cited from the ladder/baseline entries in `research/PROPOSALS.md`.

**Invariant check:** Keeps the ladder’s fixed baseline, pre-registration, null control, and stricter-than-self-reporting gate behavior. No statistical score promotes a claim.

```diff
diff --git a/plan-r1.md b/plan-r1.md
@@ §6 Protocol (2)
- a speedup is KEPT only if the whole claim CI clears `1 + 2·radius` (floor 1%) on
- group operations *and* memory stays inside the same band
+ a speedup is KEPT only if the whole claim CI clears `1 + 2·radius` (floor 1%) on
+ group operations and the method satisfies the gate-owned memory policy. The policy
+ is pre-registered in the ladder plan as: (i) a peak algorithmic-storage cap for the
+ rung, and (ii) one of `rho-Pareto` or `declared-resource-budget`. `rho-Pareto`
+ requires lower group operations than rho without exceeding the cap; it does not
+ require O(1) memory. `declared-resource-budget` is permitted only for a claim whose
+ hypothesis pre-registers the work/storage tradeoff and its intended operating
+ regime. A method that exceeds its cap is REJECT regardless of elapsed time.

@@ §6 Protocol (3)
- It reports group operations against `√n`, never seconds.
+ It reports group operations against `√n`, never seconds, and separately reports
+ peak algorithmic table/storage bytes, explicit external spill bytes, and diagnostic
+ RSS. The ladder plan defines how each baseline skill accounts for these quantities;
+ an unaccounted storage channel fails closed.
```

---

## 4. Make the skeptic’s required checklist available without exposing prover artifacts  
**Severity:** MED  
**Section:** §§4, 7  
**Component improved:** Independent-skeptic dispatch contract.

**Rationale:**  
There is a direct operational contradiction. §4 says workers have no gate rubric or detection logic reachable. §7 then says the Skeptic’s rubric includes a required quantifier/domain checklist. A skeptic cannot reliably perform a checklist it cannot see.

The independence requirement is from the **prover’s reasoning and outputs**, not from a fixed, gate-owned review protocol. The dispatch should supply a read-only skeptic-task template containing the statement and the fixed checklist, while continuing to exclude proof artifacts, panel feedback, prior reviews, gate outcomes, and general substrate access. Since the skeptic cannot promote a claim and its result is reviewed under disagreement protocol, this does not create a route to game promotion.

**Cost / failure surface:** One role-specific immutable dispatch template and tests that its closure excludes prohibited artifacts. The principal risk is template drift; pin it in the gate bundle already defined by the plan.

**Evidence:** **PROVEN-in-source** as a direct consistency repair between the plan’s stated required rubric and its worker-isolation model. No new trust mechanism is introduced.

**Invariant check:** Does not let a worker alter a gate; it gives the skeptic only the gate-owned procedure needed to execute its assigned review.

```diff
diff --git a/plan-r1.md b/plan-r1.md
@@ §4 Workers
- in whose context no gate rubric or detection logic is reachable.
+ in whose context no gate rubric or detection logic is reachable, except that a
+ role-specific, gate-owned task template may include the fixed procedure required for
+ that role to perform its review. Such a template is read-only, pinned in the gate
+ bundle, and contains no claim-specific prior outcomes.

@@ §7 Independent skeptic
- sees only the *statement*, never the prover's reasoning
+ sees only the *statement* and the fixed gate-owned skeptic checklist, never the
+ prover's reasoning, proof artifact, prior reviewer output, panel feedback, or gate
+ outcome. The checklist is a pinned dispatch-template artifact in the gate bundle; it
+ is not retrieved from the mutable substrate and cannot be claim-specifically edited.
```

---

## 5. Anchor the append-only log outside the orchestrator’s writable database  
**Severity:** HIGH  
**Section:** §3  
**Component improved:** Substrate history-integrity contract.

**Rationale:**  
A hash chain with compare-and-swap detects alteration of retained records, but it does not by itself detect truncation or rollback when the orchestrator can write the SQLite database. An attacker/process can replace the current head with an earlier valid head and delete later rows; re-verification “from origin” still succeeds. Therefore the statement “an orchestrator that rewrites history produces a log that fails verification” currently overclaims its protection.

Add monotonic, externally durable checkpointing of the chain head. For M0 this can be deliberately simple: a human/operator-controlled signed checkpoint file or append-only remote object store, with the deployment recording the expected prior checkpoint. On startup and before promotion, the gate verifies that the local chain extends the latest anchored head. Forks, rollback, and missing anchors fail closed for promotion.

**Cost / failure surface:** Adds key management or a remote append-only storage dependency and an availability failure mode. Mitigate by making inability to contact the anchor block promotion/high-tier spending, not Tier-0 local experimentation; queue signed checkpoints for later reconciliation but do not claim anchored history until reconciled.

**Evidence:** **STRONG-EMPIRICAL-in-source** for append-only checkpointing as the necessary complement to a writable hash chain; the existing hash-chain mechanism entry in `research/PROPOSALS.md` should be extended to distinguish modification detection from rollback detection.

**Invariant check:** Strengthens immutable epistemics and provenance. It does not change the strategy layer or any admission gate’s meaning.

```diff
diff --git a/plan-r1.md b/plan-r1.md
@@ §3 Retention / Mechanism
- an orchestrator that rewrites history produces a log that fails verification.
+ modification of a retained record produces a log that fails verification. Because a
+ writable local hash chain alone cannot detect deletion or rollback to an earlier valid
+ head, the chain head is periodically anchored outside the orchestrator's write
+ authority. An anchor records `{chain_head, sequence, timestamp, gate_bundle_hash}` in
+ an operator-controlled signed checkpoint or append-only remote store. At startup and
+ before promotion or higher-tier spend, the gate requires the local chain to extend the
+ latest reachable anchor; rollback, a fork, or an unanchored gap yields inadmissible
+ for those actions. M0 may use a signed operator-controlled checkpoint file; its
+ availability policy is explicit rather than silently treating local SQLite as an
+ append-only authority.
```

---

### Sections that are sound and need no revision
- The immutable-epistemics framing in §0 is appropriately load-bearing.
- The attempt-versus-recipe distinction, `DISAGREE` handling, and cache semantics in §§2–3 are unusually well specified.
- The claim-statement identity and derived-tag design in §§4 and 7 are strong.
- The waiver rule correctly prevents an operational waiver from becoming an epistemic pass.
- §14’s baseline is correctly framed and should not be softened.

### The three proposals I would stake the most on
1. **Tier-2 ladder admission split** — the present dependency cycle can halt the intended build.
2. **Finite-size failure versus asymptotic refutation** — essential to keeping the permanent ledger honest.
3. **External anchoring for the hash-chain head** — necessary for the plan’s claimed history-integrity property under its own threat model.

### Framing concern
The only framing error is localized but important: §6 occasionally presents the ladder as if it can “refute” an algorithmic idea in the broad mathematical sense. The plan’s better framing appears elsewhere: ladder results refute exactly pre-registered empirical hypotheses on declared families and ranges; formal no-go results refute broader mathematical claims. Preserve that distinction everywhere, especially in user-facing negative-results artifacts.

### Facts needed but not stated
1. **Threat model for the orchestrator host:** Can the orchestrator modify deployment configuration, database files, process environment, or only ordinary substrate rows? This determines whether external anchoring is mandatory at M0 or merely before multi-user/high-value operation.
2. **Definition of algorithmic memory:** Does “memory” include external storage, networked distinguished-point tables, recomputation caches, and worker-process memory? The ladder cannot enforce a memory condition without this.
3. **Tier-2 authorization granularity:** Can the tier gate constrain a launch to a protocol/purpose and inspect the actual skill parameters, or does it currently only inspect a declared tier? Proposal 1 requires typed purpose binding.
4. **Whether finite-domain performance is part of every algorithmic hypothesis:** If not, the hypothesis schema needs an explicit nullable field rather than treating absence as an implied claim.