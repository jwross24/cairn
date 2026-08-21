Let me carefully review this plan. It's a very detailed architecture document for "Cairn," an autonomous math research harness. I need to find genuine improvements, not manufacture changes.

Let me think about what I see:

1. The plan is extremely detailed and well-thought-out. The core invariants are sound.

2. Let me look for actual issues:

**Issue 1: The 60-bit rung deadlock and KEEP_IN_SAMPLE scoping.** The plan already handles this with the scoped KEEP_IN_SAMPLE ticket. This seems sound.

**Issue 2: The foundations auditor's spot-check bound.** At M0 parameters, `l ≈ 1.4×10³` per stratum per cycle, which "exceeds any plausible Tier-2/3 population, so that stratum is checked exhaustively." This is fine for M0 but what happens when the Tier-2/3 population grows? The plan says "where the escrow cannot fund `l`, the auditor draws what it can afford and records the achieved `bits`." This seems handled.

**Issue 3: The concurrency contract.** One writer connection, WAL mode. This is sound for M0-M4 but the plan acknowledges M4's parallel tracks stress it. The done-when says "zero broken chain heads and zero lost attempt rows." This seems adequate.

**Issue 4: The `justify` function.** It's described as returning "a typed justification or a lattice violation, never a boolean." This is good. But the actual lattice structure (which classes can justify which) isn't fully specified. The plan says "Each evidence kind has a maximum class it may justify" and lists them. This seems adequate for M0.

**Issue 5: The hypothesis key excludes per-run seeds and ladder instances.** This is correct - two honest attempts at one hypothesis should collide. But what about the parameter ranges? The hypothesis object includes "declared parameter ranges" and "declared sampling distribution D where one exists." This seems sound.

**Issue 6: The near-duplicate advisory uses SimHash.** Before M4 it routes to human, from M4 to Librarian. This is advisory only. Seems fine.

**Issue 7: The `salt` mechanism for disowning results.** When a tool version is found faulty, `salt` moves results into a fresh namespace. This is clever and sound.

**Issue 8: The gate bundle pin.** The orchestrator's process user cannot write to it. At M0 it's a file mode. This seems adequate but fragile - what if the orchestrator runs as root? The plan says "a file mode at M0" which is an operator default. This is probably fine for M0.

Let me look for more substantive issues:

**Issue 9: The ladder's A/A null arm.** The plan says "the A/A null arm — the baseline run against itself in the same harness, same trial count, same instance stream — whose CI radius sets the decision band." But wait - the A/A arm is the baseline against itself. How does this work? If you run plain rho twice on the same instances, you get the same results (deterministic given the seed). So the A/A radius would be zero, which makes the decision band too tight. Unless the A/A arm uses different seeds? But then it's not "against itself in the same harness, same trial count, same instance stream." 

Actually, re-reading: "the baseline run against itself in the same harness, same trial count, same instance stream." I think this means: run the baseline method twice with different seeds on the same instance stream, and measure the variance. The CI radius captures the sampling variability. This makes sense - it's a null comparison that calibrates the decision threshold against the inherent noise. But the wording is ambiguous. If "same instance stream" means same seeds, then the two runs are identical and the radius is zero. If it means same instances (same curves) but different random seeds for the algorithm, then it captures algorithmic variance.

Actually for rho, the walk is randomized, so even on the same curve with the same P,Q, different seeds give different walk lengths. So "same instance stream" = same curves, same P,Q, but different walk seeds. The A/A arm measures: how much does rho's cost vary when you run it twice on the same set of instances? That sets the noise floor. This is sound but the wording could be clearer.

**Issue 10: The `BUDGET_EXCEEDED` status in the ladder.** The plan says "the ladder counts such a trial as a failure in its success-rate column." But a budget-exceeded trial isn't necessarily a failure of the method - it could be an unlucky tail of the distribution. Counting it as a failure biases the success rate downward. For rho with sd ≈ 0.5×mean, a 4× ceiling aborts < 0.1% of honest trials, so the bias is negligible. This seems fine.

**Issue 11: The `KEEP_IN_SAMPLE` ticket scoping.** The plan says "a table with verdict KEEP_IN_SAMPLE is a Tier-2 ticket valid for the 60-bit rung of the same hypothesis key and for no other launch." This is well-scoped. But what if the 60-bit rung itself returns KEEP_IN_SAMPLE (i.e., it completes and recovers x on all m instances but the out-of-sample check fails)? Then the claim is stuck - it has KEEP_IN_SAMPLE at 60 bits but no path to KEEP. The plan says REJECT for "an in-sample or out-of-sample miss of the pre-registered model." So a 60-bit out-of-sample miss is REJECT, not KEEP_IN_SAMPLE. OK, that's handled.

