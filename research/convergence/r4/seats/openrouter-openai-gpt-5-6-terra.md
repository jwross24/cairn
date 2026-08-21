The plan is unusually strong on the load-bearing invariants: immutable gates, append-only attempts, explicit cache invalidation, pre-registered ladder inputs, derived calibration tags, and the honest ECDLP baseline are all sound and should remain unchanged. In particular, §0, the gate bundle/pin model, the verifier’s affirmative acceptance rule, the separation of `REFUTED` from strategy parking, and the M0-first anti-over-engineering posture need no revision.

## 1. Separate semantic method identity from implementation revision  
**Severity:** HIGH · **Sections:** §2, §3, §4, §5, §6

### Rationale

The plan currently defines a hypothesis key’s method identity as `skill@version and parameters`. That makes an implementation revision semantically change the hypothesis. This creates two bad outcomes:

1. **A method can evade its own negative-results map by changing version.** If version `rho_variant@1.2` is measured to miss its declared cost model, `rho_variant@1.3` gets a fresh hypothesis key even if the algorithm, parameters, and claim are unchanged.
2. **The plan conflates two distinct questions:**
   - “Is this mathematical/algorithmic approach already refuted for this claimed regime?”
   - “Was this exact executable sufficiently tested to receive a Tier-2 ticket?”

The former should survive harmless code revisions; the latter absolutely should not. An implementation revision should generally need fresh ladder validation before it can spend based on a prior ticket, but it must not make prior methodological refutations disappear.

This also closes a worker gaming path: repeatedly make trivial code revisions to reopen a branch blocked by a measured negative result.

**Component improved:** hypothesis key / dead-end ledger / tier-ticket binding.  
**Cost:** one additional typed identifier, migration/validation logic, and explicit review when a purported “implementation-only” revision changes algorithmic semantics. This is modest and preferable to making the ledger porous.  
**Evidence:** **CONJECTURE**, derived from the plan’s own key and ticket definitions (§3–§6); validate in M2 with a fixture where a revision changes only implementation metadata and remains ledger-blocked, while its Tier-2 ticket remains unavailable until re-laddered.  
**Invariant check:** preserves immutable epistemics and strengthens the permanent meaning of `REFUTED`; it does not allow strategy to edit truth or relax a gate.

```diff
--- a/plan-r3.md
+++ b/plan-r3.md
@@ §2 Skill identity and self-test shape
- A skill's identity is a typed bundle
- `{interface version, implementation revision, tool and container digests, numeric
- profile}`.
+ A skill has two distinct identities:
+ `method_semantics_id`, a content-addressed typed description of the algorithmic method
+ and semantically relevant parameters; and `implementation_id`, the typed bundle
+ `{interface version, implementation revision, tool and container digests, numeric
+ profile}`. An implementation revision may change without changing the method semantics;
+ any change to the algorithm, asymptotic/cost-relevant parameterization, arithmetic model,
+ or claimed resource model creates a new `method_semantics_id`.

@@ §3 Hypothesis key
- `{target family, claimed property or cost model ..., method identity
- (skill@version and parameters, or the statement hash of the approach), ...}`
+ `{target family, claimed property or cost model ..., method_semantics_id and canonical
+ semantic parameters (or the statement hash of the approach), ...}`.
+ The hypothesis key deliberately excludes `implementation_id`: the ledger records claims
+ about a method, not merely one executable. Every launched recipe still names its exact
+ `implementation_id`.

@@ §4 Ledger preflight
- same method identity failing the same cost model
+ same `method_semantics_id` failing the same cost model
+
+ A changed `implementation_id` alone does not evade a methodological REFUTED entry.
+ Conversely, an implementation-fault entry may name a retry predicate satisfied by a new
+ certified implementation revision, without clearing a formal or measured methodological
+ refutation.

@@ §5 Tier gate predicate
- ticket's recorded key and method identity with the launch's
+ ticket's recorded hypothesis key, `method_semantics_id`, and `implementation_id` with
+ the launch's
+
+ A ladder ticket is executable-specific by default: a new implementation revision must
+ obtain a fresh ladder result even where it implements the same semantic method. This is
+ intentionally stricter than ledger matching.

@@ §6 Protocol
- method identity (skill@version and canonical parameters)
+ `method_semantics_id`, canonical semantic parameters, and exact `implementation_id`
```

