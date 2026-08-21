# Cairn plan-r5 — guard round, repository-reading seat (r6)

## Part 0 — facts checked against the repository

Verified: rho pricing (0.11 µs/iter, 0.886√n, 1.25√n, BSGS ≈ 1.5√n with √n entries, 60-bit trial ≈ 1.3×10⁹ ops, CONJECTURE above 50 bits) — `briefs/adjacent-distributed-collision-search.md:50-51`; re-derived 30 / 10³ / 3×10⁴ core-hours, the 0.14 radius, n ≳ 130 (≈ 137), exp(−π) ≈ 4.3 %, l ≈ 1.4×10³, the 4× miss at exponent 0.4. `leanchecker --fresh` 32.3 s mathlib-free, rejects neither `sorryAx` nor extra axioms, raw export unstable, closure hash CONJECTURE, `landrun` Linux-only — `grounding/lean-checker-protocol.md:40-41,50,53-56`. `gp` exits 0 on fatal errors, zero-fills arguments, 60-bit `ellcard` overflows the default stack at ≈ 75 ms, draws span 11–220, `gp`/`cypari2` one implementation, BSGS-vs-SEA independent only ≤ 50 bits, Sage absent, the four corpus seeds — `grounding/pari-sage-toy-curve-backend.md:8,14,18-24,29,33-36`. ∃-linter blind spots and `collectAxioms` — `grounding/lean-statement-linters-vacuity.md:16,24`. SDK composes the subagent prompt; `setting_sources=[]` unprobed — `grounding/dbos-sqlite-and-agent-sdk-isolation.md:29-35,40`. Hallucinated-table incident — `PROPOSALS.md:245-246`. Budget = meet(parent, profile), no cumulative term — `PROPOSALS.md:492-521`. Nuance: §2's "Sage's `discrete_log` checks `base^res == a`" is `discrete_log_rho` L807-809 in the brief's §7 — right fact, imprecise name. Could not verify: an owner for the verifier behind the `Verifiable` grade — C4 (`PROPOSALS.md:180-228`) specifies the rho witness verifier only (proposal 1).

## Proposals (duties 1–3 folded in where they coincide)

**1 · `Verifiable` names no verifier owner, so a producer-shipped verifier passes its own reproducibility check · MED · §3, §7, §13 M1.**
§3:186 "`Verifiable` (a witness checked by a deterministic verifier)"; §3:143 "for a `Verifiable` recipe each witness is its own attempt and must pass its verifier"; §7:846 `repro_node (a Verifiable or Replayable attempt, §3)`; M1 (m) :1265 "a reproducible Tier-1 measurement with its repro node is admitted by `justify` to STRONG-EMPIRICAL". Nothing names who ships the verifier. Gaming (reproducibility gate): a Tier-1 skill emits `Verifiable` nodes whose "verifier" is a function in its own revision that returns pass; "the witness is always checked" (§3), the node is a `repro_node`, and `justify` derives STRONG-EMPIRICAL. Count, instances, nonce and axioms are gate-owned so that no number from the gated party reaches a gate (§6 (3)); the witness verifier is the one left out. `Replayable` is safe (the gate re-runs). Cost: one clause, one fixture. Evidence: the plan's own rule; CONJECTURE that a worker does it, but it is the evaluator-memory shape at `PROPOSALS.md:246`.
```diff
- Verifiable (a witness checked by a deterministic verifier),
+ Verifiable (a witness checked by a deterministic verifier that is a gate-bundle object or a
+ certified skill whose §2 identity bundle differs from the witness producer's and whose
+ self-test carries a must-FAIL witness; a witness whose only verifier ships in its
+ producer's revision is graded AuditOnly),
```
M1 fixture: a `Verifiable` node verified only by its producer's revision is AuditOnly and `justify` returns the CONJECTURE ceiling.

