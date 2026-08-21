# Review of plan-r2.md

The plan is unusually tight on epistemics, substrate, ladder, and gate discipline. §0–§1, §3 retention/chain, §6 protocol, §7 tag derivation, and the M0 slice are sound; I am not manufacturing edits there. The revisions below are concentrated on **contract holes a worker/orchestrator can drive a truck through**, **build-order blind spots**, and **one framing gap**.

---

### 1. Tier tickets must bind hypothesis + method, not only branch  
· **HIGH** · §5 (and §6 ticket language)

**Rationale.** The tier gate takes “the most recent admissible substrate node … **produced under the same branch**.” `KEEP_IN_SAMPLE` is correctly scoped to `hypothesis key`, but a full `KEEP` is not. A branch can ladder method A → `KEEP`, amend method identity (or quietly run skill B), and spend Tier-2/3 on B under A’s ticket. That dissolves “cheap-before-expensive” for the claim that is actually launching. Same hole exists if `most recent` is an unrelated Tier-1 repro node on a multi-claim branch.

Cost of fix: gate predicate reads two hashes already on the node — negligible. Evidence: gate-gaming shape is the same class the plan cites for fixed evaluators (**CONJECTURE** as “will be attempted under never-give-up,” **PROVEN-in-source** as pattern in the plan’s own threat model). Does not touch §0; tightens an existing gate.

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ Tier gate predicate
-The gate reads three things and nothing else: the skill's declared
-cost profile, the spawning budget (the meet above), and the branch's *ticket* — the most
-recent admissible substrate node of the kind the tier requires (status OK, replay grade
-≥ Verifiable, reproducibility-checked under the §3 policy) produced under the same branch at
-the tier below.
+The gate reads four things and nothing else: the skill's declared cost profile, the
+spawning budget (the meet above), the launch's *hypothesis key* and *method identity*
+(skill@version + canonical parameters from the hypothesis object §3), and the branch's
+*ticket* — the most recent admissible substrate node of the kind the tier requires
+(status OK, replay grade ≥ Verifiable, reproducibility-checked under the §3 policy)
+produced under the same branch at the tier below **and** whose recorded hypothesis key
+and method identity equal the launch's. A ticket is not a branch-level capability.
 ...
-for Tier 2 on an algorithmic claim the ticket is a ladder result table with verdict
-KEEP (§6), with one scoped exception — a table with verdict KEEP_IN_SAMPLE is a Tier-2 ticket
-valid for the 60-bit rung of the same hypothesis key and for no other launch;
+for Tier 2 on an algorithmic claim the ticket is a ladder result table with verdict
+KEEP (§6) for that same hypothesis key and method identity, with one scoped exception —
+KEEP_IN_SAMPLE admits only the 60-bit rung of that key+method and no other launch;
```

---

### 2. Ladder (and hunt) dispatch must freeze method identity from the hypothesis object  
· **HIGH** · §6 step (0)–(1), §7 counterexample-hunt record

**Rationale.** Pre-registration binds the **cost model** and orders entropy after the hypothesis object, but the plan never says the ladder **executes** the method identity frozen in that object. Under §1 pressure the cheap cheat is: register a plausible model + method A, run faster method B on gate instances, match A’s model by luck or slack, mint `KEEP` under A’s key. Ticket binding (§1 above) is useless if the ladder artifact can lie about what ran.

Concrete contract: dispatch record lists `hypothesis_hash`; instance-maker already mixes that hash into seeds; runner may only invoke `skill@version+params` byte-equal to the hypothesis object’s method identity; artifact records the recipe key; mismatch fails closed before trials. Same freeze for the counterexample-hunt’s sampler vs declared `D`.

Cost: one equality check + fixture. Evidence: same evaluator-overfit class the ladder text already treats as documented (**STRONG-EMPIRICAL** as threat class in-plan).

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ Protocol (0)–(1)
 (0) The claim pre-registers its cost model — exponent, constant or crossover,
 and memory — in its hypothesis object (§3) before any rung runs; the ladder tests that
-model and never a curve fitted afterward. The hypothesis object's hash is named in the
-ladder's dispatch record and its position in the substrate's append order precedes the
-gate's entropy commitment of step (1); the ladder refuses to start otherwise.
+model and never a curve fitted afterward. The hypothesis object's hash **and** its
+method identity (skill@version + canonical parameters) are named in the ladder's
+dispatch record; the runner may invoke only that identity (recipe key must match); a
+mismatch is a planted-failure class the ladder self-test must FAIL. The hypothesis
+object's position in the substrate's append order precedes the gate's entropy
+commitment of step (1); the ladder refuses to start otherwise.
```

