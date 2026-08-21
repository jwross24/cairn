# Own view — round 3 (written before opening any seat file)

Plan under review: `research/convergence/plan-r2.md`. Five weaknesses, most important first.

## 1. Ladder decision variable ownership — who counts group operations (§6, §5) — MED/HIGH

§6 decides KEEP on "group operations" and says the band is "measured in the same harness on the same instances", but nothing states that the harness owns the group-operation counter. A claimant's method is a worker-authored skill; if it reports its own `ops`, the ladder's primary metric is self-reported and the top anti-fabrication device trusts the thing it tests. Memory already has the right shape ("measured by the harness as peak algorithmic table and spill bytes with RSS as a diagnostic, an unaccounted storage channel failing closed"); ops do not. The same gap reaches the §5 budget ceiling: "a multiplier of the declared expectation" names no unit the harness can enforce on a subprocess (CPU-seconds is enforceable; group ops are not observable from outside). Fix shape: the ladder runs every method, claimant and baseline, against a harness-owned counted group-arithmetic interface; ops are read from that counter, never from the skill's output; CPU-seconds per trial are recorded by the harness and the ops-to-CPU ratio is compared against the baseline's on the same rung so an ops count that the CPU time cannot support is INCONCLUSIVE at best (never KEEP); the cost ceiling is enforced in CPU-seconds (the declared expectation in ops converted by the rate measured on the A/A arm or declared directly in CPU-seconds).

## 2. Band arithmetic does not KEEP the √2 positive control at 10² trials (§6(2), §13 M1 (j)) — MED

With sd ≈ 0.5·mean and 10² trials per arm, the SE of each mean is ≈ 5 %, the ratio's 95 % CI radius is ≈ 14 %, so the A/A radius is ≈ 0.14 and the band `1 + 2·radius` ≈ 1.28. Negation-map rho's ratio is 1.41 with its own CI ≈ [1.22, 1.61]; "the whole claim CI clears the band" fails (1.22 < 1.28) and fixture (j) returns INCONCLUSIVE. The "floor 1 %" suggests the author expected a radius of a few percent, which 10² trials at sd = 0.5·mean do not deliver. Either the band is `1 + radius` against the claim CI (then (j) passes at 10² trials: 1.22 > 1.14), or the trial count is sized from the positive control (≈ 10³ trials, which at 50 bits is ≈ hours of one core in compiled code and leaves Tier 1). The plan must say which, and say that the ladder plan's trial count is set so that (j) is KEPT with margin and (k) INCONCLUSIVE — the positive controls size the ladder plan, not the other way round.

## 3. Tier 1 has no named ticket kind (§5) — MED

"Each tier's admission ticket is a result from the tier below" and the predicate reads "the most recent admissible substrate node of the kind the tier requires", but the plan names ticket kinds only for Tier 2 (ladder table / counterexample-hunt record) and Tier 3 (adds justification, certificate plan, sign-off). A fresh implementer cannot write the Tier-1 branch of the predicate: is the Tier-1 ticket the hypothesis object (§3) plus the Tier-0 coherence checks (statement node exists, no-go declaration present), or nothing? M0's done-when refuses "a tier two above its ticket", so the ticket lattice must be total at M0. Name it: Tier 1's ticket is the branch's hypothesis object (and claim statement node where a claim exists) with the §8 presence check passed — a Tier-0 result by construction — or state explicitly that Tier 1 is ticket-free and the gate checks only budget.

## 4. 60-bit rung trial count is ambiguous (§6(2b)) — LOW/MED

(2b) fixes `m = 10` hold-out instances and then says "a full 10²-trial distribution check at 60 bits is Tier-2 work by its own declared profile". An implementer cannot tell whether the 60-bit rung runs `m` trials (≈ 10 × 1.3×10⁹ ops, minutes-to-an-hour compiled — arguably Tier 1 by cost) or 10² trials, whether the baseline runs at 60 bits at all (the out-of-sample check is the claim's own fitted model against its own 60-bit mean, so it need not), and whether the A/A arm exists at 60 bits. State: the 60-bit rung is `m` claimant trials only; no baseline or A/A arm runs there; its tier is whatever its declared profile says; the 10²-trial sentence is a pricing remark and not part of the rung.

## 5. M2's done-when does not exercise the mechanisms M2 adds (§13) — LOW/MED

M2 adds the ledger preflight with measured-point reach and the `supersedes_refuted_review` park, the hash-chained log and its head checkpoint, the terminal-status invariant (Leaked records) and the near-duplicate advisory, but its done-when is only "a parked branch auto-revives on blocker-clear; a refuted one is never re-walked". Dependency sanity (rule 10b) wants each mechanism built in a milestone whose done-when can fail on it: a log truncated to a valid prefix must fail startup verification against the checkpoint; a worker exiting with an open claim must produce a Leaked record; a proposal whose declared range contains a measured REFUTED point (jittered key) must be Blocked; a superseding hypothesis object of a REFUTED one must park. Without fixtures the checkpoint and the Leaked record are built by nobody's test.

## Also noted (not in the five)

- §4 dispatch record has fields scattered across §4, §6, §7 (role, prompt nodes, allow-list, handle scope, hypothesis hash, purpose, budget) and no single typed shape or milestone; the tier gate's "declared purpose" field is read from it.
- §6 `RequiresNullControl` can only arise for counterexample-hunt records or pre-A/A entries; harmless but unexplained.
- §5 Tier-2 arithmetic (30 / 10³ / 3×10⁴ core-hours) and §7 auditor bound (l ≈ 1.4×10³) recompute correctly.
