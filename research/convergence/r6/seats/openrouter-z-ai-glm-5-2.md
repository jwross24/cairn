Let me carefully review this plan against the three duties specified.

**Duty 1: Coherence of the constraint web**

I need to trace mechanisms across sections and find contradictions, duplicated rules, or rules that could be violated by mechanisms in other sections.

Let me check several things:

1. Substrate key and cache bits (§3) vs replay grades and certificates (§3) vs ledger preflight (§4) vs gate discipline (§4) vs budget meet (§5) vs ladder protocol (§6) vs challenge/solution Lean protocol (§7) vs disagreement protocol (§7/§10) vs deferred decisions (§15).

Let me look for contradictions:

- §3 says "A cached result is served only if every blob it references is present; otherwise it is recomputed." This is consistent with §3's cache bits.

- §3 says "for a `Verifiable` recipe each witness is its own attempt and must pass its verifier" - consistent with §6's certificate verification.

- §4 ledger preflight: "AlreadySettled" checks if a branch already holds the hypothesis key. But §5 tier gate says "A ticket is bound to a hypothesis, never to a branch." These seem consistent - the preflight prevents duplicate branches, the tier gate prevents ticket transfer.

- §5 budget: "The granted budget is a hard ceiling the harness enforces at runtime, set at a multiplier of the declared expectation named in the gate bundle (M0 default 4×...)" and §6 says "A trial that hits the per-trial patience ceiling of the ladder plan (the §5 budget ceiling) counts as a failure." This is consistent.

- §6 says the ladder's 60-bit rung "is tiered by its declared profile" and §5 says "a declared cost profile above ≈ 10³ core-hours is a Tier-3 request." A 60-bit generic trial is ≈ 1.3×10⁹ group ops. If we estimate ~0.11 µs per iteration (from §5), that's ~143 seconds per trial, and with m=10 hold-out instances, ~1430 seconds ≈ 0.4 core-hours. That's Tier 1, not Tier 2. But §6 says "a full 10²-trial distribution check at 60 bits is Tier-2 work by its own declared profile." The 60-bit rung only runs m=10 instances, so it's Tier 1. But §5 says "the ladder's 60-bit rung is tiered by its own declared cost profile." Let me re-read...

§5: "Tier 1 — one core, minutes: toy DLPs 30–50 bit, small Gröbner bases, a Lean compile, bounded counterexample sweeps. The research lives here. The ladder's distribution rungs (§6, ≤ 50 bits) are Tier-1; its 60-bit rung is tiered by its own declared cost profile."

§6: "The 60-bit rung runs the claimant's method on the m hold-out instances only... and is tiered by its declared profile. A 60-bit generic trial is ≈ 1.3×10⁹ group ops (minutes in compiled code, a quarter hour interpreted), so a full 10²-trial distribution check at 60 bits is Tier-2 work by its own declared profile, not Tier-1, is no part of the rung, and runs only when the tier gate grants that budget."

So the 60-bit rung with m=10 instances: 10 × 1.3×10⁹ ops. At 0.11 µs/op, that's ~1430 seconds ≈ 24 minutes. That's Tier 1 (minutes). But if interpreted, 10 × 15 min = 150 min = 2.5 hours, which is Tier 2. So the tier depends on the implementation. The plan says "is tiered by its declared profile" which is correct - the tier gate derives the tier from the cost profile. This seems consistent.

Let me look for actual contradictions more carefully.

- §4 says "Withdrawal is terminal and reason-bearing; it erases no gate outcome already recorded against the statement hash, and re-opening the same statement hash is a re-walk the preflight sees like any other." And §4 preflight says "AlreadySettled = the proposal opens a new branch on a hypothesis key that a branch already holds — an active or parked one, or a promoted one whose claim statement stands at PROVEN or STRONG-EMPIRICAL." But if a branch was withdrawn, it's terminal. Does a withdrawn branch's hypothesis key trigger AlreadySettled? The text says "an active or parked one, or a promoted one" - a withdrawn branch is none of these. So re-opening after withdrawal is allowed. This seems consistent with "re-opening the same statement hash is a re-walk the preflight sees like any other."

- §2 says a self-test failure "yanks the implementation revision: the tier gate refuses new launches of it, an in-flight attempt completes with status `SKILL_YANKED`" and §4 says "A harness-terminated attempt (`BUDGET_EXCEEDED`, `SKILL_YANKED`, or `INTERRUPTED`... is not a leak." These are consistent.

- §3 says "the `salt` key field that moves a whole class of results into a fresh namespace when a tool version is found faulty" and §2 says "a yank record (§2) names its reach as a predicate over recipe-key fields; every attempt inside the reach gains an append-only `disowned` mark." Wait, §2 says the yank record names its reach, but §3 says the salt moves results into a fresh namespace. Are these the same mechanism or different? Let me re-read.