---

### 3. Non-algorithmic / long-horizon work needs intermediate artifacts + an anti-starvation bar at M3  
· **HIGH** · §5 allocation, §7, §11, §13 M3, §15 P3

**Rationale.** **Framing pressure inside a sound epistemic frame:** the ladder gives algorithmic claims a dense lattice of gate outcomes; lemma work, reductions, and bound-tightening mostly mint outcomes at the end (or never, for months). Until M3, “gate-outcome reward per measured cost” therefore **structurally funds refutation churn and toy KEEP farms over publishable slow work** — exactly the increments §14 says are the realistic product. This is not a request to weaken gates; it is a missing **progress substrate** and a missing **M3 acceptance fixture**.

Add:
- Typed intermediate nodes that are admissible as *activity/evidence-of-work*, never as tag fuel alone: e.g. `lemma_obligation` (statement hash + scope), `proof_attempt` (failed closed goals / new obligations, no proof text required for Skeptic isolation), `partial_formalization` (compiles, not green), `reduction_step` (claim-hash edge). `justify` maxima unchanged: they do not raise tags by themselves.
- P3 / M3 **done-when** extension: in a mixed portfolio fixture (fast refutation farm + one long-horizon formal branch emitting intermediate nodes each tick), the long-horizon branch still receives ≥ a gate-bundle floor share over T ticks unless human-parked or REFUTED. Forced pivot (§15 P3) may not extinguish the sole deep branch in a portfolio of size 1.

Cost: a few node types + one fixture; risk of orchestrator optimizing for intermediate spam — mitigate by requiring gate-admissible structure (statement hash, verifier on obligations) and capping reward per tick. Evidence: **CONJECTURE** (standard horizon-fail of myopic bandits); does not edit truth.

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ §5 Allocation currency
-until M3 decides its mechanics (§15 P3) it is implemented as gate-outcome reward per
-measured cost, and no model probability, e-value, posterior or similarity term ever
-enters it.
+until M3 decides its mechanics (§15 P3) it is implemented as gate-outcome reward per
+measured cost, where gate-outcomes include admission of typed *intermediate* nodes
+(§7) as well as terminal ladder/ledger/formal outcomes — still no model probability,
+e-value, posterior or similarity term. Intermediate nodes never raise a calibration
+tag by themselves (`justify` maxima unchanged).
@@ §7 (after counterexample-hunt record)
+- **Intermediate research nodes (non-promoting):** `lemma_obligation`, `proof_attempt`,
+  `partial_formalization`, `reduction_step` — each names a claim/hypothesis statement
+  hash, a producer skill/gate record, and a mechanical check (typechecks; obligation
+  list non-empty and scoped; reduction edge well-typed). They exist so long-horizon
+  branches produce schedulable, auditable progress under §5 without minting
+  STRONG-EMPIRICAL/PROVEN. The Skeptic may see obligations/statements, not prover traces.
@@ M3 Done when
-on ≥ 20 seeded runs each containing a stalled branch — ... funding is withdrawn from it
-within `m` ticks unaided, with `k` and `m` pinned in the M3 test plan.
+on ≥ 20 seeded runs each containing a stalled branch — ... funding is withdrawn from it
+within `m` ticks unaided, with `k` and `m` pinned in the M3 test plan; **and** on ≥ 10
+seeded mixed-portfolio runs (high-churn refutation branches + one long-horizon branch
+emitting ≥1 admissible intermediate node per tick) the long-horizon branch's compute
+share over T ticks is ≥ the gate-bundle floor unless human-parked or REFUTED.
@@ P3
+(iv) anti-starvation / intermediate-node reward as above; if a pure priority queue plus
+human taste beats a bandit *without* starving deep work on the fixture, the bandit is
+dropped.
```

---

### 4. Target-break claims: mechanical scrutiny class, not orchestrator prose  
· **MED** · §7 proportional scrutiny, §4 gate bundle

**Rationale.** “State it in the orchestrator: a run announcing it broke ECDLP has produced evidence it *erred*” is load-bearing rhetoric currently at risk of being **prompt text**. Prompts are the first thing that fails (§1). The no-go checklist flags *attacks*; it does not classify *success claims* against the motivating target. Make a bundle-resident, non-waivable classifier: claim statement scope matches the target family ∧ claims solution/break/subexp generic algorithm → scrutiny class `TARGET_BREAK`, which requires ladder `KEEP` + formalization path as applicable + expert sign-off (§10) + reproducibility; tier gate grants no Tier-3 without that class’s checklist; orchestrator cannot clear the class.

Cost: declarative predicate on claim statement fields (family, claimed property), already structured in §3–§4. Evidence: plan’s own paradox + §1 (**STRONG-EMPIRICAL** threat model).

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ Proportional scrutiny
-**State it in the orchestrator: a run announcing it broke ECDLP has produced evidence it
-*erred*.** The bigger the claim, the more the burden inverts against it.
+**Mechanical, not prompt:** a claim statement whose scope names the target family and
+whose claimed property is a full break / generic subexponential solve is classified
+`TARGET_BREAK` by a gate-bundle predicate (content-addressed, pinned). That class
+always routes to maximum scrutiny: ladder KEEP where algorithmic, formalization +
+statement review, reproducibility, and §10 expert sign-off; the tier gate issues no
+Tier-3 ticket otherwise; the orchestrator may not clear or waive the class. *A run
+announcing it broke the target has produced evidence it erred* is this routing rule,
+not an instruction in a worker prompt. The bigger the claim, the more the burden
+inverts against it.
```

