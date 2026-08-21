# Cairn — Autonomous Math-Research Harness: Architecture & Implementation Plan (v3)

*A system for open-ended attack research on hard problems (target: ECDLP), built so it
never stops researching and never fabricates, redesigns its own search tree without ever
redesigning what counts as truth, and spends compute cheap-before-expensive with a human
supplying taste where models are weakest.*

*v3 integrates the mechanism review in `research/PROPOSALS.md` (evidence in
`research/briefs/`); the v2 text it extends is frozen at `research/PLAN-v2-frozen.md`.*

---

## 0. The principle everything hangs on

**Mutable strategy, immutable epistemics.** The orchestrator may rewrite the branch tree,
funding, worker prompts, and subproblems freely. It may **never** edit what counts as
"proven," the gates, the no-go checklist, the ladder, the verifier, or the calibration
taxonomy. A self-modifying system told "never give up" *will* redefine success into
something it can reach if you let it touch its own success criteria. Meta-level fixed,
object-level fluid.

Second, subordinate principle (compute): **cheap results gate expensive ones, and cost is
predicted before it's spent.** Compute is where rigor leaks out if you let spend happen
before a cheap check has earned it.

---

## 1. Prompt ⊂ harness

A prompt is a worker's job description in one context window: ephemeral, unenforced,
degrades over long horizons. A harness is durable state + mechanical gates + scheduler +
self-redesign loop. The Research-Mode prompt is the **template for spawned workers**, not
a rival to the harness. Every honesty property must be an enforced check, because under
"never give up" pressure, *asking* the model to comply is the first thing that fails.

---

## 2. Thin agents, fat skills (the decomposition unit)

- **Agents carry judgment** (which subproblem, which approach). **Skills carry capability**
  (compute the k-th summation polynomial, run rho to a distinguished-point certificate,
  formalize a lemma, sweep a parameter family). Push work out of agent-judgment into
  skills: a skill has a typed interface and a fixed version, so it's testable, cacheable,
  and reproducible in a way an agent never is.
- **Every skill ships a known-answer self-test.** Decomposition multiplies the places a
  subtle error can hide; each unit validates itself on cases where the answer is known.
  This is the ladder pushed down to the component level.
- **Skill identity and self-test shape.** A skill's identity is a typed bundle
  `{interface version, implementation revision, tool and container digests, numeric
  profile}`. Its self-test is (i) a vendored known-answer corpus with a per-case ledger
  (`pass | intentional_non_goal | known_gap`) and a committed pass floor that the skill
  advertises about itself — a lower bound that only an explicit, attributed update may
  raise, so the advertised floor and the measured floor cannot drift apart; (ii) a golden
  certificate = hash over the canonical transcript of the corpus and the exact outputs,
  so a changed implementation behind the same interface needs a fresh certificate and a
  mismatch fails closed; (iii) every nondeterminism source pinned (seed, hashers, clock)
  and a byte-equal double run asserted. Skills that produce floats declare a numeric
  profile or a tolerance. Tier-0 arithmetic skills verify their own answer before
  returning and, where two independent implementations exist (PARI vs Sage), require
  agreement or raise. *Why:* the known-answer corpus is the self-test; the floor keeps a
  skill from quietly regressing; the certificate makes "which implementation produced
  this" a checkable fact rather than a label.
- **Granularity rule:** grain a skill at *"a capability with a stable interface, a
  self-test, and a declared cost profile" (§5)* — no finer. Too fine and the orchestrator
  burns its budget gluing skills; too coarse and they stop being reusable.

---

## 3. Content-addressed substrate (provenance as a storage property)

