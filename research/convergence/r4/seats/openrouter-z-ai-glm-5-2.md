# Review of plan-r3.md

The plan is exceptionally thorough. Most sections are sound. I found six concrete issues worth revising; three are structural. I am not manufacturing changes where the text already holds.

---

## 1. `TierRefused` has no defined consumer in the orchestrator · HIGH · §5

**Rationale.** The plan states a tier-gate refusal "is a `TierRefused` record the ledger keeps, not an exception the orchestrator can catch and retry around." This correctly prevents silent retry-around, but then specifies no behavior at all. The orchestrator's contract is defined for funding, parking, pivoting, and withdrawing — but not for "the gate refused my launch." An implementer reading §4 (Orchestrator) and §5 together has no defined action: does the branch park? With what blocker? Does the orchestrator seek a cheaper ticket? Does it withdraw? Without this, the orchestrator either deadlocks (polling a refused launch) or improvises. The `PARKED` blocker taxonomy in §4 already has `budget_preempt`; a tier refusal is a different condition — the branch is not out of budget, it lacks a ticket — and needs its own blocker so the revival predicate is distinct.

**Change:**

```diff
--- a/plan-r3.md (§4, Orchestrator)
+++ b/plan-r3.md (§4, Orchestrator)
-A pivot or a stall never writes REFUTED: it writes PARKED with a blocker
-`∈ {low_yield_pivot, budget_preempt, human_park}` that clears under a stated
-predicate (an epoch count or a budget threshold) and auto-revives like any
-other blocker.
+A pivot or a stall never writes REFUTED: it writes PARKED with a blocker
+`∈ {low_yield_pivot, budget_preempt, human_park, tier_refused}` that clears
+under a stated predicate (an epoch count or a budget threshold) and
+auto-revives like any other blocker. A `tier_refused` park records the
+`TierRefused` record it stems from and clears when a new admissible ticket
+at the required tier lands for the same hypothesis key and method
+identity; the orchestrator may seek one by funding a cheaper-tier launch
+or by withdrawing the branch, but never by re-submitting the refused
+launch under a repointed branch (§5 ticket binding).
```

---

## 2. `RequiresNullControl` re-measurement has no resolution semantics · HIGH · §4

**Rationale.** The `RequiresNullControl` preflight is well-motivated: a refutation resting on a measurement without a null arm must be re-measured, and the re-measurement is enqueued away from the proposing worker. But the plan specifies only that "the blocker clears when it lands, after which the preflight re-runs to `Allowed` or `Blocked`." It never says what happens to the *original* refutation if the re-measurement contradicts it. If the original said "method fails at point p" and the re-measurement (now with a null arm) says "method succeeds at p," the original evidence node is stale — but the plan says REFUTED is permanent unless the retry predicate is met. A re-measurement that overturns the original is not a retry; it is a *retraction*. The plan needs a resolution rule or the ledger accumulates contradictory evidence with no defined precedence.

**Change:**

```diff
--- a/plan-r3.md (§4, Ledger preflight)
+++ b/plan-r3.md (§4, Ledger preflight)
-its table is appended to the entry as a new evidence node,
-and the blocker clears when it lands, after which the preflight re-runs to
-`Allowed` or `Blocked`.
+its table is appended to the entry as a new evidence node,
+and the blocker clears when it lands, after which the preflight re-runs to
+`Allowed` or `Blocked`. If the re-measurement's verdict contradicts the
+original refutation (the original recorded failure and the re-measured
+table does not), the original evidence node is marked `retracted` — an
+append-only tag, never a deletion — and the ledger entry's status moves
+from `REFUTED` to `PARKED` with blocker `null_control_contradicted`,
+requiring a fresh formal or measured refutation to re-establish it; the
+`retracted` node remains addressable but is inadmissible as evidence
+(§3), and a retraction is itself a terminal-status obligation the
+foundations auditor (§7) checks.
```

---