---

### 5. Formalization gate needs an explicit tier/ticket story  
· **MED** · §5, §7 Green Lean, §13 M1

**Rationale.** The plan carefully separates “Lean compile = Tier-1” from `leanchecker --fresh` (unmeasured with mathlib, possibly huge) but never says **which ticket admits a full PROVEN-gate run** or what happens when replay cost exceeds Tier-1. Without that, either PROVEN is silently Tier-1-unbudgeted (fail-open under load — the failure §5 warns about) or formalization is stuck behind algorithmic `KEEP` (wrong ticket kind).

Contract: formalization gate is a skill-shaped gate with its own cost profile; **production** = build+check; **verification** = re-replay policy. Ticket: admissible `claim statement node` + statement-review verdict (or M1 fixture equivalent), **not** a ladder table unless the claim is algorithmic. If measured profile is Tier-2, ordinary tier gate applies with that non-ladder ticket. M1 done-when already measures cost — record the profile into the bundle before trusting PROVEN in production.

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ §7 Green Lean cost
-so M1 measures it on a mathlib-importing Challenge before sizing its fixture
-corpus, and "a Lean compile" at Tier 1 (§5) names the compile only, never this gate.
+so M1 measures it on a mathlib-importing Challenge before sizing its fixture
+corpus, and "a Lean compile" at Tier 1 (§5) names the compile only, never this gate.
+The formalization gate declares production+verification cost profiles like any skill;
+its tier-gate ticket is an admissible claim statement node plus a statement-review
+verdict (human/Skeptic §7), never a ladder KEEP unless the claim is algorithmic.
+M1 writes the measured profile into the gate bundle before any non-fixture PROVEN
+admission depends on it.
```

---

### 6. Skill admission registry (who may mint a skill@version)  
· **MED** · §2, §4, M1 baseline skills

**Rationale.** Skills are the trust boundary (“fat skills”), with yank/certificate/floor machinery, but the plan never says **how a new implementation revision enters the runnable set**. Under mutable strategy, the orchestrator or a worker could register a skill whose self-test corpus is thin, or hot-swap revision bytes mid-portfolio. Need a minimal registry: append-only `skill_revision` nodes `{identity bundle, corpus ledger hash, golden certificate, cost profile, axis declarations, admitted_by ∈ {human, m0_bootstrap, ci_harness}}`; tier gate launches only `admitted` revisions; workers may propose revisions; **admission** is harness-side after self-test green (and human for Tier-2+ profiles until M4 policy). Cost: small schema + one refuse fixture. Evidence: same as skill-yank rationale already in §2 (**CONJECTURE** on attack, **PROVEN-in-source** on need for identity).

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ §2 after granularity rule
+- **Skill registry (admission ≠ proposal):** a runnable skill is an append-only
+  `skill_revision` substrate node carrying the identity bundle, corpus ledger + golden
+  certificate, cost profile, and axis declarations. Workers/orchestrator may *propose*
+  revisions; the harness *admits* only after self-test green (status OK) and records
+  `admitted_by`. The tier gate refuses launches of non-admitted or yanked revisions.
+  M0 bootstraps the exemplar by human/ci admission; Tier-2+ profiles require human
+  admission until an operator policy in the gate bundle says otherwise.
```

