Let me carefully review this plan against the three duties specified: coherence of the constraint web, ceremony audit, and gaming the gates. I need to find demonstrable defects with evidence from the text itself.

Let me work through each duty systematically.

**Duty 1: Coherence of the constraint web**

Let me trace through the mechanisms across sections to find contradictions, duplicated rules, or rules that mechanisms could violate.

1. Let me check the terminal-status invariant in §4 against the orchestrator's vocabulary in §4 and §13 M3.

§4 says: "Withdrawal is terminal and reason-bearing, the act of the branch's worker or of the human and never of the orchestrator, whose own vocabulary is PARKED (§13 M3)"

§4 also says about harness-terminated attempts: "the obligation stays with the branch, which remains active for the orchestrator's next tick to fund within budget or park with `budget_preempt`."

This seems coherent - the orchestrator parks but doesn't withdraw.

2. Let me check the KEEP_IN_SAMPLE ticket scoping. §5 says: "a table with verdict KEEP_IN_SAMPLE is a Tier-2 ticket valid for the 60-bit rung of the same hypothesis key and for no other launch; the ticket records that purpose and the gate refuses a launch whose skill and inputs name any other"

§6 says: "KEEP_IN_SAMPLE is the Tier-2 ticket for the 60-bit rung of the same hypothesis key and for nothing else (§5)"

These are consistent.

3. Let me check the tier gate ticket binding. §5 says: "A ticket is bound to a hypothesis, never to a branch" and "the gate compares the ticket's recorded key and method identity with the launch's — and, where the ticket is a ladder table, the implementation revision it ran (§6) with the launch's, so a new revision re-ladders before it spends"

But §3 says about the hypothesis key: "The method identity names the interface version and not the implementation revision because the hypothesis is about a method: a measured refutation of it reaches every implementation revision and a revision bump cannot mint a clean key"

So the hypothesis key excludes implementation revision, but the tier gate checks implementation revision for ladder tables. This is consistent - the ticket is bound to the hypothesis key (which excludes impl revision) but the gate additionally checks impl revision match for ladder tables. No contradiction.

4. Let me look at the §5 cumulative edge and the per-launch tier derivation. §5 says: "the boundary table names a cumulative edge per ticket tier: the launch that would carry the key's charge under its current best ticket past that edge is TierRefused until the next tier's ticket exists"

And: "a tier derived per launch is satisfiable by sharding — a 90-bit validation rho as a thousand honest one-core-minute walks, each on the Tier-1 ticket, no TierRefused, no drift signal, no KEEP ever required"

This is presented as the motivation for the cumulative edge, not a contradiction. The cumulative edge prevents sharding around the tier system.

5. Let me check the §3 disowned mark and §7 justify. §3 says: "a disowned node is served from no cache, is absent to justify (§7), which re-derives every claim transitively justified by it, and is no ticket"

§7 says: "a failed re-verification downgrades the node and re-derives every claim transitively justified by it"

These are consistent.

6. Let me check the §4 ledger preflight's AlreadySettled against §5's tier gate. §4 says: "AlreadySettled = the proposal opens a new branch on a hypothesis key that a branch already holds — an active or parked one, or a promoted one whose claim statement stands at PROVEN or STRONG-EMPIRICAL — or opens a branch whose method identity and claimed cost model equal such a promoted holder's and whose declared parameter region is contained in the holder's"

This is about branch opening, not tier gating. The tier gate checks tickets per hypothesis key. These seem to operate at different levels - preflight before branch open, tier gate at launch. No contradiction.

7. Let me look for a milestone dependency issue. §13 M1 says: "the REFUTED/PARKED entry record of §4 lands here, written by the ladder's REJECT and the hunt's KILLED, while the preflight that reads it arrives at M2"

So M1 writes ledger entries but M2 builds the preflight that reads them. This is fine - M1 creates the data, M2 builds the reader.

8. Let me check if M1's fixtures depend on mechanisms not built at M1. M1 includes: "the proportional-scrutiny router and the no-go checklist's presence check (§8) with the router as its consumer and the nogo_review node the tier gate reads"

M1 also includes: "the human queue as a typed object (§10)"

But M1 doesn't mention building the Librarian. The near-duplicate advisory in §4 says: "before M4 it routes the proposal to the human, or parks it with blocker near_dup_review; from M4 it routes to the Librarian"

This is fine - before M4 it goes to human, not Librarian.

9. Let me check the §6 ladder's 60-bit rung and the tier system. §6 says: "a full 10²-trial distribution check at 60 bits is Tier-2 work by its own declared profile, not Tier-1, is no part of the rung, and runs only when the tier gate grants that budget"

And: "The 60-bit rung runs the claimant's method on the m hold-out instances only — no baseline and no A/A arm run there"

And: "its 60-bit rung is tiered by its own declared cost profile" (§5)