**2 · The orchestrator may withdraw (§4, §5) and may not (§13 M3) · MED.**
§4:364-366 "remains active for the orchestrator's next tick to fund within budget, park with `budget_preempt` or withdraw"; §5:593-595 "parks the branch with `budget_preempt` or withdraws it"; §13 M3:1346-1347 "no REFUTED row and no terminal `withdrawn` status is written by the orchestrator's path in any run". Both sides landed in r4 (#11, #17). An implementer following §5 fails M3's bar. §4 decides the side: "a pivot or a stall never writes REFUTED: it writes PARKED" — the orchestrator's terminal vocabulary is PARKED; withdrawal is "terminal and reason-bearing", the worker's or human's act.
```diff
- ... to fund within budget, park with `budget_preempt` or withdraw.
+ ... to fund within budget or park with `budget_preempt`; withdrawal is the branch worker's
+ or the human's reason-bearing act, never the orchestrator's (§13 M3).
```
Same edit at §5:594; M3 unchanged.

**3 · The ≤ 50-bit rungs have two tiers, and one deadlocks · MED · §5, §6.**
§5:470 "The ladder's distribution rungs (§6, ≤ 50 bits) are Tier-1"; §6:666-668 "each rung's tier follows its declared cost profile under the chosen count (an interpreted 50-bit baseline at that count runs for hours, a compiled one for minutes; M1 records which)"; §5:487-489 "the gate derives the launch's tier from the profile's production cost". If the table assigns the 50-bit rung Tier 2 (three arms × ≳ 130 trials, interpreted, is hours), its ticket is "a ladder result table with verdict KEEP" (§5:571), which only this rung mints, and KEEP_IN_SAMPLE "is a Tier-2 ticket valid for the 60-bit rung ... and for no other launch" (§5:575-577). The 60-bit rung already has the scoped-ticket answer; the small rungs need it stated once. The rung's cost is gate-bounded (patience ceiling × count × arms are ladder-plan fields), so this is no self-declared spend.
```diff
- The ladder's distribution rungs (§6, ≤ 50 bits) are Tier-1; its 60-bit rung is tiered by its own declared cost profile.
+ The ladder's distribution rungs (§6, ≤ 50 bits) are admitted on the Tier-1 ticket whatever
+ tier the boundary table assigns their ladder-plan-bounded cost, because they are the launches
+ that mint the Tier-2 ticket; the 60-bit rung is tiered by its own declared cost profile.
```
§6:667 "each rung's tier" → "each rung's budget".

**4 · Tier-1 sharding: the tier gate tiers launches, never their sum · MED · §5, §13 M1.**
§5:487-489 derives the tier per launch; §5:515-516 "A spawned worker's budget is the meet of its parent's remaining budget and the skill's declared profile"; §0:17-18 the orchestrator rewrites "funding ... freely". Gaming (tier gate): a 90-bit validation rho becomes 1,000 honest one-core-minutes DP-walk launches, each declared truthfully, each on the Tier-1 ticket: no `TierRefused`, no P4 signal (measured = declared), no KEEP ever required. It needs a branch grant at Tier-2 scale, which §0 lets the orchestrator set. The text has no cumulative rule. Cost: one gate-owned counter (production cost charged to a hypothesis key under its current best ticket), a second boundary-table column (per-key cumulative edge; M1 sets it above the ladder's own cost), one fixture. Spend only; no tag moves.
```diff
- A spawned worker's budget is the meet of its parent's remaining budget and the skill's declared profile;
+ A spawned worker's budget is the meet of its parent's remaining budget, the skill's declared
+ profile, and the boundary table's cumulative edge for the tier its best ticket admits less the
+ production cost already charged to the hypothesis key under that ticket — the launch that
+ would cross the edge is `TierRefused`;
```
M1 fixture: a branch on the Tier-1 ticket whose launches would sum past the Tier-1 cumulative edge is refused at the crossing launch.

**5 · The memory axis has no gate-owned measurer · MED · §6.**
§6:679-681 "measured by the harness as peak algorithmic table and spill bytes with RSS as a diagnostic, an unaccounted storage channel failing closed". The harness cannot see a method's "algorithmic table" unless the method reports it, and the one quantity it can measure is the diagnostic. Gaming (ladder): hold the BSGS-sized table in ordinary process memory, report table bytes = 0; the cap never binds, and "failing closed" has no predicate behind it. §6 (3) states the principle ("a number produced by the party being gated is the hallucinated-ablation-table failure under another name") and the clock check has the right shape.
```diff
- measured by the harness as peak algorithmic table and spill bytes with RSS as a diagnostic, an unaccounted storage channel failing closed;
+ measured by the harness as peak RSS over the trial's process tree less the A/A arm's peak
+ RSS on the same instances (at the 60-bit rung, less the clock calibration run's), the table
+ bytes a method reports being a diagnostic column;
```

**LOW (wording; one line each).**
6. §5:546-553 "five launch-supplied inputs ... nothing the launching party writes reaches the gate except those five" lists the self-test standing and the ticket, both gate-resolved; read literally the launch hands over a ticket and the stale-KEEP closure at :557 ("a later REJECT ... displaces an older KEEP") has no enforcer. Fix: "three launch-supplied inputs ...; the gate resolves the revision's standing and the ticket from the key".
7. §0:17-18 "worker prompts" are mutable, while §4:418 puts "the worker role templates" in the bundle and §4:385 calls them read-only. Fix §0: "the nodes handed to a worker, never a role template (§4)".
8. Ceremony: `do_not_cache` (§3:129) has no setter and no reader anywhere; `execution receipt` (§3:114) is undefined. Cut the bit or name its setter; define the receipt as `{CPU seconds over the process tree, peak RSS, exit status, ceiling}` — its consumers are then the clock check (§6 (3)) and proposal 5.
9. §10:1074-1079 closes the human-queue class enum, yet §6:648-650 (shape departure) and §4:356-358 (`Leaked`, "escalated") route to no class. Add `shape_departure`, `leaked`.
10. §13 M1 (h) :1255 needs the transitive `justified_by` walk that §7:878 gives the M4 auditor; M1's Adds never names it. Name the walk at M1; sampling stays M4.
11. §4:323 "range jitter cannot mint a clean key" holds only for regions containing a measured point; a region excluding every measured point is `Allowed`, a new cost model is a new key, and each re-ladder REJECT is "a gate outcome" (§5:534), so under the P3 surrogate REJECT farming on one method is reward-positive. Not a ladder defect (the REJECTs are true); fix at M3's bar: a seeded run where one branch family pre-registers k junk models or jittered regions on one method must not out-earn control (j).

## Duty 2 — what holds

Consumers exist for: golden certificate (tier-gate refusal), witness certificate (verifier, repro gate), ledger (preflight), gate plan (ordered scopes), self-tests (yank, refusal), result table (ticket, `justify`), human queue (closed by human-path record), dispatch record (ladder identity refusal, canary), audit record (`audit_shortfall`, downgrade/re-derive), P4 alarms (retirement stated), tag history (disagreement protocol's pre-dispute level, egress renderer). Names promising more than delivered: `Verifiable` (1), "measured by the harness" (5), "launch-supplied" (6).

## Duty 3 — gates closed in text

Submission verifier: no path found — "accepts only `exit == 0` and `stdout == "OK"` and empty stderr", content-addressed inputs, typed writes. Ladder count/instances/clock: "the count is the gate's measurement, never the claimant's". Formalization gate: the Prover writes the formal statement at claim open, and "a green artifact without one leaves the claim at its pre-review tag" plus the non-waivable review closes it. Preflight: the interface-version bump remains the open question r1–r5 name; proposal 11 is the region half. Open: 1 (reproducibility), 4 and 6 (tier gate), 5 and 11 (ladder and ledger).

Nothing above touches §0, the gate set, the taxonomy or the baseline, re-proposes a rejected item, or challenges an operator default.

## Verdict

(a) **NOT STEADY** — five MED defects: two section-level contradictions (2, 3) and three gates the gated party can satisfy as written (1, 4, 5).
(b) Fix first: **1** — the only one through which a tag, not merely spend, is reachable without a gate-owned check.
(c) Framing: sound. One remark — every residual here is a clause stated in two sections or a quantity named without its measurer, the accretion cost of 1,473 lines; after these one-clause edits the plan's own §13 rule ("a running 40-bit slice will reveal more than more architecture will") is the next move, not a seventh round of mechanisms.
