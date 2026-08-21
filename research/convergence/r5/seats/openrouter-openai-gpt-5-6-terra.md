The plan is unusually strong on its non-negotiables: immutable epistemics, typed/calibration-derived claims, gate ownership, attempt preservation, and the honest ECDLP baseline are all sound and should not be weakened. I would not add new “intelligence” mechanisms before M0. The most valuable revisions are contract repairs where the current text can accidentally turn an implementation failure into mathematical evidence, or leave a required verification unfunded.

## 1. Separate invalid executions from refutations of a method hypothesis · **HIGH** · §§2, 4, 6, 7, 13/M1

**Component improved:** ladder verdict / ledger-refutation boundary.

**Issue.** The plan correctly distinguishes an `implementation` fault from a `measured` refutation in §4. But §6 currently labels all of the following `REJECT`: `xP ≠ Q`, self-reported-count divergence, and potentially instrumentation failure. §7 then says “a ladder REJECT on the claim’s own pre-registered model” refutes the claim. Since a hypothesis key intentionally names an interface/method rather than its implementation revision, this can permanently block *all* implementations of a method based on one bad executable, bad counter, or harness integration defect.

A model miss on valid, gate-measured successful runs is evidence against the preregistered hypothesis. A wrong answer or failed accounting is not: it is evidence that this execution is invalid and may justify yanking the implementation (§2), but not blacklisting the method.

**Revision.** Split “method/model rejection” from “execution-integrity failure,” and require an integrity-cleared table before a measured refutation can reach the method hypothesis key.

**Cost/failure surface:** one additional verdict family, more explicit ledger routing, and revised planted fixtures. It prevents a much costlier failure: poisoning the negative-results map and dead-end ledger with false mathematical negatives.

**Evidence:** **CONJECTURE as a design correction**, directly testable by the existing M1 planted wrong-answer/count fixtures and M2 “implementation-revision differs” fixture. It introduces no strategy authority, does not relax a gate, and preserves the calibration boundary: integrity failures are strictly less admissible than measured refutations.

```diff
--- a/plan-r4.md
+++ b/plan-r4.md
@@ §6, Protocol (2c)
-`REJECT` (refutation floor failed, `xP ≠ Q` on any trial, memory cap exceeded,
-a self-reported count diverging from the gate's, or an in-sample or
-out-of-sample miss of the pre-registered model, ...)
+`REJECT` is a measured refutation of the preregistered method hypothesis only
+when every included trial is execution-integrity-cleared and the fired predicate
+is a method/model predicate: refutation-floor failure, memory-model/cap failure,
+or an in-sample or out-of-sample miss of the preregistered model.
+
+`INVALID_EXECUTION` is not a method refutation: `xP ≠ Q`, a gate/counting
+integrity failure, a self-reported-count divergence, unavailable required
+instrumentation, or any trial whose receipt cannot establish the ladder's
+declared execution contract. It records the exact implementation identity and
+trial artifacts, is never a ticket or positive evidence, and is routed to the
+§2 skill-fault/yank procedure. A table containing INVALID_EXECUTION has verdict
+`INVALID_EXECUTION`, not REJECT or INCONCLUSIVE.

@@ §4, Ledger preflight / REFUTED entry
-A measured refutation reaches the hypothesis object it was measured on ...
+A measured refutation reaches the hypothesis object it was measured on only
+from an integrity-cleared ladder table whose rejection predicate is a declared
+method/model predicate. An `INVALID_EXECUTION` reaches the named implementation
+revision and its recipe-key fault predicate under §2, never the method identity
+or hypothesis key absent an independently established method-level defect.

@@ §7, derived tag/refutation rule
-a ladder REJECT on the claim's own pre-registered model — moves the claim version
-to terminal status `refuted`
+a ladder table with verdict REJECT, integrity-cleared trials, and a rejection of
+the claim's own pre-registered model — moves the claim version to terminal
+status `refuted`. `INVALID_EXECUTION` blocks promotion and routes for repair or
+yank; it does not derive a mathematical refutation.

@@ §13, M1 done-when
-(b) a correct-ops claim that fails `xP == Q` on a fresh ladder instance;
+(b) a correct-ops claim that fails `xP == Q` on a fresh ladder instance, which
+must produce `INVALID_EXECUTION`, no method-level REFUTED entry, and an
+implementation-fault/yank review;
```

## 2. Make deferred reproducibility checks a funded, durable liability · **HIGH** · §§3, 5, 7

**Component improved:** verification escrow / foundations-auditor accounting.