**Issue 12: The formalization gate's statement hash.** The plan says "the statement hash is computed over what the comparator compares (the theorem's `ConstantVal` and the full `ConstantInfo` of every constant in its transitive closure)." And notes "this closure is the right hash is CONJECTURE — the hasher is inferred from the comparator's `compareAt` and does not exist yet, so M1 builds and probes it before the gate is trusted." This is honest about the uncertainty. Good.

**Issue 13: The `corpus_origin` taxonomy and the axis rule.** The plan says `author_supplied` alone caps at CONJECTURE, and STRONG-EMPIRICAL needs "an upstream corpus, an independent implementation under the axis rule below, or a postcondition or metamorphic relation checked on inputs drawn from a seed committed after the implementation revision is content-addressed." This is well-designed.

Now let me think about what genuine improvements I can propose:

**Proposal 1: The ladder's A/A null arm needs a clearer definition.** The current wording "the baseline run against itself in the same harness, same trial count, same instance stream" is ambiguous about whether the algorithm's internal randomness (walk seed) is held fixed or varied. If held fixed, the radius is zero and the band is too tight. If varied, it captures algorithmic variance, which is what you want. This needs to be explicit.

Actually wait - re-reading more carefully: "the sorted-distribution shape compared to the claimed model, and an A/A null arm — the baseline run against itself in the same harness, same trial count, same instance stream — whose CI radius sets the decision band." 

I think "the baseline run against itself" means: run the baseline method (plain rho) on the same instances, and compare the baseline's distribution to itself. The CI radius from this A/A comparison sets the minimum detectable difference. This is standard in A/B testing - you run A/A to calibrate your significance threshold. The "same instance stream" means same curves/P/Q, and the algorithmic randomness (walk seeds) varies. The CI radius captures the sampling variability of the cost distribution.

But this is genuinely ambiguous as written. Let me propose a clarification.

**Proposal 2: The `justify` lattice needs explicit ordering.** The plan says "no claim, of any class, may carry a `justified_by` edge at any depth to a strictly weaker premise." But the lattice ordering isn't explicitly stated. It's implied: PROVEN > STRONG-EMPIRICAL > CONJECTURE > SPECULATION. But what about the sub-types within STRONG-EMPIRICAL (ladder vs sampled)? The plan says "sampled or statistical evidence → at most STRONG-EMPIRICAL on its declared population" and "a Lean proof about a model of the system → at most CONJECTURE." The lattice seems to be:

```
PROVEN (green Lean)
  > STRONG-EMPIRICAL (ladder + repro, or sampled on declared population)
    > CONJECTURE (model proof, or anything below)
      > SPECULATION
```

This should be made explicit so `justify` is implementable. Actually, the plan says "justify is implementable at M0 from two synthetic evidence kinds and a synthetic statement" so maybe the lattice is simple enough. But the M0 done-when says "justify returns STRONG-EMPIRICAL from a synthetic ladder_table evidence node and a lattice violation when a synthetic statistical node is offered for PROVEN." So the lattice is: ladder_table can justify up to STRONG-EMPIRICAL, statistical can justify up to STRONG-EMPIRICAL (on its population), but neither can justify PROVEN. This is clear enough for M0.

Actually, I think the lattice is fine as specified. Let me not manufacture a change here.

**Proposal 3: The terminal-status invariant and long-running branches.** The plan says "every opened branch and every opened claim is a linear obligation that must reach a terminal status." But what about a branch that's active indefinitely - the orchestrator keeps funding it? That's fine - "active" is not terminal, and the obligation is that it must *eventually* reach terminal. But there's no timeout. Is that intentional? Yes - "never give up" means the orchestrator can keep a branch active. The invariant is about leaked branches (worker exits leaving one open), not about time limits. This is sound.

**Proposal 4: The `SKILL_YANKED` status and in-flight attempts.** The plan says "an in-flight attempt completes with status SKILL_YANKED." But what does "completes" mean? If the skill is yanked, does the subprocess keep running? The plan says "the tier gate refuses new launches of it" - so new launches are blocked, but in-flight ones complete. This makes sense - you don't want to kill a running computation that might be producing useful (if disowned) diagnostic data. But the results are "never cached, never a ticket, never evidence." This is sound.

**Proposal 5: The hash-chained log checkpoint.** The plan says "the chain head is also appended, at every gate run, to a checkpoint outside the orchestrator's write path — at M0 an operator-owned append-only file beside the gate-bundle pin." But what if the checkpoint file grows unboundedly? Every gate run appends the chain head. Over a long research campaign, this could be large. The plan doesn't mention rotation or compaction of the checkpoint. This is a minor issue but worth flagging.

Actually, the checkpoint is just the chain head hash (32 bytes), not the full log. So even at 1M gate runs, it's 32MB. This is fine.

