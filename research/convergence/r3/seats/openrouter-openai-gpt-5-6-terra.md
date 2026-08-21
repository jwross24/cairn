The plan is unusually strong on the core invariants. I would **not** weaken §0, the gate layer, calibration taxonomy, ladder, verifier, no-go checklist, or the honest ECDLP baseline. In particular, the immutable claim/hypothesis identities, append-only attempt model, `DISAGREE` handling, skill yanking, verification-budget escrow, and refusal records are sound architectural choices and need no revision.

## 1. Make M0’s calibration fixture obey the actual `justify` contract  
**Severity:** HIGH  
**Section:** §7, §13 M0  
**Component improved:** `justify` / typed-evidence admission contract

**Rationale:** §7 says `STRONG-EMPIRICAL` requires **“ladder + repro node.”** M0’s done-when instead says a synthetic `ladder_table` alone yields `STRONG-EMPIRICAL`. That is a direct contract contradiction in the first milestone: an implementer can make M0 pass with a `justify` function that later admits evidence §7 forbids. M0 should absolutely test `justify` synthetically, but the synthetic fixture must have the same graph shape as a real admissible empirical claim.

This also catches two important implementation bugs early: accepting an evidence node whose replay grade is too weak, and accepting a ladder table whose population/assumptions do not cover the statement.

**Cost:** A few synthetic substrate nodes and additional M0 assertions; no new runtime dependency or meaningful compute.  
**Evidence:** **PROVEN-in-source** as a consistency correction: the authoritative rule is already stated in §7’s “maximum class” and `justify` definition.  
**Invariant check:** Strengthens the calibration boundary; does not let strategy set tags or waive a gate.

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ §13 M0 — Done when
-  `justify` returns STRONG-EMPIRICAL from a synthetic `ladder_table` evidence node and a
-  lattice violation when a synthetic `statistical` node is offered for PROVEN, against a
-  synthetic statement hash; and a blob unreachable from the roots table is collectable
+  `justify` returns STRONG-EMPIRICAL only from a synthetic evidence set containing both
+  (i) a `ladder_table` and (ii) a covering `repro_node` whose attempt has the required
+  replay grade and completed reproducibility check; it returns a typed lattice or
+  coverage violation for each of: ladder-without-repro, AuditOnly repro, a population or
+  assumption mismatch, and a synthetic `statistical` node offered for PROVEN, against a
+  synthetic statement hash; and a blob unreachable from the roots table is collectable
   while a rooted one is not.
```

## 2. Repair the foundations-auditor sampling guarantee  
**Severity:** HIGH  
**Section:** §7, “Standing foundations-auditor”  
**Component improved:** foundations-auditor sampling policy

**Rationale:** The stated bound assumes random sampling from the stratum: if rot occupies fraction `f`, then missing it in `l` independent draws has probability at most `(1-f)^l`. The plan then says “nodes with the largest `justified_by` fan-in are drawn first.” That priority selection invalidates the quoted probability bound for the overall stratum. It may be operationally wise to exhaustively audit high-fan-in nodes, but it is not a random sample and cannot be counted toward a random-detection guarantee without a revised argument.

The fix is simple and beneficial: split each tier stratum into (a) a deterministic critical set audited exhaustively and (b) a residual population sampled uniformly without replacement using gate-owned committed entropy. Report the achieved bound for the residual, and report critical-set coverage separately. This improves the security property rather than merely making reporting more precise.

**Cost:** Sampling metadata, a gate-owned random draw, and potentially more rechecks if the critical set is large. No dependency required.  
**Evidence:** **PROVEN-in-source** for the existing finite-population/random-sampling detection bound; §7 already invokes its with-replacement form. The without-replacement version should be selected and tested in the auditor fixture.  
**Invariant check:** This strengthens a mechanical audit gate and does not promote claims or involve strategy judgments.

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ §7 Standing foundations-auditor
-  the bound is applied per tier stratum so that cheap Tier-0/1
-  nodes cannot absorb the whole sample, and within the Tier-2/3 stratum the
-  nodes with the largest `justified_by` fan-in are drawn first.
+  the bound is applied per tier stratum so that cheap Tier-0/1 nodes cannot
+  absorb the whole sample. Each stratum is partitioned before drawing into a
+  deterministic critical set (the highest `justified_by` fan-in nodes, with
+  the cutoff fixed in the gate bundle) and a residual set. The critical set is
+  audited exhaustively and reported as such; the residual set is sampled
+  uniformly without replacement using gate-owned committed entropy. The audit
+  record names the population size, critical-set cutoff and coverage, sampled
+  identifiers, sampling algorithm, and the exact achieved residual detection
+  bound. A deterministic priority audit is never represented as contributing
+  to the random-sampling `bits` guarantee.
```