- **Every artifact is hashed by `(skill@version, inputs-by-hash, seed, tool-versions,
  container-digest)`.** Provenance stops being an audit you run afterward and becomes how
  results are stored. A result not in the substrate does not exist to the claims DB.
  - *Key construction:* the key is BLAKE3-256 over a canonical, typed, domain-separated
    encoding of that tuple (fields in fixed order, sorted maps and sets, length-prefixed
    variable-length fields, no unknown fields, `(hash, size)` digests for inputs),
    enforced at write time and covered by a known-answer test vector. Two logically equal
    recipes that hash differently are a canonicalizer bug, never a feature. *Why:*
    REFUTED-by-hash (below) is exactly as sound as the canonicalizer; a key computed from
    non-canonical bytes silently under-reports dead ends.
  - *Cache bits on every node:* `do_not_cache` (never memoize), `skip_cache_lookup` (run
    even if cached and overwrite; the Skeptic's re-runs always set it), `status ≠ OK ⇒
    never cached` (a failure is a record, not a memo), and a `salt` that moves a whole
    class of results into a fresh namespace when a tool version is found faulty. A cached
    result is served only if every blob it references is present; otherwise it is
    recomputed. *Why:* a cache hit must never stand in for a gate pass, and a poisoned
    class must be disownable without rewriting history.
- **Dead-ends become structural, not memory-dependent.** When the orchestrator proposes a
  branch whose hash matches a `REFUTED` ledger entry, the system recognizes it instantly —
  same computation, same hash, already dead — with no agent needing to *remember* that two
  approaches are secretly the same. This is what gives the ledger teeth.
- **Versioning keeps history honest.** Improve a skill and old results keep their
  old-version tag rather than being silently corrupted; the tree redesigns without
  rewriting the past.
- **Replayable ≠ verifiable.** Deterministic work (a Sage computation) is bit-reproducible.
  Nondeterministic/expensive work (distributed rho) is not — store a **succinct
  certificate cheap to check** (the found relation, seed, walk definition) instead of a
  full replay. Same move as verify-before-submit: check the answer, don't redo the search.
  - *Replay grades:* every node carries `replay ∈ {Replayable (bit-identical re-run),
    Verifiable (a witness checked by a deterministic verifier), AuditOnly (logs only)}`.
    The grade can only be weakened, and `AuditOnly` is inadmissible as evidence.
  - *Certificate = declared content address + witness.* For a rho/kangaroo run the
    witness is the curve, `n`, `P`, `Q`, the walk definition (multipliers or their PRNG
    seed, index function, distinguished-point predicate θ) and the two colliding DP
    triples `(X, a, b)`, `(X, c, d)`; the verifier checks `aP + bQ = X = cP + dQ`, rejects
    `b ≡ d (mod n)` outright (never retries silently), computes
    `x = (a − c)(d − b)⁻¹ mod n` and checks `xP == Q`. Storing seeds instead of `(a, b)`
    shrinks reports but makes verification cost O(1/θ) walk steps; that is a Tier-3
    storage optimization, not the certificate. A certificate certifies identity and
    checkability, never truth: the artifact keeps its producer's calibration tag.
  - *Reproducibility gate = re-run and compare.* Admission re-runs the recipe (or
    re-checks the witness) and compares bitwise; on divergence the second copy is kept,
    rooted, as evidence of non-reproducibility and the node is marked inadmissible.
- **Retention:** keep lineage + certificates forever (cheap, load-bearing); GC the giant
  intermediate blobs once their derivation is recorded and the result verified. Keep the
  edges, prune the mass.
  - *Mechanism:* recipes, ledger rows, certificates and recorded divergences are GC
    roots; liveness is reachability from roots over lineage edges; only blobs are
    collectable. The ledger and branch-tree history are an append-only, hash-chained log
    (`chain = H(domain ‖ prior_chain ‖ canonical_record)`, every variable-length field
    length-prefixed) with compare-and-swap head advancement, re-verifiable from origin; an
    orchestrator that rewrites history produces a log that fails verification. *Why:*
    "the orchestrator may rewrite the tree but never REFUTED entries" needs a
    tamper-evident form, not a convention.
- **Store:** SQLite (blobs, lineage edges, roots table) keyed by BLAKE3 at M0. Off-the-shelf
  content-addressed caches (REAPI servers, cacache) retain by LRU and have no roots or
  lineage; their *semantics* (canonical keys, cache bits, completeness check, fixed-output
  certificates, `--check` re-runs, GC roots) are adopted, their binaries are not.

Skills are the nodes; the substrate is the edges + store. The whole research history is
one replayable-or-verifiable DAG — which is the only thing that makes a `STRONG-EMPIRICAL`
tag mean something.

---

## 4. Components

- **State layer:** branch tree (`{id, parent, hypothesis, status∈{active,parked,refuted,
  promoted}, priors, effort, yield, blocker?}`); **dead-end ledger** with `REFUTED`
  (proven dead → permanent blacklist, recognized by hash §3) vs `PARKED` (blocked-not-dead,
  tagged with blocker → auto-revived when blocker clears); **claims DB** (mandatory
  calibration tag §7, pointer to evidence node); substrate §3 is the reproducibility store.
  - *Ledger preflight:* before any branch is funded the ledger answers `Allowed | Blocked
    | RequiresNullControl`. `Blocked` = the hash matches a REFUTED entry whose retry
    predicate is unmet; `RequiresNullControl` = a prior refutation rests on a measurement
    taken without a null control and must be re-measured first. Every REFUTED/PARKED
    entry carries `{hypothesis hash, evidence node, method, result (+CI where measured),
    decision, retry predicate, caught_by}`. A near-duplicate signal (SimHash or embedding
    similarity to a REFUTED entry) is advisory only: it routes the proposal to the
    Librarian, who must state the difference in writing; it never sets a status.
    *Why:* "REFUTED is permanent unless the retry predicate is met" has to be a query the
    orchestrator cannot skip, and similarity must never be allowed to edit the ledger.
  - *Terminal-status invariant:* every opened branch and every opened claim is a linear
    obligation that must reach a terminal status (refuted / parked / promoted /
    withdrawn). A worker that exits leaving one open produces a `Leaked` record that is
    counted and escalated — fail-fast in tests, logged and escalated in production — and
    is never silently dropped.
- **Orchestrator (mutable brain):** bandit allocation over active branches (fund yield,
  prune stalls, revive parked, force periodic pivots so it can't rabbit-hole); self-redesign
  = editing *data* (tree/prompts/subproblems), never gates; cannot mark `proven`, cannot
  bypass a gate. Allocation mechanics and crash-safe ticks are decided at M3 (§15 P3).
- **Workers (Research-Mode prompt = template):** Librarian (lit-grounding: "tried before /
  why it failed" before any new attack), Reframer (falsifiable subproblems only),
  Experimentalist (small-case → conjecture → counterexample hunt), Prover, Formalizer,
  Skeptic (independent §7). Every worker is a fresh-context subagent whose inputs are
  exactly the nodes it is handed; gate rubrics and detection logic are never placed in a
  gated worker's context.
- **Gate layer (mechanical, immutable):** submission verifier (`xP==Q` subprocess or no
  submit, ever) · small-scale ladder §6 · no-go checklist §8 · formalization gate §7 ·
  reproducibility gate (no substrate node = inadmissible; §3 re-run) · proportional-scrutiny
  router §7 · tier gate §5.
  - *Gate discipline:* every gate ships a planted-failure self-test (a fixture that must
    FAIL and one that must PASS) run before the gate itself; gates run from a declarative
    plan with expected exit codes and ordered scopes, where an earlier failure blocks
    later ones and records why; invalid or missing gate config fails closed; a waiver is
    explicit, attributed, reason-bearing and expiring, and a waived check never counts as
    satisfied; a green result whose provenance is weaker than required (dry run, missing
    raw output, stale tool digest) cannot strengthen a claim. The gate plan, the no-go
    set, the non-goal sets of skill corpora, and the waiver registry live with the gates,
    outside the orchestrator's write path. *Why:* a gate that silently fails open is worse
    than no gate — it manufactures the appearance of enforcement. Every documented way a
    prior autonomous research system fabricated or gamed (editing its own time limit,
    hallucinating an ablation table, overfitting a single evaluator input, removing the
    instrumentation that detected it) maps onto one of these gates; the discipline is
    what keeps them from being dissolved by the worker they gate.

---

## 5. Compute tiers & allocation

Tier the whole surface; each tier's admission ticket is a result from the tier below.

- **Tier 0 — instant (ms–s):** typechecks, `xP==Q`, small-field arithmetic, "does the
  claim even cohere." Nearly every refutation and orchestration decision lives here. Free;
  run constantly.
- **Tier 1 — one core, minutes:** toy DLPs 30–60 bit, small Gröbner bases, a Lean compile,
  bounded counterexample sweeps. **The research lives here.** The ladder §6 is Tier-1. Fail
  here → never see another core.
- **Tier 2 — many cores, hours:** larger linear algebra, 80–100-bit rho for *validation*,
  big families, substantial formalization. Entered only holding a strong Tier-1 signal.
- **Tier 3 — cluster, days:** record-scale. Almost nothing reaches it; reaching it requires
  an explicit predicted-cost-vs-payoff justification and a certificate verification plan
  (§3 — you can't bit-replay it).

**Mechanism:** every skill declares its **cost profile** (complexity in inputs, expected
tier) as part of its typed interface, so the orchestrator *predicts* spend before launch
and the tier gate enforces cheap-before-expensive automatically. A spawned worker's budget
is the meet of its parent's remaining budget and the skill's declared profile; a retry or
restart is launched only if the remaining budget can afford it. **Allocation currency is
expected information per compute-dollar**, not raw yield — a cheap experiment that halves a
conjecture's probability outranks an expensive one that nudges a bound. Compute is a
tracked, finite resource flowing through the DAG exactly like claims. Measured cost is
compared against the declared profile; a persistent mismatch is a strategy-layer alarm
(§15 P4), never a gate.

---

## 6. The small-scale ladder (top anti-fabrication device)

Any claimed *algorithmic* advance must, mechanically, before it earns attention at full
size: run end-to-end on prime-order toy curves (~30/40/50/60 bit), actually recover `x`
(`xP==Q`), and show measured scaling matching its *claimed* asymptotic. A "subexponential
attack" that can't beat baby-step-giant-step at 50 bits is refuted on the spot. Cheap,
mechanical, near-impossible to fake; kills the dominant failure mode (proof-shaped text
that's subtly wrong).

**Protocol.** (1) The ladder generates its own instances: a fresh random prime-order curve
and random `(P, Q)` per run, at each size, never a fixed instance the worker has seen
(the documented exploit class for automated evaluators is overfitting a fixed input).
(2) It gates on distributions, not runs: at least 10² independent trials per size (for
rho the standard deviation is ≈0.5× the mean, so a single run calibrates nothing), the
sorted-distribution shape compared to the claimed model, and an A/A null arm whose CI
radius sets the decision band (a speedup is KEPT only if the whole claim CI clears
`1 + 2·radius`, floor 1%; otherwise INCONCLUSIVE or REJECT). (3) It reports group
operations against `√n`, never seconds. (4) The bar is quantitative: at 50 bits the
generic baseline is rho ≈ 1.25√n ≈ 4×10⁷ group ops and BSGS ≈ 1.5√n ops with ≈ 3×10⁷
table entries; "beats BSGS at 50 bits" means fewer than ~5×10⁷ group ops and under 1 GB,
and the method must *complete* at 60 bits, where BSGS needs 2³⁰ entries. (5) The result
table (size, trials, mean and sd of ops, memory, success rate, fit to the claimed
exponent) is the ladder's artifact and the template for a negative-results entry (§11).

---

## 7. Epistemic mechanics (humility made mechanical)

- **Calibration taxonomy (mandatory per claim):** `PROVEN` (formalized) · `STRONG-EMPIRICAL`
  (ladder + repro node) · `CONJECTURE` · `SPECULATION`. No green Lean check → not `PROVEN`.
  - **"Green Lean" is the challenge/solution protocol.** The gate owns a Challenge module
    holding the statement; the Formalizer submits a Solution module; the gate (i) rebuilds
    in a sandbox under the pinned `lean-toolchain` and `lake-manifest` mathlib revision
    recorded in the artifact, (ii) kernel-replays the result (`leanchecker --fresh`;
    comparator with an external kernel at the gold tier), (iii) requires `#print axioms`
    ⊆ {`propext`, `Classical.choice`, `Quot.sound`} — which rejects `sorryAx`, the
    per-computation axioms of `decide +native` / `bv_decide`, and any custom axiom — and
    (iv) requires the Challenge and Solution theorem statements to be identical over the
    statement's transitive constant closure, so a redefined constant anywhere under the
    statement fails the check. "No error messages" or an empty `sorries` list is never a
    PROVEN criterion (both have leaked `sorry`/`admit` in published systems). A REFUTED
    ledger entry may carry a machine-matched proof of the Challenge's *negation*. *Why:*
    this mechanizes "the thing proved is the thing stated"; "the Challenge says what we
    mean" is the human/Skeptic half below.
  - **The tag is derived, never set.** Each evidence kind has a maximum class it may
    justify: green Lean via the protocol above → PROVEN; ladder + repro node →
    STRONG-EMPIRICAL; sampled or statistical evidence → at most STRONG-EMPIRICAL on its
    declared population; a Lean proof about a *model* of the system → at most CONJECTURE.
    A claim's tag = the strongest class some evidence node justifies via
    `justify(evidence, target)`, which returns a typed justification or a lattice
    violation, never a boolean. A weaker class may *inform* a stronger claim; it may
    never *justify* it. The foundations auditor's core query is the transitive form: no
    PROVEN claim may carry a `justified_by` edge to a weaker premise.
  - **Statistical monitors block or alarm; they never promote.** An e-value, conformal
    bound, posterior, or similarity score may withhold a promotion, trigger extra
    scrutiny, or raise an alarm. It may never move a tag upward, and non-rejection is
    never positive evidence. *Why:* across the surveyed systems every misuse of a
    statistical gate had the same shape — a name ("certificate", "conformal",
    "e-process") promising more than the mechanism delivered, then read as permission.
  - **Tag history is append-only and attributed.** Every tag transition records what
    moved it and the evidence node; a downgrade requires an evidence pointer
    (refutation, retraction, failed re-verification); PROVEN has a non-waivable floor (the
    artifact above must exist and re-verify). Nothing is edited in place.
- **Statement-level review:** Lean verifies a proof is valid, not that you stated the
  theorem you meant. Verified-but-wrong-statement (weaker/trivial, smuggled hypothesis,
  wrong quantifier) is *more* dangerous than an open gap. Check the statement separately.
  - *Mechanical pre-filters (reject or flag, never pass):* a vacuity check that tries to
    derive `False` from the hypotheses (certified vacuous ⇒ reject); linters for the
    `∃ x, P x → Q` trap, stubs and new axioms; a bounded prove/disprove attempt with a
    weak prover (trivially provable or disprovable ⇒ flag); a blind round-trip
    informalization diffed against the source claim (divergence ⇒ flag). The Skeptic's
    rubric is the quantifier-order / strict-vs-non-strict / implication-direction /
    domain-and-boundary checklist (`ZMod 0`, `x/0`, `sInf ∅`, impossible hypotheses). The
    human verdict remains the gate.
- **Independent skeptic:** sees only the *statement*, never the prover's reasoning; rewarded
  solely for gaps/counterexamples. If it reads the proof it just agrees — independence is
  the whole value.
  - *By construction:* the skeptic is a fresh-context worker whose only input is the
    statement node plus tools for counterexample search; no prover output, no panel
    feedback and no gate rubric is reachable from its context. Its re-runs of any
    experiment set `skip_cache_lookup` (§3).
  - *Disagreement protocol:* a Prover/Skeptic or panel disagreement is never resolved by
    vote; it is recorded with both artifacts' hashes, classified (statement error, proof
    gap, harness bug, out-of-scope, inconclusive), routed to an owner (the human for
    statement errors), and the claim's tag stays at its pre-dispute level until resolved.