**Proposal 6: The `RequiresNullControl` ledger preflight result.** The plan says "RequiresNullControl = a prior refutation rests on a measurement taken without a null control and must be re-measured first." But what does "re-measured first" mean operationally? The branch is blocked until the prior refutation is re-measured with a null control? Who re-measures it? The worker proposing the new branch? The foundations auditor? This is underspecified.

Actually, re-reading: the ledger preflight returns `Allowed | Blocked | RequiresNullControl`. `RequiresNullControl` means the prior refutation is suspect (no null control), so the new branch can't proceed until the prior result is re-validated. But the plan doesn't say who does this re-validation or how the branch transitions from `RequiresNullControl` to `Allowed`. This is a gap.

Let me think about this more carefully. The `RequiresNullControl` state means: a prior refutation that would block this branch was measured without a null control, so we're not sure the refutation is valid. The branch should be parked (not blocked permanently) until the prior refutation is re-measured with a null control. The blocker is "prior refutation needs null control re-measurement." This is a PARKED state with a specific blocker. The plan should make this explicit.

**Proposal 7: The M1 done-when and the `KEEP_IN_SAMPLE` fixture.** The M1 done-when says "the tier-gate fixture: a KEEP_IN_SAMPLE table admits the 60-bit rung of its own hypothesis key and is refused for every other Tier-2 launch." But this fixture requires a 60-bit rung to actually run, which is Tier-2 work. Does M1 include Tier-2 runs? The plan says M1 is "single track" and the 60-bit rung "runs only when the tier gate grants that budget." So the M1 fixture might need to use a synthetic KEEP_IN_SAMPLE table (not a real 60-bit run) to test the tier gate's scoping logic. The plan should clarify whether this is a synthetic fixture or a real run.

Actually, the M1 done-when says "the tier-gate fixture: a KEEP_IN_SAMPLE table admits the 60-bit rung..." - this could be a synthetic table used as a fixture, not a real 60-bit run. The tier gate just needs to read the table and check the scoping. This is probably fine but could be clearer.

**Proposal 8: The `salt` mechanism and its scope.** The plan says "the `salt` key field that moves a whole class of results into a fresh namespace when a tool version is found faulty." But how is `salt` determined? Is it per-skill, per-tool-version, global? The plan says "results already cached under it are disowned by salt when the fault is found to reach them." So salt is applied retroactively to disown results. But the recipe key includes salt as a field - so changing salt changes the key, which means the old results are still in the substrate under the old key but are "disowned." How does disownal work? The plan says "disowned by salt" but doesn't specify the mechanism. Is it a GC root removal? A status change? 

Actually, re-reading: "results already cached under it are disowned by salt (§3) when the fault is found to reach them." I think this means: when a tool version is found faulty, a new salt value is set for that tool version, and all results computed under the old salt are marked as disowned (no longer served as cache hits, no longer admissible as evidence). The mechanism is probably: the old results' GC roots are removed, so they become collectable, and any claim depending on them is downgraded. This is sound but the exact mechanism could be clearer.

Let me now think about what the most impactful proposals would be:

1. **The `RequiresNullControl` preflight result needs an operational specification.** This is a real gap - the plan introduces a state but doesn't say how it transitions.

2. **The A/A null arm definition needs clarification on algorithmic randomness.** This is a correctness issue - if the A/A arm holds walk seeds fixed, the decision band is zero and every honest method gets REJECT.

3. **The `salt` disownal mechanism needs a concrete specification.** How are results disowned? What happens to claims depending on them?

4. **The M1 `KEEP_IN_SAMPLE` tier-gate fixture should be explicitly synthetic.** Otherwise it implies M1 needs real Tier-2 runs.

Let me also think about whether there are any gaming vectors:

**Gaming vector 1: The cost profile declaration.** A skill declares its cost profile, and the tier gate uses it. A skill could under-declare its cost to get a lower tier. But the plan has the budget ceiling (4× the declared expectation) and the exhaustion status. And "a persistent mismatch across runs is a strategy-layer alarm." So under-declaration is caught by the ceiling (the run aborts) and the alarm (the drift is noticed). This seems adequate.

**Gaming vector 2: The hypothesis key.** A worker could paraphrase a refuted hypothesis to get a different key. The plan addresses this: "free-text fields are excluded, so the key is about structure — paraphrase is the near-duplicate advisory's job." And the near-duplicate advisory routes to human/Librarian. This seems adequate.

**Gaming vector 3: The ladder's instance-maker.** A worker could try to influence the instance generation. The plan addresses this: "a gate-owned instance-maker whose entropy the worker never sees before committing its method." This seems adequate.

**Gaming vector 4: The formalization gate.** A worker could try to redefine a constant. The plan addresses this: "requires the Challenge and Solution theorem statements to be identical over the statement's transitive constant closure." This seems adequate.