## 2. Make audit funding finite and separate from mandatory reproducibility funding  
**Severity:** HIGH · **Sections:** §5, §7, §13 M4

### Rationale

§5 says launch-time verification cost is reserved from a grant. §7 then says the standing auditor repeatedly re-verifies nodes over audit cycles “from the verification component escrowed at each node’s launch.” Those are incompatible unless every node escrows an unbounded future audit budget.

The plan correctly refuses to let mandatory reproducibility be unfunded. It should apply the same accounting honesty to audit: reserve the *required admission check* at launch, but fund periodic auditor rechecks from a bounded, explicit audit-cycle budget. If that budget cannot meet its target, report achieved coverage/bits—as the plan already wisely requires—rather than imply that a historical per-node escrow will pay indefinitely.

**Component improved:** tier budget accounting and foundations auditor.  
**Cost:** two budget buckets and audit-cycle scheduling/accounting. It can reduce audit frequency under constrained budget, but makes that reduction explicit rather than silently underfunded.  
**Evidence:** **CONJECTURE**, based on an internal accounting contradiction between §5’s per-launch reservation and §7’s recurring audit requirement. Validate in M4 by proving that all audit records reconcile to a finite cycle budget and that no node can be charged below zero.  
**Invariant check:** does not weaken the reproducibility gate. It makes audit shortfall visible and preserves the existing human-queue escalation.

```diff
--- a/plan-r3.md
+++ b/plan-r3.md
@@ §5 Compute tiers & allocation
- A cost profile names two components: production ... and verification ...; the tier gate
- reserves the verification component from the grant at launch
+ A cost profile names three components: production; admission verification (the mandatory
+ re-run or witness check required before the node may support its advertised class); and
+ audit re-verification cost (an estimate only). The tier gate reserves the admission
+ verification component from the launch grant at launch. It never represents a finite
+ per-node reserve as funding for unbounded future audit cycles.

@@ §7 Standing foundations-auditor
- checked exhaustively ... from the verification component escrowed at each node's launch;
- where the escrow cannot fund l, the auditor draws what it can afford
+ checked exhaustively from the auditor's explicit, finite audit-cycle grant. The grant,
+ its stratum allocation, and every charge are recorded in the audit record. Where that
+ grant cannot fund `l`, the auditor draws what it can afford and records achieved `bits`;
+ an unmet target surfaces on the human queue. Admission reproducibility funding is not
+ consumed to conceal an audit shortfall.

@@ §13 M4 Done when
- foundations auditor's audit record names its critical set, its residual seed and its
- achieved `bits`
+ foundations auditor's audit record names its cycle grant, per-stratum charges, critical
+ set, residual seed, and achieved `bits`, and reconciles all charges without drawing on
+ already-consumed admission-verification reservations
```

## 3. Narrow measured “refutation” to the actual finite, pre-registered predicate  
**Severity:** HIGH · **Sections:** §4, §6, §11, §14

### Rationale

The framing “a subexponential attack that can’t beat BSGS at 50 bits is refuted on the spot” is too broad. The plan correctly says elsewhere that finite sizes do not establish an asymptotic. The converse is equally important: a finite benchmark failure cannot refute an asymptotic method in general, especially one with a declared crossover beyond the tested range.

The ladder should remain a hard anti-fabrication gate. But it should refute only what it actually tests: for example, “this exact method and implementation meets this pre-registered performance/crossover model on the declared 30–50-bit region,” or “this method recovers `x` on every trial in the specified family.” An asymptotic theorem belongs in formalization; an empirical finite-range claim belongs in the ladder. The ledger’s permanent reach should mirror that distinction.