## 3. Resolve the M0 checkpoint-writer trust-boundary contradiction  
**Severity:** HIGH  
**Section:** §3 retention/checkpointing; §4 gate bundle  
**Component improved:** append-only checkpoint sink

**Rationale:** The plan correctly observes that a hash chain cannot detect truncation. But it gives M0 two incompatible properties: the checkpoint is “outside the orchestrator’s write path,” while the harness must append it “at every gate run.” If the harness process can modify the checkpoint file normally, compromised harness code can truncate/rewrite it; if it cannot write it, it cannot append every gate run. “Append-only file flag” may help, but it is not itself a complete authority model, and its behavior varies by OS/filesystem—something the plan already says must be grounded.

Define the authority boundary, not just the file. A minimal append-only checkpoint service is enough: a separate OS identity accepts a canonical chain-head record over a local IPC interface and permits only append, never read-modify-write/truncate. The harness has only the client capability. M0 can use a tiny helper rather than a distributed service. Its test must attempt rollback/truncation and prove startup fails against the last external checkpoint.

**Cost:** One small privileged helper/OS identity, IPC failure handling, and deployment setup. This is justified because it protects the irreversibility of `REFUTED` and audit history.  
**Evidence:** **CONJECTURE pending M0 grounding** for the exact OS-level implementation; the need for an external anti-truncation witness is already established by §3’s stated hash-chain limitation.  
**Invariant check:** Separates truth-history authority further from strategy; does not dissolve or alter a gate.

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ §3 Retention
-  so the chain head is also appended, at every gate run, to a
-  checkpoint outside the orchestrator's write path — at M0 an operator-owned
-  append-only file beside the gate-bundle pin (§4; the append-only file flag is a stack
-  fact M0 grounds before relying on it, §16), from M4 a writer the substrate's own process
-  cannot truncate —
+  so the chain head is also appended, at every gate run, to a checkpoint sink outside the
+  orchestrator's write authority. At M0 this is a minimal operator-owned append-only
+  helper under a distinct OS identity: the harness may submit a canonical
+  `{sequence, chain_head, gate_run_hash}` record through a narrow local interface but has
+  no truncate, replace, or direct filesystem capability. The helper's append semantics
+  and failure behavior are grounded before reliance (§16). From M4 it may be replaced by
+  an equivalent writer the substrate process cannot truncate —
   and a log that does not extend the last checkpoint fails verification at startup and
   before any promotion.
@@ §13 M0 — Done when
+  The checkpoint fixture proves that a stale-prefix substrate log, a missing checkpoint,
+  and an attempted truncate/replace of the checkpoint are each detected before promotion;
+  an unavailable checkpoint sink fails closed for promotion rather than silently disabling
+  checkpointing.
```

## 4. Turn “human verdict” into a gate-readable, bound attestation  
**Severity:** MED  
**Section:** §7 statement-level review; §10 human loop  
**Component improved:** statement-review admission input

**Rationale:** The plan rightly says the human statement verdict “remains the gate,” and says absence blocks. But it never defines the artifact that the formalization/proportional-scrutiny gate reads. Without this, an implementer has to invent whether a comment, a mutable UI status, or a worker-created database row is sufficient—precisely the ambiguity immutable gates are intended to prevent.

Introduce a signed, immutable `review_attestation` bound to the exact claim statement hash and gate-bundle hash. It should record reviewer role/identity, verdict (`approve | reject | needs_revision`), checklist version, scope, timestamp, and optional expiry/revocation/supersession link. A review of one statement version must not carry over to a successor statement. The gate accepts only a currently valid, appropriately scoped approval. This is not a proposal to automate human judgment; it makes the existing human decision enforceable.

**Cost:** Identity/key-management policy, attestation storage, and review UI/CLI. The main new failure mode is unavailable or compromised reviewer credentials; require explicit revocation and human recovery procedures.  
**Evidence:** **CONJECTURE** as an integration mechanism; validate in M1 with fixtures proving a review for the wrong statement, stale bundle, rejected verdict, and revoked approval cannot pass. The need is directly exposed by §7/§10.  
**Invariant check:** Keeps statement review human-controlled and makes it harder for strategy to fabricate approval.

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ §7 Statement-level review
-  The human verdict remains the gate.
+  The human verdict remains the gate. It is represented by an immutable,
+  attributed `review_attestation` bound to `{claim statement hash, gate-bundle hash,
+  review scope, checklist version}` with
+  `verdict ∈ {approve, reject, needs_revision}`, reviewer role/identity, issuance time,
+  and optional expiry, revocation, or supersession reference. A gate accepts only an
+  unrevoked `approve` attestation whose scope covers the requested promotion; an
+  attestation for a superseded statement hash or different bundle is not transferable.
@@ §13 M1 — Done when
+  The statement-review fixture proves that an absent, rejected, revoked, stale-bundle,
+  or wrong-statement review attestation cannot satisfy formalization or high-scrutiny
+  admission, while a correctly bound human approval can.
```