**Issue.** §5 says verification cost is reserved at launch and “released to the granting branch when the attempt reaches a terminal status.” But §3 deliberately defers the first required Tier-2/3 replay until `justify` time or an auditor draw. §7 then says the first auditor draw is funded “from each node’s escrow.” Those statements conflict: the reservation cannot both be released on completion and fund a later mandatory check.

This is not merely bookkeeping. Under load, it creates precisely the silent degradation the plan seeks to avoid: lots of Tier-2 nodes can be produced, their escrow released and reallocated, and later claims cannot pay for the checks required to rise above `CONJECTURE`.

**Revision.** Persist a node-bound verification liability at successful completion. Transfer—not release—the reserved funds to it until the first mandatory re-verification completes. Subsequent periodic audits remain funded by the standing audit line as intended.

**Cost/failure surface:** retained budget reduces apparent available capacity; requires an explicit transfer transaction and reconciliation test. This is preferable to admitting evidence whose required verification is unfunded.

**Evidence:** **CONJECTURE as an accounting-contract repair**; validate with an M0/M1 synthetic deferred-replay test and M4 audit reconciliation. No new truth mechanism is introduced; it only ensures existing reproducibility gates can execute.

```diff
--- a/plan-r4.md
+++ b/plan-r4.md
@@ §5, verification component
-the tier gate reserves the verification component from the grant at launch ...
-and releases the reservation to the granting branch when the attempt reaches a
-terminal status
+the tier gate reserves the verification component from the grant at launch.
+For an OK node whose §3 policy requires a check after attempt completion, the
+reservation is atomically transferred at completion into a node-bound
+`verification_liability {node, required_check, amount, funding_source,
+state ∈ {reserved, spent, released}}`; it is not returned to the granting
+branch. The liability is spent by the first required `justify`-time replay or
+first auditor draw. It is released only when the node becomes inadmissible,
+is disowned, or its required first check completes for less than the reserve;
+the release record names the disposition. A status ≠ OK attempt releases its
+unspent reservation at termination.

@@ §5, later re-verification
-every later re-verification of a node is funded from the standing per-cycle
-audit line ...
+every re-verification after the node's required first check is funded from the
+standing per-cycle audit line ...

@@ §7, foundations auditor
-from each node's escrow on its first draw and from the standing per-cycle audit
-line ... on every later one
+from the node's persisted `verification_liability` on its first required draw,
+and from the standing per-cycle audit line on every later one. An auditor may
+not count a node as checked if its required liability cannot be charged.

@@ §13, M0 done-when
+...; and a synthetic successful Tier-2/3-grade node with deferred replay keeps
+its verification liability after attempt completion, cannot be promoted after
+its source branch has spent all other funds, and releases or spends that
+liability only through the recorded terminal paths;
```

## 3. Replace the LLM “echoed context” canary with deterministic dispatch-input attestation · **MED** · §§4, 7, 13/M1

**Component improved:** worker-context isolation and Skeptic independence.

**Issue.** The proposed dispatch canary asks whether a planted token is absent from a worker’s “echoed context.” An LLM’s response cannot establish what it did or did not receive: it may omit a token, transform it, or refuse to reveal it. This makes the canary useful as a smoke test but unsound as proof of the claimed dispatch boundary.

The plan already has the right underlying architecture: a top-level dispatch, explicit allow-lists, and no general file access. It should attest the bytes and capabilities supplied to the provider, not infer them from model behavior.

**Revision.** Record a canonical dispatch-input manifest/hash before invocation: approved node hashes, rendered role-template hash, tool allow-list, settings-source policy, and any permitted attachments. The test must inspect rendered request bytes and sandbox capability configuration before the model is called. The token canary remains a regression test, but not the security proof.

**Cost/failure surface:** a request-renderer boundary and redaction rules for any provider metadata. This is a small, inspectable component. It does not attempt to trust an LLM judge or make a gate model-dependent.

**Evidence:** **CONJECTURE until grounded in M1**; the test is deterministic once Cairn controls the request renderer. M1’s existing toolchain/SDK-change re-grounding is the appropriate acceptance point. It preserves all invariant gates and strengthens, rather than broadens, isolation claims.