So the 60-bit rung is Tier-2 work admitted by a KEEP_IN_SAMPLE ticket. This is coherent.

10. Let me look at the §5 escrow and the §3 reproducibility policy. §5 says: "the tier gate reserves the verification component from the grant at launch" and "it is spent where the §3 policy's first check runs"

§3 says: "Verifiable ⇒ the witness is always checked; Replayable at Tier 0/1 ⇒ always re-run; Replayable at Tier 2/3 ⇒ re-run at the moment justify (§7) would derive a class above CONJECTURE from the node"

So for a Replayable Tier-2/3 node, the first check runs at justify time, which could be after the branch reaches terminal status. §5 says: "a branch reaching a terminal status returns its unreserved grant and never the escrow of an admissible node it produced, so a withdrawn branch's Tier-2 node stays re-runnable when justify waits on it months later"

This is coherent.

11. Let me look more carefully for contradictions. Let me check the §2 self-test and the §6 ladder trial.

§2 says: "a ladder trial under §6 that returns xP ≠ Q or a self-reported count diverging from the gate's" is a self-test failure that yanks the implementation revision.

§6 says: "xP ≠ Q on any trial" is a REJECT predicate, and "a count divergence is an implementation entry against the revision the dispatch record names, whose retry predicate is a new certified revision, and yanks that revision (§2)"

So §6 says xP≠Q leads to REJECT and yanks the revision, while §2 says a ladder trial with xP≠Q is a self-test failure that yanks. These are consistent - the ladder REJECT for xP≠Q is an implementation entry that yanks, and §2 describes the same event as a self-test failure.

Wait, but §6 also says: "the floor, the memory predicates and the model misses are measured entries on the hypothesis key" - these don't yank. And "xP ≠ Q or a count divergence is an implementation entry against the revision" - these do yank. So the distinction is clear.

12. Let me check the §4 terminal-status invariant and the §13 M3 crash-safe tick. §4 says: "a harness-terminated attempt (BUDGET_EXCEEDED, SKILL_YANKED, or INTERRUPTED... is not a leak: the obligation stays with the branch, which remains active for the orchestrator's next tick"

§13 M3 says: "every attempt in flight at the crash standing at INTERRUPTED on restart — never OK, never a leak"

Consistent.

13. Now let me look for a potential issue with the §7 justify and the §3 AuditOnly grade. §3 says: "AuditOnly is inadmissible as evidence" and "AuditOnly nodes are kept and are not in [the admissible evidence graph]"

§7 says: "a table without it [reproducibility record] has ceiling CONJECTURE"

But what about an AuditOnly node? §3 says it's inadmissible. §7 says the tag is "the strongest class some evidence node justifies via justify". If an AuditOnly node is inadmissible, justify should return nothing for it. But §7 doesn't explicitly say justify rejects AuditOnly nodes. Let me check...

§7 says: "An evidence node is typed: {kind ∈ {lean_artifact, ladder_table, repro_node...}}" - AuditOnly is a replay grade, not an evidence kind. The replay grade is on the attempt/node, not on the evidence kind. So an evidence node of kind ladder_table whose attempt has replay grade AuditOnly... §3 says "AuditOnly is inadmissible as evidence" and "AuditOnly nodes are kept and are not in [the admissible evidence graph]". So justify should not consider them. But does §7 explicitly handle this?

§7 says about ladder tables: "a ladder_table whose verdict is KEEP, or KEEP_IN_SAMPLE... where 'repro node' means the reproducibility record the §3 policy attaches to the table's own attempt (a second agreeing attempt or a passed witness check) and a table without it has ceiling CONJECTURE"

So a ladder table without a reproducibility record has ceiling CONJECTURE. But what about a ladder table whose replay grade is AuditOnly? §3 says it's inadmissible. §7 doesn't explicitly say "an AuditOnly evidence node justifies nothing." This could be a gap, but §3's statement that AuditOnly is inadmissible should be read as a constraint on justify. Let me check if there's an explicit link...

Actually, §3 says: "The admissible evidence graph is one replayable-or-verifiable DAG (AuditOnly nodes are kept and are not in it) — which is the only thing that makes a STRONG-EMPIRICAL tag mean something."

And §7 says justify checks evidence nodes. If AuditOnly nodes are not in the admissible evidence graph, then justify shouldn't see them. This seems like it should be explicit in §7 but is stated in §3. Not a contradiction, but a potential gap in explicitness. Let me not flag this as it's more of a clarity issue than a demonstrable defect.

14. Let me check the §5 budget meet and the §6 patience ceiling. §5 says: "The granted budget is a hard ceiling the harness enforces at runtime" and "exhaustion stops the attempt with status BUDGET_EXCEEDED"

§6 says: "A trial that hits the per-trial patience ceiling of the ladder plan (the §5 budget ceiling) counts as a failure in the success-rate column"