This is not leniency. It prevents Cairn’s negative-results map from making mathematically unjustified universal claims—which would itself violate the project’s epistemic standards.

**Component improved:** ladder verdict semantics and ledger reach.  
**Cost:** claim authors must explicitly distinguish finite-range operational assertions from asymptotic assertions; the ledger stores a more precise rejected predicate.  
**Evidence:** **PROVEN-in-source** as a logical consequence of the plan’s own statement that “finite sizes test a declared model; they do not establish an asymptotic” (§6). The exact revised schema is **CONJECTURE** and should be tested by M1/M2 fixtures.  
**Invariant check:** retains the ladder, its hard failure conditions, and its role as a Tier-2 gate. It narrows overclaiming rather than relaxing scrutiny.

```diff
--- a/plan-r3.md
+++ b/plan-r3.md
@@ §4 Ledger preflight
- A measured refutation reaches the hypothesis object it was measured on and every object
- asserting the same cost model for the same method identity over a declared region that
- contains the measured point
+ A measured refutation reaches only the pre-registered finite predicate actually tested:
+ the same `method_semantics_id`, claimed performance/resource model, declared family,
+ implementation where relevant, and declared parameter region containing the measured
+ point. It does not refute an asymptotic claim, a different crossover claim outside that
+ region, or a theorem unless a formal entry establishes that broader reach.

@@ §6 Small-scale ladder
- A "subexponential attack" that can't beat baby-step-giant-step at 50 bits is
- refuted on the spot.
+ A method whose pre-registered finite-range claim says it should beat the refutation
+ floor by 50 bits, but does not, is refuted on that finite predicate on the spot.
+ A finite ladder result neither establishes nor refutes an asymptotic claim outside its
+ declared range; such a claim requires a separately stated theorem or is retained as a
+ CONJECTURE with its failed finite prediction recorded.

@@ §6 Verdicts
- `REJECT` (refutation floor failed, ...)
+ `REJECT` (the declared finite predicate failed: refutation floor failed where the model
+ predicted success, `xP ≠ Q` on any trial, ...). The table records the exact rejected
+ predicate and its finite reach for the §4 ledger.

@@ §11 Negative-results map
- "approach X provably fails on prime-field curves, here's why"
+ "the stated approach/claim fails on this declared prime-field family and regime, here's
+ why" (or, only for a formal entry, "approach X provably fails under these assumptions")
```

## 4. Repair M3’s status contradiction and test the actual persistence policy  
**Severity:** MED · **Sections:** §4, §13 M3, §15 P3

### Rationale

§4 explicitly says a yield-based stall is a strategy decision and must create `PARKED`, not `REFUTED`. It also says forced pivots use `low_yield_pivot` and auto-revive. But M3’s done condition says funding is “withdrawn,” which is a terminal branch status elsewhere in the plan. A fresh implementer could reasonably implement terminal withdrawal and thereby defeat the stated persistence/revival policy.

The M3 acceptance test should verify: (1) automatic force-park; (2) no `REFUTED`/terminal `withdrawn` record; (3) preserved obligation and provenance; and (4) revival when the declared blocker predicate clears.

**Component improved:** orchestrator status transition contract.  
**Cost:** one more M3 fixture and explicit transition assertions.  
**Evidence:** **PROVEN-in-source** inconsistency: §4’s pivot definition conflicts with §13’s “withdrawn” wording.  
**Invariant check:** directly protects “never give up” at the program level and preserves evidence-only `REFUTED`.

```diff
--- a/plan-r3.md
+++ b/plan-r3.md
@@ §13 M3 Done when
- funding is withdrawn from it within `m` ticks unaided
+ it is force-parked within `m` ticks unaided with blocker `low_yield_pivot`; no REFUTED
+ or terminal `withdrawn` transition is written; and it auto-revives when its pinned
+ epoch-count or budget-threshold predicate clears. The fixture asserts that its prior
+ artifacts, obligation, and ledger visibility remain intact.
```

