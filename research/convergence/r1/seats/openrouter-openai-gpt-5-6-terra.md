## 1. Make claim identity immutable and bind every justification to the exact claim statement  
**Severity:** HIGH  
**Section:** §4 claims DB; §7 derived tags and statement-level review  

**Rationale:** The plan correctly makes tags derived rather than worker-set, but it does not define an immutable identity for the *claim being tagged*. A claim title, informal statement, formal Lean statement, scope/model assumptions, and target curve can otherwise drift independently while retaining an evidence pointer. This is especially dangerous for `PROVEN`: Lean can prove an exact formal theorem while a mutable natural-language claim describes something stronger.

Add a versioned `ClaimStatement` artifact and require `justify(evidence, target)` to name its hash. A changed statement is a new claim version, not an edit. This makes the existing Challenge/Solution and human statement review operate on a stable object.

**Component improved:** claims DB / calibration derivation.  
**Cost:** Additional schema, versioning UI, and explicit supersession edges; modest implementation cost.  
**Evidence:** **PROVEN-in-source** as a consequence of Lean checking an elaborated declaration rather than an informal label; the relevant stack evidence should be attached to the existing §7 Lean grounding. Artifact/version binding is also directly testable in M1 with a “same title, changed quantifier” fixture.  
**Invariant check:** Does not let strategy edit truth or alter tags/gates; it makes tag derivation stricter and preserves the calibration boundary.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §4. Components
- **State layer:** branch tree (...); ... **claims DB** (mandatory
- calibration tag §7, pointer to evidence node);
+ **State layer:** branch tree (...); ... **claims DB**. A claim is an
+ immutable, content-addressed `ClaimStatement` artifact:
+ `{claim_id, version, informal_statement, formal_statement?,
+ scope/model/target assumptions, quantities/units, source-claim hash,
+ supersedes?}`. Editing any semantic field creates a new version with an
+ explicit `supersedes` edge; it never edits the old claim in place. Every
+ calibration tag, statement-review verdict, dispute, and
+ `justify(evidence, target)` result names the exact ClaimStatement hash.