**Gaming vector 5: The `justify` function.** A worker could try to attach evidence to a statement it doesn't cover. The plan addresses this: "coverage is a structural comparison of the population and assumption fields against the statement's scope field, never a text match." This seems adequate.

Let me think about one more thing: the `supersedes` edge and refutation transfer. The plan says "a hypothesis object, or the claim statement it names, whose supersedes chain reaches a version carrying a REFUTED entry with an unmet retry predicate is parked with blocker supersedes_refuted_review." And "the refutation itself does not transfer, since a measured refutation reaches what was measured." This is subtle but correct: a measured refutation on version 1 doesn't automatically apply to version 2 (which might have changed the relevant parameter), but the structural signal (a version edge to a refuted version) triggers review. This is sound.

OK, let me also think about the framing. The plan frames itself as a harness for ECDLP research. Is this framing right? The plan says "the motivating instance is a 254-bit prime-order ECDLP" and "the realistic target is publishable increments on open subproblems." This is honest. The framing seems right.

One thing I notice: the plan doesn't explicitly address what happens when the system produces a result that's genuinely novel and correct but not about ECDLP. The plan says "progress = knowledge gained" and lists "a proven lemma, tighter bound, refuted approach, reproducible regularity, reduction." So non-ECDLP results are first-class. This is good.

Let me also think about whether there's a missing gate. The plan has: submission verifier, ladder, no-go checklist, formalization gate, reproducibility gate, proportional-scrutiny router, tier gate. Is there a missing gate?

One thing that might be missing: a gate on the *problem selection* itself. The plan says "the selector is itself audited" but the audit is a monitor, not a gate. A bad problem selection wastes compute but doesn't fabricate results. So this is fine - problem selection is strategy, not epistemics.

Another potential missing gate: what if a worker produces a result that's correct but the *interpretation* is wrong? E.g., the worker says "this proves the method is subexponential" when the ladder actually shows it's exponential with a small constant. The plan addresses this: the tag is derived from the evidence, not set by the worker. And the ladder's verdict is typed (REJECT/INCONCLUSIVE/KEEP_IN_SAMPLE/KEEP). So the worker can't misinterpret the ladder result. This seems adequate.

Let me now draft my proposals. I'll focus on the few that matter most.

1. **`RequiresNullControl` needs an operational transition specification** - HIGH - §4
2. **A/A null arm must explicitly vary algorithmic randomness** - HIGH - §6
3. **`salt` disownal mechanism needs concrete specification** - MED - §3
4. **M1 `KEEP_IN_SAMPLE` tier-gate fixture should be explicitly synthetic** - LOW - §13

Actually, let me reconsider #2. Re-reading the A/A arm: "the baseline run against itself in the same harness, same trial count, same instance stream — whose CI radius sets the decision band." 

For rho, the cost is random (mean ≈ 1.25√n, sd ≈ 0.5×mean). If you run rho twice on the same instances (same curves, same P, Q) with different walk seeds, you get two independent samples from the same distribution. The A/A comparison measures the variance of the difference, which sets the noise floor. This is standard.