§2: "the yank record names the fault's reach as a predicate over recipe-key fields — by default the whole implementation revision, every recipe key naming it; a narrower predicate... is installed only by an attributed human ruling... and every attempt inside that reach is disowned (§3), and only an attributed new revision with a fresh certificate clears the yank."

§3: "the `salt` key field that moves a whole class of results into a fresh namespace when a tool version is found faulty: a yank record (§2) names its reach as a predicate over recipe-key fields; every attempt inside the reach gains an append-only `disowned` mark... the class's `salt` is bumped so fresh attempts take fresh keys; attempts outside the named reach stand."

So §3 references §2's yank record. The salt bump is the mechanism that ensures fresh attempts take fresh keys after a yank. These are consistent - §2 defines the yank and its reach, §3 defines how the substrate responds (disowned mark + salt bump).

Let me look for something more subtle...

- §5 tier gate: "The ticket is the most recent admissible substrate node of the kind the tier requires... produced at the tier below for that same hypothesis key and method identity... where 'most recent' ranges over every node of that kind for the hypothesis whatever its verdict — a later REJECT or INCONCLUSIVE ladder table displaces an older KEEP." 

This is interesting. If a KEEP table is the ticket for Tier 2, and then a later REJECT table is produced, the REJECT displaces the KEEP as "most recent." But a REJECT is not a ticket (it's a refutation). So what happens? The gate would see the most recent node is a REJECT, which is not an admissible ticket. So the gate refuses. This seems correct - a later refutation should block Tier-2 spend.

But wait - §5 also says "the verdict rule below is applied to the node so selected." Let me check what the verdict rule says... "for Tier 2 on an algorithmic claim the ticket is a ladder result table with verdict KEEP (§6)." So if the most recent node is a REJECT, it's not a KEEP, so it's not a valid ticket. The gate refuses. This is consistent.

- §6 says "KEEP_IN_SAMPLE is the Tier-2 ticket for the 60-bit rung of the same hypothesis key and for nothing else" and §5 says "a table with verdict KEEP_IN_SAMPLE is a Tier-2 ticket valid for the 60-bit rung of the same hypothesis key and for no other launch; the ticket records that purpose and the gate refuses a launch whose declared purpose differs." Consistent.

- §7 says "A verified refutation of the statement — a counterexample_hunt_record KILLED by a counterexample that passed its verifier, a machine-checked proof of the Challenge's negation, a ladder REJECT on the claim's own pre-registered model (a REJECT whose predicate is xP ≠ Q or a count divergence yanks the revision and refutes no claim version, §6) — moves the claim version to terminal status refuted." 

And §6 says: "the ledger entry a REJECT writes takes its refutation_kind from the predicate — xP ≠ Q or a count divergence is an implementation entry against the revision... and yanks that revision (§2), since a wrong answer on a gate-generated instance is a known-answer failure the corpus missed and says nothing about the method's cost; the floor, the memory predicates and the model misses are measured entries on the hypothesis key."

So a REJECT from xP≠Q is an implementation entry (yanks revision, no claim refutation), while a REJECT from model miss is a measured entry (refutes the claim). §7 says the ladder REJECT that refutes is "a ladder REJECT on the claim's own pre-registered model" - this is the measured entry kind. And it explicitly excludes "a REJECT whose predicate is xP ≠ Q or a count divergence" from claim refutation. Consistent.

Let me look at milestones now.

- M0 done-when: "justify returns STRONG-EMPIRICAL from a synthetic ladder_table evidence node with verdict KEEP whose attempt carries a passed reproducibility record." This depends on the §7 derived-tag rule and §3 reproducibility. M0 builds the schema for these. ✓

- M0 done-when: "the tier gate refuses a fixture launch declaring a tier two above its ticket and records TierRefused." This depends on the tier gate (§5). M0 builds the tier gate. ✓

- M1 done-when includes "the escrow and yank fixtures." M0 schema includes "the columns of the budget ceiling and the verification escrow with its release rule (§5)." M0 says "the behaviors those columns serve... are exercised first at M1." So M0 has the schema, M1 exercises the behavior. ✓

- M1 done-when: "a dispatch whose method identity differs from its hypothesis object's is refused before any trial." This depends on §6's dispatch record. M1 builds the ladder. ✓

- M2 done-when: "a log truncated to an earlier valid prefix fails startup verification against the checkpoint." This depends on §3's hash-chained log and checkpoint. M0 schema includes... let me check. M0 says "the gate-bundle pin (§4)" but does M0 include the hash-chained log? 

§3 says "the log and its checkpoint are built at M2 (§13)." And M2 done-when includes the checkpoint test. M0 doesn't build the log. But §3 also says the checkpoint is "a file beside the gate-bundle pin (§4), owned by the operator." And M0 builds the gate-bundle pin. So M0 builds the pin but not the log/checkpoint. M2 builds the log. This seems consistent.

But wait - §4 says "the ledger and branch-tree history are an append-only, hash-chained log" and M0 includes "the claim statement node (§4)" and "the typed evidence node and the §7 derived-tag rule (justify) with append-only tag history." Does M0 need the hash-chained log for the tag history? §7 says "Tag history is append-only and attributed." But the hash-chained log is a §3 mechanism built at M2. 

Actually, M0 can have append-only tag history without the hash-chained log - the hash chain is a tamper-evidence mechanism on top of append-only records. M0 can have append-only records (SQLite tables that only insert) without the hash chain. The hash chain is added at M2. This seems fine.

Let me look for a milestone that depends on a mechanism no milestone builds...

- M3 done-when: "on seeded runs holding one branch whose hypothesis is the known true advance of control (j) and one whose hypothesis is fixture (a)'s method, the orchestrator's own dispatch carries the first to KEEP and a STRONG-EMPIRICAL tag through justify and the second to a measured REFUTED entry." This depends on the ladder (M1), justify (M0), and the ledger (M2). All built before M3. ✓

- M4 done-when: "the foundations auditor's audit record names its cycle grant and per-stratum charges." This depends on the foundations auditor (§7). M4 builds it. ✓

Let me look more carefully for contradictions...

§5 says: "The ticket is the most recent admissible substrate node of the kind the tier requires (status OK, replay grade ≥ Verifiable, reproducibility-checked under the §3 policy) produced at the tier below for that same hypothesis key and method identity (or statement hash), where 'most recent' ranges over every node of that kind for the hypothesis whatever its verdict — a later REJECT or INCONCLUSIVE ladder table displaces an older KEEP"

Wait - the ticket must have "status OK" but a REJECT table has status... what? Let me check. §3 says "status ≠ OK ⇒ never cached." A REJECT is a verdict, not a status. The attempt status is OK (the computation completed), but the verdict is REJECT. So the attempt has status OK, replay grade ≥ Verifiable, and reproducibility-checked. So a REJECT table is an admissible node (status OK) but its verdict is REJECT. The "most recent" rule says it displaces an older KEEP. Then the verdict rule says the ticket must have verdict KEEP. So the most recent node is a REJECT (admissible but not KEEP), and the gate has no valid ticket. This is correct behavior - a later refutation blocks tier advancement.

But actually, is a REJECT table's status OK? §6 says the result table is "the ladder's artifact." The attempt that produced it - did it complete successfully? The ladder ran, produced a table, and the verdict was REJECT. The attempt status would be OK (it completed), but the verdict is REJECT. So yes, the attempt has status OK. The "most recent" rule includes it. The verdict rule excludes it as a ticket. Consistent.

Let me look at the §4 "AlreadySettled" more carefully:

"AlreadySettled = the proposal opens a new branch on a hypothesis key that a branch already holds — an active or parked one, or a promoted one whose claim statement stands at PROVEN or STRONG-EMPIRICAL — or opens a branch whose method identity and claimed cost model equal such a promoted holder's and whose declared parameter region is contained in the holder's"

And later: "the holding branch's own launches never see this answer, and gate-owned re-runs (the Skeptic's, the auditor's, a null-control re-measurement) are not branch fundings."

This seems fine. The preflight prevents duplicate branches, not duplicate gate runs.

Now let me check for a rule in one section that a mechanism in another could violate:

§2 says: "a cross-check that has never disagreed is reported as untested, not as passing." And §2 says "Two builds of one library (gp and cypari2 both wrap libpari) are one implementation." 

§13 M0 exemplar skill says: "with a BSGS-vs-SEA algorithm cross-check on the order, valid for bits ≤ 50 only (at 60 bits PARI's generic path is SEA and the two agree by construction)." 

Wait - BSGS and SEA are different algorithms, not different implementations. So this is an "algorithm" axis cross-check. But at 60 bits, "the two agree by construction" - meaning BSGS is not used at 60 bits (too expensive), and PARI's generic path IS SEA. So the cross-check is only valid for bits ≤ 50. This is consistent with §2's axis rule - the cross-check declares its axis (algorithm) and input range (≤ 50 bits).

But §2 also says "a cross-check that has never disagreed is reported as untested, not as passing." The BSGS-vs-SEA cross-check at ≤ 50 bits - has it ever disagreed? If not, it's "untested." But the plan says it's a cross-check. Is this a contradiction? 

Actually, §2 says "a cross-check that has never disagreed is reported as untested, not as passing." This means in the skill's self-test reporting, if the cross-check has never produced a disagreement, it's reported as untested. The M0 exemplar skill has this cross-check, and if BSGS and SEA have never disagreed on the test cases, the cross-check is reported as untested. But the plan says the skill "ships a known-answer self-test" and the cross-check is part of the skill's validation. 

Hmm, I think the "reported as untested" is about the cross-check's power to detect faults, not about whether to use it. The skill declares the cross-check, its axis, and its range. If it's never disagreed, it's reported as untested (meaning it hasn't been shown to catch bugs), but it still runs. This is a reporting requirement, not a prohibition. I don't think this is a contradiction.