## 3. Verification budget reservation is not released on failure · MED · §5

**Rationale.** §5 says "the tier gate reserves the verification component from the grant at launch and refuses a launch whose verification the remaining budget cannot cover." This is correct for admission. But when a run fails (`BUDGET_EXCEEDED`, `SKILL_YANKED`, or any `status ≠ OK`), the reserved verification budget is not spent — a failed attempt is never cached and never reproducibility-checked. The plan never states the reservation is released back to the parent's remaining budget. Without this, every failed attempt permanently consumes its verification reservation from the branch's budget, and a branch that fails several times can exhaust its budget on reservations for verification that never happens. This is a silent budget leak that penalizes honest exploration of hard subproblems.

**Change:**

```diff
--- a/plan-r3.md (§5, Mechanism)
+++ b/plan-r3.md (§5, Mechanism)
-the tier gate reserves the verification component from the grant at
-launch and refuses a launch whose verification the remaining budget
-cannot cover.
+the tier gate reserves the verification component from the grant at
+launch and refuses a launch whose verification the remaining budget
+cannot cover. The reservation is released back to the parent's
+remaining budget when the attempt reaches a terminal status, whether
+the verification ran (status OK: the reservation is spent) or did not
+(status ≠ OK: the reservation is released unspent), so a failed
+attempt costs only its production budget, not its verification
+reservation.
```

---

## 4. `justify`'s coverage direction is ambiguous · MED · §7

**Rationale.** The plan says `justify` "checks that the evidence's declared target, assumptions and population cover that exact statement." "Cover" is used in one direction for population (evidence.population ⊇ statement.scope — the evidence was measured on a population that includes the statement's scope) but the direction for assumptions is the opposite in standard logic: evidence proved under *weaker* assumptions is *stronger* and covers a statement with *stronger* assumptions. The plan never disambiguates. An implementer could build it either way, and the wrong choice either admits evidence that doesn't apply or rejects evidence that does. This is the core epistemic function; the direction must be pinned.

**Change:**

```diff
--- a/plan-r3.md (§7, "The tag is derived, never set")
+++ b/plan-r3.md (§7, "The tag is derived, never set")
-which checks that the evidence's declared target, assumptions and
-population cover that exact statement and returns a typed justification
-or a lattice violation, never a boolean
+which checks that the evidence's declared target matches the statement
+hash exactly, that the evidence's declared population is a superset of
+the statement's scope (the evidence was measured on a population that
+includes everything the statement claims about), and that the
+evidence's assumptions are a subset of the statement's assumptions
+(the evidence was proved under no stronger assumptions than the
+statement requires — evidence under weaker assumptions is stronger and
+covers it), and returns a typed justification or a lattice violation,
+never a boolean
```

---

## 5. Checkpoint file has no compaction strategy · MED · §3

**Rationale.** The hash-chained log's checkpoint is "a file beside the gate-bundle pin... writable by the orchestrator's process user" with an append-only flag. Over a long-running research campaign, this file grows monotonically — every gate run appends the chain head. The plan specifies no rotation, compaction, or truncation strategy. A multi-month run could produce a checkpoint file of hundreds of MB, slowing startup verification (which reads it). The tamper-evidence property must be preserved under compaction: the compacted checkpoint must hash to the same chain head as the full log it replaces, and the compaction itself must be operator-gated (the orchestrator's process cannot initiate it, since that would let it rewrite history).

**Change:**

```diff
--- a/plan-r3.md (§3, Retention)
+++ b/plan-r3.md (§3, Retention)
-from M4 a writer the substrate's own process cannot truncate — and a log
-that does not extend the last checkpoint fails verification at startup
-and before any promotion, while a checkpoint that cannot be reached or
-extended blocks promotion rather than disabling checkpointing.
+from M4 a writer the substrate's own process cannot truncate — and a log
+that does not extend the last checkpoint fails verification at startup
+and before any promotion, while a checkpoint that cannot be reached or
+extended blocks promotion rather than disabling checkpointing.
+Checkpoint compaction: the operator may, in a session the orchestrator's
+process cannot initiate, replace the checkpoint file with a compacted
+form whose content is `{prior chain head, compacted-from sequence
+number, compacted-to sequence number, new chain head}` signed by the
+operator; the compacted checkpoint verifies against the same chain head
+the full log would produce, and the full log is retained until the
+compacted checkpoint is verified. A compacted checkpoint that does not
+verify blocks promotion exactly as a missing one does.
```

---

## 6. `BUDGET_EXHAUSTED` vs `BUDGET_EXCEEDED` naming collision · LOW · §5/§7

**Rationale.** `BUDGET_EXCEEDED` (§5) is an attempt status when the harness-enforced runtime ceiling is hit. `BUDGET_EXHAUSTED` (§7) is a counterexample-hunt verdict when the pre-registered trial count is spent without finding a counterexample. These are semantically distinct — one is a per-run enforcement event, the other is a planned budget outcome that is a valid (non-failing) terminal state for a hunt — but the names differ by one letter. An implementer reading both sections in one sitting will confuse them. Renaming the hunt verdict costs nothing and prevents a class of bugs where a `BUDGET_EXHAUSTED` hunt is treated as a `BUDGET_EXCEEDED` attempt (which is never a ticket, never evidence).

**Change:**

```diff
--- a/plan-r3.md (§7, Strong law of small numbers)
+++ b/plan-r3.md (§7, Strong law of small numbers)
-  verdict ∈ {SURVIVED, KILLED, BUDGET_EXHAUSTED}}`; SURVIVED under the
-declared budget is the Tier-2 ticket for a conjecture (§5), KILLED writes
-the ledger entry of §4, BUDGET_EXHAUSTED is no ticket
+  verdict ∈ {SURVIVED, KILLED, HUNT_SPENT}}`; SURVIVED under the declared
+budget is the Tier-2 ticket for a conjecture (§5), KILLED writes the
+ledger entry of §4, HUNT_SPENT is no ticket
```

