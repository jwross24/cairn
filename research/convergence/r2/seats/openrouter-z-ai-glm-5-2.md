Let me carefully review this plan. It's a very detailed architecture document for "Cairn," an autonomous math research harness focused on ECDLP. I need to find genuine improvements, not manufacture changes.

Let me think about what's actually problematic or could be improved:

1. **The ladder's A/A null arm** - The plan says the A/A null arm's CI radius sets the decision band. But there's a subtlety: the A/A arm compares the baseline against itself, which gives you the noise floor. The KEEP threshold is `1 + 2·radius`. This seems sound but I want to check if there's a multiple-comparisons issue across the multiple rungs (30/40/50/60 bits).

2. **The foundations auditor sampling** - The spot-check bound `l ≥ ln(2^bits)/ln(1/(1−f))` is a standard coverage bound. But the plan says it's applied "per tier stratum" and within Tier-2/3 "nodes with the largest justified_by fan-in are drawn first." This is sound but there's a question about what happens when a re-run fails - the plan says it downgrades and re-derives transitively, but doesn't specify whether the failed node's children are re-queued for re-verification or just downgraded.

3. **The terminal-status invariant** - Every opened branch/claim must reach terminal status. But what about claims that are justified by evidence that later gets downgraded? The claim's tag gets re-derived, but does the claim itself need to reach a new terminal status? The plan says withdrawal is terminal, but a downgraded claim isn't withdrawn - it's just re-tagged. Is there a gap here?

4. **The gate bundle** - It's a separate SQLite file opened read-only. But the plan says the orchestrator process opens it read-only. What about the gate process? Is the gate a separate process? The plan says gates are "mechanical, immutable" but doesn't clearly specify the process boundary. If the gate runs in the same process as the orchestrator, the read-only SQLite file is the only boundary, which is weak (the process can open it read-write if it wants). This seems like a real gap.

5. **The recipe key canonicalizer** - The plan says "Two logically equal recipes that hash differently are a canonicalizer bug, never a feature." But the canonicalizer is itself code that could have bugs. The plan has a known-answer test vector for it, but there's no mechanism for handling a canonicalizer bug discovered after results have been stored. If the canonicalizer changes, all old keys are stale. The `salt` field handles tool-version faults, but canonicalizer bugs are different - they affect the key construction itself.

6. **The disagreement protocol** - Disagreements are "never resolved by vote" and are "recorded with both artifacts' hashes, classified, routed to an owner." But what happens when the owner is the human and no human session is open? The plan says "the claim's tag stays at its pre-dispute level until resolved." This is sound. But what about a disagreement between two workers on whether a branch should be funded? That's not a claim-level disagreement. Actually, the plan scopes this to "Prover/Skeptic or panel disagreement" so it's about claims and problem selection.

7. **The cost profile** - Skills declare cost profiles, and "a persistent mismatch is a strategy-layer alarm, never a gate." But what if a skill consistently underestimates its cost? The tier gate uses the declared cost to decide admission. If the declared cost is too low, work gets admitted to a higher tier than it should. The alarm fires after the fact, but the gate already let it through. This seems like a real gap - the cost profile is load-bearing for the tier gate but only checked after the fact.

8. **The 60-bit rung** - The plan says a full 10²-trial distribution check at 60 bits is Tier-2 work. But the 60-bit rung is supposed to be the "completion-and-extrapolation rung" that tests whether the model fitted on ≤50 bits predicts the 60-bit mean. If the 60-bit rung requires Tier-2 budget, and Tier-2 requires a ladder result table with verdict KEEP as a ticket, there's a circular dependency: you need the 60-bit rung to get KEEP, but you need KEEP to get Tier-2 budget for the 60-bit rung. Let me re-read...

Actually, re-reading §6: "the 60-bit rung is the completion-and-extrapolation rung" and "a full 10²-trial distribution check at 60 bits is Tier-2 work by its own declared profile, not Tier-1, and runs only when the tier gate grants that budget." And §5 says "for Tier 2 on an algorithmic claim the ticket is a ladder result table with verdict KEEP (§6)."

So the question is: can you get a KEEP verdict from the ≤50-bit rungs alone, and then use that KEEP to get Tier-2 budget for the 60-bit rung? Let me re-read §6 step (2b): "The 60-bit rung is the completion-and-extrapolation rung: the model fitted on the ≤ 50-bit rungs must predict the measured 60-bit mean inside the band, and the method must complete and recover x on at least 10 fresh instances."

And step (5): "The result table... is the ladder's artifact, the Tier-2 ticket (§5) when its verdict is KEEP."

So the KEEP verdict requires the 60-bit rung to pass, but the 60-bit rung needs Tier-2 budget, which requires a KEEP verdict. This is a circular dependency. Unless the ≤50-bit rungs can produce a provisional KEEP that grants Tier-2 access for the 60-bit rung specifically. But the plan doesn't say this.