@@ §7. Epistemic mechanics
- A claim's tag = the strongest class some evidence node justifies via
- `justify(evidence, target)`, ...
+ A claim version's tag = the strongest class some evidence node justifies via
+ `justify(evidence, claim_statement_hash)`, where the justification checks
+ that the evidence's declared target, assumptions, population, and quantities
+ cover that exact artifact. Evidence attached to a superseded statement does
+ not transfer automatically to its successor.
```

---

## 2. Separate immutable recipe identity from execution attempts; never “overwrite” a content-addressed result  
**Severity:** HIGH  
**Section:** §3 substrate; M0 schema  

**Rationale:** `skip_cache_lookup` currently says “run even if cached and overwrite.” That conflicts with the stated append-only, reproducible DAG: if the same recipe has a second output, overwriting loses precisely the divergence needed to diagnose nondeterminism, tool faults, or a poisoned cache. A content-addressed recipe key is not necessarily an artifact identity.

Use a stable **recipe key** plus append-only **attempt records**. An attempt has an output-manifest digest, execution receipt, status, and parent recipe key. For deterministic/replayable work, multiple successful attempts must have identical manifests before the recipe is cache-servable. For verifiable work, each witness is retained as a separate attempt and independently verified. `skip_cache_lookup` means “create a fresh attempt,” never overwrite.

Also include `salt` in the recipe key/namespace definition; as written it is described as moving results to a namespace but is absent from the key tuple.

**Component improved:** substrate cache, reproducibility gate, divergence retention.  
**Cost:** One extra table and slightly more storage for duplicate manifests/receipts; more explicit cache-selection logic.  
**Evidence:** **PROVEN-in-source** for immutable append-only records and transactional consistency from SQLite’s documented transaction model; **STRONG-EMPIRICAL** for separating build/action identity from executions in reproducible-build systems. Add the existing mechanism citation from `research/PROPOSALS.md` to this subsection.  
**Invariant check:** Strengthens provenance and gates; does not permit strategy to rewrite history or treat a cache hit as evidence.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §3. Content-addressed substrate
-- **Every artifact is hashed by `(skill@version, inputs-by-hash, seed,
+- **Every recipe is hashed by `(skill@version, inputs-by-hash, seed,
   tool-versions, container-digest)`.**
+  `salt` is a domain-separated field in that recipe key. A recipe key identifies
+  requested computation, not a mutable result slot.
@@
- `skip_cache_lookup` (run even if cached and overwrite; the Skeptic's re-runs
- always set it),
+ `skip_cache_lookup` (run even if cached and create a fresh execution attempt;
+ the Skeptic's re-runs always set it),
@@
- A cached result is served only if every blob it references is present;
- otherwise it is recomputed.
+ Each launch writes an append-only attempt
+ `{recipe_key, attempt_id, output_manifest_hash, execution_receipt_hash,
+ status, replay_grade, verifier_result}`. A cached result is served only from
+ a verified attempt whose referenced blobs are present. For `Replayable`,
+ disagreeing successful output manifests mark the recipe non-reproducible and
+ inadmissible; neither attempt is overwritten. For `Verifiable`, each witness
+ remains a distinct attempt and must pass its deterministic verifier.
@@ M0 schema includes
- the §3 key construction and cache bits, the replay grade and certificate slot,
+ the §3 recipe-key construction and cache bits, append-only attempt records,
+ the replay grade and certificate slot,
```

---

## 3. Correct the ladder’s inference claim and make its cost tier-consistent  
**Severity:** HIGH  
**Section:** §5–§6; M1 done condition  

**Rationale:** The ladder is sound as a necessary empirical screen, but two sentences overclaim:

1. Measurements at 30–60 bits cannot establish an asymptotic. They can test a preregistered finite-size performance model and falsify specific predicted behavior.  
2. One hundred independent 60-bit rho-scale trials is roughly \(100 \times 2^{30}\) group operations before overhead—plainly not a Tier-1 “minutes, one core” activity. The plan calls the ladder Tier-1 while requiring exactly that workload.

The correction should preserve the hard ladder gate while separating cheap screening from expensive confirmation. Failure to beat BSGS at 50 bits should reject a claim of *50-bit practical superiority* or invalidate a stated extrapolation, not “refute” an algorithm whose stated crossover is above that range. A mathematical asymptotic claim still needs a proof/derivation and appropriate formalization route.

**Component improved:** small-scale ladder and tier gate.  
**Cost:** Requires preregistered crossover/model fields and a scheduler budget estimate; may delay 60-bit confirmation to Tier 2.  
**Evidence:** **PROVEN-in-source** from elementary finite-sample versus asymptotic logic and the plan’s own stated rho cost; **STRONG-EMPIRICAL** for repeated-trial benchmarking and null controls, already cited for §6.  
**Invariant check:** Retains the ladder and strengthens its anti-fabrication role; does not promote empirical results above `STRONG-EMPIRICAL`.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §6. The small-scale ladder
- ... show measured scaling matching its *claimed* asymptotic. A
- "subexponential attack" that can't beat baby-step-giant-step at 50 bits is
- refuted on the spot.
+ ... test a preregistered finite-size performance model and its stated
+ crossover range. Finite-size measurements are necessary evidence about that
+ range; they do not establish an asymptotic. An asymptotic claim additionally
+ requires a mathematical derivation/proof appropriate to its calibration tag.
+ A method that misses a preregistered 50-bit superiority prediction is rejected
+ for that prediction; it is not a refutation of a separately stated
+ higher-crossover algorithmic claim.
@@
- at least 10² independent trials per size ...
+ at least 10² independent trials at sizes whose declared cost fits Tier 1.
+ Larger-size confirmation uses a preregistered sequential/trial budget and is
+ admitted at the tier implied by its cost profile; it cannot be mislabeled as
+ Tier-1 merely because it is part of the ladder.
@@ §5. Tier 1
- The ladder §6 is Tier-1.
+ The ladder's screening arm is Tier-1; any confirmation arm is tiered by its
+ declared trial count and measured group-operation budget.
```

---

## 4. Scope `REFUTED` entries so an empirical negative cannot permanently blacklist a broader hypothesis  
**Severity:** HIGH  
**Section:** §3 dead ends; §4 ledger  

**Rationale:** “Hypothesis hash matches `REFUTED`” conflates at least three different things: exact computational recipe deduplication, a bounded empirical negative, and a mathematical impossibility result. Only exact recipe identity can safely auto-block by hash. A measured failure under one distribution, implementation, parameter range, or resource cap must not permanently blacklist a broader attack family.

Add a typed refutation scope and make preflight compare the proposed branch’s declared assumptions against that scope. A formal contradiction/no-go can have a broad scope; a ladder result should be limited to its registered family, sizes, resource limits, and performance predicate. This also makes retry predicates objective rather than a discretionary escape hatch.

**Component improved:** dead-end ledger / preflight.  
**Cost:** Typed scope predicates and a containment checker; some initial ledger-entry authoring burden.  
**Evidence:** **PROVEN-in-source** as a logical requirement: evidence only entails conclusions within its stated assumptions; §7 already applies this principle to sampled evidence and model proofs.  
**Invariant check:** Preserves permanent refutations where justified, but prevents strategy or a worker from using a too-broad label to suppress valid research.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §4. State layer / Ledger preflight
- `Blocked` = the hash matches a REFUTED entry whose retry predicate is unmet;
+ `Blocked` has two distinct cases: (a) an exact recipe/attempt-equivalence
+ match, which is always deduplicated; or (b) a proposed branch whose declared
+ assumptions are contained in a REFUTED entry's typed refutation scope and
+ whose retry predicate is unmet.
@@
- Every REFUTED/PARKED entry carries `{hypothesis hash, evidence node, method,
+ Every REFUTED/PARKED entry carries `{hypothesis hash, refutation_kind ∈
+ {formal, bounded_empirical, implementation, exact_recipe}, typed_scope,
+ evidence node, method,
   result (+CI where measured), decision, retry predicate, caught_by}`.
+ `bounded_empirical` scope must state family/distribution, parameter range,
+ resource limit, metric, and confidence procedure; it cannot block a proposal
+ outside those bounds. Broad permanent blocking requires a formal result or an
+ explicitly applicable immutable no-go rule.
```

---

## 5. Make admission-gate waivers impossible, not merely unattributed  
**Severity:** HIGH  
**Section:** §4 gate discipline  

**Rationale:** The plan says waivers are explicit and that a waived check “never counts as satisfied,” but does not say whether a waiver can nevertheless allow promotion, Tier advancement, submission, or a stronger tag. If it can, the waiver is a gate bypass in practice. This is a direct conflict with the immutable gate-layer invariant.

Waivers can be useful for operational diagnostics, e.g., allowing an `AuditOnly` dry run to continue as non-evidence. They must not affect an admission decision.

**Component improved:** gate layer / waiver registry.  
**Cost:** A gate-policy field and negative fixtures; little runtime cost.  
**Evidence:** **PROVEN-in-source** from the plan’s own fail-closed requirement; this is a contract clarification, not a new research mechanism.  
**Invariant check:** Explicitly protects, rather than weakens, immutable gates.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §4. Gate discipline
- a waiver is explicit, attributed, reason-bearing and expiring, and a waived
- check never counts as satisfied;
+ a waiver is explicit, attributed, reason-bearing and expiring. Admission gates
+ (submission verifier, ladder, no-go, formalization, reproducibility,
+ proportional-scrutiny, and tier admission) are non-waivable: failure, absence,
+ or waiver yields `inadmissible` for promotion, submission, and higher-tier
+ spend. Waivers are permitted only for explicitly non-admission operational
+ checks and produce `AuditOnly` output; a waived check never counts as
+ satisfied. Gate self-tests include a fixture proving that a waiver cannot
+ advance a claim or tier.
```

---

## 6. Fix P2’s test-martingale domain before prototype evaluation  
**Severity:** MED  
**Section:** §15 P2  

**Rationale:** The proposed factor `1 + λ_t(Y_t − q_t)` is only a valid nonnegative test-martingale factor if the predictable stake is bounded according to `q_t`. No range for `λ_t` is stated. With a fixed positive λ, for example, the factor can be negative when \(Y_t=0\) and \(q_t\) is near one. Since the plan rightly rejects invalid e-value machinery, this deferred mechanism needs a mathematically complete contract before it is tested.

**Component improved:** selector-audit monitor.  
**Cost:** Implement stake bounds and record the forecast/timing filtration; no meaningful compute cost.  
**Evidence:** **PROVEN-in-source** under the standard conditional-calibration null: require predictable \(\lambda_t \in [-1/(1-q_t), 1/q_t]\), with endpoint handling, so the factor is nonnegative and conditionally mean one. Cite the martingale source already intended for P2 in `research/PROPOSALS.md`.  
**Invariant check:** Remains a monitor only; explicitly cannot gate, promote, or automatically swap selectors.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §15 P2
- `M_t = ∏(1 + λ_t(Y_t − q_t))` is a test martingale under "calibrated";
+ `M_t = ∏(1 + λ_t(Y_t − q_t))` is used only with predictable stakes
+ `λ_t ∈ [-1/(1-q_t), 1/q_t]` (with explicit endpoint handling), recorded
+ before observing `Y_t`; under the conditional-calibration null this makes each
+ factor nonnegative with conditional mean one. Outcome-lag handling must also
+ define the filtration under which `q_t`, λ_t, and adjudication become known.
```

---

## 7. Tighten M0’s “end-to-end” acceptance test  
**Severity:** MED  
**Section:** §13 M0  

**Rationale:** M0’s sole exemplar is `toy_curve(bits, seed) → (p,a,b,n,P)`, while its done condition says it runs one skill “on a 40-bit toy curve end to end.” That does not actually exercise the Tier-0 verifier on a generated `(x, Q)` pair, nor prove that the substrate can preserve a secret scalar and derived public point through an artifact boundary. Since the verifier is load-bearing, M0 should demonstrate it with a deterministic test fixture generated from the exemplar output.

This does **not** require adding a second skill or changing the operator-default exemplar.

**Component improved:** M0 vertical slice / verifier integration.  
**Cost:** A small deterministic harness fixture and negative case.  
**Evidence:** **PROVEN-in-source** as direct integration-test coverage; validated by the M0 done condition itself.  
**Invariant check:** Retains the fixed M0 exemplar and gate; makes both demonstrably connected.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §13 M0 done when
- *Done when:* it runs one skill on a 40-bit toy curve end to end, and the
- result is a hashed, self-tested, cost-tagged substrate node.
+ *Done when:* it runs the exemplar skill on a 40-bit toy curve; a deterministic
+ M0 fixture derives `x` and `Q = xP` from that output; and the subprocess
+ verifier accepts that pair and rejects a one-coordinate/one-scalar negative
+ fixture. The generator output, derivation receipt, verifier result, and gate
+ plan are hashed, self-tested, cost-tagged substrate nodes. This is an
+ integration fixture, not a second research skill.
```

## Sections that are sound as written

- §0’s mutable-strategy / immutable-epistemics boundary is clear and appropriately load-bearing.  
- §7’s rejection of statistical signals as promotion evidence is unusually strong and should remain unchanged.  
- §10’s treatment of model panels as filters rather than epistemic authorities is correct.  
- §14 states the honest ECDLP baseline plainly; it should not be softened.

## The three proposals I would stake the most on

1. **Immutable claim-statement identity** (#1). It closes the most serious route from valid formal artifacts to misleading published claims.  
2. **Recipe/attempt separation** (#2). It resolves an internal contradiction in the reproducibility substrate and protects divergence evidence.  
3. **Tier-consistent, properly scoped ladder** (#3). It prevents both a computationally infeasible M1 and an empirical result being misrepresented as an asymptotic conclusion.

## Framing concern

The framing is mostly right, but “open-ended attack research” is slightly too narrow and incentive-loaded for the project’s stated realistic value. The operational framing should consistently be **research on ECDLP and adjacent mathematical subproblems**, where an attack is one possible outcome and rigorous negative results, bounds, reductions, and formal infrastructure are first-class successes. §9 and §14 already say this; the title/lead should not pull in the opposite direction.

## Facts needed but not stated

1. The intended exact schema for `claim`, `evidence`, `justified_by`, and branch/claim lifecycle records.  
2. Whether the M0 environment is actually hermetic enough to promise byte-identical Sage/PARI runs, including CPU/library/locale handling.  
3. The expected group-operation throughput and memory representation used for the 50/60-bit ladder budgets; this is needed to set credible Tier-1 versus Tier-2 trial counts.  
4. Who has authority to create a broad `REFUTED` scope and how the typed-scope containment checker will represent mathematical assumptions.  
5. The precise source and conditions for the P2 martingale, especially its outcome-lag/adjudication model.