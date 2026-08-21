# Ledger — round 2

Plan reviewed: `research/convergence/plan-r1.md` (v3). Plan produced:
`research/convergence/plan-r2.md` (950 lines; 384 diff lines against r1). Synthesizer own view
(written before any seat was opened): `research/convergence/r2/own-view-r2.md`. Seats:
GPT-5.6-terra (G), Grok-4.5 (K), GLM-5.2 (L), DeepSeek-v4-flash (D), Anthropic Opus grounded
(O); synthesizer own view (S). Prior ledger read in full: `r1/ledger-r1.md`.

Verdict: **NEEDS-ANOTHER-ROUND** — one accepted cluster is HIGH (the Tier-2 ticket / 60-bit
rung circularity changes the tier-gate contract and the ladder's verdict set), and three
factual corrections changed mechanisms (statement-hash tag and gate cost, M0 corpus
composition, hash-chain truncation over-claim).

---

## 1. Accepted (cluster · severity as re-judged · seats · section · what landed · evidence)

| # | Cluster | Sev | Seats | § | Disposition and what landed |
|---|---|---|---|---|---|
| 1 | Tier-2 ticket and 60-bit rung are circular: KEEP needs the 60-bit rung, the rung costs Tier-2 budget, the Tier-2 ticket is KEEP | HIGH | O1, G1, K1, L1, S1; D (ticket "of the required kind" wording) | §5, §6, §13 M1 | ACCEPT. Typed ladder verdicts `REJECT / INCONCLUSIVE / KEEP_IN_SAMPLE / KEEP` fixed in the ladder plan; `KEEP_IN_SAMPLE` is a purpose-bound Tier-2 ticket valid for the 60-bit rung of the same hypothesis key and nothing else, the gate refuses a launch whose declared purpose differs; `KEEP` is the ticket for every other Tier-2 launch and any Tier-3 request; the ticket is "the most recent admissible node of the kind the tier requires"; M1 gains the fixture that a `KEEP_IN_SAMPLE` table admits the 60-bit rung and is refused elsewhere. Evidence: the plan's own predicates (r1 §5:316-318, §6:353-360); 60-bit cost `briefs/adjacent-distributed-collision-search.md:51` (1.35×10⁹ ops, ≈ 15 min interpreted). Cheap-before-expensive holds: the 50-bit floor fires first. |
| 2 | A superseded claim version mints a fresh hypothesis key and escapes its ancestor's REFUTED entry | MED | O2 | §4, §13 M2 | ACCEPT-PARTIAL. The preflight follows `supersedes` edges from the hypothesis object or the claim statement it names; an ancestor with a REFUTED entry (retry predicate unmet) parks the proposal with blocker `supersedes_refuted_review` until an attributed written statement of which semantic field changed and why the refutation does not reach it is recorded (human before M4, Librarian from M4). Not `Blocked`: a measured refutation reaches what was measured (§4); a declared version edge is a structural routing signal, like the near-dup advisory but exact. Evidence: plan §4 claim identity and `supersedes` text; `PROPOSALS.md` C8 (similarity routes, never sets status). |
| 3 | Hypothesis object has no author, store or immutability, so ladder pre-registration is a convention; instance-maker entropy is asserted, not constructed | MED | O3, K5, S5, O(c.3) | §3, §6 | ACCEPT. The hypothesis object is an immutable content-addressed node written at branch open by the worker or human that opens the branch, naming the claim statement hash where one exists; an amendment is a new object with a `supersedes` edge; it is appended to the substrate's append-only record sequence (the hash-chained log carries that order tamper-evidently from M2); the ladder refuses a rung whose hypothesis object does not precede the gate's entropy commitment; the gate draws a nonce after the object is recorded, per-trial seed `H(nonce ‖ hypothesis hash ‖ s ‖ i)`, nonce outside every worker allow-list until the run completes, nonce and seeds recorded in the result table; a worker-supplied instance list is a must-FAIL self-test fixture. Evidence: retroactive seed assignment in the FPGA record run, `briefs/adjacent-distributed-collision-search.md:22`; fixed-input overfitting class, `briefs/adjacent-agent-orchestration.md:27`. |
| 4 | Verification compute is unbudgeted; auditor bound at M0 defaults is `l ≈ 1.4×10³` per stratum | MED | O4, S (minor), O(c.4) | §5, §7, §4 | ACCEPT-PARTIAL. Cost profile names *production* and *verification* components; the tier gate reserves the verification component at launch and refuses a launch it cannot cover (a sharpening of r1's "budgeted before launch"). Auditor: the bound's magnitude is stated; a stratum smaller than `l` is checked exhaustively from the escrow; an unaffordable `l` yields an achieved `bits` recorded in the audit record and surfaced on the human queue (consumer named); cadence is a gate-bundle parameter set at M4. O4's per-claim achieved-bits column not integrated (no code branches on it). Arithmetic re-verified: ln(2²⁰)/ln(1/0.99) = 13.86/0.01005 ≈ 1379. |
| 5 | 60-bit out-of-sample check compares a 10-instance point estimate (SE ≈ 16 %) against the A/A band and REJECTs honest methods at a meaningful rate | MED | O5 | §6 | ACCEPT. Band widened by the rung's sampling error, `1 ± 2·√(radius² + (sd₆₀/(mean₆₀·√m))²)`, `m = 10` at M1 and fixed in the ladder plan. Evidence: sd ≈ 0.53–0.56 × mean, `briefs/adjacent-distributed-collision-search.md:16`. Re-derived: at ±20 % band the false-REJECT rate is ≈ 21 %, at ±28 % ≈ 8 % — either way a noise floor the gate should not pay. Not a weakening: REJECT of a correct model is noise that invites waivers. |
| 6 | §5 prices Tier-2 rho at 0.886√n (negation map) while §6's baseline is plain rho at 1.25√n | LOW | O6 | §5, §6 | ACCEPT. §5 names the negation-map rho; §6 names the baseline as plain rho without the negation map at M1 and states that a shipped negation-map rho becomes the baseline the day it lands. Evidence: `briefs/adjacent-distributed-collision-search.md:51` ("0.886√n with negation"); the brief's Rejected list (negation map not at Tier-1). |
| 7 | M1 done-when has no positive control; "no matched true advance is rejected" names no fixture | MED | K3, S2 | §13 M1 | ACCEPT-PARTIAL. Four must-PASS controls (the must-PASS half of §4's gate discipline): (j) negation-map rho pre-registered at ≈ 0.886√n is KEPT against plain rho (known answer, BLS PKC 2011 §6 via the brief :16); (k) the A/A null arm submitted as a claim returns INCONCLUSIVE (K3's plain-rho "KEEP" corrected: the baseline cannot clear its own band); (l) an exact-match Lean Solution reaches PROVEN; (m) a reproducible Tier-1 measurement is admitted to STRONG-EMPIRICAL. K3's (k) bsgs cost band is a §2 self-test, (n) duplicates (e), (o) marginal — not integrated. |
| 8 | Tier gate admits on a self-declared cost; a skill declaring Tier 1 and running for hours skips the Tier-2 ticket | MED | K2, L4, D | §5, §6, §13 M0, §15 P4 | ACCEPT-PARTIAL. The granted budget is a hard ceiling enforced at runtime at a bundle-named multiplier of the declared expectation (M0 default 4×, CONJECTURE — with rho's sd ≈ 0.5× mean a 2× ceiling aborts ≈ 4 % of honest trials, 4× well under 0.1 %; M1 re-sets from measured distributions); exhaustion ⇒ status `BUDGET_EXCEEDED` (≠ OK, never cached, never a ticket, never evidence); the ladder counts such a trial as a failure; P4 stays the drift monitor. K2's 2× default replaced. Evidence: asupersync budget exhaustion ⇒ cancellation, `briefs/asupersync.md:48-50`; ladder patience thresholds `briefs/adjacent-distributed-collision-search.md:16,55`. |
| 9 | Auditor and reproducibility re-runs must set `skip_cache_lookup` | LOW | L3 | §3 | ACCEPT (wording: the bit is set by the Skeptic's, the auditor's and every reproducibility-gate re-run). |
| 10 | "Opens read-only" is a convention; what stops the process reopening the bundle writable; pin location unstated | LOW | L2, O(c.5) | §4 | ACCEPT-PARTIAL. The pin is a deployment constant held with the bundle in an operator-owned location the orchestrator's process user cannot write (a file mode at M0), never a substrate row; the orchestrator's model components hold no file handle; a separate gate process is not required while every gate run checks the pin. L2's gate daemon not integrated (no evidenced defect the pin misses). |
| 11 | Hash chain detects rewrites, not truncation to an earlier valid prefix; "a log that fails verification" over-claims | MED | G5 | §3, §13 M2, §16 | ACCEPT-PARTIAL. Over-claim corrected; the chain head is appended at every gate run to a checkpoint outside the orchestrator's write path — M0: an operator-owned append-only file beside the gate-bundle pin (the OS flag is a stack fact M0 grounds), M4: a writer the substrate's process cannot truncate — and a log not extending the last checkpoint fails verification at startup and before promotion. G5's signed checkpoints, remote store and availability policy rejected as over-engineering at M0. Evidence: `PROPOSALS.md` C9 (fgdb-chronicle: "prefix verifies without suffix"). |
| 13 | "Memory stays inside the same band" against O(1)-memory rho rejects any nontrivial-memory method | MED | G3 | §6, §4 | ACCEPT-PARTIAL. Memory gated by a per-rung cap fixed in the ladder plan — the BSGS table for that size (≈ 1 GB at 50 bits, consistent with the refutation floor) — measured as peak algorithmic table and spill bytes with RSS diagnostic, unaccounted channel fails closed; KEEP still requires beating rho on group operations. G3's `declared-resource-budget` mode rejected (lets a claim pre-register its own bar). The §6 closing example (4.9×10⁷ ops, 900 MB) still fails, on ops. |
| 14 | Skeptic cannot perform a checklist it cannot see; "sees only the statement" conflicts with re-running experiments | LOW | G4, D | §4, §7 | ACCEPT. Dispatch rule rewritten: no detection logic of a gate that judges the worker's output is reachable; a role's own fixed procedure ships as a read-only, claim-agnostic role template in the gate bundle; the Skeptic's substrate closure = statement + recipes and certificates of its evidence nodes, never the Prover's transcript. Evidence: `PROPOSALS.md` C10 ("hidden from the worker being gated"). |
| 15 | Statement-hash construction stated in the voice of a verified mechanism; formalization gate has no cost | MED (factual) | O7 | §7, §5, §13 M1 | ACCEPT. Tagged: raw-export instability PROVEN by probe, closure hash CONJECTURE, hasher does not exist and M1 builds and probes it; the gate declares a cost profile; `leanchecker --fresh` 32.3 s mathlib-free, unmeasured with mathlib, M1 measures on a mathlib-importing Challenge before sizing the fixture corpus; §5's "a Lean compile" is the compile only. Verified `grounding/lean-checker-protocol.md:40-41,50,53,55`. |
| 16 | M0 "upstream_vendored corpus seeded from doctests" is one complete triple | MED (factual) | O8 | §13 M0 | ACCEPT with a correction to the seat: the exemplar is the curve generator, and the four vendored cases (one full triple, two curve-and-order cases, one negative control) do serve its order/primality self-test; what is one-of-a-kind is the verifier's `(P, Q, x)` triple. Integrated as: four vendored cases named precisely plus a `randomized_postcondition` arm for the generator (`isprime(n)`, `n·P = O`, Hasse interval) and the verifier (`Q = xP` ⇒ OK, `x' ≠ x` ⇒ FAIL). Verified `grounding/pari-sage-toy-curve-backend.md:33-36,42`. |
| 17 | M0 builds the tier gate, the bundle pin, `justify` and GC roots but its done-when exercises none of them | MED | S4; O framing (b) partial | §13 M0 | ACCEPT. M0 done-when adds: a `TierRefused` record on a fixture launch two tiers above its ticket; a bundle-hash mismatch fails closed; `justify` returns STRONG-EMPIRICAL from a synthetic `ladder_table` node and a lattice violation for a synthetic `statistical` node offered for PROVEN; an unrooted blob is collectable, a rooted one is not. Meets O's "schema with no consumer" concern without moving the schema (r1 REJECT U stands). |
| 18 | Range jitter mints a clean hypothesis key; REFUTED reach is exact-key only | MED | K4 | §4, §11, §13 M2 | ACCEPT-PARTIAL. REFUTED/PARKED entries record the measured parameter points; `Blocked` also when the proposal's declared region contains a measured point at which the same method identity failed the same cost model (axis-aligned inclusion on numeric fields, equality on categorical); reach restated as "the object measured and every object asserting the same model for the same method over a region containing the measured point, nothing broader". K4's superset-coverage direction (a refuted superset claim does not refute a subset unless the witness lies inside) and the constant-tweak clause not integrated. Distinct from r1 REJECT AF: the representation (numeric ranges already in the hypothesis object) is named. |
| 19 | The conjecture Tier-2 ticket ("counterexample-hunt record") has no shape | MED | K6 | §7, §5 | ACCEPT. Typed substrate node `{statement hash, D (content-addressed), pre-registered budget, entropy commitment and seeds, per-trial outcomes, counterexample + verifier status, verdict ∈ {SURVIVED, KILLED, BUDGET_EXHAUSTED}}`; SURVIVED is the ticket, KILLED writes the §4 entry, BUDGET_EXHAUSTED is no ticket; tag ceiling CONJECTURE without it. K6's null arm dropped (P1 covers the distributional case). |
| 20 | M4 parallel tracks on one SQLite file with no writer contract | MED | K7 | §3, §13 M4 | ACCEPT. One writer connection in the harness process (WAL, busy timeout: stack facts M0 grounds), workers are subprocesses returning artifacts with no write capability, the log advanced only by that writer; M4 done-when: ≥ 4 parallel tracks, zero broken heads, zero lost attempt rows. Evidence: `grounding/dbos-sqlite-and-agent-sdk-isolation.md:19` (DBOS on SQLite: IMMEDIATE isolation, busy_timeout, "can't be used in a distributed setting"). |
| 21 | Self-test failure has no consumer: "fails closed" unspecified for new launches and in-flight attempts | LOW | K8 | §2 | ACCEPT. Yank: the tier gate refuses new launches of the revision; in-flight attempts complete with `SKILL_YANKED` (≠ OK); cached results disowned by `salt` when the fault reaches them; only an attributed new revision with a fresh certificate clears it. Evidence: `PROPOSALS.md` C7 (`GoldenVectorMismatch` fail-closed, ratcheted floor). |
| 24 | `justify` is in the M0 schema but the evidence node it reads has no typed shape; empirical coverage undefined | MED | S3, L5 | §7, §13 M0 | ACCEPT. Evidence node `{kind ∈ {lean_artifact, ladder_table, repro_node, counterexample_hunt_record, statistical, model_proof}, target statement hash, declared population and assumptions (typed fields shared with the hypothesis object and the statement node's scope), producer identity, producer's own tag}`; max class is a function of `kind`; coverage is a structural comparison, never text. |
| 26 | Recipe key names a `container-digest` but M0 runs no container | LOW | S | §3 | ACCEPT. Where no container runs the field is the digest of the runtime's environment manifest, never empty. |
| 31 | "promotion past CONJECTURE is sought" names no actor | LOW | L (stream item 15) | §3 | ACCEPT (wording): the re-run fires when `justify` would derive a class above CONJECTURE from the node; the derivation waits on it. |

Gate-bundle contents were re-enumerated to carry the objects introduced above (`m`, per-rung
memory cap, patience ceiling, role templates, ceiling multiplier, auditor `f`/`bits`/cadence).

Accepted clusters: 23 (9 of them partial).

## 2. Rejected (cluster · seats · cause)

| # | Cluster | Seats | Cause |
|---|---|---|---|
| R1 | Finite-size loss is not an asymptotic refutation: re-scope "refuted on the spot" to "REJECT for the requested ticket / PARKED with a crossover blocker" when the hypothesis declares a crossover above 50 bits | G2 | Re-litigates r1 REJECT AD (G3 part) with no new evidence: the hypothesis object already carries `crossover`; the retry predicate on the REFUTED entry is the designed path for a crossover claim; the measured-refutation reach is already exact (§4). Softens the ladder — flagged below. |
| R2 | Slim M0: move hypothesis key, `justify`, GC roots out of M0 because they have no consumer there | O framing (b) | Re-litigates r1 REJECT U (K4): a tag column retrofitted after M1's gates exist is the churn §13 avoids. The consumer concern is met by cluster 17 (every M0 mechanism now has a done-when fixture). |
| R3 | Re-head §5's allocation sentence ("Allocation target (M3+)" / "default until P3") | K9 | Churn: r1 V′ already states that until M3 the currency is gate-outcome reward per measured cost; the sentence as written is unambiguous. |
| R4 | M3 bar should include "does not starve slow high-payoff branches" | K framing (b) | Premature: M3's test plan and P3 decide the bar; recorded as an open question, not integrated. |

Rejected clusters: 4. Partial rejections inside accepted clusters (G3's `declared-resource-budget`
mode, G5's signed/remote anchoring, K2's 2× default, K3's (j)/(k)/(n)/(o), K4's superset
direction and constant-tweak clause, K6's null arm, L2's gate daemon, O4's per-claim achieved-bits
column) are recorded in §1.

## 3. Flagged invariant attacks

- **G2:** re-scoping "refuted on the spot" weakens the ladder (an immutable gate); the same
  attack as r1's AD. Rejected, not integrated. Its sound half (refutation reaches the hashed
  object; a broader blacklist needs a formal entry) was already in the plan.
- **G3 (part):** a `declared-resource-budget` mode under which a claim pre-registers its own
  work/storage tradeoff and may be KEPT without beating rho on group operations lets a worker
  set its own bar; rejected; the memory-cap half accepted.

No seat proposed weakening §0, the gate layer's existence, the taxonomy, the verifier, the
no-go checklist or the honest baseline. Every accepted change adds a refusal, a fixture, a typed
field or a tag; none removes a gate input.

## 4. Factual corrections (each checked against the cited file)

1. Statement-hash construction is CONJECTURE, hasher does not exist; `leanchecker --fresh`
   32.3 s mathlib-free, OPEN with mathlib — `grounding/lean-checker-protocol.md:41,50,53,55`.
   **Changed a mechanism** (the formalization gate gains a cost profile and an M1 build-and-probe
   step).
2. M0 exemplar corpus: one complete F_p triple upstream, seeds 2–4 lack `x` or `P`, no second
   triple — `grounding/pari-sage-toy-curve-backend.md:33-36,42`. **Changed a mechanism** (corpus
   composition and the randomized-postcondition arm).
3. Hash chain: a prefix verifies without its suffix — `PROPOSALS.md` C9 (fgdb-chronicle tests);
   §3's "a log that fails verification" over-claimed. **Changed a mechanism** (head checkpoint).
4. §5's 0.886√n is the negation-map constant; §6's baseline is plain rho —
   `briefs/adjacent-distributed-collision-search.md:51`. Wording.
5. Auditor bound at M0 defaults ≈ 1379 per stratum (arithmetic re-done). Wording plus the
   exhaustive-stratum consequence.
6. 60-bit rung: `m = 10` gives SE ≈ 16 % vs sd ≈ 0.53–0.56 × mean (brief `:16`); point-vs-band
   REJECTs honest methods at ≈ 8–21 % depending on band width. Changed the out-of-sample test.
7. D's check that P1's e-process `∏(1 − λ_t(X_t − ε))`, `λ_t ∈ [0, 1/(1−ε)]` is a valid
   e-process under H₀ "fail probability ≥ ε" — reproduced (factor mean ≤ 1, nonnegative); no
   change. D's P2 stake-range check likewise agrees with r1 correction 6.
8. O8's framing that the vendored corpus "for the thing M0 must get right is one 5-element
   curve" conflates the generator's corpus (four usable order/primality cases) with the
   verifier's triple (one); integrated with that distinction.
9. K3's fixture (j) "plain rho_dp → KEEP-PROVISIONAL" is the wrong expected outcome: the
   baseline cannot clear its own band; corrected to the A/A null arm → INCONCLUSIVE.

Corrections 1–3 and 6 changed mechanisms ⇒ verdict cannot be STEADY.

## 5. Seat reliability

- **GPT-5.6-terra:** complete; 5 numbered proposals with diffs, format respected. G1 accepted
  (HIGH); G3, G4, G5 accepted in part; G2 rejected (re-litigation, invariant attack).
- **Grok-4.5:** complete; 9 proposals with diffs. K1 accepted (HIGH); K3, K4, K6, K7, K8
  accepted (partial or full); K2 partial (numbers replaced); K5 folded into cluster 3; K9
  rejected. Strongest on done-whens and ticket shapes.
- **GLM-5.2:** 43 KB raw reasoning stream, no numbered proposals or diffs, truncated
  mid-sentence (seat file line 265). Five findings recovered from the stream (L1–L5): L1
  (circularity) and L3, L5 accepted; L2, L4 partial. Exceeded the format; counted toward
  consensus only where stated as a finding.
- **DeepSeek-v4-flash:** 41 KB raw reasoning stream, no numbered proposals, truncated. Three
  findings folded (ticket-of-required-kind wording; cost under-declaration; Skeptic re-run
  needs the recipe); its P1/P2 formula checks are positive evidence for the plan. Exceeded the
  format.
- **Opus grounded:** complete; 8 proposals, framing, facts. Every fact check re-verified here at
  the cited lines; one overstatement (O8's corpus framing, see correction 8); O1–O7 accepted in
  whole or part; framing (b) re-litigates r1 U and was rejected with its concern met otherwise.

## 6. Open questions for the operator

1. Compiled rho/BSGS at M1 (r1 Q5 stands): at 2–3 minutes per 60-bit trial the hold-out rung
   and the ceiling arithmetic both change.
2. The budget ceiling multiplier default (4×, CONJECTURE) and whether wall-time, core-seconds or
   both bind.
3. Who clears a skill yank or issues a `salt`: human-only (mirroring waivers) or
   orchestrator-requested and human-granted? The plan says "attributed new revision"; the
   attribution authority is an operator ruling.
4. The chain-head checkpoint writer at M4 (a separate process user; the Linux host of r1 Q4?).
5. M4 write-rate target, to size the single-writer stress fixture.
6. Whether M3's bar should include "does not starve slow high-payoff branches" (K framing).
7. r1 Q1–Q4 stand (second implementation at M0; Tier-2 human-session knob; claim statement
   author default; Linux host for the PROVEN gold tier).

## 7. Validation

- **(a) Self-containment.** Most obscure M0 task: `justify` over the typed evidence node with
  its M0 fixture. Implementable as written: the kind enum, the max-class map per kind, the
  population/assumption fields shared with the hypothesis object and the statement node's scope,
  structural comparison, a typed justification or lattice violation, and the two synthetic
  evidence kinds plus synthetic statement hash the done-when names. The tier-gate `TierRefused`
  fixture and the bundle-pin mismatch fixture are likewise buildable from §5 and §4. The one M0
  object whose check lands at M1 is the hypothesis object's append-order-before-entropy rule
  (exercised by the ladder).
- **(b) Dependency sanity.** M0 → M1 → M2 → M3 → M4 is a DAG. Builders for every mechanism
  added this round: M0 — immutable hypothesis object, typed evidence node, `BUDGET_EXCEEDED` /
  `SKILL_YANKED` statuses, budget ceiling, container-digest rule, four new done-when fixtures;
  M1 — typed ladder verdicts and the scoped ticket, commit-ordered entropy and seed derivation,
  memory cap, patience ceiling, widened 60-bit band, positive controls, counterexample-hunt
  record, statement hasher and gate-cost measurement; M2 — measured-point reach,
  `supersedes_refuted_review` park, hash-chained log and head checkpoint; M4 — concurrency
  stress, auditor cadence and achieved-bits record. Ordering fix made during integration: the
  ladder's pre-registration check (M1) reads the substrate's append order; the hash-chained log
  (M2) hardens it rather than preceding it. No orphan: the yank's consumer is the tier gate;
  the checkpoint's consumer is startup verification; the achieved-bits record's consumer is
  the human queue.
- **(c) Justification sampling.** Scoped `KEEP_IN_SAMPLE` ticket (why: an unscoped rule is
  satisfiable by no honest claim); budget ceiling (why: a self-declared cost is fail-open under
  §1's pressure); `supersedes_refuted_review` park (why: structure may route, similarity may
  not); head checkpoint (why: truncation is the one edit a chain cannot see); skill yank (why: a
  revision minting OK after its self-test fails is a gate that fails open). All five carry a
  why; so do the memory cap, verification escrow, typed evidence node, hunt record and
  widened band.
- **(d) Steady-state diff.** +174 lines (776 → 950), 384 diff lines. Structural in two places
  — the tier-gate predicate (a purpose-bound ticket kind) and the ladder's verdict set —
  mechanism-level elsewhere (§3 hypothesis object, checkpoint, concurrency; §4 preflight reach
  and park, dispatch wording, bundle contents; §5 two-component profile and ceiling; §7 evidence
  node, hunt record, auditor magnitude, Skeptic template, hasher tag; §13 fixtures and positive
  controls). Section numbering, §0, §8, §9, §14 and §16's invariant list unchanged. Less
  structural than r1, which reworked the §2–§7 contracts.

## 8. Verdict and residual scope

**NEEDS-ANOTHER-ROUND.** Expected residual scope for round 3: coherence of the typed objects
introduced this round against each other and against the gate bundle's enumerated contents
(ladder verdicts and ticket purposes, evidence-node kinds, the counterexample-hunt record, the
budget ceiling and `m`/cap numbers) — wording-level unless a seat finds a new contradiction.