Actually, wait. Let me re-read more carefully. The plan says "at least 10 fresh instances" at 60 bits, not 10². And "a full 10²-trial distribution check at 60 bits is Tier-2 work." So maybe the 10-instance completion check is Tier-1, and only the full 10² distribution check is Tier-2? But 10 instances at 60 bits is still ~1.3×10^10 group ops total, which is minutes in compiled code. That could be Tier-1 (minutes). But the plan says "a full 10²-trial distribution check at 60 bits is Tier-2 work by its own declared profile, not Tier-1." It doesn't explicitly say the 10-instance check is Tier-1.

This is a real ambiguity/circular dependency. Let me flag it.

9. **The `skip_cache_lookup` bit** - The Skeptic's re-runs always set it. But what about the foundations auditor's re-runs? The plan says "The re-run it performs is the §3 policy" but doesn't explicitly say it sets `skip_cache_lookup`. If it doesn't, the auditor might just re-read the cached value and "verify" it's the same, which is meaningless. Actually, re-reading §3: "skip_cache_lookup (run even if cached and record a fresh attempt — never overwrite; the Skeptic's re-runs always set it)." The foundations auditor should also set it. This seems like a gap.

10. **The claim statement node and the Challenge** - The claim statement node has "formal statement (the Challenge source, when one exists)". The Challenge is compiled by the gate from the claim statement node. But who writes the formal statement in the claim statement node? The Reframer, Prover, or human. And the gate renders the Challenge from it. But what if the formal statement in the node is ambiguous or incomplete? The gate renders a Challenge from it, but the rendering could be wrong. The plan says "the Formalizer never creates or edits Challenge text" - so the gate renders it. But what does "renders" mean? Is there a template? This seems underspecified.

Actually, I think the claim statement node contains the Lean source for the Challenge, and the gate compiles it. The "renderer" might just be extracting the source from the node and compiling it. Let me not over-think this.

11. **The `justify` function** - It "checks that the evidence's declared target, assumptions and population cover that exact statement and returns a typed justification or a lattice violation, never a boolean." This is a critical function. How is it implemented? It needs to compare the evidence's target with the claim statement. For formal evidence (Lean proofs), this is straightforward (same statement hash). For empirical evidence (ladder results), it needs to check that the ladder was run on the right family with the right parameters. This seems like it could be gamed if the comparison is too loose. But the plan says it returns a "typed justification or a lattice violation" which suggests it's structural, not semantic. This seems sound but complex.

12. **The near-duplicate advisory** - "a 64-bit SimHash over the hypothesis text; no embedding model before the Librarian's retrieval stack exists." SimHash on hypothesis text. But the hypothesis key is over a typed hypothesis object, not text. So the SimHash is on the text representation, not the structural representation. This means two structurally identical hypotheses with different text would have different SimHashes but the same hypothesis key. The plan says "paraphrase is the near-duplicate advisory's job" - so this is intentional. But SimHash on text is a weak signal for mathematical near-duplicates, where the same idea can be expressed in very different words. This is a known limitation and the plan acknowledges it's "advisory only." I think this is sound as stated.

13. **The `author_supplied` corpus cap** - "a corpus supplied only by the worker that authored the skill is not a self-test, and author_supplied alone caps the skill's results at CONJECTURE." But what about a skill authored by a human? The human is the operator. If the human authors a skill with only their own corpus, it's capped at CONJECTURE. But the human might have good reasons for the corpus. The plan says "STRONG-EMPIRICAL needs an upstream corpus, an independent implementation under the axis rule below, or a postcondition or metamorphic relation." This seems right - even human-authored skills need independent validation.

14. **The gate bundle hash pin** - "whose hash is pinned at deployment and recorded in every gate-run record; a gate whose bundle hash differs from the pin fails closed." But who pins it? The deployment process. And who controls the deployment process? The operator. This is outside the orchestrator's write path, which is correct. But what about updates to the gate bundle? When the ladder plan changes (e.g., new sizes), the gate bundle changes, and the pin must be updated. The plan says "a waiver is explicit, attributed, reason-bearing and expiring, issued only by a human" - but updating the gate bundle isn't a waiver, it's a deployment. The plan doesn't specify the update protocol for the gate bundle. This seems like a gap.

Actually, re-reading: "the gate bundle: a content-addressed bundle held in a separate store the orchestrator process opens read-only (a separate SQLite file at M0), whose hash is pinned at deployment and recorded in every gate-run record." So each gate run records which bundle hash it used. If the bundle is updated, new runs use the new hash, and old runs keep their old hash. This is sound - it's content-addressed. But the "pin" is what the current deployment expects. If someone updates the bundle without updating the pin, gates fail closed. If someone updates the pin without updating the bundle, gates fail closed. This seems correct.

