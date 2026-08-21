# Review of plan-r4.md

## 1. Dual-ticket requirement for claims carrying both an algorithmic cost claim and a correctness conjecture · HIGH · §5

**Component improved:** Tier gate predicate (§5).

**Cost:** One additional clause in the tier gate's ticket-lattice definition. No new infrastructure; the gate already reads both ticket kinds. Failure surface: a claim that declares both an algorithmic cost model and a correctness conjecture must produce both tickets before Tier-2 spend, which is the correct behavior and costs only what the two tickets already cost.

**Evidence:** The plan itself establishes the need: §5 specifies "for Tier 2 on an algorithmic claim the ticket is a ladder result table" and "for Tier 2 on a conjecture it is a counterexample-hunt record" as separate branches. A claim that says "method M solves DLP in O(n^{1/3}) ops and always terminates" carries both an algorithmic cost claim (ladder-testable) and a correctness conjecture (hunt-testable). The plan has no branch for "both." An implementer reading the predicate as written would pick one ticket kind, leaving the other untested. This is a missing gate, not an over-engineering risk. STRONG-EMPIRICAL (the gap is structural, derivable from the plan's own definitions).

**Does not touch §0, gates, or calibration boundaries:** Adds a requirement, never removes one.

```diff
--- a/plan-r4.md
+++ b/plan-r4.md
@@ §5, Tier gate predicate, ticket lattice
- for Tier 2 on a conjecture it is a counterexample-hunt
- record (§7) with verdict SURVIVED (plus the P1 floor, if adopted); for Tier 2 on a theorem
- claim whose formalization-gate run declares a Tier-2 profile it is the claim statement node with a
- `review_verdict` of `approve` (§7)
+ for Tier 2 on a conjecture it is a counterexample-hunt
+ record (§7) with verdict SURVIVED (plus the P1 floor, if adopted); for Tier 2 on a theorem
+ claim whose formalization-gate run declares a Tier-2 profile it is the claim statement node with a
+ `review_verdict` of `approve` (§7). A claim whose hypothesis object carries both an
+ algorithmic cost model and a correctness conjecture requires both tickets — a ladder
+ result table with verdict KEEP (or KEEP_IN_SAMPLE scoped to the 60-bit rung) and a
+ counterexample-hunt record with verdict SURVIVED — and the gate refuses if either is
+ absent; the ticket lattice's meet is the stricter ticket, so a KEEP_IN_SAMPLE table
+ plus a SURVIVED hunt admits only the 60-bit rung and no other Tier-2 launch.
```

## 2. Worker subprocess crash recovery — the `INTERRUPTED` status · MED · §4, §13

**Component improved:** Terminal-status invariant (§4) and M0/M1 crash recovery.

**Cost:** One new attempt status constant and a restart scan. No new dependency. Failure surface: the scan must run before any new launch on restart, which is a simple ordering constraint.

**Evidence:** The plan specifies `BUDGET_EXCEEDED` and `SKILL_YANKED` as harness-terminated statuses and says "a harness-terminated attempt is not a leak." But a worker subprocess killed by a harness crash or OS signal is neither a worker exit (which produces `Leaked`) nor a harness-terminated attempt. On restart, the attempt record has a non-terminal status and no living process behind it. The plan's