---

### 7. Sharpen two done-whens; fix §5 overclaim vs P3  
· **LOW** · §5, §13 M2/M3

**Rationale.** M2 done-when omits the preflight behaviors that are the actual teeth (`measured-point` reach, `supersedes_refuted_review`). §5 states “expected information per compute-dollar” as present tense while P3 still decides whether a bandit exists — implementers will build a fake info estimator. Small text fixes; no new mechanism.

```diff
--- a/plan-r2.md
+++ b/plan-r2.md
@@ §5
-**Allocation currency is expected information per compute-dollar**, not raw yield —
-... until M3 decides its mechanics (§15 P3) it is implemented as gate-outcome reward per
-measured cost
+**Allocation currency targets expected information per compute-dollar**, not raw yield —
+... Through M2, and until M3 decides its mechanics (§15 P3), the *only* implemented
+surrogate is gate-outcome reward per measured cost (including §7 intermediate nodes)
@@ M2 Done when
-a parked branch auto-revives on blocker-clear; a refuted one is never re-walked.
+a parked branch auto-revives on blocker-clear; a refuted hypothesis key is Blocked
+unaided; a measured refutation Blocks a superseding object whose declared region still
+contains the measured point; a `supersedes` edge into unmet REFUTED parks with
+`supersedes_refuted_review` until an attributed difference statement is recorded;
+truncating the hash-chained log below the checkpoint fails verification at startup.
```

---

### Sound as written (no change)
- §0–§1 principles; §3 key/attempt/salt/GC/checkpoint design; §6 statistical protocol and two-threshold rationale; §7 derived tags, Skeptic isolation, disagreement non-voting; §8 presence-check + consumer; §9–§10 human-as-taste; §12 borrow constraint; §14 baseline; rejected-dependency list.

---

### (a) Three to stake the most on
1. **#1 Ticket ↔ hypothesis+method** — without it Tier-2 is a branch club card.  
2. **#2 Ladder freezes method identity** — without it the ladder certifies the wrong algorithm.  
3. **#3 Intermediate nodes + M3 anti-starvation** — without it the harness optimizes for everything except §14’s realistic outputs.

### (b) Framing that may be wrong
The plan’s epistemic frame is right; its **early product frame is ladder-centric**. M0–M1 success is defined almost entirely by toy-curve DLP and attack-refutation fixtures. That is correct for anti-fabrication on algorithmic claims, but it quietly trains the orchestrator and the operator to treat **publishable lemma/bound/negative-map work as second-class** until M3–M4. If the honest outcome is increments on open subproblems while the 254-bit curve stands, the **primary accretive loop** should be framed as “library + negative map + obligations,” with the ladder as the **specialized** high-risk gate for attack-shaped claims — not the archetype of all research progress. Revision #3 is a mechanism patch; the deeper fix is milestone narrative weight.

Secondary frame risk: **“info-per-dollar”** names an unmeasured quantity. Until a surrogate is validated, the honest frame is **“gate-admissible progress per compute, with human taste on the queue.”**

### (c) Facts the plan does not state (needed before locking M1–M3)
1. Measured `leanchecker --fresh` wall time and memory on a mathlib-importing Challenge/Solution pair (blocks #5).  
2. Whether claim statement nodes gain **typed fields** for `target_family` and `claimed_property` sufficient for a non-NLP `TARGET_BREAK` predicate (#4), or whether that waits on human labeling through M2.  
3. Expected parallel dispatch rate at M4 and SQLite write-proxy latency budget under the one-writer contract.  
4. Who is allowed to admit skills in operator practice (single human key? CI role?) and recovery if the admission path is down mid-run.  
5. Empirical distribution of “time between gate outcomes” on formalization-heavy branches (sizes the anti-starvation floor).