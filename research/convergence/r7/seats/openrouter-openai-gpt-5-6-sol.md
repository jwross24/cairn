## 1. Algorithm laundering can earn STRONG-EMPIRICAL · severity HIGH · §§6–7

**Rationale.** The ladder binds an executable identity, but it cannot establish that the executable implements the mechanism named by the claim. The plan acknowledges this observational limit:

> “The harness cannot see a method's ‘algorithmic table’ except through what the method reports”

Yet `justify` permits:

> “ladder + repro node → STRONG-EMPIRICAL”

for a statement carrying a cost model. A worker can label an implementation “new_method,” implement the known negation-map rho positive control, and earn a KEEP for a claim attributing the measured performance to the fictitious mechanism. Fresh instances, operation counting, and reproducibility do not detect this: they validate black-box performance, not mechanism attribution.

Constrain ladder evidence to extensional claims about the exact executable and measured population. A mechanism-attribution or asymptotic claim needs separate evidence. This tightens `justify`; it does not weaken any gate or taxonomy boundary. Cost: one typed claim distinction and stricter coverage logic; no dependency or compute cost. The defect is established directly by the plan’s stated observability limit.

```diff
--- a/plan-r6.md
+++ b/plan-r6.md
@@ §7 The tag is derived, never set
- ladder + repro node → STRONG-EMPIRICAL — a `ladder_table` whose verdict is
- KEEP ...
+ ladder + repro node → STRONG-EMPIRICAL only for an extensional statement about
+ the measured performance and correctness of the exact implementation identity
+ recorded in the table, on the population measured. A ladder table does not by
+ itself justify attribution of that behavior to a named internal mechanism,
+ source-level algorithm, or asymptotic argument; such attribution remains at
+ most CONJECTURE absent separately admissible evidence. `justify` rejects a
+ ladder table whose target statement asserts more than the executable behavior
+ the ladder observed.
```

---

## 2. The tier gate permits successful cross-tier spending through understated profiles · severity HIGH · §5

**Rationale.** The tier is derived from declared expected cost:

> “the gate derives the launch's tier from the profile's production cost”

The runtime ceiling then expressly permits:

> “a launch runs past the tier its declaration earned by at most the multiplier”

At the default 4× multiplier, a worker can declare a Tier-1 expected cost just below an edge, consume 3.9× that amount, finish successfully, and repeat until predicted charges reach the cumulative edge. The alarm is not enforcement:

> “a persistent mismatch across runs is a strategy-layer alarm … never a gate”

Thus successful actual spend can enter the next tier without its ticket. The cumulative edge must meter actual receipt cost, not only predicted charges.

This improves the existing tier gate. Cost: continuous accounting against an already measured CPU/wall receipt and more honest jobs terminated near an edge; no new dependency. It preserves cheap-before-expensive rather than weakening it.

```diff
--- a/plan-r6.md
+++ b/plan-r6.md
@@ §5 Mechanism
- The gate also charges every non-refused launch's production cost to its
- hypothesis key ...
+ The gate reserves the declared production cost at admission and continuously
+ charges actual production cost, using the same process-tree counters as the
+ execution receipt, to the hypothesis key under its current ticket. The runtime
+ ceiling is the minimum of (a) the declared-profile multiplier ceiling, (b) the
+ spawning budget, and (c) the remaining cumulative edge under that ticket.
+ Reaching any ceiling terminates the attempt as `BUDGET_EXCEEDED`; an attempt
+ may not finish OK after actual cumulative spend has crossed its ticket's edge.
+ Unused reservation is released when the attempt closes.
```

---

## 3. Method-identity aliasing bypasses ledger preflight · severity HIGH · §§3–4

**Rationale.** Measured reach requires:

> “the same method identity failing the same cost model”

while method identity is:

> “the skill named by its §2 interface version”

A worker can publish the same implementation behind a fresh interface version/name and obtain a fresh method identity. It need not add a `supersedes` edge. The only fallback is:

> “A near-duplicate signal … is advisory only”

and free-text paraphrase can evade SimHash. This defeats the ledger’s claimed protection against structurally re-funding known failures. Range jitter is closed; identity jitter is not.

A complete semantic-equivalence gate is unrealistic. The concrete repair is to narrow the ledger’s claim and make known interface lineage non-optional. Cost: lineage metadata and preflight traversal; no new service. Evidence is by construction against the quoted alias path.

```diff
--- a/plan-r6.md
+++ b/plan-r6.md
@@ §2 Skill identity
+ Every new interface version of an existing skill family records an immutable
+ `supersedes_interface` edge. That edge is part of certification and cannot be
+ omitted when the registered skill-family name already exists.

@@ §4 Ledger preflight
+ Preflight follows `supersedes_interface` edges when comparing method identity.
+ A measured refutation therefore cannot be escaped by an interface-version
+ bump within a registered skill family. A newly named family remains subject
+ only to the advisory near-duplicate path; the ledger does not claim to decide
+ semantic equivalence between independently registered methods.

@@ §3 Dead-ends become structural
- same hypothesis, same key, already dead — with no agent needing to remember
- that two approaches are secretly the same.
+ same canonical hypothesis or declared interface lineage, already dead. The
+ substrate does not infer that independently named approaches are secretly the
+ same; near-duplicate review handles that advisory case.
```

---

## 4. M1 and M2 both claim to build the formalizer/review machinery · severity MED · §13