- **Proportional scrutiny + the paradox, written in:** tightened bound → clean argument;
  claimed break of the target → formalization + ladder + expert sign-off. **State it in the
  orchestrator: a run announcing it broke ECDLP has produced evidence it *erred*.** The
  bigger the claim, the more the burden inverts against it.
- **Strong law of small numbers (hard gate):** a small-case pattern is a conjecture until it
  survives larger cases + a deliberate counterexample hunt. Whether this gate also gains a
  pre-registered quantitative floor (an anytime-valid e-process on sampled cases, used as a
  *resource* gate before Tier-2 spend) is decided at M1 with planted-false conjectures
  (§15 P1); the floor, if adopted, never promotes a tag and never enters the orchestrator's
  reward.
- **Standing foundations-auditor (above the per-claim skeptic):** the per-claim skeptic
  catches bad proofs; it can't catch a bad *premise* the whole tree rests on (an FFDA-style
  heuristic everyone assumed). Periodically re-audit the shared assumptions — a tall tower
  on a cracked base is the failure no local check sees. Its mechanical core is the
  transitive `justified_by` query above; its sampling cadence for re-verifying substrate
  nodes uses the spot-check bound `l ≥ ln(2^bits)/ln(1/(1−f))` so that undetected rot at
  fraction `f` has probability below `2^−bits`.

