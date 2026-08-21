# Ledger — round 3

Plan reviewed: `research/convergence/plan-r2.md` (v3, 950 lines). Plan produced:
`research/convergence/plan-r3.md` (1117 lines; 369 diff lines against r2). Synthesizer own view
(written before any seat was opened): `research/convergence/r3/own-view-r3.md`. Seats:
GPT-5.6-terra (G), Grok-4.5 (K), GLM-5.2 (L), DeepSeek-v4-flash (D), Anthropic Opus grounded
(O); synthesizer own view (S). Prior ledgers read in full: `r1/ledger-r1.md`, `r2/ledger-r2.md`.

Verdict: **NEEDS-ANOTHER-ROUND** — one accepted cluster is HIGH (the ladder's decision variable
gains a gate-owned measurer and the ladder's execution contract freezes the method it runs, which
changes the interface every ladder-tested method must satisfy), and two factual corrections
changed mechanisms (the M0 corpus's declared origin; PROVEN's derivation reading the
statement-review verdict, per `HANDOFF.md` non-negotiable 2).

---

## 1. Accepted (cluster · severity as re-judged · seats · section · what landed · evidence)

| # | Cluster | Sev | Seats | § | Disposition and what landed |
|---|---|---|---|---|---|
| 1 | The ladder's primary metric has no measurer; the ladder never says it runs the method frozen in the hypothesis object | HIGH | O1, K2, S1 | §6, §13 M1 | ACCEPT (merged). §6(3): the count is the gate's measurement — every method, claimant and baseline, runs against a gate-owned group-arithmetic object (the baseline arithmetic skill, instrumented) that counts additions, doublings and inversions; a ladder-tested method's allow-list names no other arithmetic backend; a self-reported count is a diagnostic column and a divergence beyond the ladder plan's tolerance is REJECT; CPU-seconds per trial are recorded and a trial whose CPU time exceeds what its counted operations would take at the A/A-measured per-operation rate marks the rung INCONCLUSIVE (never KEEP, never REJECT) and surfaces on the human queue — "the counter cannot see arithmetic done around it, but the clock can" (S1); a method needing an uncounted backend declares it and its rungs are INCONCLUSIVE at best. §6(0)–(1): the dispatch record names the hypothesis hash *and* method identity; the ladder runs exactly that identity (trial recipe keys built from it), refuses a different one before any trial, and a mismatch is a must-FAIL self-test fixture; the hunt freezes its sampler against `D` the same way (K2). §6(5): the table carries CPU-seconds, hypothesis hash, method identity, bundle hash. M1 fixtures: mismatched identity refused; a planted under-reporting method REJECTed. Evidence: the incident class — `PROPOSALS.md:245` (AI Scientist hallucinated an ablations table); the published ladder template verifies logs against planted scalars and spot-checks walks against an independent implementation, `briefs/adjacent-distributed-collision-search.md:16,22`. Re-judged HIGH: it changes what a ladder-tested method is (a skill written against the harness's counted group object), not only how the gate reads it. |
| 2 | Tier tickets are branch-level; Tier 1 and theorem-claim Tier 2 have no named ticket kind | MED | K1, K5 (ticket half), S3 | §5, §13 M1 | ACCEPT (merged). The tier gate reads four things: profile, budget, the launch's hypothesis key and method identity (or statement hash), and a ticket produced for that same key and identity — a ticket is bound to a hypothesis, never a branch, and a mismatch is refused. The lattice is total: Tier 0 no ticket; Tier 1 = the hypothesis object (and claim statement node) recorded, with the §8 presence check passed for an attack and the §7 pre-filters passed for a theorem statement; Tier 2 algorithmic = KEEP (KEEP_IN_SAMPLE scoped as before); conjecture = SURVIVED hunt record; theorem with a Tier-2 gate profile = claim statement node with an `approve` `review_verdict`; Tier 3 adds justification, certificate plan, sign-off. M1 fixture: a KEEP table refused for a launch whose key or identity differs. Evidence: the plan's own predicate (r2 §5:386-402) named kinds for two cases only; the branch tree's `hypothesis` pointer is mutable (§4) so a branch-bound ticket survives a repoint. |
| 3 | The human statement-review verdict is "the gate" but no artifact the gate reads; PROVEN derived from `lean_artifact` alone contradicts HANDOFF non-negotiable 2 | MED (factual) | G4, K5 (part), S (via `HANDOFF.md:96`) | §7, §5, §13 M0/M1/M2 | ACCEPT-PARTIAL. Typed immutable `review_verdict {statement hash, reviewer, verdict ∈ {approve, reject, needs_revision}, checklist template hash, gate-bundle hash, time, supersedes?}` written only through the human path (as waivers are), non-transferable across statement versions; `justify` derives PROVEN only from a `lean_artifact` plus an `approve` verdict on the same statement hash; absent or `reject` blocks, never defaults; M0 schema gains the node; M1 (l) runs with a human-path verdict fixture and its negative (absent / superseded-hash verdict stays below PROVEN); M2 builds the review workflow and its fixture. G4's signing and key management not integrated (the human write path is the attribution at M0–M4; no evidenced defect). Evidence: `HANDOFF.md:96` ("Nothing is PROVEN without a green Lean check **and** a statement-level match review"); plan-r2 §7:517-520 granted PROVEN to green Lean alone. |
| 4 | "CI radius" and "whole claim CI" name no estimator, pairing or coverage; at 10² trials the √2 control sits at the band's edge; A/A independence unstated; 60-bit rung trial count ambiguous | MED | G5 (part), L3, S2, S4 | §6, §4 | ACCEPT-PARTIAL. The ladder plan fixes a versioned comparison protocol: estimator (ratio CI, median- or mean-form, named), pairing (claimant and both baseline arms on the same instance stream, each under its own gate-drawn method seeds — the A/A arms differ only in those seeds), CI method and coverage, per-rung trial count and the every-rung rule, tolerances, baseline revision; the trial count is sized at M1 so that (j) is KEPT and (k) INCONCLUSIVE with margin, the 10² figure being a floor; each rung's tier follows its declared profile under that count (interpreted 50-bit = hours, compiled = minutes; M1 records which). 60-bit rung: claimant only on the `m` hold-out instances, no baseline or A/A arm, the 10²-trial sentence a pricing remark. Result table names the bundle hash; a verdict is never recomputed under a later bundle; REJECT records the predicate that fired and the measured points. Evidence: band formula is frankensqlite's `max(1 + 2·radius, 1.01)` on the whole claim CI, `briefs/frankensqlite.md:22`, `PROPOSALS.md:288-289`; sd ≈ 0.53–0.56 × mean, `briefs/adjacent-distributed-collision-search.md:16`. Arithmetic: SE per arm ≈ 5 % at 10² trials, ratio SE ≈ 7 %, 95 % radius ≈ 14 %, band ≈ 1.28; the √2 control's CI ≈ [1.22, 1.61] — INCONCLUSIVE at the floor count. G5's protocol-version object beyond the bundle hash not integrated (the bundle hash on every gate-run record already versions it). |
| 5 | M0's `justify` fixture admits STRONG-EMPIRICAL from a `ladder_table` alone while §7 says "ladder + repro node" | MED | G1 | §7, §13 M0 | ACCEPT (re-judged MED from HIGH: a fixture/contract mismatch, not an architectural hole). §7 defines "repro node" as the §3 reproducibility record attached to the table's own attempt (a second agreeing attempt or a passed witness check), ceiling CONJECTURE without it; M0 fixture: STRONG-EMPIRICAL with the record, CONJECTURE ceiling with it absent or `AuditOnly`, a coverage violation when population does not cover scope, the `statistical`-for-PROVEN lattice violation. Evidence: plan-r2 §7:517-520 and §13:756-758 (the contradiction is internal); `PROPOSALS.md` C2 lattice rule. |
| 6 | Auditor's spot-check bound assumes uniform random draws; "largest fan-in drawn first" voids it | MED | G2 | §7, §13 M4 | ACCEPT. Each stratum is partitioned into a critical set (fan-in above a bundle cutoff) audited exhaustively and a residual sampled uniformly without replacement from gate-owned committed entropy (seed in the audit record); the `bits` guarantee is stated for the residual alone; the record names population, cutoff, coverage, seed, sampled identifiers. M4 fixture: a planted rotten node in the critical set is always found, one in the residual at the declared rate. Evidence: `briefs/frankenfs.md:38-43` — `min_challenges(f, bits)` is the with-replacement random bound and the source draws its challenge set from a seed via BLAKE3 XOF. |
| 7 | The formalization gate's checker configuration, the verifier's invocation and the tier cost boundaries are gate semantics living in prose, not in the pinned bundle | MED | O2 | §4, §7 | ACCEPT. Bundle contents extended: checker configuration (challenge module, theorem and definition names, permitted-axiom set, external-kernel commands) with `lean-toolchain` and `lake-manifest` pins; the Tier-0 verifier's invocation (backend path, stack ceiling, accept predicate); the §5 tier cost boundaries; the router's class predicate; the §6 comparison protocol; the auditor's critical-set cutoff. §7: the axiom set and checker command are bundle fields, a run whose configuration differs fails closed before compilation. Evidence: `grounding/lean-checker-protocol.md:21` (comparator config `{challenge_module, solution_module, theorem_names[], definition_names?[], permitted_axioms[], enable_nanoda?, external_kernels?}`), `:29` of the PARI grounding for the verifier's three load-bearing invocation facts. |
| 8 | Worker context isolation rests on a settings-source path the grounding records as unprobed | MED | O5 | §4, §13 M1 | ACCEPT (moved from O's proposed M0 to M1, where workers first exist). §4 tags the property as a stack fact the dispatch canary grounds; M1 done-when: distinct tokens planted in each settings source (project- and user-level instruction files, a skill file, working-tree status) are absent from a dispatched worker's echoed context; the canary is a gate self-test of the dispatch path, re-run on every toolchain or SDK change, whose failure yanks the path as a failed self-test yanks a skill revision. Evidence: `grounding/dbos-sqlite-and-agent-sdk-isolation.md:30` (subagent receives project CLAUDE.md via settingSources), `:33` (startup context includes every CLAUDE.md level and a git-status snapshot), `:40` (OPEN: whether `setting_sources=[]` suppresses `~/.claude/CLAUDE.md`). |
| 9 | The Skeptic's substrate closure hands it the Solution for Lean claims ("the recipes … which a re-run needs") | MED | O6 | §7 | ACCEPT. Closure filtered by evidence kind: recipes and certificates for `repro_node`, `ladder_table`, `counterexample_hunt_record`; for `lean_artifact` the Challenge's statement hash and the gate-run verdict only, never the Solution blob or its recipe inputs — the checker re-run is the gate's job. Evidence: plan-r2 §7:570-573 (internal contradiction); `PROPOSALS.md` C10. |
| 10 | "State it in the orchestrator: a run announcing it broke ECDLP has erred" is prompt text; the router's classes are not a typed predicate | MED | K4 | §7 | ACCEPT-PARTIAL. The router's classes are a bundle predicate over the hypothesis object's and statement node's typed fields (target family, claimed property or cost model, scope) and the §8 flag; the top class (scope names the target family, claimed property is a solve below the generic bound) requires ladder KEEP where algorithmic, formalization and statement review where a theorem, reproducibility, and §10 sign-off; no Tier-3 ticket without all; the orchestrator may request a class and never lower one; the sentence becomes that routing rule. M1 fixture added. K4's `TARGET_BREAK` name not adopted (the class is defined by its predicate). Evidence: `HANDOFF.md:100-101` (non-negotiable 5), §1 of the plan. |
| 11 | `RequiresNullControl` is defined but has no transition: who re-measures, how the branch leaves the state, where "had a null control" is recorded | MED | L1 | §4, §13 M2 | ACCEPT-PARTIAL (re-judged MED from HIGH). Null-control presence is a field of the entry's evidence node (a ladder table carries its A/A arm; a hunt KILLED by a verified counterexample needs none); `RequiresNullControl` parks with `null_control_pending`, enqueues a gate-owned re-measurement of the refuted hypothesis object under the current ladder plan (human queue before M4, auditor's queue from M4, never the proposing worker), appends its table to the entry as a new evidence node, clears the blocker when it lands, and re-runs the preflight. M2 fixture added. Evidence: `briefs/frankensqlite.md:15` ("the prior REJECT had no A/A null, rerun it before proposing anything new"); `PROPOSALS.md:363`. |
| 12 | "Disowned by `salt` when the fault is found to reach them" names no mechanism: who finds the reach, what code reads "disowned" | MED | L2 | §2, §3, §13 M0 | ACCEPT. The yank record names its reach as a predicate over recipe-key fields (revision, plus a declared input range where the fault is input-dependent); every attempt inside gains an append-only `disowned` mark (rows and blobs kept); a disowned node is served from no cache, is absent to `justify` (which re-derives every claim transitively justified by it), and is no ticket; the class's `salt` is bumped; attempts outside the reach stand. M0 schema gains the mark. Evidence: `PROPOSALS.md` C7 (`GoldenVectorMismatch` fail-closed) for the yank; the mechanism is the plan's own §7 downgrade rule made reachable. |
| 13 | M0 checkpoint: "outside the orchestrator's write path" yet appended at every gate run — the authority boundary is unstated | MED | G3 (boundary half) | §3, §13 M2 | ACCEPT-PARTIAL. The boundary is named: the file is owned by the operator, carries the append-only flag only its owner can clear, and is writable by the orchestrator's process user — a user distinct from the operator, as the pin already requires — so that process can extend and cannot truncate it or clear the flag; that the flag binds against a non-owner writer is the stack fact M0 grounds; a checkpoint the process can truncate is no checkpoint; an unreachable or unwritable checkpoint blocks promotion rather than disabling checkpointing. M2 fixture: a log truncated to an earlier valid prefix fails startup verification. G3's helper under a distinct OS identity with an IPC interface not integrated (r2 #11 rejected signed/remote anchoring as over-engineering at M0; the file boundary meets the stated threat, a raw write by a model component or a bug). |
| 14 | M2's done-when exercises none of the mechanisms M2 adds | MED | K7 (part), S5 | §13 M2 | ACCEPT. Done-when enumerates: refuted key Blocked unaided; jittered-range proposal containing a measured point Blocked; `supersedes` into REFUTED parks; `null_control_pending` parks and clears; truncated log fails startup; unreachable checkpoint blocks promotion; a worker returning with an open claim yields `Leaked` while a harness-terminated attempt yields none; a green Lean artifact without a verdict stays below PROVEN. |
| 15 | M0 corpus's declared origin contradicts the grounding: `upstream_vendored` for a triple whose `P`, `Q`, `x` were enumerated locally | MED (factual) | O3 | §13 M0 | ACCEPT. Per-field origin: curve and order `upstream_vendored`; `P`, `Q = 3P`, `x = 3` derived locally and re-checked by postcondition at every self-test run (`ord(P) = 7`, `3P = Q`), never trusted as vendored; the second curve-and-order case's `P` is not explicit upstream and is chosen locally under the same postcondition (any nonzero point, the order being prime). Verified `grounding/pari-sage-toy-curve-backend.md:33` (curve+N PROVEN-in-source; P,Q,x STRONG-EMPIRICAL, local enumeration), `:34` (seed 2's P OPEN), `:42` (no explicit F_p triple beyond seed 1). |
| 16 | KEEP checks memory against the cap only, never against the pre-registered memory model | LOW | O4 | §6 | ACCEPT (wording: (0) already pre-registers memory and (2c) already REJECTs a model miss; (2) now names it: measured peak memory must stay under the cap *and* match the pre-registered memory model on the sizes measured; undeclared growth is REJECT). Evidence: `briefs/adjacent-distributed-collision-search.md:31,51` (rho O(1) memory, BSGS √n). |
| 17 | §5's Tier-2 pricing carries no tag though its source tags the extrapolation CONJECTURE above 50 bits | LOW | O7 | §5 | ACCEPT. Verified `briefs/adjacent-distributed-collision-search.md:51` ("Derived ladder bar (CONJECTURE beyond 50 bits)"). |
| 18 | A `BUDGET_EXCEEDED` attempt leaves a linear obligation the plan never disposes | LOW | O7 (part) | §4 | ACCEPT-PARTIAL. A harness-terminated attempt (`BUDGET_EXCEEDED`, `SKILL_YANKED`) is not a leak; the obligation stays with the branch, which remains active for the orchestrator's next tick to fund within budget, park with `budget_preempt` or withdraw. O7's automatic park not adopted (disposition is a strategy decision; `budget_preempt` is one of its options). |
| 19 | Nothing says how a revision enters the runnable set; an uncertified revision is launchable | LOW | K6 (part) | §2 | ACCEPT-PARTIAL. A revision is launchable only once its self-test has passed and its certificate is recorded; the tier gate refuses an uncertified revision as it refuses a yanked one; who may admit a revision whose profile reaches Tier 2 is an operator ruling the bundle records. K6's `skill_revision` registry node and "human admission for Tier-2+ until M4 policy" not integrated (the identity bundle and certificate are already nodes; the authority is an operator ruling, open question 2). |
| 20 | M1's `KEEP_IN_SAMPLE` tier-gate fixture should be explicitly synthetic | LOW | L4 | §13 M1 | ACCEPT (wording: "a (synthetic) `KEEP_IN_SAMPLE` table"). |

Accepted clusters: 20 (7 of them partial). Gate-bundle contents re-enumerated to carry the
objects introduced above (comparison protocol, checker configuration and pins, verifier
invocation, tier cost boundaries, router predicate, auditor cutoff).

## 2. Rejected (cluster · seats · cause)

| # | Cluster | Seats | Cause |
|---|---|---|---|
| R1 | Typed intermediate research nodes (`lemma_obligation`, `proof_attempt`, `partial_formalization`, `reduction_step`) as reward fuel; an anti-starvation floor in M3's done-when | K3 | Re-litigates r2 R4 ("M3 bar should include does not starve slow branches" — premature, P3 decides) and r1 X (`reduces_to` edge, no code branches on it) with no new evidence (K3's own tag: CONJECTURE, "standard horizon-fail of myopic bandits"); the reward is the M3 decision (§15 P3), so the nodes are homeless before it. Open question 6 of r2 stands. |
| R2 | Re-head §5's allocation sentence to "targets expected information per compute-dollar" | K7 (part) | Re-litigates r2 R3 (K9): the sentence already states the implemented surrogate and forbids every model term. |
| R3 | Append-only checkpoint helper under a distinct OS identity with a narrow IPC interface at M0 | G3 (half) | Re-litigates r2 #11's partial rejection (signed checkpoints, remote store, availability policy — over-engineering at M0); the accepted half (cluster 13) names the authority boundary the file already provides. |
| R4 | Signed `review_attestation` with reviewer keys, revocation and recovery procedures | G4 (half) | No evidenced defect at M0–M4 scale: the human write path is the attribution, as for waivers; the typed node and its binding were accepted (cluster 3). |
| R5 | Ladder protocol-version object beyond the bundle hash; "a ladder REJECT is a measured refutation only of its recorded reach, never of an unqualified method family" | G5 (half) | The bundle hash on every gate-run record and now on the result table already versions the protocol; the reach sentence restates §4's measured-reach rule and §6's "finite sizes test a declared model" — adding it echoes the r1 AD / r2 R1 re-scoping of "refuted on the spot", which stays rejected. The failed predicate and measured points on the table were accepted (cluster 4). |
| R6 | Delete "(floor 1%)" as dead text | O7 (part) | Does not reproduce as a defect: the floor is the source mechanism's `1.01` (`briefs/frankensqlite.md:22`, `PROPOSALS.md:288-289`) and guards a degenerate null arm (a near-deterministic baseline gives radius ≈ 0); kept, with that why stated. |
| R7 | A rule that nothing enters §§2–8 that M0–M1 does not exercise; delete §15 P5–P7 | O framing (b) | A rule about the review apparatus (rule 13); P5–P7 each name a decide-by milestone and a drop condition, and P7 is cited by §4 and §13 M4. Recorded as open question 6 for the operator. |
| R8 | The foundations auditor blind re-presents past human statement-review verdicts and publishes the self-disagreement rate | O framing (b) | Ceremony under rule 13: no gate branches on the rate, no verdict is overridden, no retirement condition. Recorded as open question 5. |
| R9 | Human admission of every Tier-2+ skill revision as a plan default | K6 (part) | Operator policy, not an evidenced defect; recorded as an operator ruling the bundle records (cluster 19) and open question 2. |

Rejected clusters: 9.

## 3. Flagged invariant attacks

None this round. No seat proposed weakening §0, the gate layer's existence or immutability, the
taxonomy, the ladder, the verifier, the no-go checklist or the honest baseline. G5's reach
sentence (R5) is not an attack as phrased — it restates a rule already in §4 — and was not
integrated because its framing repeats the r1 AD / r2 R1 re-scoping that was. Every accepted
change adds a measurer, a refusal, a fixture, a typed field or a tag; none removes a gate input.

## 4. Factual corrections (each checked against the cited file)

1. M0 corpus origin: seed 1's `P`, `Q`, `x` are locally enumerated (STRONG-EMPIRICAL), the curve
   and order PROVEN-in-source; seed 2's `P` OPEN; no explicit F_p triple beyond seed 1 —
   `grounding/pari-sage-toy-curve-backend.md:33,34,42`. **Changed a mechanism** (per-field
   corpus origin and the self-test's postcondition re-check).
2. PROVEN requires a statement-level match review — `HANDOFF.md:96`. plan-r2 §7:517-520 derived
   PROVEN from `lean_artifact` alone. **Changed a mechanism** (`justify`'s PROVEN rule reads the
   `review_verdict` node).
3. comparator config fields — `grounding/lean-checker-protocol.md:21`. Bundle contents (wording
   plus a fail-closed clause).
4. Tier-2 pricing is CONJECTURE above 50 bits — `briefs/adjacent-distributed-collision-search.md:51`.
   Tag added.
5. Subagent settings-source leak paths PROVEN-in-docs, suppression OPEN —
   `grounding/dbos-sqlite-and-agent-sdk-isolation.md:30,33,40`. The isolation property is tagged
   as grounded by the canary.
6. The spot-check bound is a with-replacement random-sampling bound drawn from a seed —
   `briefs/frankenfs.md:38-43`. Auditor sampling restated.
7. O's check that positive control (j) "clears its own band (1.41 against ≈1.20)" compares the
   point estimate; the rule is the whole claim CI. Re-derived: at 10² trials and sd ≈ 0.5·mean the
   per-arm SE is ≈ 5 %, the ratio's 95 % radius ≈ 14 %, the band ≈ 1.28, the control's CI ≈
   [1.22, 1.61] — INCONCLUSIVE at the floor count. The ladder plan's trial count is sized by the
   control (cluster 4).
8. D's claim that "about one run in five" should read "one in twenty" does not reproduce: the
   sentence describes the un-widened point-against-band test (band `1 ± 2·radius`, radius ≈ 0.10,
   SE ≈ 0.158: `P(|Z| > 1.27) ≈ 0.20`); the widened band is the remedy the sentence introduces.
   Not integrated.
9. L's claim that the ledger entry has no null-control field is half right: the A/A arm is a
   field of the ladder table (the entry's evidence node), not of the entry; integrated as "a field
   of its evidence node".
10. O7's "(floor 1%) can never bind" — the floor is the source's `1.01` (`briefs/frankensqlite.md:22`);
    it binds only for a degenerate null arm, which is its purpose. Not a defect.

Corrections 1 and 2 changed mechanisms ⇒ verdict cannot be STEADY.

## 5. Seat reliability

- **GPT-5.6-terra:** complete; 5 numbered proposals with diffs, format respected. G1 accepted
  (re-judged MED), G2 accepted (MED), G3 and G4 accepted in half (the boundary and the typed
  node; the helper/IPC and the keys rejected), G5 accepted in part (protocol pinned, predicate
  recorded; version object and reach sentence not). Its "facts still needed" (checkpoint threat
  model, attestation governance, ladder estimator, auditor population) are sound and appear in
  the open questions.
- **Grok-4.5:** complete; 7 proposals with diffs. K1 and K2 accepted (merged into clusters 1 and
  2), K4 accepted in part, K5's ticket half accepted, K6 and K7 in part; K3 rejected
  (re-litigation, homeless before M3). Strongest on gate-binding holes; its framing (b) repeats
  r2's anti-starvation concern.
- **GLM-5.2:** 44 KB reasoning stream, no numbered proposals or diffs, truncated mid-sentence
  (seat file line 311, "Actually, I think this is"). Four findings recovered (L1–L4); all
  accepted in some form, L1 re-judged MED from its HIGH. Exceeded the format; counted toward
  consensus only where stated as a finding.
- **DeepSeek-v4-flash:** 42 KB stream of "Potential issue N … Good.", no proposals, truncated.
  Its one concrete claim (correction 8) does not reproduce; its arithmetic checks elsewhere agree
  with the plan. Contributed nothing integrable this round.
- **Opus grounded:** complete; 7 proposals, framing, facts. O1 accepted (HIGH), O2–O6 accepted
  (MED/LOW), O7 in part; framing (b) rejected under rule 13 with its two ideas recorded as open
  questions. Every cited line re-verified here; one loose check (correction 7: point versus CI
  for control (j)).

## 6. Open questions for the operator

1. Compiled baseline skills at M1 (r1 Q5, r2 Q1, now with a number): at the trial count the √2
   control needs (≈ 10³ per arm per rung), an interpreted 50-bit rung is hours of one core and
   leaves Tier 1 — compile `rho_dp` and `bsgs`, or accept a Tier-2 classification of the 50-bit
   rung and the cheap-before-expensive cost that carries?
2. Who admits a skill revision whose cost profile reaches Tier 2, and who clears a yank or issues
   a `salt` (r2 Q3 stands)?
3. Does the orchestrator run under an OS user distinct from the operator at M0 (the pin and the
   checkpoint both assume it), and on which host — macOS `uappnd` and Linux `chattr +a` differ in
   who may set and clear the flag?
4. Statement-review reviewer identity: the operator alone, or an expert role too; does an
   `approve` expire or require re-review when the gate bundle changes?
5. Do you want the foundations auditor to blind re-present a sample of your own past
   statement-review verdicts and publish the self-disagreement rate (O framing; rejected as
   ceremony unless adopted as an operator practice with a consumer)?
6. Prune §15 P5–P7 now (O framing) or leave them to their decide-by milestones?
7. r1 Q1–Q4 and r2 Q2, Q4–Q6 stand (second implementation at M0; Tier-2 human-session knob; claim
   statement author default; Linux host for the PROVEN gold tier; ceiling units; M4 checkpoint
   writer; M4 write rate; M3 starvation bar).

## 7. Validation

- **(a) Self-containment.** Most obscure M0 task: `justify` over the typed evidence node with
  the reproducibility record, plus the `review_verdict` node in the schema. Implementable as
  written: the kind enum and max-class map (§7), the repro record as the §3 policy's second
  agreeing attempt or passed witness check attached to the table's attempt, coverage as a
  structural comparison of population and assumption fields against the statement's scope field,
  the four M0 fixture outcomes (STRONG-EMPIRICAL, CONJECTURE ceiling, coverage violation,
  lattice violation), and the `review_verdict` fields with their human-path-only writer. The
  `disowned` mark is likewise buildable: an append-only mark selected by a predicate over
  recipe-key fields, read by the cache, `justify` and the tier gate. The M0 corpus's per-field
  origin and postcondition re-check follow the grounding's §4 verbatim.
- **(b) Dependency sanity.** M0 → M1 → M2 → M3 → M4 is a DAG. Builders for every mechanism added
  this round: M0 — `disowned` mark, `review_verdict` schema, the four-outcome `justify` fixture,
  per-field corpus origin; M1 — gate-owned counter and CPU cross-check, frozen method identity,
  comparison protocol and trial-count sizing, memory-model check, hypothesis-bound tickets and
  the Tier-1 / theorem ticket kinds (the tier gate exists at M0; the new branches are exercised
  by M1's fixtures), `review_verdict` in the PROVEN derivation with fixture (l), the dispatch
  canary, the router's class predicate with its fixture, the checker configuration in the bundle;
  M2 — `null_control_pending` park and re-measurement queue, checkpoint authority and truncation
  fixture, `Leaked` fixture, statement-review workflow; M4 — auditor critical/residual split and
  its fixture. No orphan: every new object has a consumer that branches on it (the tier gate,
  the ladder verdict, `justify`, startup verification, the preflight, the audit record's human
  queue).
- **(c) Justification sampling.** Gate-owned counter (why: the KEEP band is computed from the one
  input the party being gated would otherwise produce); hypothesis-bound ticket (why: a ticket
  that followed the branch would be a club card); `review_verdict` in PROVEN (why: HANDOFF's
  non-negotiable is enforceable only as a node the derivation reads); critical/residual auditor
  split (why: the bound is about random draws); `null_control_pending` (why: the party that wants
  a refutation re-examined must not re-measure it). All five carry a why; so do the `disowned`
  mark, the checkpoint boundary, the router predicate and the canary.
- **(d) Steady-state diff.** +167 lines (950 → 1117), 369 diff lines. Structural in one place —
  §6's measurement ownership and execution contract (every ladder-tested method is a skill over
  the harness's counted group object; the ladder runs the identity frozen in the hypothesis
  object) — and mechanism-level elsewhere: §5 (total ticket lattice bound to hypothesis and
  method), §7 (review verdict in PROVEN, Skeptic closure by kind, router predicate, auditor
  split), §3/§4 (`disowned` mark, checkpoint authority, `RequiresNullControl` transition,
  bundle contents), §13 (fixtures and done-whens). Section numbering, §0, §8, §9, §14 and §16's
  invariant list unchanged. Less structural than r2 (which changed the verdict set and the tier
  contract) and far less than r1.

## 8. Verdict and residual scope

**NEEDS-ANOTHER-ROUND.** Expected residual scope for round 4: coherence of the ladder
execution contract (counted group object, CPU cross-check tolerances, frozen method identity)
with §2's skill interface and M1's corpus, and of the `review_verdict` and ticket-lattice
additions with §10's human-queue semantics — wording-level unless a seat finds a new
contradiction.