15. **The `Replayable` at Tier 2/3 policy** - "re-run at the moment a promotion past CONJECTURE is sought (the promotion waits on it), otherwise sampled by the foundations auditor." But what if a Tier-2 result is used as evidence for a STRONG-EMPIRICAL claim, and then the foundations auditor's sample doesn't include it? The claim is tagged STRONG-EMPIRICAL without a re-run. The plan says "the claim's tag capped at CONJECTURE meanwhile" - wait, let me re-read: "Replayable at Tier 2/3 ⇒ re-run at the moment a promotion past CONJECTURE is sought (the promotion waits on it), otherwise sampled by the foundations auditor (§7) with the claim's tag capped at CONJECTURE meanwhile."

So the claim is capped at CONJECTURE until the re-run happens. The re-run happens either at promotion time or when the auditor samples it. This is sound. But "promotion past CONJECTURE" - who initiates the promotion? The orchestrator? A worker? The plan doesn't say. If the orchestrator initiates it, the orchestrator could choose not to, leaving the claim at CONJECTURE forever. But that's fine - CONJECTURE is honest. If a worker initiates it, the worker would need to request the re-run. This seems like it needs clarification.

16. **The `do_not_cache` bit** - When is this set? The plan says "never memoize." But for what kinds of results? AuditOnly results? Failed results? The plan says "status ≠ OK ⇒ never cached" separately. So `do_not_cache` is for OK results that should never be memoized. When would you want an OK result to not be cached? Maybe for results that are too context-dependent? The plan doesn't give an example. This seems underspecified but not critical.

Let me now focus on the most impactful changes:

**A. The 60-bit rung circular dependency** - This is a real structural issue. The KEEP verdict requires the 60-bit rung, but the 60-bit rung needs Tier-2 budget, which requires KEEP. I need to propose a fix.

**B. The gate process boundary** - The plan says the gate bundle is in a separate SQLite file opened read-only by the orchestrator process. But if the gate runs in the orchestrator process, the process can open the file read-write. The plan needs to specify that the gate runs in a separate process, or that the file permissions enforce read-only at the OS level.

**C. The foundations auditor should set `skip_cache_lookup`** - The plan explicitly says the Skeptic does, but doesn't say the auditor does. This is a gap.