---

## 8. No-go checklist (auto-flag tripwire)

Any proposed attack on the target must state how it evades all three or be flagged
almost-certainly-broken: (1) **Shoup √n** — must exploit named curve-specific structure, not
generic ops; (2) **isogeny invariance** — order & embedding degree are invariant, walking
can't help; (3) **prime-field index-calculus obstruction** — no efficient point
decomposition over prime fields; Weil-descent/GHS/summation-polynomial methods need
`F_{q^n}, n>1`.

---

## 9. Never give up — defined so it can't become fabrication

Persistence at the **program** level; honesty at the **claim** level. *Never give up* means
there's always a next legitimate action (reframe · prove an impossibility · pivot to an
adjacent open subproblem · tighten a bound · map a dead end) — the agent never stops
researching. It does **not** mean never concluding a path is dead or never reporting a
negative; it stops *claiming*, not *working*. **Progress = knowledge gained** (a proven
lemma, tighter bound, refuted approach, reproducible regularity, reduction), not distance to
the summit — so it can honestly never run out of moves. The one forbidden terminal state:
manufacturing the appearance of progress.

---

## 10. Problem selection, taste & the human loop (the real bottleneck)

Execution and verification are the parts the harness does superbly; **choosing the right
problem is the part it does worst**, because models pattern-match to problem-shaped things.
So this is the highest-leverage layer, and it's explicitly human-anchored.