---

## (a) Three proposals I would stake the most on

1. **#1 (TierRefused consumer).** Without a defined orchestrator behavior, the system has a dead-end state with no exit. This is a contract gap, not a design preference.
2. **#2 (RequiresNullControl resolution).** The plan introduces a re-measurement mechanism with no resolution rule for the case where the re-measurement overturns the original. A ledger that can hold contradictory evidence with no precedence rule is a ledger that can be gamed by re-measurement.
3. **#3 (Verification budget release).** This is a silent budget leak that directly penalizes the system's core behavior — exploring hard subproblems where early failures are expected. It is cheap to fix and the fix unlocks honest exploration.

## (b) Where the plan's framing is right

The framing is sound. "Mutable strategy, immutable epistemics" (§0) is the correct axis, and the separation of taste (human, §10) from execution (machine) is the right decomposition. The honest baseline (§14) is load-bearing and correctly treated as non-negotiable. I would not revise the frame.

## (c) Facts the plan does not state that I would need

- The measured constant `c` in the toy-curve generator's `≈ c·ln p` tries profile (the plan says "M0 measures" it but the value is absent; it determines whether the generator's cost profile is honestly Tier-0 or occasionally Tier-1 at 50 bits).
- Whether the OS-level append-only file flag (chflags on macOS, chattr on Linux) actually binds against a non-owner writer on the target platform — the plan flags this as a stack fact to verify at M0, but the entire checkpoint mechanism (§3) rests on it, and if it does not hold, the checkpoint must be re-architected before M2.
- The actual `leanchecker --fresh` cost on a mathlib-importing Challenge — the plan says "M1 measures it" but the formalization gate's tier classification (Tier 1 vs Tier 2) and the fixture corpus sizing both depend on this number, and the plan's "a Lean compile at Tier 1" explicitly excludes this gate's cost.