**D. The cost profile as a tier gate input** - The declared cost profile is load-bearing for the tier gate but only checked after the fact. A skill that consistently underestimates its cost gets work admitted to higher tiers. The plan needs a mechanism to escalate a persistent underestimation to a gate-level constraint (e.g., temporarily capping the skill's declared tier).

**E. The `justify` function's implementation** - This is the most critical function in the system (it derives all tags) but its implementation is underspecified. How does it compare an evidence node's target with a claim statement? For formal evidence, it's a hash comparison. For empirical evidence, what is it? The plan says it "checks that the evidence's declared target, assumptions and population cover that exact statement" but doesn't say how. This is a M0-level concern since M0 includes "the §7 derived-tag rule (justify)."

Let me think about which of these are the most impactful and write them up.

Actually, let me reconsider the 60-bit circular dependency more carefully.

§6 step (2b): "The 60-bit rung is the completion-and-extrapolation rung: the model fitted on the ≤ 50-bit rungs must predict the measured 60-bit mean inside the band, and the method must complete and recover x on at least 10 fresh instances; the fit-on / hold-out split is fixed in the ladder plan (gate bundle, §4), never chosen by the worker, and a clean in-sample fit that misses out of sample is REJECT."

§6 step (5): "The result table (size, trials, mean and sd of ops, memory, success rate, fit to the pre-registered model, out-of-sample prediction and its band) is the ladder's artifact, the Tier-2 ticket (§5) when its verdict is KEEP."

§5: "for Tier 2 on an algorithmic claim the ticket is a ladder result table with verdict KEEP (§6)"

§6 step (2b) also says: "a full 10²-trial distribution check at 60 bits is Tier-2 work by its own declared profile, not Tier-1, and runs only when the tier gate grants that budget."

So the 60-bit rung has two parts:
1. 10-instance completion check (cost unclear)
2. 10²-trial distribution check (Tier-2)

And the KEEP verdict requires the 60-bit rung to pass. But the 60-bit rung's distribution check is Tier-2, which requires KEEP.

I think the intended reading is:
- The ≤50-bit rungs produce a provisional verdict
- The 60-bit rung's 10-instance completion check is Tier-1 (minutes)
- The 60-bit rung's full distribution check is Tier-2
- The KEEP verdict requires the full 60-bit distribution check

But this creates the circular dependency. Unless:
- The ≤50-bit rungs alone can produce a provisional KEEP that grants Tier-2 access specifically for the 60-bit distribution check
- The 60-bit distribution check then confirms or rejects the KEEP

This would be a two-phase gate: provisional KEEP from ≤50 bits, then full KEEP from 60 bits. But the plan doesn't say this.

Alternatively, maybe the 10-instance completion check at 60 bits is sufficient for KEEP, and the full 10² distribution check is for something else (like STRONG-EMPIRICAL vs CONJECTURE). But the plan says "the ≤ 50-bit figures are STRONG-EMPIRICAL; the 60-bit figures carry the CONJECTURE tag their source assigns them." So the 60-bit figures are CONJECTURE anyway. And the KEEP verdict is about whether the method is an advance, not about the tag.

I think the cleanest fix is: the ≤50-bit rungs produce a provisional KEEP that grants Tier-2 access for the 60-bit rung specifically. The 60-bit rung then confirms or rejects. The final KEEP verdict includes the 60-bit result. This breaks the circularity.

Let me also think about the cost profile issue more carefully.

§5: "every skill declares its cost profile (complexity in inputs, expected tier) as part of its typed interface, so the orchestrator predicts spend before launch and the tier gate enforces cheap-before-expensive automatically."

§5: "Measured cost is compared against the declared profile; a persistent mismatch is a strategy-layer alarm (§15 P4), never a gate."

So the cost profile is used by the tier gate to decide admission, but a mismatch is only a strategy-layer alarm. This means a skill that declares "Tier-1, minutes" but actually takes hours would get work admitted to Tier-1, and the alarm would fire after the fact. The work already ran at the wrong tier. This is a real gap.

The fix could be: a persistent positive mismatch (actual cost > declared cost) escalates the skill's effective declared tier. After N mismatches, the skill's declared cost profile is automatically adjusted upward (to match observed cost), and this adjustment is recorded and attributed. This would be a gate-level mechanism, not just a strategy alarm. But the plan says "a persistent mismatch is a strategy-layer alarm, never a gate." So this would be a change to the plan's design.

Actually, I think the plan's position is defensible: the cost profile is a prediction, and predictions can be wrong. The alarm catches persistent errors. The question is whether the alarm has teeth. If the alarm just logs, it has no teeth. If the alarm adjusts the cost profile, it has teeth but it's a gate. The plan says it's "never a gate" - so it's a strategy-layer alarm. But a strategy-layer alarm that the orchestrator can ignore is useless. The plan should specify that the alarm has a consumer: the orchestrator's allocation mechanism, which should down-weight skills with persistent cost overruns. But that's already implied by "info-per-dollar" allocation.

Actually, I think the real issue is simpler: a skill that underestimates its cost could get Tier-2 work admitted as Tier-1, bypassing the Tier-2 ticket requirement. The tier gate checks the declared tier, not the actual runtime. If the skill says "Tier-1" but actually runs for hours, the tier gate lets it through as Tier-1 without a ticket. The fix is: the tier gate should also check the actual runtime against the tier boundary, and if the actual runtime exceeds the declared tier's budget, the result is inadmissible (not just alarming). This would be a gate-level check.

But this is tricky: you can't know the actual runtime before you run. And after you run, the result is already computed. The plan's approach (alarm after the fact) is reasonable, but it should have teeth: after a persistent mismatch, the skill's declared cost profile is adjusted, and old results are not retroactively inadmissible (they were admitted under the old profile), but new launches use the adjusted profile. This is a strategy-layer adjustment with gate-level consequences for future launches.

Hmm, but the plan says "a persistent mismatch is a strategy-layer alarm (§15 P4), never a gate." The "never a gate" is the issue. I think the fix is: the alarm triggers a cost-profile re-declaration, and the re-declaration is a gate-level event (the skill's interface version changes, so old cached results keep their old version and new launches use the new profile). This is consistent with the plan's versioning mechanism.

Actually, I think I'm overcomplicating this. Let me focus on the clearest, most impactful changes.

Let me also think about the `justify` function. The plan says M0 includes "the §7 derived-tag rule (justify) with append-only tag history." So `justify` must be implemented at M0. But the plan doesn't specify how it works for empirical evidence. For formal evidence, it's a statement hash comparison. For ladder evidence, it needs to check that the ladder was run on the right family. How?

The claim statement node has "scope and model assumptions, quantities and units." The ladder result table has "size, trials, mean and sd of ops, memory, success rate, fit to the pre-registered model, out-of-sample prediction and its band." The `justify` function needs to check that the ladder's family matches the claim's scope. But "family" is a mathematical concept, not a hash. How does `justify` compare them?

I think the answer is: the claim statement node's "scope and model assumptions" field is a typed object (not free text), and the ladder's instance-maker parameters are also typed, and `justify` compares them structurally. But the plan doesn't specify the type of the scope field. This is a gap that would block M0 implementation.

OK, let me now write up my proposals. I'll focus on the most impactful ones.

1. **60-bit rung circular dependency** (HIGH) - The KEEP verdict requires the 60-bit rung, but the 60-bit rung's distribution check is Tier-2, which requires KEEP. Fix: ≤50-bit rungs produce a provisional KEEP that grants Tier-2 access for the 60-bit rung specifically.

2. **Gate process boundary** (HIGH) - The gate bundle is a separate SQLite file opened read-only, but if the gate runs in the orchestrator process, the process can open it read-write. Fix: specify that the gate runs in a separate process, or that the file is opened with OS-level read-only permissions.

3. **Foundations auditor must set `skip_cache_lookup`** (MED) - The plan explicitly says the Skeptic does, but doesn't say the auditor does. Without it, the auditor's re-runs could hit the cache and "verify" nothing.

4. **Cost profile mismatch needs teeth** (MED) - A persistent cost underestimate gets work admitted to the wrong tier. The alarm fires after the fact but has no gate-level consequence. Fix: after a persistent mismatch, the skill's cost profile is re-declared (new interface version), and future launches use the adjusted profile.

5. **`justify` function's comparison mechanism for empirical evidence** (MED) - The plan says `justify` checks that evidence covers the exact statement, but doesn't specify how for empirical evidence. Fix: specify that the claim's scope field and the evidence's target field are typed objects compared structurally.

6. **The terminal-status invariant and downgraded claims** (LOW) - A downgraded claim isn't withdrawn (terminal), but its tag changed. Does it need a new terminal status? The plan says "every opened claim is a linear obligation that must reach a terminal status." A downgraded claim has reached a terminal status (e.g., promoted to STRONG-EMPIRICAL, then downgraded to CONJECTURE). The downgrade is a tag transition, not a status transition. The claim is still "promoted" in status but CONJECTURE in tag. This seems fine - the status is about the branch lifecycle, not the tag. But it could be confusing. Actually, I think this is fine as stated. Let me not propose this.

Let me also think about whether there are any missing gates or failure modes.

One thing I notice: the plan says "a worker that exits leaving one open produces a Leaked record." But what if a worker crashes? The harness should detect the crash and produce the Leaked record. The plan says "fail-fast in tests, logged and escalated in production." This seems sound.

Another thing: the plan says "the orchestrator may rewrite the branch tree, funding, worker prompts, and subproblems freely." But if the orchestrator can rewrite worker prompts, it could rewrite a worker's prompt to bypass a gate. The plan says "in whose context no gate rubric or detection logic is reachable" - but the orchestrator composes the prompt. If the orchestrator puts gate rubric in the prompt, the worker could use it to game the gate. The plan says the worker's prompt is "exactly the nodes it is handed" and "no gate rubric or detection logic is reachable." But the orchestrator is the one composing the prompt. If the orchestrator is compromised (by a worker that gained too much influence), it could inject gate rubric. The plan's defense is that the gate is mechanical and immutable, so even if the worker knows the gate rubric, it can't bypass the gate. This is sound - the gate doesn't depend on the worker not knowing it. The plan says "context isolation is a property of the dispatch, not of the model" and "a worker with a general file read can open what its context hides." But the gate runs in a separate process (or at least from a separate store), so the worker can't modify the gate even if it knows the rubric. This is sound.

Actually, wait - I said the gate process boundary is unclear. Let me re-read: "the gate bundle: a content-addressed bundle held in a separate store the orchestrator process opens read-only (a separate SQLite file at M0), whose hash is pinned at deployment and recorded in every gate-run record; a gate whose bundle hash differs from the pin fails closed."

So the orchestrator process opens the gate bundle read-only. But the gate logic itself - where does it run? In the orchestrator process? If so, the orchestrator could skip the gate logic even if it can't modify the bundle. The plan says "every gate ships a planted-failure self-test" and "gates run from a declarative plan with expected exit codes and ordered scopes." But if the gate logic is in the orchestrator process, the orchestrator could skip it. The plan's defense is the hash-chained log: "an orchestrator that rewrites history produces a log that fails verification." But if the orchestrator skips a gate, it just doesn't write a gate-run record. The log doesn't have a record to verify. The plan needs a mechanism to detect missing gate runs.

Actually, the plan says "a result not in the substrate does not exist to the claims DB." And "a cached value is served only from a verified attempt." So if the orchestrator skips the gate, the result doesn't have a gate-run record, and it's not admissible. But who checks this? The claims DB? The `justify` function? If `justify` checks for a gate-run record, then a result without one is not justifiable. This seems sound - the gate is enforced by the claims DB, not by the gate process.

But wait - the claims DB is also in the orchestrator process (or is it?). The plan says "the orchestrator process opens read-only" the gate bundle. But the claims DB is part of the state layer, which the orchestrator can write. So the orchestrator could write a claim without a gate-run record. The `justify` function would need to check for the gate-run record. But `justify` is part of the gate layer, which is immutable. If `justify` runs in the orchestrator process, the orchestrator could skip it.

I think the key question is: is there a separate process for the gate layer? The plan doesn't explicitly say so. It says the gate bundle is in a separate store, but it doesn't say the gate logic runs in a separate process. This is a real gap.

The fix: the gate layer runs in a separate process (a "gate daemon") that the orchestrator can only invoke, not modify. The gate daemon reads the gate bundle, runs the gate logic, and writes gate-run records to the substrate. The orchestrator can request a gate run but cannot skip it or modify its result. The claims DB's `justify` function is part of the gate daemon, not the orchestrator.

This is a significant architectural change, but it's necessary for the "immutable epistemics" principle to hold mechanically. Without it, the gate is a convention, not a mechanism.

Actually, let me reconsider. The plan says "the gate layer (mechanical, immutable)" and lists it as a component. It says "outside the orchestrator's write path." But it doesn't specify the process boundary. The separate SQLite file is a store boundary, not a process boundary. If the orchestrator process can open the file read-write (by just opening a new connection), the store boundary is a convention, not a mechanism.

The fix could be simpler: the gate bundle file has OS-level read-only permissions (chmod 444), and the orchestrator process runs as a user that cannot modify it. This is a deployment-level constraint, not a code-level one. The plan should specify this.

Or: the gate runs in a separate process, and the orchestrator communicates with it via a pipe or socket. The gate process has its own credentials and the gate bundle is only accessible to the gate process.

I think the simplest fix is to specify that the gate bundle file is owned by a separate user/account and the orchestrator process runs with reduced privileges that cannot write to it. This is a deployment constraint that should be specified in the plan.

Let me also think about one more thing: the plan says "the orchestrator may rewrite the branch tree, funding, worker prompts, and subproblems freely." But the branch tree is part of the state layer, which includes the dead-end ledger. The plan says "the orchestrator may rewrite the tree but never REFUTED entries." The REFUTED entries are in the ledger, which is an "append-only, hash-chained log." So the orchestrator can't rewrite REFUTED entries because the log is tamper-evident. But the orchestrator can append new entries. Could the orchestrator append a new PARKED entry that supersedes a REFUTED entry? The plan says "REFUTED (proven dead → permanent blacklist)" and "PARKED (blocked-not-dead)." These are different statuses. A PARKED entry can't supersede a REFUTED entry because they have different hypothesis keys (or do they?). Actually, the same hypothesis could be both REFUTED and PARKED if different evidence supports each. But the preflight checks REFUTED first: "Blocked = the hypothesis key matches a REFUTED entry whose retry predicate is unmet." So a REFUTED entry blocks new branches regardless of PARKED entries. This seems sound.

OK, I think I have enough. Let me write up my proposals.

Let me also think about the framing question. The plan's framing is "autonomous math research harness." Is this the right framing? I think the framing is sound - the plan is clear about what it is and what it isn't. The "mutable strategy, immutable epistemics" principle is the right core. The honest baseline is load-bearing. I don't think the framing is wrong.

One thing I might say about framing: the plan frames itself as a system for "open-ended research on hard problems" with ECDLP as the motivating instance. But the architecture is very specifically tuned to ECDLP - the ladder, the no-go checklist, the verifier. This is fine for a motivating instance, but the plan should acknowledge that the architecture would need different gates for different problems. The plan does say "the motivating instance" and "the realistic target is publishable increments on open subproblems," so it's not claiming generality. I think this is fine.

Actually, let me reconsider one more time. The plan says the gate layer is immutable and includes "submission verifier (xP==Q subprocess)." This is ECDLP-specific. If the system were to work on a different problem, the verifier would need to change. But the plan says the gate layer is immutable - so changing the verifier would require a new deployment. This is fine - the plan is for a specific instance. But the plan should be clear that the gate layer is immutable within a deployment, not across deployments. I think this is implied but not stated.

OK, let me finalize my proposals. I'll aim for 5-6 high-quality ones.

1. **60-bit rung circular dependency** (HIGH, §6)
2. **Gate process boundary** (HIGH, §4)
3. **Foundations auditor must set `skip_cache_lookup`** (MED, §7)
4. **Cost profile mismatch escalation** (MED, §5)
5. **`justify` comparison for empirical evidence** (MED, §7)
6. Maybe one more...

Actually, let me think about one more: the plan says "the orchestrator may request a [waiver], never grant one." But the orchestrator could request a waiver for every gate, flooding the human queue. The plan says "a waived check never counts as satisfied" and "the admission gates are non-waivable." So waivers are only for operational checks, not admission gates. And "a waiver may only let an explicitly operational check continue as AuditOnly output." So waivers are limited. But the orchestrator could still flood the human queue with waiver requests for operational checks. The plan doesn't address this. But this is a minor operational issue, not a structural one. Let me not propose this.

Let me think about one more potential issue: the plan says "every skill ships a known-answer self-test" and "every skill ships a known-answer self-test" with a "committed pass floor." But what if a skill's self-test passes but the skill produces wrong results on inputs outside the corpus? The plan addresses this with the axis rule (cross-checks) and the randomized postcondition. But the randomized postcondition is only for Tier-0 arithmetic skills. What about Tier-1 skills? The plan says "Tier-0 arithmetic skills verify their own answer before returning (the randomized postcondition; Sage's discrete_log checks base^res == a before it returns)." But Tier-1 skills (like rho) don't have a simple postcondition. The plan says they produce a certificate (the witness), which is checked by the verifier. So the certificate is the postcondition for Tier-1 skills. This seems sound.

OK, I think I have my proposals. Let me write them up concisely.

Actually, one more thought on the 60-bit circular dependency. Let me re-read the plan one more time...

§6: "a full 10²-trial distribution check at 60 bits is Tier-2 work by its own declared profile, not Tier-1, and runs only when the tier gate grants that budget."

§5: "for Tier 2 on an algorithmic claim the ticket is a ladder result table with verdict KEEP (§6)"

So the ticket for Tier-2 is a ladder result table with verdict KEEP. The verdict KEEP requires the 60-bit rung. The 60-bit rung's distribution check is Tier-2. So you need KEEP to get Tier-2, and you need Tier-2 to get the 60-bit rung, and you need the 60-bit rung to get KEEP. Circular.

But wait - maybe the 60-bit rung's 10-instance completion check (not the full 10² distribution check) is Tier-1? The plan says "the method must complete and recover x on at least 10 fresh instances" at 60 bits. 10 instances at 60 bits is ~1.3×10^10 group ops, which is minutes in compiled code. That's Tier-1. And the full 10² distribution check is Tier-2. So maybe the KEEP verdict only requires the 10-instance completion check (Tier-1), and the full distribution check is for something else?

But the plan says "the model fitted on the ≤ 50-bit rungs must predict the measured 60-bit mean inside the band." The "measured 60-bit mean" requires multiple trials, not just 10. With 10 instances, you have a mean but it's very noisy (sd ≈ 0.5×mean). The band is set by the A/A null arm. With only 10 instances, the CI is wide. Can you make a KEEP/REJECT decision with 10 instances?

Actually, the plan says "the method must complete and recover x on at least 10 fresh instances" - this is a completion check, not a distribution check. And "the model fitted on the ≤ 50-bit rungs must predict the measured 60-bit mean inside the band" - this requires a mean, which you can compute from 10 instances, but it's noisy. The plan doesn't say how many trials are needed for the 60-bit mean prediction. It says "a full 10²-trial distribution check at 60 bits is Tier-2 work" - so 10² trials is the full check. But 10 trials might be enough for a provisional check.

I think the plan's intent is:
- ≤50-bit rungs: 10² trials each, Tier-1, produce the model fit
- 60-bit rung: 10 trials for completion (Tier-1), 10² trials for distribution (Tier-2)
- KEEP verdict requires the 60-bit completion check (Tier-1) and the model prediction check
- The full 60-bit distribution check (Tier-2) is for STRONG-EMPIRICAL confirmation

But the plan doesn't clearly separate these. The "verdict KEEP" is defined in step (2) as "the whole claim CI clears 1 + 2·radius" which requires the distribution check. And step (2b) says the 60-bit rung is part of the KEEP verdict. So KEEP requires the 60-bit distribution check, which is Tier-2, which requires KEEP. Circular.

I think the fix is: introduce a "provisional KEEP" verdict from the ≤50-bit rungs that grants Tier-2 access specifically for the 60-bit distribution check. The final KEEP verdict requires the 60-bit distribution check. This breaks the circularity.

Let me write this up.

Actually, I realize there might be an even simpler reading. Maybe the ≤50-bit rungs alone can produce a KEEP verdict, and the 60-bit rung is an additional check that can REJECT but not produce KEEP. Let me re-read...

§6 step (2): "at the 30/40/50-bit rungs at least 10² independent trials per size... the sorted-distribution shape compared to the claimed model... a speedup is KEPT only if the whole claim CI clears 1 + 2·radius."

§6 step (2b): "The 60-bit rung is the completion-and-extrapolation rung: the model fitted on the ≤ 50-bit rungs must predict the measured 60-bit mean inside the band, and the method must complete and recover x on at least 10 fresh instances... a clean in-sample fit that misses out of sample is REJECT."

So step (2) defines KEEP based on the ≤50-bit rungs. Step (2b) adds the 60-bit rung as an additional check that can REJECT. So KEEP is produced by ≤50-bit rungs, and the 60-bit rung can override it to REJECT. This would mean:
- ≤50-bit rungs produce KEEP → Tier-2 ticket
- 60-bit rung (Tier-2) can REJECT, overriding KEEP

But this creates a different problem: the 60-bit rung can REJECT a claim that already has a Tier-2 ticket. The Tier-2 work was already done (the 60-bit distribution check). If it REJECTs, the claim is refuted. But the Tier-2 ticket was used to get the Tier-2 budget for the 60-bit check. So the claim got Tier-2 budget, ran the 60-bit check, and was rejected. This is fine - it's the normal flow. The Tier-2 ticket from ≤50-bit rungs grants Tier-2 budget for the 60-bit check, which can confirm or reject.

Wait, but §5 says "for Tier 2 on an algorithmic claim the ticket is a ladder result table with verdict KEEP (§6)." If the ≤50-bit rungs produce KEEP, that's the ticket. The 60-bit rung is Tier-2 work that uses the ticket. If the 60-bit rung REJECTs, the claim is refuted. This seems to work!

But then what does "the result table... is the Tier-2 ticket when its verdict is KEEP" mean? The result table includes the 60-bit data. If the 60-bit rung hasn't run yet (it's Tier-2), the result table only has ≤50-bit data. Can that produce KEEP?