- **Problem queue:** open subproblems scored `tractability × payoff × novelty`, ranked and
  injectable by a human.
- **Mixture-of-models as filter, not oracle.** A panel surfaces disagreement and cheaply
  prunes — but **ensembling cuts variance, not shared bias**; correlated blind spots across
  frontier models yield a *confident consensus that's wrong*, the worst case for a
  non-expert driver. So the panel **proposes and ranks with legible reasons** (tractable?
  novel? what falsifies it? tried before?) and **surfaces its own disagreement**; it never
  emits final verdicts. Panel disagreement is recorded and routed under the §7
  disagreement protocol, never averaged.
- **Two non-LLM anchors:** (a) cheap empirical reality — a candidate must yield a Tier-0/1
  testable prediction before "the models like it" counts; (b) a human ruling at the meta
  level (the reasons above are checkable without understanding the proof), with a **domain
  expert signing off on expensive, high-commitment calls**.
- **The selector is itself audited.** Problem-selection is a *pluggable, measured* component:
  track whether greenlit problems panned out, score its calibration, and swap it (single
  strong model / debate / cheap heuristic) if that beats the panel on record. Taste is held
  to the system's own standard. "Panned out" is adjudicated by a gate, never by the
  selector; the measurement protocol (a calibration test martingale on greenlight
  probabilities, with the outcome-lag caveat) is decided at M4 (§15 P2).