But "same instance stream" could mean the same seeds for the instance-maker, which means same curves. The walk seeds are separate (derived from the gate's nonce). So the A/A arm uses the same curves but different walk seeds. The CI radius captures the algorithmic variance.

Actually, I think the issue is more subtle. The A/A arm is "the baseline run against itself." In A/B testing, A/A means running the same treatment twice to calibrate the test. Here, the "treatment" is the baseline method (plain rho). Running it twice on the same instances with different walk seeds gives you the null distribution of the difference. The CI radius of this null distribution sets the decision band.

But the plan says "same instance stream" - does this mean the same instances (curves) or the same instance seeds? If the instance seeds are the same, the curves are the same, and the only difference is the walk seeds. This is what you want. But if "same instance stream" means the same everything including walk seeds, then the two runs are identical and the radius is zero.

I think the intent is clear (same curves, different walk seeds) but the wording is ambiguous. Let me propose a clarification.

Wait, actually, re-reading again: "the baseline run against itself in the same harness, same trial count, same instance stream." The "instance stream" is the sequence of (curve, P, Q) instances generated by the instance-maker. "Same instance stream" means both A/A arms use the same instances. The walk seeds are part of the algorithm, not the instance. So the A/A arm runs the baseline method twice on the same instances with different walk seeds. This is correct.

But the plan doesn't explicitly say the walk seeds differ. It says "same instance stream" which is about the instances, not the algorithm's randomness. The algorithm's randomness (walk seeds) is implicitly different because the gate draws fresh seeds for each run. But this should be explicit.

Actually, I realize the A/A arm might not even use different walk seeds. Let me think about what "the baseline run against itself" means. If you run the baseline once and compare it to itself, the difference is zero. That's not useful. The A/A arm must involve some source of randomness. The only source is the walk seeds (for rho) or the algorithm's internal randomness. So the A/A arm must use different walk seeds.

But the plan says the gate "derives the seed of trial i at size s as H(nonce ‖ hypothesis hash ‖ s ‖ i)." So the seeds are deterministic given the nonce. If the A/A arm uses the same nonce, the seeds are the same, and the runs are identical. If it uses a different nonce, the seeds differ.

I think the A/A arm should use a different nonce (or the same nonce with a different tag) to generate independent walk seeds. The plan should make this explicit.

Actually, I think I'm overcomplicating this. The A/A arm is: run the baseline method on the same instances, with independent randomness, and measure the variance of the cost difference. This variance sets the decision band. The plan's wording is ambiguous about how the independence is achieved, but the intent is clear. Let me propose a minor clarification.

Hmm, but actually there's a deeper issue. The A/A arm compares the baseline to itself. But the decision band is used to compare the claim to the baseline. The A/A radius measures the noise in the baseline-vs-baseline comparison. But the claim-vs-baseline comparison has noise from both the claim and the baseline. So the A/A radius underestimates the noise in the claim-vs-baseline comparison by a factor of √2 (if the claim and baseline have similar variance).

Wait, no. The A/A arm measures the variance of the difference of two independent samples from the baseline distribution. The claim-vs-baseline comparison measures the difference of a sample from the claim distribution and a sample from the baseline distribution. If the claim and baseline have similar variance, the A/A radius is a good estimate of the noise. If the claim has much larger variance, the A/A radius underestimates the noise. But the plan says "the sorted-distribution shape compared to the claimed model" - so the claim's variance is also measured. The A/A radius sets the minimum detectable difference, and the claim's variance is used to compute the claim's CI. The decision band is "1 + 2·radius" where radius is the A/A CI radius. This is the threshold for the claim's CI to clear.

Actually, I think the A/A radius is the CI radius of the baseline-vs-baseline difference. The claim's CI is computed from the claim's own distribution. The claim is KEPT if the claim's CI clears "1 + 2·radius." This is a conservative threshold that accounts for the baseline's noise. But it doesn't account for the claim's noise separately - the claim's CI already does that. So the A/A radius is the noise floor of the comparison, and the claim's CI is the claim's own uncertainty. The threshold "1 + 2·radius" ensures the claim's CI doesn't overlap with the baseline's noise band. This seems sound.

OK, I think the A/A arm is sound but the wording could be clearer about the independence mechanism. Let me make this a LOW severity proposal.

Let me reconsider my proposals:

1. **`RequiresNullControl` needs an operational transition** - HIGH - §4
2. **`salt` disownal mechanism needs concrete specification** - MED - §3  
3. **A/A null arm independence mechanism should be explicit** - LOW - §6
4. **M1 `KEEP_IN_SAMPLE` fixture should be explicitly synthetic** - LOW - §13

Actually, let me think about whether there are more impactful issues I'm missing.

**The `justify` function and the M0 done-when.** The M0 done-when says "justify returns STRONG-EMPIRICAL from a synthetic ladder_table evidence node and a lattice violation when a synthetic statistical node is offered for PROVEN." But the plan also says "An evidence node is typed: {kind ∈ {lean_artifact, ladder_table, repro_node, counterexample_hunt_record, statistical, model_proof}, ...}." The M0 done-when tests two of these kinds. What about the others? The plan says "justify is implementable at M0 from two synthetic evidence kinds and a synthetic statement." So M0 only needs two kinds. The others are added in M1+. This is fine.

**The branch tree and the hypothesis object.** The branch tree has `{id, parent, hypothesis, status, priors, effort, yield, blocker?}`. The hypothesis field points to the hypothesis object (§3). But the branch tree is mutable (the orchestrator can rewrite it). The hypothesis object is immutable. So the orchestrator can change which hypothesis a branch points to, but not the hypothesis itself. This is sound - the orchestrator can reframe a branch (point to a new hypothesis) but can't edit an existing hypothesis.

But wait - if the orchestrator changes a branch's hypothesis, does the old hypothesis's ledger entries still apply? Yes - the ledger is keyed by hypothesis key, not branch id. So changing a branch's hypothesis doesn't affect the ledger. The new hypothesis is checked against the ledger independently. This is sound.

**The `withdrawn` terminal status.** The plan says "Withdrawal is terminal and reason-bearing; it erases no gate outcome already recorded against the statement hash, and re-opening the same statement hash is a re-walk the preflight sees like any other." This is sound - withdrawal doesn't erase history.

**The `Leaked` record.** The plan says "a worker that exits leaving one open produces a Leaked record that is counted and escalated." But what if the worker is killed by the harness (e.g., budget exceeded)? The plan says budget exhaustion "stops the attempt with status BUDGET_EXCEEDED." So the attempt is stopped, not leaked. But what about the branch? If the worker was working on a branch and the budget is exhausted, the branch is still active. The worker exits, but the branch is not leaked - it's still active and can be picked up by another worker. This seems fine.

Actually, the `Leaked` record is about a worker exiting leaving a branch or claim open. But branches and claims are not "owned" by workers - they're in the state layer. A worker is dispatched to work on a branch, but the branch exists independently. So a worker exiting doesn't "leave a branch open" - the branch is already open. The `Leaked` record must be about something else - maybe a claim that was opened by the worker but not resolved? The plan says "every opened branch and every opened claim is a linear obligation that must reach a terminal status." So if a worker opens a claim and then exits without resolving it, that's a leak. But the claim is in the state layer, not the worker's context. So the claim is still open and can be picked up by another worker. The `Leaked` record is a diagnostic, not a gate. This seems fine.

Let me think about one more thing: the `P1` decision (quantitative floor for small-numbers gate). The plan says it's decided at M1 with planted-false conjectures. The e-process is `E_t = ∏(1 − λ_t(X_t − ε))` against H₀ "P fails with probability ≥ ε under D." This is a valid e-process if `λ_t ∈ [0, 1/(1−ε)]` and `X_t ∈ [0, 1]` (where X_t = 1 if the instance fails, 0 otherwise). Under H₀, E[X_t] ≥ ε, so E[1 − λ_t(X_t − ε)] ≤ 1 (since λ_t ≤ 1/(1−ε) ensures the factor is nonnegative). This is a valid e-process. The plan says "log₁₀E is a numeric attribute, not a sub-grade." This is consistent with the rejection of e-values as sub-grades. Good.

But wait - the plan says "Tier-2 spend on proving the conjecture requires E ≥ 1/α." This is a resource gate, not a promotion. The e-process is used to gate compute, not to promote a tag. This is consistent with "statistical monitors block or alarm; they never promote." Good.

OK, I think I have enough. Let me also think about the framing question.

**Framing:** The plan frames itself as a harness for autonomous math research with ECDLP as the motivating instance. The framing is sound. The key insight - "mutable strategy, immutable epistemics" - is the right abstraction. The honest baseline ("this stands") is load-bearing and correct.

One potential framing issue: the plan assumes the operator is honest. If the operator is adversarial (wants the system to say "ECDLP is broken"), the gates prevent fabrication, but the operator can still misrepresent the system's output externally. The plan doesn't address this. But this is out of scope - the plan is about the system's internal honesty, not the operator's external honesty.

Another framing issue: the plan focuses on ECDLP but claims generality ("a system for open-ended research on hard problems"). The mechanisms are indeed general (the ladder, the gates, the substrate), but the no-go checklist (§8) is ECDLP-specific. The plan should acknowledge that the no-go checklist is problem-specific and would need to be replaced for a different target. Actually, the plan does say "Any proposed attack on the target" - so the no-go checklist is for "the target," which is ECDLP. For a different target, you'd need a different no-go checklist. This is implicit but could be explicit.

Actually, I think this is fine. The plan is about Cairn, whose motivating instance is ECDLP. The no-go checklist is part of the gate bundle, which is problem-specific. The plan says the gate bundle is "content-addressed" and "pinned at deployment." So changing the target means changing the gate bundle, which is a deployment action. This is sound.

Let me finalize my proposals. I'll focus on:

1. **`RequiresNullControl` operational transition** - HIGH
2. **`salt` disownal mechanism** - MED
3. **A/A null arm independence** - LOW (actually, let me reconsider if this is even an issue)

For #3, re-reading one more time: "the A/A null arm — the baseline run against itself in the same harness, same trial count, same instance stream — whose CI radius sets the decision band." 

I think "the baseline run against itself" is clear enough: you run the baseline twice and compare. The "same instance stream" means same instances. The independence comes from the algorithm's randomness (walk seeds), which the gate generates. The gate "derives the seed of trial i at size s as H(nonce ‖ hypothesis hash ‖ s ‖ i)." For the A/A arm, you'd use a different nonce (or a different tag in the hash) for the second run. This is implicit but standard. I'll make this a LOW proposal to add one clarifying phrase.

Actually, I realize there might be a more important issue I should focus on. Let me re-read the `RequiresNullControl` more carefully.

"RequiresNullControl = a prior refutation rests on a measurement taken without a null control and must be re-measured first."

So a prior refutation (a REFUTED ledger entry) was measured without a null control (A/A arm). This means the refutation itself might be spurious - the method might have failed for reasons unrelated to the hypothesis (e.g., a bug in the skill, not a fundamental obstruction). The `RequiresNullControl` result says: before you can use this refutation to block new branches, you need to re-measure it with a null control.

But who re-measures it? The plan doesn't say. Options:
1. The worker proposing the new branch must re-measure the prior refutation. This is problematic - the worker has a conflict of interest (it wants its branch to proceed).
2. The foundations auditor re-measures it. This is better - the auditor is independent. But the auditor's cadence is periodic, so the branch might wait a long time.
3. The system automatically queues a re-measurement when a `RequiresNullControl` result is returned. This is the cleanest - the system itself initiates the re-measurement.

I think option 3 is the right design. When the ledger preflight returns `RequiresNullControl`, the system should:
1. Park the proposed branch with blocker `prior_refutation_needs_null_control`.
2. Queue a re-measurement of the prior refutation with a null control (using the same method, same parameter region, but with the A/A null arm).
3. When the re-measurement completes, update the prior refutation's ledger entry (add the null control result) and re-run the preflight.

This is a concrete operational specification that the plan is missing. Let me propose this.

Actually, wait. The plan says "a prior refutation rests on a measurement taken without a null control." How does the system know whether a prior refutation had a null control? The ledger entry must record whether a null control was used. The plan's ledger entry schema is: `{hypothesis key, refutation_kind, evidence node, method, measured parameter points, result (+CI where measured), decision, retry predicate, caught_by}`. There's no field for "null control status." This is a gap - the ledger entry should record whether the measurement included a null control.

So my proposal has two parts:
1. Add a `null_control_status` field to the ledger entry schema.
2. Specify the operational transition for `RequiresNullControl`.

This is a HIGH severity proposal because it's a structural gap - the `RequiresNullControl` state is defined but not implementable without knowing how to detect it and how to transition out of it.

Let me also think about the `salt` disownal mechanism more carefully.

The plan says: "the `salt` key field that moves a whole class of results into a fresh namespace when a tool version is found faulty" and "results already cached under it are disowned by `salt` (§3) when the fault is found to reach them."

So the mechanism is:
1. A tool version is found faulty (e.g., a bug in PARI's `ellcard`).
2. A new `salt` value is set for that tool version.
3. New results are computed with the new salt (different key, fresh namespace).
4. Old results (computed with the old salt) are "disowned."

But what does "disowned" mean? The plan says the old results are still in the substrate (under the old key) but are no longer admissible. How is this enforced? Options:
1. The old results' status is changed to `DISOWNED` (a new status). But the plan says "a slot that is overwritten destroys exactly that evidence" - so the old results are not overwritten, they're kept. A status change is fine.
2. The old results' GC roots are removed, making them collectable. But the plan says "recipes, ledger rows, certificates and recorded divergences are GC roots" - so removing a result from the roots table would make it collectable. But the plan also says "keep lineage + certificates forever" - so maybe disowned results are kept but marked as inadmissible.
3. A separate "disowned" flag is set on the old results, and the claims DB / `justify` function ignores disowned results.

I think option 3 is the cleanest. The `salt` change sets a flag on all results computed under the old salt, and `justify` ignores them. The results are kept (for forensics) but are inadmissible. Claims depending on them are downgraded.

But the plan doesn't specify this. It says "disowned by salt" but doesn't say how. This is a MED severity gap.

Actually, re-reading: "results already cached under it are disowned by `salt` (§3) when the fault is found to reach them." The "when the fault is found to reach them" is important - not all results from a faulty tool version are disowned, only the ones the fault reaches. So the disownal is selective, not blanket. This makes it more complex - you need to determine which results the fault reaches.

How is this determined? The plan doesn't say. This is a real gap. Options:
1. All results from the faulty tool version are disowned (conservative).
2. Only results that used the specific buggy function are disowned.
3. The skill's self-test failure determines the reach.

The plan says "a self-test failure (a floor miss, a certificate mismatch, a double-run divergence) yanks the implementation revision." So the self-test failure is the trigger. And "results already cached under it are disowned by `salt` when the fault is found to reach them." So the disownal is triggered by the self-test failure, and the "reach" is determined by... what? The plan doesn't say.

I think the simplest sound mechanism is: when a skill revision is yanked, all results cached under that revision are disowned (the salt changes for that revision). This is conservative but simple. The plan should specify this.

Let me draft my proposals now.

Actually, let me reconsider. The plan says "results already cached under it are disowned by `salt` (§3) when the fault is found to reach them." The "when the fault is found to reach them" might mean: the disownal happens lazily, when a specific result is found to be affected. But this is vague. Let me propose a concrete mechanism.

OK, I think I have three solid proposals. Let me also think about whether there's a fourth.

**The `caught_by` field in the ledger entry.** The plan says every REFUTED/PARKED entry carries `caught_by`. What is this field? It records which gate or mechanism caught the refutation. This is useful for forensics but isn't specified further. This is fine - it's a diagnostic field, not a gate.

**The `priors` field in the branch tree.** The branch tree has `{id, parent, hypothesis, status, priors, effort, yield, blocker?}`. What are `priors`? Presumably the prior probability of success or the prior distribution of outcomes. The plan doesn't specify. This is probably an orchestrator detail decided at M3. Fine.

**The `effort` and `yield` fields.** These are used by the bandit allocation. Not specified further. Fine - M3 decides the mechanics.

OK, I think my three proposals are the most impactful. Let me also think about the framing question.

**Framing:** I think the plan's framing is sound. The key insight - "mutable strategy, immutable epistemics" - is the right abstraction. The honest baseline is correct and load-bearing. The decomposition into thin agents + fat skills is the right architecture. The tier system is the right compute discipline.

One thing I might flag: the plan is very long and dense. This is a risk for implementation - a fresh implementer might miss subtle interactions between sections. But this is a documentation issue, not a framing issue.

Another thing: the plan doesn't address the case where the system produces a result that's correct but uninteresting. The plan says "progress = knowledge gained" but doesn't have a mechanism for deciding whether a result is worth publishing. The problem queue and human loop (§10) handle this - the human decides what's worth pursuing. But the system might produce correct but uninteresting results (e.g., a lemma that's technically novel but not useful). The plan doesn't have a mechanism for this. But this is a taste issue, not an epistemics issue, and the plan correctly delegates taste to the human. So this is fine.

Let me finalize. I'll write three proposals plus the framing assessment and facts needed.

Wait, I want to reconsider whether the A/A arm issue is real. Let me re-read one more time.

"an A/A null arm — the baseline run against itself in the same harness, same trial count, same instance stream — whose CI radius sets the decision band"

I think "the baseline run against itself" is clear: run the baseline method twice and compare. The "same instance stream" means same instances. The independence comes from the algorithm's internal randomness. For rho, this is the walk seed. The gate generates the walk seeds, so the two A/A runs get different walk seeds. This is implicit in the gate's design (the gate generates seeds, not the worker).

But the plan says "the gate draws a nonce after the hypothesis hash is recorded, derives the seed of trial i at size s as H(nonce ‖ hypothesis hash ‖ s ‖ i)." For the A/A arm, the hypothesis hash is the baseline's hypothesis hash. The nonce is drawn once. So all trials in one A/A run use the same nonce. For the second A/A run, a different nonce is drawn. This gives independent walk seeds. But the plan doesn't say this explicitly.

Actually, I think the A/A arm might not need different nonces. The A/A arm is "the baseline run against itself." If you run the baseline once with nonce N1 and once with nonce N2, you get two independent samples. The CI radius of their difference sets the decision band. But the plan says "same instance stream" - the instance stream is generated from the nonce. If the two A/A runs use different nonces, they get different instance streams. If they use the same nonce, they get the same instance stream but different walk seeds (if the walk seed is derived differently).

Hmm, this is getting complicated. Let me think about what the A/A arm is actually measuring.

The A/A arm measures the noise in the comparison between two runs of the same method. This noise has two sources:
1. Instance variability (different curves have different costs)
2. Algorithmic variability (different walk seeds give different costs)

If the A/A arm uses the same instances (same nonce for instance generation) but different walk seeds, it measures only algorithmic variability. If it uses different instances, it measures both.

The decision band should account for both sources of noise, because the claim-vs-baseline comparison has both. So the A/A arm should use different instances (different nonces) to capture both sources.

But the plan says "same instance stream." This means the A/A arm uses the same instances, capturing only algorithmic variability. This underestimates the noise.

Wait, but the claim-vs-baseline comparison also uses the same instances (the ladder generates instances for both the claim and the baseline). So the instance variability cancels out in the comparison. The A/A arm with same instances captures the right noise - the algorithmic variability, which is the only source of noise in a paired comparison.

Actually, this is the key insight. The ladder uses the same instances for both the claim and the baseline. So the comparison is paired - same instance, different methods. The noise in a paired comparison is the algorithmic variability, not the instance variability. The A/A arm with same instances captures exactly this. This is correct.

So the A/A arm is: run the baseline twice on the same instances (same curves, same P, Q) with different walk seeds. The CI radius of the paired difference sets the decision band. This is correct.

But the plan doesn't say "different walk seeds." It says "same instance stream" which implies same instances but doesn't specify the walk seeds. The walk seeds are part of the algorithm, not the instance. The gate generates them. For the A/A arm, the two runs should use different walk seeds. The plan should make this explicit.

Actually, I think this is