So the per-trial patience ceiling IS the §5 budget ceiling. This is explicitly stated. Consistent.

15. Let me look at the §4 gate bundle contents and check if all referenced mechanisms are built by the milestones that use them.

The gate bundle includes: "the auditor's f, bits, critical-set cutoff, cadence and per-cycle audit line (§7)" - but the auditor arrives at M4. The gate bundle is built at M0. So M0's gate bundle would have placeholder/empty auditor fields? 

Actually, §13 M0 says: "M0 schema includes: ... the gate-bundle pin (§4)". The gate bundle itself is built incrementally. M0 includes the verifier's config and the tier boundaries. The auditor's parameters would be added at M4 when the auditor is built. This seems fine - the gate bundle is content-addressed and versioned, so it grows as mechanisms are added.

16. Let me look for a real contradiction. Let me re-read the §5 tier gate predicate carefully.

§5 says: "The ticket is the most recent admissible substrate node of the kind the tier requires (status OK, replay grade ≥ Verifiable, reproducibility-checked under the §3 policy) produced at the tier below for that same hypothesis key and method identity"

And: "where 'most recent' ranges over every node of that kind for the hypothesis whatever its verdict — a later REJECT or INCONCLUSIVE ladder table displaces an older KEEP"

Wait - the ticket must have "status OK" but a REJECT ladder table has status... what? Let me check. §6 says verdicts are REJECT, INCONCLUSIVE, KEEP_IN_SAMPLE, KEEP. But the attempt status is separate from the verdict. §3 says attempt has a "status" field. A ladder table attempt that produces a REJECT verdict - what's its attempt status?

§3 says: "status ≠ OK ⇒ never cached". A REJECT ladder table - is its attempt status OK or not? The ladder ran successfully and produced a result (REJECT), so the attempt itself succeeded (status OK) even though the verdict is REJECT. The verdict is a property of the result, not the attempt status.

But then §5 says the ticket must have "verdict KEEP" for Tier 2: "for Tier 2 on an algorithmic claim the ticket is a ladder result table with verdict KEEP (§6)". So the ticket requires both status OK AND verdict KEEP. But then it says "a later REJECT or INCONCLUSIVE ladder table displaces an older KEEP" - this means a REJECT table displaces the KEEP as the "most recent" node, but since the ticket requires verdict KEEP, a REJECT would not be a valid ticket. So the displacement means: if there's a later REJECT, there is no valid ticket (the most recent node is a REJECT, which doesn't qualify as a ticket).

Actually wait, let me re-read: "where 'most recent' ranges over every node of that kind for the hypothesis whatever its verdict — a later REJECT or INCONCLUSIVE ladder table displaces an older KEEP — and the verdict rule below is applied to the node so selected."

So the gate selects the most recent node of the kind (ladder table), regardless of verdict, and then applies the verdict rule. If the most recent is a REJECT, the verdict rule says... what? The verdict rule says the ticket must have verdict KEEP. So a REJECT as the most recent means no valid ticket exists. This is coherent - a later refutation kills the ticket.

OK, let me look for actual defects more carefully.

17. Let me check the §4 claim statement node and the §7 formal statement hash. §4 says: "where the node carries a formal statement the formalization gate derives a second, formal statement hash when it compiles the Challenge (§7), and its gate-run record binds the two under the bundle hash — the Solution names the formal statement hash, everything else names the claim statement hash"

§7 says: "The gate compiles the Challenge module from the claim statement node (§4)" and "The formal statement hash is computed by the gate when it compiles the Challenge"

Consistent.

18. Let me check the §3 hypothesis object and the §4 ledger preflight. §3 says the hypothesis object is "written by the worker or human that opens the branch, at branch open, naming the claim statement hash where a claim exists"

§4 says: "before any branch is funded the ledger answers Allowed | Blocked | RequiresNullControl, and before a branch is opened it also answers AlreadySettled"

So the preflight runs before the branch is opened, but the hypothesis object is written at branch open. Does the preflight need the hypothesis object? §4 says: "Blocked = the hypothesis key (§3) matches a REFUTED entry". The hypothesis key is derived from the hypothesis object. But the hypothesis object is written at branch open, which is after the preflight.

Wait, let me re-read. §4 says: "before any branch is funded the ledger answers..." and "before a branch is opened it also answers AlreadySettled". So there are two stages: before funding and before opening. The hypothesis object might exist before the branch is opened - it's written "at branch open" but the preflight before funding would need it.

Actually, §3 says: "the hypothesis object is an immutable, content-addressed node... written by the worker or human that opens the branch, at branch open". But the preflight runs "before any branch is funded" and "before a branch is opened". So the preflight needs the hypothesis key, but the hypothesis object is written at branch open. This seems like a chicken-and-egg problem.