```diff
--- a/plan-r4.md
+++ b/plan-r4.md
@@ §4, Workers
-That a dispatched worker's context holds nothing but the nodes it is handed ...
-is a stack fact the dispatch canary of §13 M1 grounds ...
+The dispatch path emits, before provider invocation, an immutable
+`dispatch_manifest {approved_node_hashes, rendered_role_template_hash,
+tool_allow_list_hash, settings_source_policy, attachment_hashes,
+request_bytes_hash}`. The harness verifies that the rendered request bytes and
+sandbox capability configuration are derived solely from this manifest.
+Claims about worker-visible Cairn content are grounded from this deterministic
+boundary; they are not inferred from model output. Provider-owned hidden system
+context remains outside this claim and must not contain Cairn artifacts.

@@ §13, M1 dispatch canary
-and the dispatch canary: a distinct token planted in each settings source ...
-is absent from a dispatched worker's echoed context ...
+and the dispatch canary: distinct tokens planted in each forbidden settings
+source and working-tree location are absent from the canonical rendered request
+bytes and from the dispatch manifest before provider invocation; the sandbox
+configuration denies their corresponding filesystem capabilities. An optional
+model-echo check is diagnostic only and is not evidence of isolation.
```

## 4. Eliminate ambiguity between method identity and implementation identity · **MED** · §§2, 3, 5, 6

**Component improved:** hypothesis-key, ladder-dispatch, and ticket join contract.

**Issue.** The plan’s intended distinction is excellent: hypothesis keys use a stable method/interface identity so a revision bump cannot evade a refutation; recipe keys and tickets bind the executable identity so a new revision must re-ladder. But the text alternates among “interface version,” “skill@version,” and “full §2 identity bundle.” In §6 especially, `skill@version` can reasonably be implemented as either identifier. A fresh implementer could accidentally put the implementation digest into the hypothesis key, defeating the dead-end ledger, or omit it from a ticket, defeating re-laddering.

**Revision.** Introduce two explicit typed fields and prohibit overloaded terminology.

**Cost/failure surface:** schema naming/migration only. It removes a high-impact join error. This is a clarification, not a new mechanism; it reinforces existing immutable-gate behavior.

**Evidence:** existing plan rationale in §§2–3 is the evidence for the intended separation; no additional empirical mechanism is proposed.

```diff
--- a/plan-r4.md
+++ b/plan-r4.md
@@ §2, Skill identity
-A skill's identity is a typed bundle ...
+A skill has two non-interchangeable identifiers:
+`method_interface_id` = the stable interface version plus canonical algorithm
+parameter schema, and `implementation_identity` = the full typed bundle
+`{method_interface_id, implementation revision, tool/container digests,
+numeric profile}`.

@@ §3, Hypothesis key
-method identity (the skill named by its §2 interface version with its canonical
-parameters — never its implementation revision ...)
+method identity (`method_interface_id` with canonical parameters — never
+`implementation_identity` ...)

@@ §5, Tier gate predicate
-the launch's hypothesis key and method identity ...
+the launch's hypothesis key, `method_interface_id`, and
+`implementation_identity` ...
@@
-the implementation revision it ran (§6) with the launch's
+the `implementation_identity` it ran (§6) with the launch's
+`implementation_identity`

@@ §6, Protocol (0)
-the hypothesis object's hash, its method identity (skill@version and canonical
-parameters, §3) and the implementation revision under test ...
+the hypothesis object's hash, its `method_interface_id` and canonical
+parameters, and the `implementation_identity` under test ...
```

### The three proposals I would stake the most on

1. **Separate `INVALID_EXECUTION` from method-level `REJECT`.** This protects the permanent negative-results ledger from false mathematical conclusions.
2. **Persist the deferred-verification liability.** The current escrow lifecycle has an internal contradiction that can leave mandatory checks unfunded.
3. **Deterministic dispatch manifest instead of LLM echo evidence.** Isolation needs to be established at the request/capability boundary, not inferred from generated text.

### Framing assessment

I do **not** think the central framing is wrong. In particular, the statement that the 254-bit prime-order ECDLP almost certainly stands, and that useful outcomes are publishable increments on open subproblems, is correctly load-bearing.

One wording risk is the opening “never stops researching.” §9 repairs it well by defining persistence at program level and terminality at claim level. I would retain that repair prominently; without it, the phrase invites readers to mistake persistence for a success metric.

### Facts I would need that the plan does not state

- The exact trust boundary for native skills: whether a skill/container can access the host SQLite files, operator checkpoint location, network, process table, or other workers. The current worker allow-list is strong, but the native-skill sandbox contract is less explicit.
- Whether budgets are actual enforceable scheduler reservations (cgroup/job scheduler/accounting integration) or cooperative process limits. The answer determines how credible Tier ceilings and escrow accounting are.
- The authoritative definition of “gate-owned operation counter” for optimized algorithms that cannot call a shared arithmetic object. The plan correctly refuses uncounted implementations from `KEEP`; it should state the extension path for making a new arithmetic representation countable.
- The operator identity and key-management model for attributed human rulings, bundle pins, and checkpoint ownership. “Human path” needs an authentication/audit primitive before it is relied upon for Tier-2/3 admission.