- **Legible state** is what makes this workable *and* engaging: the branch tree, open
  conjectures, and dead-end map are visible and reach-in-able, so the human contributes
  exactly where they're strong (taste, catching a wrong-statement formalization, challenging
  a calibration tag).

---

## 11. Compounding assets (what makes it accretive across runs)

- **Formalized-lemma library (shared, mathlib-style):** every `PROVEN` lemma lands here, so
  month N is cheaper than month 1 — deeper scaffolding is what "accretive" means.
  - *Coverage decision (mathlib @1f29011, toolchain v4.34.0-rc1):* adequate for statements
    about curve groups and generic-group/DLP lemmas — Weierstrass curves, the proved
    affine group law, division polynomials, finite fields are present. First library
    items, absent upstream: `Finite W.Point` over a finite field, the Hasse bound, a DLP
    definition (`∃ k, k • P = Q`), Gröbner bases as library objects, summation
    polynomials. Intake runs the §7 statement pre-filters and a symbolic-equivalence
    dedup (a positive signal only).
- **Negative-results map (first-class, citable):** "approach X provably fails on prime-field
  curves, here's why" is a durable artifact, not a ledger footnote. A well-mapped landscape
  of what-doesn't-work-and-why saves the next researcher years. Every entry carries the
  ledger record of §4 (hypothesis hash, evidence node, method, result with CI, decision,
  retry predicate, caught_by) plus, for measured negatives, the ladder's result table and
  its A/A null arm; superseded schema generations stay addressable but are inadmissible
  as evidence.

Without these the system accumulates only *within* a run; with them it accumulates across
them.

---

## 12. Where `research-software` fits

It designs none of the above. Its one job: current, code-level truth on the stack before
you wire it — Lean/mathlib, Sage/PARI/Magma, the orchestration framework, Claude Code's
subagent/Task interface. Output: commands/config/gotchas per tool from the latest stable
tag. De-risks the stack; touches no math.

Recorded negative results from the 2026-08 mechanism mining (`research/PROPOSALS.md`
§3, so they are not re-walked): no off-the-shelf content-addressed cache fits (LRU-only
retention, no roots or lineage) — SQLite + BLAKE3 at M0; RaptorQ / fountain codes are real
in the surveyed implementations but have no home before a Tier-3 distributed lane exists
(revisit criterion: shipping distinguished-point tables across unreliable links); none of
frankensqlite / frankengraphdb / frankensearch is a dependency (scale, maturity, license
rider) — their accretive mechanisms are re-implemented from the primary papers and specs
they cite; Temporal / LangGraph are not the orchestrator's state layer; no LLM faithfulness
judge, similarity score, or statistical monitor is a gate.