I think the plan is ambiguous here. The result table is defined in step (5) as including "out-of-sample prediction and its band" which is the 60-bit data. So the result table requires the 60-bit rung. But the 60-bit rung is Tier-2. And the Tier-2 ticket is the result table with KEEP. Circular.

OK, I'm now confident this is a real circular dependency. Let me propose the fix.

The fix: split the verdict into two phases:
1. **Provisional KEEP** from ≤50-bit rungs (Tier-1): the model fits in-sample, the CI clears the band, BSGS is beaten. This is the Tier-2 ticket.
2. **Confirmed KEEP** after the 60-bit rung (Tier-2): the model predicts out-of-sample, the method completes. This upgrades the ladder result from provisional to confirmed.

A provisional KEEP that fails the 60-bit rung is REJECT. A provisional KEEP that passes is confirmed KEEP. The Tier-2 ticket is the provisional KEEP. The confirmed KEEP is the final verdict.

This is clean and breaks the circularity. Let me write it up.

Now let me also think about the gate process boundary issue more carefully.

The plan says: "the gate bundle: a content-addressed bundle held in a separate store the orchestrator process opens read-only (a separate SQLite file at M0), whose hash is pinned at deployment and recorded in every gate-run record; a gate whose bundle hash differs from the pin fails closed."