Wait, maybe the hypothesis object is created first (as a proposal), then the preflight checks it, then the branch is opened pointing at it. §3 says "written... at branch open" but maybe the worker creates the hypothesis object as a proposal first, the preflight checks it, and then the branch opens pointing at it. The "at branch open" might mean "as part of the branch opening process" which includes the preflight.

Actually, §6 says: "The hypothesis object's hash... is named in the ladder's dispatch record" and "the object's position in the substrate's append order precedes the gate's entropy commitment of step (1)". And §3 says: "because it is appended to the substrate's append-only record sequence when the branch opens (an order the hash-chained log below carries tamper-evidently from M2), pre-registration (§6 step 0) is an order of records"

So the hypothesis object is appended when the branch opens. But the preflight runs before the branch opens. So the preflight must work with a proposed hypothesis object that hasn't been appended yet. The preflight computes the hypothesis key from the proposed object and checks the ledger. If it passes, the branch opens and the object is appended.

This seems like it could work - the preflight computes the key from the proposed object (which exists as a proposal, not yet appended), checks the ledger, and if allowed, the branch opens and the object is appended. The key can be computed before the object is appended. No contradiction.

19. Let me look at the §7 disagreement protocol and §10. §7 says: "a Prover/Skeptic or panel disagreement is never resolved by vote; it is recorded with both artifacts' hashes, classified (statement error, proof gap, harness bug, out-of-scope, inconclusive), routed to an owner (the human for statement errors), and the claim's tag stays at its pre-dispute level until resolved."

§10 says: "Panel disagreement is recorded and routed under the §7 disagreement protocol, never averaged."

Consistent.

20. Let me now focus on Duty 2: Ceremony audit.

Artifacts the plan creates:
- Certificates (§3): The running code that branches on them is the reproducibility gate (§3: "Verifiable ⇒ the witness is always checked") and the ladder (§6: "a rho trial with its DP witness is Verifiable"). Consumer: reproducibility gate, ladder. Gate enforced: reproducibility gate. Defect class: non-reproducible results. Retirement: when the node is GC'd (but certificates are GC roots per §3). Seems sound.

- Ledgers (§4): The running code that branches on them is the ledger preflight (§4). Consumer: preflight, tier gate (§5: "a branch flagged by §8 holds no ticket above Tier 1"). Gate enforced: preflight blocks branch opening. Defect class: re-walking dead ends. Retirement: REFUTED entries are permanent. Seems sound.

- Tag histories (§7): The running code that branches on them is justify (§7). Consumer: justify, tier gate (reads tags for ticket eligibility). Gate enforced: tag derivation. Defect class: unjustified claims. Retirement: append-only, never retired. Seems sound.

- Gate plans (§4): The running code that branches on them is every gate run. Consumer: gate execution. Gate enforced: ordered scopes. Defect class: gate bypass. Retirement: versioned with gate bundle. Seems sound.

- Self-tests (§2): The running code that branches on them is the tier gate (§2: "the tier gate refuses new launches of it") and the cache serve path. Consumer: tier gate, cache. Gate enforced: tier gate refuses uncertified/yanked revisions. Defect class: buggy skills. Retirement: superseded by new revision. Seems sound.

- Receipts (§3): The running code that branches on them is the budget ceiling (§5: "its readers are the budget ceiling (§5), the ladder's clock and memory measurements (§6) and the provenance check of §4"). Consumer: budget ceiling, ladder, provenance check. Gate enforced: budget ceiling. Defect class: cost misreporting. Retirement: with the attempt. Seems sound.

- Result tables (§6): The running code that branches on them is the tier gate (§5: "the ticket is the most recent admissible substrate node"). Consumer: tier gate, justify. Gate enforced: tier gate. Defect class: fabricated results. Retirement: GC root. Seems sound.

- Alarms (§15 P4): The running code that branches on them is... §15 P4 says "A fired alarm is a human-queue item of class cost_drift (§10) and a strategy input the orchestrator's tick may read to park with budget_preempt; it moves no tag, ticket or scrutiny class." Consumer: orchestrator's tick (strategy), human queue. No gate enforced. Defect class: cost drift. Retirement: when dropped per P4 decision. This is explicitly a monitor, not a gate. Seems sound.

Now let me check for mechanisms whose name promises more than their definition delivers.

- "Strong law of small numbers (hard gate)" in §7: The name says "hard gate" and the definition says "a small-case pattern is a conjecture until it survives larger cases + a deliberate counterexample hunt." The gate is: without a counterexample_hunt_record with verdict SURVIVED, the conjecture's tag ceiling is CONJECTURE, and SURVIVED is the Tier-2 ticket for a conjecture. This seems to deliver on "hard gate" - it's a gate on the tag and the tier.

- "Terminal-status invariant" in §4: The name says "invariant" and the definition says every opened branch and claim must be resolved or handed off. The enforcement is: a worker that exits without resolving produces a Leaked record. This is an invariant with enforcement. Seems sound.