## 5. Do not make the conjectural statement hash the proof-statement equality decision  
**Severity:** MED · **Sections:** §7, §13 M1

### Rationale

The plan is admirably candid that the proposed transitive-closure statement hash is **CONJECTURE** until M1. But the formalization gate currently appears to use that hash as the equality check that protects against redefined constants. If the hasher omits a relevant dependency or normalizes incorrectly, it could produce a false acceptance—exactly the failure the formalization gate exists to prevent.

Use the hash as an efficient index/cache key only. The admission decision must invoke the pinned structural comparator over the Challenge and Solution closures. Until the comparator and its mutation corpus are qualified, the PROVEN route must be unavailable, not merely “not trusted” informally.

**Component improved:** formalization gate readiness and statement-equivalence check.  
**Cost:** direct structural comparison can be slower; a qualification corpus must include transitive-definition mutations. This cost is appropriate for the only route to `PROVEN`.  
**Evidence:** **CONJECTURE** for the hasher, explicitly acknowledged in §7; the direct comparator is already the plan’s intended source of truth. Validate in M1 with existing wrong-statement plants plus transitive-closure mutation fixtures.  
**Invariant check:** strengthens, rather than changes, green Lean plus statement-level review.

```diff
--- a/plan-r3.md
+++ b/plan-r3.md
@@ §7 Green Lean protocol
- The statement hash is computed over what the comparator compares ...
+ The statement hash is an index and cache key over what the comparator compares; it is
+ never by itself an admission decision. The pinned structural comparator must directly
+ compare the Challenge and Solution transitive closures before PROVEN admission.

+ Formalization-gate readiness is false until M1 qualifies the comparator/hash pair with a
+ versioned mutation corpus including altered theorem bodies, altered transitive
+ definitions, changed quantifiers, and renamed-but-equivalent position-dependent exports.
+ While readiness is false, green artifacts remain below PROVEN and queue for engineering
+ remediation; no fallback equality rule exists.

@@ §13 M1 Done when
- M1 builds and probes the statement hasher ...
+ M1 qualifies the direct comparator and statement-hash prefilter against the versioned
+ mutation corpus before enabling the PROVEN derivation route; a hash match with a direct
+ comparator mismatch must fail closed.
```

## Three proposals I would stake the most on

1. **Separate semantic method identity from implementation identity** (§§2–6). This is the most important ledger-integrity correction.
2. **Narrow measured refutations to tested finite predicates** (§§4, 6). This prevents Cairn from becoming overconfident in its negative results.
3. **Separate recurring audit budgets from mandatory reproducibility reserves** (§§5, 7). This fixes an otherwise unsound resource-accounting promise.

## Framing that is wrong

The plan’s framing is wrong where it calls failure at 50 bits a refutation of a “subexponential attack” without qualifying the claim’s declared crossover/range. That conflicts with the plan’s own correct claim that finite tests do not establish asymptotics. The ladder should be uncompromising about operational claims at tested sizes, but mathematically precise about what it has and has not ruled out.

The broader framing is right: the 254-bit prime-order ECDLP almost certainly stands; Cairn’s credible purpose is publishable partial progress, rigorous negative results, bounds, reductions, and reusable formal/experimental infrastructure.

## Facts needed but not stated

1. Whether skill revisions can currently be classified mechanically as implementation-only versus algorithmically semantic; this determines how practical `method_semantics_id` review is.
2. Expected node volumes, audit-cycle cadence, and actual replay/witness-check costs by tier; these are needed to size a finite M4 auditor budget.
3. The exact semantics of branch `withdrawn` versus funding cessation; M3’s test should use the former only for a reason-bearing terminal human/strategy decision, if at all.
4. Whether Lean’s planned comparator can be invoked directly as a deterministic admission check, rather than inferred indirectly through a proposed hash.