The key phrase is "the orchestrator process opens read-only." This means the orchestrator process has a read-only file handle to the gate bundle. But the orchestrator process could also open a read-write file handle to the same file (unless OS permissions prevent it). The plan doesn't specify OS-level permissions.

More importantly, the gate logic itself - where does it run? If it runs in the orchestrator process, the orchestrator could skip it. The plan says "gates run from a declarative plan with expected exit codes and ordered scopes, where an earlier failure blocks later ones." But if the orchestrator process is the one running the gates, it could choose not to run a gate. The hash-chained log would show a missing gate-run record, but only if someone checks. The `justify` function checks for gate-run records, but if `justify` also runs in the orchestrator process, it could be skipped too.

The fix: the gate layer runs in a separate process. The orchestrator can submit work to the gate process, but cannot modify the gate process or skip its checks. The gate process writes gate-run records to the substrate. The `justify` function runs in the gate process. The orchestrator can read gate-run records but cannot write them.

This is a significant architectural change, but it's necessary for the "immutable epistemics" principle to hold mechanically. The plan says "outside the orchestrator's write path" but doesn't specify how. A separate process is the simplest mechanism.

Actually, the plan says "a separate SQLite file at M0." This is a store boundary. But it also says "the orchestrator process opens read-only." If the orchestrator process opens the file read-only (O_RDONLY), it can't write to it through that handle. But it could open another handle. Unless the file permissions prevent it.

I think the simplest fix is: the gate bundle file is owned by root (or a gate user), the orchestrator process runs as a non-root user, and the file has 0444 permissions. The orchestrator process literally cannot open the file for writing. This is a deployment constraint, not a code constraint. The plan should specify it.

But this doesn't address the gate logic running in the orchestrator process. Even if the orchestrator can't modify the gate bundle, it could skip the gate logic. The gate-run record would be missing, and `justify` would reject the claim. But `justify` runs in the orchestrator process too (it's part of the claims DB, which the orchestrator writes). So the orchestrator could skip `justify` too.

The fix: `justify` and the gate logic run in a separate process. The orchestr