- "Proportional scrutiny" in §7: The name suggests scrutiny scales with claim size. The definition says the router's classes are a predicate over typed fields, and the top class requires ladder KEEP, formalization, reproducibility, and expert sign-off. This delivers on the name. Seems sound.

Let me now focus on Duty 3: Gaming the gates.

**Submission verifier:**
The verifier checks xP==Q on the instance from the claim statement node. A worker under pressure could... try to submit x for a different instance? §4 says: "a verifier run takes the curve, n, P and Q from the claim statement node it is invoked against... never from the submitter, who supplies x alone" and "a submission whose verifier node names any other instance is refused by the egress renderer (§10)." This closes the instance substitution. What about submitting a trivial x (like x=0 or x=1)? The verifier would check 0*P==Q, which would fail unless Q is the identity. This doesn't game it. What about the worker setting Q to be a known multiple of P in the claim statement? The claim statement is written before any proof or measurement, and the ladder generates its own instances. For the target instance, Q is fixed. Seems closed.

**The ladder:**
A worker under pressure could... declare a cost model that's trivially true? §6 says the model is pre-registered and the ladder tests it. A worker could declare a very loose model (e.g., exponent 0.5 with a large constant) that's easy to satisfy. But §6 says: "the floor 1.01 guarding a degenerate null arm" and the refutation floor requires beating BSGS at 50 bits. A method that just barely beats BSGS with a loose model would get KEEP, but it wouldn't be a real advance. However, the ladder's purpose is to catch fabrication, not to evaluate significance. The orchestrator's allocation handles significance. This seems like the intended behavior, not a gaming issue.

What about a worker declaring a very narrow parameter range to avoid measured REFUTED points? §4 says: "Blocked = ... the proposal's declared parameter region contains a measured parameter point at which a REFUTED entry records the same method identity failing the same cost model". So if the worker declares a narrow range that doesn't contain any measured point, they could avoid the block. But §4 also says: "AlreadySettled = ... opens a branch whose method identity and claimed cost model equal such a promoted holder's and whose declared parameter region is contained in the holder's". So a sub-region of a promoted holder is blocked. But what about a sub-region of a REFUTED holder that doesn't contain the measured point? The worker could declare a narrow range adjacent to but not containing the measured point. §4 says the reach is "the minimal logical reach of the measurement, recorded as fields so that range jitter cannot mint a clean key." But the reach is axis-aligned inclusion on numeric fields. If the measured point is at size 50 and the worker declares range [30, 49], the measured point (50) is not in [30, 49], so it's not blocked. This could be a gaming vector - a worker declares a range just below the measured point. But the ladder would still test the method at the declared sizes, and if the method fails at those sizes too, it would be REFUTED. If it doesn't fail at those sizes, then the refutation at 50 doesn't reach 30-49, which is correct behavior. So this isn't really gaming - it's the system correctly recognizing that a refutation at 50 doesn't necessarily apply at 30.

Actually, wait. The cost model is about asymptotic behavior. If a method is refuted at 50 bits because it doesn't beat BSGS, and the worker declares a range [30, 49], the ladder would test at 30-49 and might find it beats BSGS there (BSGS is cheaper at small sizes). But the cost model would be about the exponent, and if the exponent is wrong, the in-sample check would catch it. If the worker declares a range where the method happens to work, that's not gaming - it's a legitimate (if uninteresting) result on a smaller range.

Let me think about a more concrete gaming vector for the ladder.

A worker could try to make the A/A null arm look bad (large radius) to widen the KEEP band, making it easier to pass. The A/A arm is gate-owned (same harness, same trial count, same instance stream, differing only in method seeds). The worker can't influence the A/A arm. The radius is computed from the A/A arm's results. The worker can't widen the band. Closed.

A worker could try to report a lower count than the gate's count. §6 says: "a divergence from the gate's count beyond the ladder plan's tolerance is REJECT" and "a count the method reports about itself is a diagnostic column." The gate's count is from the gate-owned arithmetic object. The worker can't influence it. Closed.

A worker could try to hide memory usage. §6 says: "measured by the harness, from the execution receipt (§3), as peak RSS over the trial's process tree less the A/A arm's peak on the same instances... plus the bytes written to the gate-owned scratch path." The worker can't influence the harness's RSS measurement. But what about memory allocated but not in the process tree? If the worker spawns a process outside the process tree... §6 says: "a ladder-tested method's allow-list permitting no process spawn beyond the backends its hypothesis object declares." So the allow-list restricts process spawning. And §6 says: "a storage channel the allow-list does not name — another writable path, network egress — is a planted-failure fixture the ladder's self-test must FAIL." Closed.

**Formalization gate:**
A worker could try to submit a Solution that proves a weaker statement. §7 says: "requires the Challenge and Solution theorem statements to be identical over the statement's transitive constant closure, so a redefined constant anywhere under the statement fails the check." And the Challenge is gate-compiled from the claim statement node. The worker can't edit the Challenge. Closed.