**Borrowed-mechanism constraint.** The six repositories mined for this plan carry an
"MIT with OpenAI/Anthropic Rider" license whose definition of use includes incorporation
into automated pipelines. Cairn therefore borrows *mechanisms* re-implemented from the
primary paper or spec each brief cites; it never vendors code from, or depends on, those
repositories. Every borrowed mechanism is small (tens to a few hundred lines) and
textbook, so this costs little.

---

## 13. Build order (each milestone gated by a demonstrable property)

- **M0 — the real slice.** Substrate schema (§3) + **one exemplar skill built end-to-end**
  (content-addressed I/O, captured seed, self-test, declared cost profile) + Tier-0 verifier
  + tier gate. *Done when:* it runs one skill on a 40-bit toy curve end to end, and the
  result is a hashed, self-tested, cost-tagged substrate node. Everything else plugs into
  this shape — get it right once.
  - *Exemplar skill:* `toy_curve(bits, seed) → (p, a, b, n, P)` — a random prime `p` of
    `bits` bits, random `(a, b)`, group order via PARI `ellcard` (Shanks–Mestre at these
    sizes; milliseconds below 60 bits), accept if the order is prime (acceptance ≈ c/ln p;
    of the order of 10 / 25 / 130 tries at 30 / 40 / 50 bits), with
    `cardinality(algorithm='all')`-style two-implementation agreement on the order; its
    known-answer corpus is seeded from Sage/PARI doctests; its cost profile is "Tier-0,
    ≈ c·ln p tries".
  - *Tier-0 verifier:* subgroup membership (`n·Q = O`) then `xP == Q`, in a subprocess
    with decimal-string inputs and a one-line result; PARI's generic discrete log can
    loop when no solution exists, so membership precedes any log call.
  - *M0 schema includes:* the §3 key construction and cache bits, the replay grade and
    certificate slot, the §7 derived-tag rule (`justify`) with append-only tag history,
    and a GC roots table. The first gate self-tests (§4) are the verifier's planted
    `xP ≠ Q` fixture and the canonicalizer's known-answer vector.
- **M1 — single track.** Prover + independent skeptic + ladder. *Done when:* a
  deliberately-planted false "advance" is caught every time. Adds the ladder protocol
  (§6) with its A/A null arm, the formalization gate's challenge/solution protocol (§7)
  with its planted-`sorry` and wrong-statement fixtures, the statement pre-filters, and
  the M1 decision on the small-numbers floor (§15 P1).
- **M2 — memory.** Dead-end ledger (refuted-by-hash vs parked) + formalizer + statement-level
  review. *Done when:* a parked branch auto-revives on blocker-clear; a refuted one is never
  re-walked. Adds the ledger preflight and hash-chained log (§3, §4), the terminal-status
  invariant, and the near-duplicate advisory.
- **M3 — orchestrator.** Branch tree + bandit + info-per-dollar allocation + structured
  self-redesign (data, not gates). *Done when:* it reallocates off a stall unaided. Decides
  the allocation mechanics and crash-safe tick shape (§15 P3, P6) against that bar.
- **M4 — scale-out + taste.** Parallel tracks, Librarian gate, problem queue + measured
  selector + human/expert loop, lemma library + negative-results map, foundations-auditor.
  *Done when:* multi-track portfolio runs with ledger + calibration coherent, and the
  selector's calibration is being tracked. Decides the selector audit protocol and the
  Librarian retrieval stack (§15 P2, P7).

**Anti-over-engineering:** the remaining real gaps are the ones you can't see from the
whiteboard — they appear on contact with a running system. Build M0 before adding another
design layer; a running 40-bit slice will reveal more than more architecture will.

**Engineering tracking.** The harness engineering (M0–M4) is converted to beads with
dependency edges (`/beads-workflow`, `/beads-br`, `/beads-bv`) and closed under
`/beads-compliance-and-completion-verification`; the research tree itself is never
pre-decomposed into beads — it is built and rewritten at runtime by the orchestrator.

---

## 14. Honest expected outcomes

This can plausibly produce **real, publishable increments on open subproblems** — an LFD
bound, a low-Hamming-weight result, a clean negative result, a rigorous partial analysis.
Your specific 254-bit curve almost certainly **stays standing**, because only a general
algorithmic breakthrough moves it and the field's consensus is that such a breakthrough may
not exist. That sentence is load-bearing: a harness that can't tell you "this stands" is one
that will eventually tell you what you want to hear.

---

## 15. Decisions deferred to a prototype (validity established; usefulness is the question)