Let me look at §7's "justify" and §4's claim statement node more carefully.

§4: "where the node carries a formal statement the formalization gate derives a second, formal statement hash when it compiles the Challenge (§7), and its gate-run record binds the two under the bundle hash — the Solution names the formal statement hash, everything else names the claim statement hash."

§7: "The gate compiles the Challenge module from the claim statement node (§4)... the Formalizer... submits a Solution module that names the Challenge's formal statement hash."

So the formal statement hash is derived by the gate when it compiles the Challenge. But the Formalizer submits a Solution naming that hash. How does the Formalizer know the formal statement hash before the gate compiles it? 

Actually, re-reading: the gate compiles the Challenge, which produces the formal statement hash. The Formalizer writes a Solution that names this hash. But the Formalizer needs to know the hash to name it. So the Formalizer must have access to the compiled Challenge or its hash. But §7 says "the Formalizer never creates or edits Challenge text." The Formalizer can read the Challenge (it's derived from the claim statement node) and thus know the formal statement hash after the gate compiles it. 

Actually, I think the flow is: (1) claim statement node is created, (2) the gate compiles the Challenge from it, producing the formal statement hash, (3) the Formalizer reads the Challenge and writes a Solution naming the formal statement hash, (4) the gate checks the Solution. This seems fine - the Formalizer reads the compiled Challenge, not creates it.

But wait - does the gate compile the Challenge before the Formalizer writes the Solution? The plan says "the gate compiles the Challenge module from the claim statement node." When does this happen? It seems like it happens as part of the formalization gate run. But the Formalizer needs the formal statement hash to write the Solution. So there must be a pre-compilation step. 

Actually, I think this is fine. The claim statement node is created first. Then the gate can compile the Challenge at any time (it's deterministic from the claim statement node). The Formalizer gets the formal statement hash (from the compiled Challenge or by asking the gate to compile it) and writes the Solution. Then the formalization gate runs the full check. This is a workflow detail, not a contradiction.

Let me now look at the §10 egress rule and §7 tags.

§10: "every assertion it prints names a claim statement hash and carries that version's derived tag (§7) and evidence pointer." This depends on §7's derived tag. Consistent.

§10: "a submission — the egress of a recovered x for the target or for any instance — is the verifier's passing node (§13) or nothing." And §4: "submission verifier (xP==Q subprocess or no submit, ever)." Consistent.

Now let me look for duplicated rules stated two ways...

§5 says "a declared cost profile above ≈ 10³ core-hours is a Tier-3 request whatever the skill is called" and §5 also says "the ≈ 10³ core-hour rule above is that table's Tier-2/Tier-3 edge" (referring to the boundary table). And §4 says "the tier cost boundaries of §5" are in the gate bundle. These are all referring to the same thing - the boundary table contains the ≈ 10³ core-hour rule. Not a contradiction, just multiple references.

§6 says "A trial that hits the per-trial patience ceiling of the ladder plan (the §5 budget ceiling) counts as a failure in the success-rate column" and §5 says "exhaustion stops the attempt with status BUDGET_EXCEEDED (≠ OK: never cached, never a ticket, never evidence), and the ladder counts such a trial as a failure in its success-rate column." These say the same thing. The §6 version adds "(the §5 budget ceiling)" to link them. Not a problematic duplication - §5 states the rule, §6 references it.

Let me look at §2's self-test and §4's gate discipline more carefully.

§2: "A self-test failure (a floor miss, a certificate mismatch, a double-run divergence — or a ladder trial under §6 that returns xP ≠ Q or a self-reported count diverging from the gate's, a known-answer failure the corpus missed) yanks the implementation revision."

§4: "every gate ships a planted-failure self-test (a fixture that must FAIL and one that must PASS) run before the gate itself."

These are different things - §2 is about skill self-tests, §4 is about gate self-tests. Not a duplication.

§4: "the admission gates (verifier, ladder, no-go, formalization, reproducibility, proportional scrutiny, tier) are non-waivable" and §4 also says "a waiver may only let an explicitly operational check continue as AuditOnly output." These are consistent - admission gates can't be waived, only operational checks can.

Let me now look at something potentially problematic. §5 says:

"the tier gate reserves the verification component from the grant at launch, refuses a launch whose verification the remaining budget cannot cover, and binds the reservation to the node, never to the branch"

And later: "a branch reaching a terminal status returns its unreserved grant and never the escrow of an admissible node it produced"

And: "every later re-verification of a node is funded from the standing per-cycle audit line the gate bundle names (§7), never from the node's escrow."

So the escrow funds the first re-verification, and the audit line funds later ones. But §7 says: "from each node's escrow on its first draw and from the standing per-cycle audit line the gate bundle names on every later one (§5)." Consistent.

But what about a node whose escrow was released because the attempt ended with status ≠ OK? §5 says: "released unspent only where the attempt ended with status ≠ OK or the node was disowned." If the attempt ended with status ≠ OK, the node is not admissible (status ≠ OK ⇒ never cached, never a ticket, never evidence). So there's nothing to re-verify. Consistent.

What about a node whose escrow was released because the branch was withdrawn but the node was admissible (status OK)? §5 says: "a branch reaching a terminal status returns its unreserved grant and never the escrow of an admissible node it produced." So the escrow stays even after the branch is withdrawn. And: "the auditor's exhaustive Tier-2/3 pass (§7) spends every such escrow within one audit cycle, so an unspent reservation outlives its branch by at most that cycle." Consistent.

OK, I'm not finding obvious contradictions in the constraint web. Let me look more carefully at one thing...

§4 says: "the orchestrator may rewrite the branch tree, funding, worker prompts, and subproblems freely. It may never edit what counts as 'proven,' the gates, the no-go checklist, the ladder, the verifier, or the calibration taxonomy."

And §4 says: "self-redesign = editing data (tree/prompts/subproblems), never gates."

And §0 says: "Meta-level fixed, object-level fluid."

These are all consistent.

Let me check one more thing. §3 says: "the hypothesis object is an immutable, content-addressed node... written by the worker or human that opens the branch, at branch open." And §4 says: "a claim is an immutable, content-addressed claim statement node... written when the claim is opened — by the Reframer, the Prover or the human, before any proof or measurement." 

The hypothesis object is written at branch open. The claim statement node is written when the claim is opened. Are these the same event? §3 says "the branch points at it by hash" and "naming the claim statement hash where a claim exists." So a branch may or may not have a claim. If it does, the hypothesis object names the claim statement hash. If not, the hypothesis object stands alone. This seems fine - they're different objects created at related but potentially different times.

Now let me look at §6 step (0): "The hypothesis object's hash, its method identity... and the implementation revision under test... are named in the ladder's dispatch record; the ladder runs exactly that identity... the object's position in the substrate's append order precedes the gate's entropy commitment of step (1)."

And §3: "the hypothesis object is... appended to the substrate's append-only record sequence when the branch opens... pre-registration (§6 step 0) is an order of records — the ladder refuses a rung whose hypothesis object does not precede the gate's entropy commitment for that rung."

Consistent - both say the hypothesis object must precede the entropy commitment.

Let me now move to Duty 2: Ceremony audit.

Artifacts the plan creates:
1. **Certificates** (§3): "Certificate = declared content address + witness." Consumer: the reproducibility gate re-checks the witness (§3). The verifier checks aP + bQ = X = cP + dQ, etc. This is consumed by running code - the reproducibility gate. ✓

2. **Ledgers** (§4): dead-end ledger with REFUTED/PARKED entries. Consumer: the ledger preflight (§4) which branches on Allowed/Blocked/RequiresNullControl/AlreadySettled. The tier gate (§5) reads the §8 flag. The preflight is running code that branches on it. ✓

3. **Tag histories** (§7): "Tag history is append-only and attributed." Consumer: justify derives tags, the foundations auditor re-derives. Running code branches on it. ✓

4. **Gate plans** (§4): "gates run from a declarative plan with expected exit codes and ordered scopes." Consumer: the gate runner itself. ✓

5. **Self-tests** (§2): "Every skill ships a known-answer self-test." Consumer: the tier gate refuses uncertified/yanked revisions (§5). Running code branches on it. ✓

6. **Receipts** (§3): "execution receipt" is part of the attempt record. Consumer: part of the substrate node, read by justify and the reproducibility gate. ✓

7. **Result tables** (§6): "The result table... is the ladder's artifact, the Tier-2 ticket." Consumer: the tier gate (§5) reads it as a ticket. justify (§7) reads it for tag derivation. ✓

8. **Alarms** (§15 P4): "Strategy-layer alarms only." Consumer: §15 says "drift monitors." §10 says "depth and age are drift-monitor inputs (§15 P4), never gate inputs." So alarms are consumed by... what running code? §15 P4 says they're "drift monitors" but doesn't name a consumer that branches on them. The plan says they're "strategy-layer alarms only" and "never a gate on a claim." So they exist for humans/status reports. The plan should name this. Actually, §15 P4 says "Decides: whether either fires on anything the ladder misses." This is a deferred decision (M1-M2). So at M0-M1, alarms may not have running code that branches on them. But the plan says they're "strategy-layer alarms" - they would surface on the human queue (§10). 

Actually, looking more carefully, §15 P4 is a deferred decision. The alarms don't exist yet. When they exist, they would be consumed by the human queue (§10). The plan says "depth and age are drift-monitor inputs (§15 P4), never gate inputs." So they're human-facing. This is fine - they exist for humans and status reports, and the plan says so.

9. **Audit records** (§7): "the audit record names the population size, the cutoff, the critical-set coverage, the seed and the sampled identifiers." Consumer: the foundations auditor itself uses it for tracking. But does any other code branch on it? §7 says "a stratum below the bundle's target surfaces on the human queue (§10)." So the audit record's shortfall is consumed by the human queue. And the audit record itself is used by the auditor to track what it has checked. ✓

10. **Near-duplicate signal** (§4): "a 64-bit SimHash over the hypothesis text... is advisory only and never sets a status." Consumer: "before M4 it routes the proposal to the human, or parks it with blocker near_dup_review; from M4 it routes to the Librarian." So it's consumed by the preflight routing. But it "never sets a status" - it's advisory. The preflight uses it to route, not to block. This is fine - it has a named consumer (preflight routing) and a clear retirement condition (when the Librarian's retrieval stack exists at M4, it replaces the human routing). ✓

11. **Waiver registry** (§4): "the waiver registry" is part of the gate bundle. Consumer: "the waiver check" - every reader of a waiver row treats it as absent unless the digest matches. Running code branches on it. ✓

12. **Attestation file** (§4): "operator-owned, append-only attestation file." Consumer: "every reader of such a row — justify, the tier gate, the waiver check, the preflight — treats the row as absent unless the digest matches the record at that offset." Running code branches on it. ✓

13. **Dispatch records** (§4): "The dispatch record names the hashes of the nodes handed over, the role-template hash, the allow-list and... the hash of those request bytes." Consumer: the dispatch canary (§13 M1) checks it. The ledger records it. ✓

14. **Yank records** (§2): "the yank record names the fault's reach as a predicate over recipe-key fields." Consumer: the tier gate refuses yanked revisions (§5). The substrate marks attempts as disowned (§3). Running code branches on it. ✓

15. **Counterexample-hunt records** (§7): "a substrate node {statement hash, sampling distribution D...}." Consumer: the tier gate reads SURVIVED as a Tier-2 ticket for conjectures (§5). justify reads KILLED as a refutation (§7). ✓

16. **Review verdicts** (§7): "review_verdict {statement hash, reviewer, verdict...}." Consumer: justify derives PROVEN only from a lean_artifact node and an approve verdict (§7). The tier gate reads it for Tier-2 theorem claims (§5). ✓

17. **Nogo review nodes** (§8): "nogo_review node records accept_for_tiering." Consumer: "the tier gate (§5) grants it no... ticket above Tier 1 until a nogo_review node records accept_for_tiering." ✓

18. **Human queue items** (§10): "The human queue is a typed substrate object." Consumer: the orchestrator reads queue depth and age. The harness blocks on human input. ✓

Now, are there any artifacts that nothing branches on?

Let me check the **gate-bundle hash** recorded in every gate-run record. §4 says "whose hash is pinned at deployment and recorded in every gate-run record; a gate whose bundle hash differs from the pin fails closed." Consumer: every gate run checks the pin. ✓

The **chain head checkpoint** (§3): "the chain head is also appended, at every gate run, to a checkpoint outside the orchestrator's write authority." Consumer: "a log that does not extend the last checkpoint fails verification at startup and before any promotion." Running code branches on it. ✓

I think all artifacts have consumers. Let me check for mechanisms whose names promise more than their definitions deliver.

- "Terminal-status invariant" (§4): The name suggests an invariant that's maintained. The definition says "every opened branch and every opened claim is a linear obligation that must reach a terminal status." It produces a "Leaked" record when violated. The name promises an invariant, but the mechanism is a detection + escalation, not enforcement. However, the plan is clear about this: "A worker that exits leaving one open produces a Leaked record that is counted and escalated." It's a detection mechanism, not a prevention mechanism. The name "invariant" might over-promise, but the definition is clear. I'll note this but it's not a demonstrable defect.

- "Proportional scrutiny" (§7): The name suggests scrutiny proportional to claim size. The definition delivers a router with classes based on typed fields. The top class requires ladder KEEP, formalization, reproducibility, and expert sign-off. This seems to deliver what the name promises. ✓

- "Strong law of small numbers" (§7): The name suggests a hard gate. The definition says "a small-case pattern is a conjecture until it survives larger cases + a deliberate counterexample hunt." This is enforced by the counterexample-hunt record being the Tier-2 ticket for a conjecture. ✓

Let me now move to Duty 3: Gaming the gates.

**1. Submission verifier (xP==Q):**
The verifier checks xP == Q in a subprocess. A worker under "never give up" pressure...

The verifier is straightforward - it either passes or fails. Can a worker game it? The worker would need to produce an x such that xP == Q. If the worker can solve the DLP, that's a legitimate result, not gaming. If the worker can't, it can't fake it because the verifier checks the actual computation.

But wait - §13 M0 says: "the subprocess verifier accepts that pair, rejects a one-coordinate and a one-scalar negative fixture." The verifier takes x and Q (or x, P, Q) and checks xP == Q. Could a worker submit x = 0 and Q = O (the point at infinity)? The verifier should check that Q is not the identity. Actually, §13 says "subgroup membership (n·Q = O) then xP == Q." If Q = O, then n·Q = O is trivially true, and xP = O when x = 0 (or x = n). So x = 0, Q = O would pass. But is this a real concern? The worker is trying to solve a DLP instance. If it submits the trivial solution, that's not gaming - it's just wrong, and the result would be meaningless. The verifier accepts it, but the claim would be about solving a specific instance, and the trivial solution doesn't solve a real instance.

Actually, the instances are generated by the ladder's instance-maker, which generates random (P, Q) where Q = xP for random x. The worker doesn't choose Q. So the worker can't submit Q = O. The verifier checks the worker's x against the gate's Q. This is closed.

But what about the egress rule? §10 says "a submission — the egress of a recovered x for the target or for any instance — is the verifier's passing node (§13) or nothing." So a submission requires a verifier passing node. The verifier checks xP == Q for the specific instance. The worker can't choose the instance. Closed.

**2. The ladder:**
A worker under pressure could try to:
- Pre-register a cost model that's easy to fit. §6 says "The claim pre-registers its cost model... before any rung runs." The model must beat BSGS at 50 bits (the refutation floor). A worker could pre-register a model that's just barely above BSGS, making it easy to pass. But the acceptance bar is against rho (≈ 1.25√n), not BSGS. And the model must fit in-sample and predict out-of-sample. A worker could pre-register a model with a free constant that fits anything. But §6 says "the exponent and the memory model's shape are always fixed; a constant or crossover may be left to the fit." So the exponent is fixed. A worker claiming a subexponential attack must fix the exponent. If the exponent is fixed at 0.5 (square root), the method must beat rho, which is also ~√n. This is hard to game.

- Use a method that's actually just rho with a different name. The ladder compares against rho as the baseline. If the method IS rho (or a trivial variant), it won't beat the band. The band is "1 + 2·radius" above 1. A method that's exactly as fast as rho has speedup 1, which doesn't clear the band. Closed.

- Overfit to the instances. The ladder generates fresh random instances from gate-owned entropy. The worker never sees the instances before committing its method. The hypothesis object precedes the entropy commitment. Closed.

- Report a false count. §6 says "the count is the gate's measurement, never the claimant's." The gate owns the operation counter. A self-reported count is a diagnostic, and a divergence is REJECT. Closed.

- Use uncounted arithmetic. §6 says "a ladder-tested method's allow-list names no other arithmetic backend." And "A method that needs an uncounted backend declares it in its hypothesis object, and its rungs are INCONCLUSIVE at best until a counted implementation exists." Closed.

One potential gaming: the worker could declare a very high constant in the cost model, making the band easy to clear. For example, if the method is rho with a 2x overhead, and the worker pre-registers a model with constant 2.5√n, then the method at 2√n would be "better than declared" and might pass. But the acceptance bar is against rho (1.25√n), not against the declared model. The method must beat rho by the band amount. If the method is 2√n and rho is 1.25√n, the speedup is 1.25/2 = 0.625, which is below 1. So it would REJECT. The worker can't game by declaring a high constant because the bar is against the baseline, not the declaration.

Wait, let me re-read. §6 says "a speedup is KEPT only if the whole claim CI clears 1 + 2·radius — its lower bound exceeds the band." The speedup is "baseline group-operation cost divided by claim group-operation cost." So speedup = baseline_ops / claim_ops. If the claim is slower than the baseline, speedup < 1, and it can't clear the band (which is > 1). So a method that's worse than rho can't pass. Closed.

But what about the in-sample check? The in-sample check fits the declared free parameters on the ≤ 50-bit rungs and checks each rung's mean against the fitted model. If the worker declares a free constant, the fit will always match (it's fitted). But the out-of-sample check at 60 bits tests the fitted model's prediction. If the method is just rho with overhead, the fitted model might predict the 60-bit mean correctly (since it's the same algorithm at a different size). So the in-sample and out-of-sample checks might pass. But the acceptance bar (speedup > 1 + 2·radius) would fail because the method isn't faster than rho. So the worker can't game by declaring a model that fits - the acceptance bar catches it. Closed.

Actually, wait. Let me re-read the verdict rules. §6 (2c): "KEEP (KEEP_IN_SAMPLE plus the 60-bit completion and out-of-sample check)." And KEEP_IN_SAMPLE requires "floor beaten, claim CI clears the band on group operations, memory under cap, x recovered on every trial, model fits in sample." So KEEP_IN_SAMPLE already requires the claim CI to clear the band. The band is against rho. So even at the ≤ 50-bit rungs, the method must beat rho. Closed.

One more: could a worker game the memory cap? §6 says "peak memory both stays under the cap at the rungs where the refutation floor is measured — the 50-bit rung and the 60-bit completion rung, the cap fixed in the ladder plan as the BSGS table for that size." The memory is "measured by the harness as peak algorithmic table and spill bytes with RSS as a diagnostic." The harness measures it, not the worker. Closed.

**3. Formalization gate:**
A worker under pressure could:
- Submit a Solution with `sorryAx`. §7 says the gate "requires it ⊆ {propext, Classical.choice, Quot.sound} — which rejects sorryAx." And "a gate-owned module in the bundle that imports the Solution and runs Lean.collectAxioms over the Challenge's theorem names, never a list read from output the Solution's own compilation emits, since leanchecker rejects neither sorryAx nor extra axioms." So the gate computes axioms itself, not from the Solution's output. Closed.

- Prove a weaker statement. §7 says "(iv) requires the Challenge and Solution theorem statements to be identical over the statement's transitive constant closure." And the statement-level review checks for this. The pre-filters include "a vacuity check that tries to derive False from the hypotheses" and "a bounded prove/disprove attempt with a weak prover." But these are pre-filters, not complete. The human review is the gate. But what if no human is available? §10 says "absence never defaults to pass." The claim stays at its pre-review tag. So the worker can't get PROVEN without human review. Closed.

- Redefine a constant. §7 says "(iv) requires the Challenge and Solution theorem statements to be identical over the statement's transitive constant closure, so a redefined constant anywhere under the statement fails the check." Closed.

- Use a different Lean version that accepts different axioms. §7 says the gate "rebuilds in a sandbox under the pinned lean-toolchain and lake-manifest mathlib revision recorded in the artifact." And "a run whose checker configuration differs from the bundle's fails closed before compilation." Closed.

One potential gaming: the worker could write a Challenge that's trivially true (e.g., `True → True`). But the Challenge is derived from the claim statement node, which is written before any proof. And the statement-level review checks for this. The pre-filters include "trivially provable or disprovable ⇒ flag." And the human review is the gate. Closed.

But wait - who writes the Challenge? §7 says "the gate compiles the Challenge module from the claim statement node (§4) with a gate-side renderer and pinned prelude." So the Challenge is compiled by the gate from the claim statement node. The worker doesn't write the Challenge. The Formalizer writes the Solution. So the worker can't write a trivial Challenge. Closed.

But the claim statement node is written by "the Reframer, the Prover or the human, before any proof or measurement." So a worker (Reframer or Prover) writes the claim statement. Could a worker write a trivially true claim statement? The statement-level review would catch this. And the pre-filters would flag it. And the human review is required for PROVEN. Closed.

**4. Reproducibility gate:**
A worker could:
- Submit a non-reproducible result and hope it's not re-run. §3 says "Replayable at Tier 0/1 ⇒ always re-run." So Tier 0/1 results are always re-run. For Tier 2/3, "re-run at the moment justify (§7) would derive a class above CONJECTURE from the node." So if the worker tries to use a Tier 2/3 result to support a claim above CONJECTURE, it's re-run. If the worker keeps the claim at CONJECTURE, the result might not be re-run (only sampled by the auditor). But CONJECTURE is a low tag, so there's no benefit to gaming for CONJECTURE. Closed.

- Submit a Verifiable result with a false witness. The witness is checked by the deterministic verifier. For a rho certificate, the verifier checks aP + bQ = X = cP + dQ and xP == Q. A false witness would fail this check. Closed.

- Submit a Replayable result that's deterministic but wrong. The re-run would produce a different output, and the node would be marked non-reproducible. Closed.

One potential gaming: the worker could submit a result with `replay = AuditOnly`. §3 says "AuditOnly is inadmissible as evidence." And §7 says a table without a reproducibility record has ceiling CONJECTURE. So AuditOnly can't support anything above CONJECTURE. Closed.

**5. Ledger preflight:**
A worker could