A worker could try to use sorryAx. §7 says: "requires it ⊆ {propext, Classical.choice, Quot.sound} — which rejects sorryAx." And: "a gate-owned module in the bundle that imports the Solution and runs Lean.collectAxioms over the Challenge's theorem names, never a list read from output the Solution's own compilation emits, since leanchecker rejects neither sorryAx nor extra axioms." Closed.

A worker could try to exploit the formal statement hash. §7 says: "a hash match with a comparator mismatch fails closed" and "the hash names and binds; it decides nothing — check (iv) below is the comparator's own closure comparison." Closed.

**Reproducibility gate:**
A worker could try to make their result non-reproducible to avoid scrutiny. But §3 says non-reproducible results are "marked inadmissible." Making your result non-reproducible hurts you. Not a gaming vector.

A worker could try to make a result that's reproducible only on their specific machine. §3 says: "where no container runs, as on the M0 build machine, container-digest is the digest of the runtime's environment manifest." The recipe key includes tool-versions and container-digest. A result that only reproduces on one machine would have a specific container-digest, and re-runs would use the same digest. But the reproducibility gate re-runs the recipe, which includes the same environment. If it reproduces, it reproduces. If the worker's environment is different from the gate's... but the gate runs in the gate bundle's environment. Actually, the re-run uses the same recipe key, which includes the same tool versions and container digest. If the gate's environment matches, it should reproduce. If not, the recipe key would differ. This seems closed.

**Ledger preflight:**
A worker could try to avoid the preflight by... the preflight runs before branch funding/opening. The worker can't skip it. But could a worker phrase their hypothesis differently to get a different hypothesis key? §3 says: "free-text fields are excluded, so the key is about structure." The key is over typed fields. A worker could change the method identity (use a different interface version name) to get a different key. But §5 says the tier gate compares the ticket's method identity with the launch's. If the method identity is different, there's no ticket. And the ladder tests the declared method identity. So a worker could declare a new method identity to avoid a REFUTED entry, but then they'd have no ticket and would need to re-ladder. This is correct behavior - a genuinely different method should be tested fresh.

But what about a worker who renames the same method to get a fresh key? §3 says the method identity is "the skill named by its §2 interface version with its canonical parameters." The interface version is part of the skill's identity bundle. If the worker creates a new skill with a different interface version but the same implementation, the hypothesis key would differ. But the ladder would test the new skill, and if it's the same method, it would produce the same results. The worker would need to re-ladder, which costs compute. This is annoying but not a fabrication vector - it just wastes compute. And the near-duplicate advisory (§4) would catch it: "a 64-bit SimHash over the hypothesis text... advisory only." This routes to human review. So a worker renaming the same method would be caught by the near-duplicate advisory. Partially closed.

**Tier gate:**
A worker could try to satisfy the tier gate by producing a trivial KEEP. For example, a method that's slightly better than rho at small sizes but useless at large sizes. The ladder would give KEEP at the 60-bit rung if the model fits. But the tier gate for Tier 3 requires "an explicit predicted-cost-vs-payoff justification, a certificate verification plan and the expert sign-off of §10." So even with a KEEP, Tier 3 requires human sign-off. And the proportional scrutiny router would route a claim about the target to the top class, requiring all gates. Closed.

A worker could try to shard a Tier-2 computation into many Tier-1 computations. §5 says: "the boundary table names a cumulative edge per ticket tier: the launch that would carry the key's charge under its current best ticket past that edge is TierRefused until the next tier's ticket exists." This prevents sharding. Closed.

Now let me look for actual demonstrable defects.

Let me re-read the §5 tier gate ticket selection more carefully:

"The ticket is the most recent admissible substrate node of the kind the tier requires (status OK, replay grade ≥ Verifiable, reproducibility-checked under the §3 policy) produced at the tier below for that same hypothesis key and method identity (or statement hash), where 'most recent' ranges over every node of that kind for the hypothesis whatever its verdict — a later REJECT or INCONCLUSIVE ladder table displaces an older KEEP — and the verdict rule below is applied to the node so selected."

So the gate selects the most recent node of the kind, regardless of verdict, then applies the verdict rule. The verdict rule says: "for Tier 2 on an algorithmic claim the ticket is a ladder result table with verdict KEEP." So if the most recent is a REJECT, the verdict rule fails, and there's no ticket. This means a later REJECT doesn't just block - it removes the ticket entirely. But what if the REJECT is later overturned? §4 says a measured refutation's retry predicate is met by a gate-owned re-measurement. If the re-measurement doesn't REJECT, the answer is Allowed. But the REJECT table is still in the substrate as the most recent node. Would the re-measurement's table (if it's KEEP) be more recent and displace the REJECT? Yes - the re-measurement produces a new ladder table that would be more recent. So the re-measurement's KEEP would displace the earlier REJECT. This is coherent.