Each item names the milestone that decides it and what evidence decides it. None of them
touches §0; each is a mechanism that may be added to a mutable layer if the prototype
shows it binds.

- **P1 · Quantitative floor for the small-numbers gate (M1).** A pre-registered betting
  e-process on sampled instances: the Experimentalist declares a sampling distribution
  `D` over the family, `ε`, `α` and a seed before sampling (all hashed into the claim, so
  a new `D` is a new claim and the orchestrator cannot tune `D` toward clean cases), and
  accumulates `E_t = ∏(1 − λ_t(X_t − ε))`, `λ_t ∈ [0, 1/(1−ε)]`, against H₀ "P fails with
  probability ≥ ε under D"; Tier-2 spend on *proving* the conjecture requires `E ≥ 1/α`.
  It is about `D`, never the family; it never promotes a tag; `log₁₀E` is a numeric
  attribute, not a sub-grade. *Decides:* whether, at honest `ε` (hundreds to thousands of
  clean cases), the floor ever changes a decision the counterexample hunt would not
  already make, on planted-false conjectures. If it never binds, it is dropped.
- **P2 · Selector audit as a calibration test martingale (M4).** Panel greenlight
  probability `q_t` vs gate-adjudicated outcome `Y_t`; `M_t = ∏(1 + λ_t(Y_t − q_t))` is a
  test martingale under "calibrated"; with outcome lag the stopping rule needs the lagged
  correction. *Decides:* power at realistic greenlight volume; it is a monitor plus a
  confidence sequence on mean Brier difference, never a swap trigger on its own.
- **P3 · Orchestrator mechanics (M3).** (i) The forced pivot as a periodic, mechanical
  reset that kills the worst half of branches regardless of agent opinion; (ii) reward
  computed only from gate outcomes, with a relative-improvement baseline and a
  cost-aware blend as the nearest prior for info-per-dollar; (iii) one tick = one short
  idempotent step sequence with its RNG draws stored, so a crash resumes from the last
  step (a tick table in SQLite; not a workflow server). *Decides:* M3's bar,
  "reallocates off a stall unaided"; branch-level bandits are unvalidated in the
  literature, so the bar, not the prior art, decides.
- **P4 · Operational alarms (M1–M2).** A split-conformal anomaly flag on ladder and
  self-test measurements (order-statistic threshold returning +∞ when the sample is too
  small rather than clamping) and a one-sided bounded-mean e-process on
  `log(measured/declared cost)`. Strategy-layer alarms only. *Decides:* whether either
  fires on anything the ladder misses.
- **P5 · Conformal surprise per claim class as an extra scrutiny trigger (M2).** A claimed
  effect in the top-α of historical claims of its class raises scrutiny; it can never
  lower it. *Decides:* whether it adds anything beyond "bigger claim ⇒ more scrutiny".
- **P6 · Exact-dispatch replay receipt for the orchestrator's own concurrency (M3).** A
  sealed, config-bound record of every dispatch with typed mismatch errors on replay; only
  needed if the orchestrator is itself concurrent.
- **P7 · Librarian retrieval stack and off-policy evaluation (M4).** Hybrid BM25 + one
  embedding model fused by RRF (k ≈ 10; never two ensembled embedders), conformal
  retrieval depth as an advisory budget; IPS/DR off-policy evaluation of a proposed
  allocation policy from logged outcomes and propensities before switching.

---

## 16. Evidence, provenance, and operator defaults

- **Evidence.** `research/PROPOSALS.md` holds the rationale and evidence tag for every
  mechanism above (PROVEN-in-source / STRONG-EMPIRICAL / CONJECTURE / SPECULATION, with
  file:line or paper-section citations); `research/briefs/` holds the per-source deep
  dives; `research/grounding/` holds verified stack facts. A reviewer who can read the
  repository should check a mechanism's evidence there before proposing to remove or
  replace it.
- **Operator defaults (challengeable with evidence, otherwise standing):** the name
  *Cairn*; Sage/PARI as the Tier-0/1 arithmetic backend; the M0 exemplar skill is the
  toy-curve generator; SQLite + BLAKE3 as the M0 store; Lean 4 + mathlib as the
  formalization stack.
- **Invariants (not revisable by review):** §0, the gate layer's existence and immutability,
  the calibration taxonomy, the no-go checklist, the ladder, the verifier, and the honest
  baseline of §14 and `HANDOFF.md`. A proposed change that weakens any of them is flagged
  and rejected, not integrated.