## 5. Make ladder decisions statistically reproducible and limit `REJECT` to its evidence  
**Severity:** MED  
**Section:** §6  
**Component improved:** ladder result-table/verdict contract

**Rationale:** The ladder’s conceptual design is sound, especially preregistration, gate-owned entropy, A/A control, and the scoped `KEEP_IN_SAMPLE` ticket. Two implementation-critical details remain underspecified:

1. “CI radius,” “whole claim CI,” and the 60-bit prediction band do not define the estimator, pairing, confidence coverage across sizes, treatment of multiple tested models/rungs, or baseline-run randomness. Different implementations can therefore produce different `KEEP` outcomes from the same trials.
2. The prose says a method that fails at 50 bits “is refuted on the spot,” but the preceding and later text correctly says finite tests only refute the declared measured cost/performance model. A measured failure must not permanently blacklist a broader method family or a revised model; §4’s measured-reach rule points in the right direction, but the ladder artifact should explicitly carry that reach.

Pin a complete comparison protocol in the gate bundle: primary estimator, paired-instance scheme, CI method and joint coverage/multiplicity rule, fixed model-selection rule, and baseline skill revision. A baseline upgrade begins a new protocol version; prior verdicts remain historically valid but are not silently recomputed or mixed. Require `REJECT` to emit the exact failed predicate and measured reach.

**Cost:** More fixture work and possibly wider intervals/more trials. No new dependency necessarily.  
**Evidence:** **PROVEN-in-source** for the need to define a test statistic and coverage before decision; the plan’s existing ladder evidence in `research/PROPOSALS.md` should support the selected estimator.  
**Invariant check:** Tightens the immutable ladder; does not convert statistics into independent promotion evidence.

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ §6 Protocol (2)
-  The band is always a ratio against the best generic baseline the harness ships,
+  The ladder plan fixes a versioned comparison protocol: the primary estimator, candidate
+  and baseline pairing on gate-generated instances, treatment of algorithm randomness,
+  CI construction and joint coverage across rungs, multiplicity/model-selection rule, and
+  the exact baseline skill revision. The band is always a ratio against the best generic
+  baseline the harness ships under that protocol,
@@ §6 Protocol (2c)
-  `REJECT` (refutation floor failed, `xP ≠ Q` on any trial, memory cap exceeded, or an
-  in-sample or out-of-sample miss of the pre-registered model),
+  `REJECT` (refutation floor failed, `xP ≠ Q` on any trial, memory cap exceeded, or an
+  in-sample or out-of-sample miss of the pre-registered model), with the result table
+  recording the failed predicate and its measured reach: the exact hypothesis/cost model,
+  parameter point or declared region, and baseline-protocol version. A ladder REJECT is a
+  measured refutation only of that recorded reach, never of an unqualified method family
+  or asymptotic claim.
@@ §6 Protocol
+  Landing a new baseline revision creates a new ladder-protocol version. Existing verdicts
+  retain their original protocol version and are never silently reclassified; claims and
+  tickets may compare results only within one protocol version unless a separately
+  preregistered bridge study is admitted.
```

## The three proposals I would stake the most on

1. **#1 — Fix the M0 `justify` contradiction.** It is a concrete inconsistency in the bootstrapping milestone and risks encoding the wrong calibration rule at the foundation.  
2. **#2 — Repair auditor sampling semantics.** The plan currently claims a quantitative guarantee that its priority sampling policy does not support.  
3. **#3 — Specify the checkpoint authority boundary.** The append-only log is load-bearing for non-rewritable negative knowledge; the current M0 ownership/write model is not implementable as stated.

## Framing assessment

I do **not** think the overall framing is wrong. The central frame—an ECDLP break is overwhelmingly unlikely, while rigorous negative results and subproblem advances are worthwhile—is exactly right and should remain load-bearing.

The one framing risk is local: §6’s rhetoric occasionally calls a finite ladder failure a refutation of an “attack,” while its actual epistemic model only supports refuting a declared measured cost model over measured scope. The proposed revision fixes that without weakening the ladder.

## Facts still needed

1. **Checkpoint threat model and deployment facts:** target OS/filesystem, whether a distinct-identity append helper is feasible, recovery behavior after helper outage, and who controls its credentials.  
2. **Human-attestation governance:** accepted reviewer identities/roles, key storage and revocation process, required review scopes for each scrutiny tier, and whether approvals expire.  
3. **Exact ladder statistical protocol:** estimator, paired-trial design, confidence procedure, multiplicity policy, and expected M1 trial cost after applying those choices.  
4. **Auditor population/cost data:** expected node counts by tier, fan-in distribution, re-verification costs, and whether the intended `f=0.01`, `bits=20` cadence is operationally affordable.