But wait - what about INCONCLUSIVE? §5 says "a later REJECT or INCONCLUSIVE ladder table displaces an older KEEP." An INCONCLUSIVE table would displace a KEEP, meaning no ticket. But INCONCLUSIVE is not a refutation - it's "inside the band." So an INCONCLUSIVE result removes the ticket? That seems harsh. If a method gets KEEP at 50 bits, then someone re-runs and gets INCONCLUSIVE (maybe due to a budget exhaustion on one trial), the KEEP is displaced and the method loses its Tier-2 ticket.

Is this a defect? Let me think... The INCONCLUSIVE could come from a re-run with a fresh instance (§6: "a rung re-run after INCONCLUSIVE sees fresh instances"). If the re-run is INCONCLUSIVE, it means the method didn't clearly pass this time. Displacing the KEEP seems intentional - you don't want a method that's inconsistent across runs to hold a Tier-2 ticket. But the INCONCLUSIVE could be due to budget exhaustion (BUDGET_EXCEEDED on a trial), which is a harness issue, not a method issue. §6 says: "A trial that hits the per-trial patience ceiling... counts as a failure in the success-rate column." So a budget-exhausted trial counts as a failure, which could make the rung INCONCLUSIVE. If this happens on a re-run, it displaces a valid KEEP.

But who initiates the re-run? §3 says: "Replayable at Tier 2/3 ⇒ re-run at the moment justify (§7) would derive a class above CONJECTURE from the node." And: "otherwise sampled by the foundations auditor (§7)." So the re-run is gate-owned. If the gate's re-run gets INCONCLUSIVE due to budget issues, that's a gate problem, not a worker gaming issue. And the worker can't control the re-run. So this isn't a gaming vector, but it could be a fairness issue. However, the plan seems to intend this - an inconsistent method shouldn't hold a ticket.

Actually, I think this is the intended behavior and not a defect. Let me move on.

Let me look for a real defect in the milestone dependencies.

§13 M1 says: "the REFUTED/PARKED entry record of §4 lands here, written by the ladder's REJECT and the hunt's KILLED, while the preflight that reads it arrives at M2"

M1 also says: "the proportional-scrutiny router and the no-go checklist's presence check (§8) with the router as its consumer"

M1 includes the no-go checklist's presence check, which is a §8 mechanism. The no-go checklist's `nogo_review` node is read by the tier gate. M1 includes the tier gate. So M1 builds the no-go checklist and the tier gate that reads it. But M1 also says the `nogo_review` node is "written only through the human path of §4." The human path (attestation file) is built at M0 (§13 M0: "a write to the attestation file, each attempted as the orchestrator's process user, are refused by the operating system, and a review_verdict row whose digest matches no attestation record is absent to justify"). So the human path exists at M0, and the nogo_review uses it at M1. This is fine.

Let me check if M1's fixtures depend on something not built until M2 or later.

M1 fixture (h): "a PROVEN claim with a weaker premise in its transitive closure" - this exercises "the transitive justified_by query of §7." M1 says: "the transitive justified_by query of §7 that fixture (h) exercises (the auditor's sampling cadence arrives at M4)." So the transitive query is built at M1, but the auditor's sampling is M4. This is fine - the query itself is at M1, the auditor's use of it is M4.

M1 includes: "the human queue as a typed object (§10)." But §10's full human loop (problem queue, selector, expert loop) arrives at M4. M1 only needs the typed queue object, not the full loop. This is fine.

Let me look at M2. M2 says: "the hash-chained log and its head checkpoint (§3, §4)." §3 says the log is "built at M2." M2's done-when includes: "a log truncated to an earlier valid prefix fails startup verification against the checkpoint." This is consistent.

M2 also says: "the terminal-status invariant." M2's done-when includes: "a worker that returns with a claim it opened still open yields a Leaked record while a harness-terminated attempt yields none." This is the terminal-status invariant of §4. But §4's terminal-status invariant also mentions INTERRUPTED status, which is about crash recovery. M2 doesn't mention crash recovery - that's M3 ("crash mid-tick resumes without double-applying a completed step"). But the INTERRUPTED status is assigned by "a restart scan" which is about the harness process dying. Is the restart scan built at M2 or M3? §4 says: "INTERRUPTED — the status a restart scan gives every attempt that was in flight when the harness process died, assigned before any new launch." M0's schema includes "the BUDGET_EXCEEDED, SKILL_YANKED and INTERRUPTED statuses." But the restart scan itself - when is it built?

M0 says: "M0 schema includes: ... the BUDGET_EXCEEDED, SKILL_YANKED and INTERRUPTED statuses." But M0 doesn't mention a restart scan. M1 doesn't either. M3 says: "a crash mid-tick resumes without double-applying a completed step (§15 P3), every attempt in flight at the crash standing at INTERRUPTED on restart." So the restart scan is built at M3.