**Rationale.** M1 says it adds:

> “the formalization gate's challenge/solution protocol”

and:

> “the statement pre-filters”

while M2 is titled:

> “Dead-end ledger … + formalizer + statement-level review.”

M1’s positive control already requires an approved verdict to reach PROVEN. M2 later says it adds the review *workflow* and queue routing, which is a coherent incremental boundary, but its title claims the underlying formalizer and review again. A fresh implementer cannot tell which milestone owns them.

```diff
--- a/plan-r6.md
+++ b/plan-r6.md
@@ §13
-- **M2 — memory.** Dead-end ledger (refuted-by-hypothesis-key vs parked) +
- formalizer + statement-level review.
+- **M2 — memory.** Dead-end ledger (refuted-by-hypothesis-key vs parked) +
+ statement-review workflow and queue routing. The formalization gate,
+ statement pre-filters, `review_verdict` schema, and PROVEN derivation were
+ built at M1; M2 adds their persistent human workflow.
```

---

## 5. Append-only tag history has no named code consumer · severity LOW · §7

**Rationale.** The plan creates:

> “Tag history is append-only and attributed.”

But `justify`, the auditor, tier gate, and egress renderer branch on evidence nodes, current derived tags, refutation status, and admissibility—not on the tag-history sequence. The only stated use is recording. That duplicates the append-only evidence and gate-run records and is ceremony under the requested standard.

Cut the separate artifact rather than inventing a consumer.

```diff
--- a/plan-r6.md
+++ b/plan-r6.md
@@ §7
-- **Tag history is append-only and attributed.** Every tag transition records
- what moved it and the evidence node; ...
+- Tags are derived views, not separately authored history records. The
+ append-only evidence nodes, gate-run records, refutation records and
+ `justified_by` edges are the history from which the current tag is re-derived;
+ downgrades require the evidence pointer carried by those records.
```

# Ceremony audit

- **Skill golden certificates:** consumed by self-test admission and tier-gate launchability; mismatch yanks/refuses. Holds.
- **Rho/witness certificates:** consumed by deterministic verifiers, reproducibility admission, tickets, and `justify`. The text correctly limits the name: “certifies identity and checkability, never truth.” Holds.
- **Ledgers:** preflight branches to `Allowed | Blocked | RequiresNullControl | AlreadySettled`; egress and negative-results map consume records. Holds, subject to identity aliasing above.
- **Tag histories:** no code branches on the sequence. Cut per Proposal 5.
- **Gate plans:** gate runner branches on ordered scopes, expected exit codes, missing config, and prior failures. Holds.
- **Self-tests:** skill admission/yanking, tier gate, and pre-gate execution branch on them. Holds.
- **Execution receipts:** budget ceiling, ladder clock/memory predicates, provenance checks, and drift monitoring consume them. Holds.
- **Result tables:** ladder verdict, Tier-2 ticket selection, `justify`, reproducibility recomputation, ledger negatives, and egress consume them. Holds.
- **Alarms:** P4 names the orchestrator park path and `cost_drift` human-queue item; it also supplies a retirement condition: “one that never does is dropped.” Audit shortfall similarly enters the queue. These are honestly named alarms, not gates. Holds.

# Gaming the gates as written

- **Submission verifier:** no defeating path found. It reads `(P,Q)` from the claim/dispatch record, accepts only `x`, and egress refuses a verifier node for another instance.
- **Ladder:** implement negation-map rho under a fictitious method identity and claim its observed cost as evidence for the fictitious mechanism. Open; Proposal 1 closes the calibration consequence.
- **Formalization gate:** no defect found. The worker cannot edit Challenge text; closure equality, gate-owned axiom collection, kernel replay, and same-hash human approval close weaker-statement and custom-axiom paths.
- **Reproducibility gate:** no defect found relative to its stated purpose. Deterministic fabrication can reproduce, but the plan does not call reproducibility truth; separate verifiers and claim gates supply validity.
- **Ledger preflight:** rename/re-version the same method without a lineage edge, obtaining a fresh identity and key. Open; Proposal 3.
- **Tier gate:** understate expected cost and finish below the 4× runtime ceiling but above the ticket’s actual cumulative edge. Open; Proposal 2.

# Constraint-web and milestone disposition

No defect found in cache/disown semantics, replay-grade policy, gate discipline, challenge/solution hash binding, disagreement handling, or deferred-decision retirement rules. The material conflicts are the tier gate’s declared-cost/actual-spend gap, ledger identity aliasing, ladder evidence exceeding what it observes, and the M1/M2 ownership duplication.

**Three proposals I would stake most on:** 2, 1, and 3.

**Facts needed:** whether skill-family names/interfaces are already admitted through a registry not stated here; whether cumulative tier charges are intended to use measured rather than declared cost; and whether claim statements already distinguish extensional executable-performance claims from mechanism-attribution claims.

**VERDICT: NOT STEADY — the tier gate allows successful actual spend to cross a ticket boundary, and ladder evidence can justify more about a mechanism than the gate observes.**

**Single defect to fix first:** Proposal 2, actual-cost enforcement at cumulative tier edges.

**FRAMING problem:** “two approaches are secretly the same” is not a property content addressing can establish. The ledger can enforce canonical identity and declared lineage; semantic equivalence remains an advisory/human judgment and should not be advertised as structurally solved.