But M2's done-when says: "a harness-terminated attempt yields none [no Leaked record]." To test this, you need a harness-terminated attempt, which requires either a budget exhaustion (BUDGET_EXCEEDED, built at M1) or a skill yank (SKILL_YANKED, built at M1) or an interrupt (INTERRUPTED, built at M3). M2 can test with BUDGET_EXCEEDED and SKILL_YANKED without needing INTERRUPTED. So M2's done-when can be satisfied without M3's restart scan. This is fine.

Let me now look for a demonstrable defect more carefully.

Actually, let me re-examine the §5 cumulative edge and the §6 ladder's Tier-1 ticket.

§5 says: "The ladder's distribution rungs (§6, ≤ 50 bits) are Tier-1 — admitted on the Tier-1 ticket whatever tier the boundary table would assign their ladder-plan-bounded cost, because they are gate-owned launches whose count, arms and patience ceiling are ladder-plan fields"

And: "its 60-bit rung is tiered by its own declared cost profile."

So the ≤50-bit rungs are always Tier-1, regardless of cost. But §5 also says: "the boundary table names a cumulative edge per ticket tier: the launch that would carry the key's charge under its current best ticket past that edge is TierRefused until the next tier's ticket exists (M1 sets the Tier-1 edge above the ladder's own cost on one key)."

So the cumulative edge applies to the ladder's ≤50-bit rungs too. M1 sets the Tier-1 edge above the ladder's own cost on one key. But what if the ladder runs on multiple hypothesis keys? Each key has its own cumulative charge. The ladder runs on one hypothesis key per claim. So the cumulative edge is per-key, and the ladder's cost on one key is below the edge. This seems fine.

But wait - the ladder's ≤50-bit rungs are "admitted on the Tier-1 ticket whatever tier the boundary table would assign their ladder-plan-bounded cost." This means even if the boundary table says the cost is Tier-2, the rungs are admitted on Tier-1. But the cumulative edge is about the total charge under the current best ticket. If the ≤50-bit rungs are admitted on Tier-1, their cost counts toward the Tier-1 cumulative edge. M1 sets this edge above the ladder's own cost. So the ladder's ≤50-bit rungs won't hit the edge. But what about other Tier-1 work on the same key? If there's a lot of Tier-1 work on the same key, the cumulative charge could hit the edge, and the ladder's rungs would be refused. But the ladder's rungs are gate-owned launches. Would they be refused?

§5 says: "the launch that would carry the key's charge under its current best ticket past that edge is TierRefused." This applies to all launches, including gate-owned ones. But M1 sets the edge above the ladder's cost. If other Tier-1 work on the same key has already consumed the budget, the ladder's rungs could be refused. Is this a defect?

Actually, the ladder's rungs are gate-owned. The plan says they're "admitted on the Tier-1 ticket whatever tier the boundary table would assign their ladder-plan-bounded cost." This is about the per-launch tier derivation, not the cumulative edge. The cumulative edge is a separate check. So the ladder's rungs could be refused by the cumulative edge if there's too much Tier-1 work on the same key.

But is this intended? The cumulative edge is meant to prevent sharding. The ladder's rungs are not sharding - they're gate-owned. But the text doesn't exempt gate-owned launches from the cumulative edge. This could be a defect: the cumulative edge could block the ladder's own rungs, preventing the system from testing a hypothesis.

Wait, but M1 sets the Tier-1 edge above the ladder's own cost on one key. So the ladder's cost alone won't hit the edge. The edge would only be hit if there's additional Tier-1 work on the same key beyond the ladder. What other Tier-1 work would run on the same key? The counterexample hunt (§7) runs on the same hypothesis key. And the no-go checklist's presence check is Tier-0. And the statement pre-filters are Tier-0. So the main additional Tier-1 work on the same key would be the counterexample hunt.

If the counterexample hunt and the ladder both run on the same key at Tier 1, their combined cost could exceed the cumulative edge. The edge is set above the ladder's cost, but not necessarily above the ladder plus the hunt. This could block either the ladder or the hunt.

Is this a demonstrable defect? Let me check if the plan addresses this.

§5 says: "M1 sets the Tier-1 edge above the ladder's own cost on one key." It says "the ladder's own cost," not "the ladder's cost plus the hunt's cost." If the hunt's cost is significant, the combined cost could exceed the edge.

But actually, the counterexample hunt is for conjecture claims, and the ladder is for algorithmic claims. A claim could carry both (§5: "a claim whose typed fields carry more than one of these kinds"). In that case, both the ladder and the hunt would run on the same key at Tier 1. The cumulative edge could block one of them.

However, the plan says M1 sets the edge. M1 can set it high enough to accommodate both. The text says "above the ladder's own