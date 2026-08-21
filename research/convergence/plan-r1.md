# Cairn — Autonomous Math-Research Harness: Architecture & Implementation Plan (v3)

*A system for open-ended research on hard problems (motivating instance: ECDLP, where an
attack is one possible outcome and a rigorous negative result, bound or reduction is a
first-class success), built so it never stops researching and never fabricates, redesigns
its own search tree without ever redesigning what counts as truth, and spends compute
cheap-before-expensive with a human supplying taste where models are weakest.*

*v3 integrates the mechanism review in `research/PROPOSALS.md` (evidence in
`research/briefs/`) and the executed stack probes in `research/grounding/`; the v2 text it
extends is frozen at `research/PLAN-v2-frozen.md`.*

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
  profile or a tolerance. Every corpus declares its origin, `corpus_origin ∈
  {upstream_vendored, independent_oracle, randomized_postcondition, author_supplied}`; a
  corpus supplied only by the worker that authored the skill is not a self-test, and
  `author_supplied` alone caps the skill's results at CONJECTURE — STRONG-EMPIRICAL needs
  an upstream corpus, an independent implementation under the axis rule below, or a
  postcondition or metamorphic relation checked on inputs drawn from a seed committed
  *after* the implementation revision is content-addressed. Tier-0 arithmetic skills verify
  their own answer before returning (the randomized postcondition; Sage's `discrete_log`
  checks `base^res == a` before it returns). Where a cross-check is claimed the skill
  declares its axis — `implementation` (distinct codebases) or `algorithm` (distinct
  methods in one codebase) — and the input range over which that axis is independent;
  outside that range it declares no cross-check and its result is capped accordingly. Two
  builds of one library (`gp` and `cypari2` both wrap libpari) are one implementation, and
  a cross-check that has never disagreed is reported as untested, not as passing. On
  disagreement the skill returns `status = DISAGREE` (not OK, so never cached), writes both
  transcripts and digests to a substrate node, and the caller must park or refute; a silent
  retry with a third tool is forbidden. *Why:* the known-answer corpus is the self-test
  only when its author could not tune it; the floor keeps a skill from quietly regressing;
  the certificate makes "which implementation produced this" a checkable fact rather than
  a label; and a cross-check that cannot disagree is a silent-fail-open gate at the tier
  where nearly every refutation lives.
- **Granularity rule:** grain a skill at *"a capability with a stable interface, a
  self-test, and a declared cost profile" (§5)* — no finer. Too fine and the orchestrator
  burns its budget gluing skills; too coarse and they stop being reusable.

---

## 3. Content-addressed substrate (provenance as a storage property)

- **Every recipe is hashed by `(skill@version, inputs-by-hash, seed, tool-versions,
  container-digest, salt)`.** Provenance stops being an audit you run afterward and becomes
  how results are stored. A result not in the substrate does not exist to the claims DB.
  The recipe key names a requested computation, never a mutable result slot: every launch
  appends an *attempt* `{recipe key, attempt id, output-manifest hash, execution receipt,
  status, replay grade, verifier result}`, and a cached value is served only from a
  verified attempt. *Why:* two attempts at one recipe that disagree are the evidence of
  non-reproducibility; a slot that is overwritten destroys exactly that evidence.
  - *Key construction:* the key is BLAKE3-256 over a canonical, typed, domain-separated
    encoding of that tuple (fields in fixed order, sorted maps and sets, length-prefixed
    variable-length fields, no unknown fields, `(hash, size)` digests for inputs),
    enforced at write time and covered by a known-answer test vector. Two logically equal
    recipes that hash differently are a canonicalizer bug, never a feature. *Why:*
    REFUTED-by-hash (below) is exactly as sound as the canonicalizer; a key computed from
    non-canonical bytes silently under-reports dead ends.
  - *Cache bits on every node:* `do_not_cache` (never memoize), `skip_cache_lookup` (run
    even if cached and record a fresh attempt — never overwrite; the Skeptic's re-runs
    always set it), `status ≠ OK ⇒ never cached` (a failure is a record, not a memo), and
    the `salt` key field that moves a whole class of results into a fresh namespace when a
    tool version is found faulty. For a `Replayable` recipe, two successful attempts with
    different output manifests mark the recipe non-reproducible and inadmissible, both
    attempts kept and rooted; for a `Verifiable` recipe each witness is its own attempt and
    must pass its verifier. A cached result is served only if every blob it references is
    present; otherwise it is recomputed. *Why:* a cache hit must never stand in for a gate
    pass, and a poisoned class must be disownable without rewriting history.
- **Dead-ends become structural, not memory-dependent.** When the orchestrator proposes a
  branch whose *hypothesis key* matches a `REFUTED` ledger entry, the system recognizes it
  instantly — same hypothesis, same key, already dead — with no agent needing to *remember*
  that two approaches are secretly the same. This is what gives the ledger teeth.
  - *Hypothesis key:* BLAKE3-256, under its own domain tag and with the same canonicalizer
    rules and known-answer vector as the recipe key, over a typed hypothesis object
    `{target family, claimed property or cost model (exponent, constant, crossover — or the
    claim statement hash of §4), method identity (skill@version and parameters, or the
    statement hash of the approach), declared parameter ranges, declared sampling
    distribution D where one exists}`. Per-run seeds and ladder instances are excluded, so
    two honest attempts at one hypothesis collide; free-text fields are excluded, so the
    key is about structure — paraphrase is the near-duplicate advisory's job (§4). *Why:*
    the recipe key carries the seed and can never match across the ladder's fresh
    instances; a ledger keyed on it would have no teeth.
- **Versioning keeps history honest.** Improve a skill and old results keep their
  old-version tag rather than being silently corrupted; the tree redesigns without
  rewriting the past.
- **Replayable ≠ verifiable.** Deterministic work (a Sage computation) is bit-reproducible.
  Nondeterministic/expensive work (distributed rho) is not — store a **succinct
  certificate cheap to check** (the found relation, seed, walk definition) instead of a
  full replay. Same move as verify-before-submit: check the answer, don't redo the search.
  - *Replay grades:* every node carries `replay ∈ {Replayable (bit-identical re-run),
    Verifiable (a witness checked by a deterministic verifier), AuditOnly (logs only)}`,
    strongest first. The grade can only be weakened, and `AuditOnly` is inadmissible as
    evidence.
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
    rooted, as evidence of non-reproducibility and the node is marked inadmissible. The
    re-run policy is fixed by grade and tier and budgeted before launch: `Verifiable` ⇒
    the witness is always checked; `Replayable` at Tier 0/1 ⇒ always re-run; `Replayable`
    at Tier 2/3 ⇒ re-run at the moment a promotion past CONJECTURE is sought (the
    promotion waits on it), otherwise sampled by the foundations auditor (§7) with the
    claim's tag capped at CONJECTURE meanwhile. *Why:* an unconditional re-run doubles the
    cost of exactly what the tier system rations; the cap keeps a cheaper policy from
    becoming a silent promotion.
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
  (proven dead → permanent blacklist, recognized by hypothesis key §3) vs `PARKED`
  (blocked-not-dead,
  tagged with blocker → auto-revived when blocker clears); **claims DB** (mandatory
  calibration tag §7, pointer to evidence node); substrate §3 is the reproducibility store.
  - *Claim identity:* a claim is an immutable, content-addressed **claim statement node**
    `{claim id, version, informal statement, formal statement (the Challenge source, when
    one exists), scope and model assumptions, quantities and units, source-claim hash,
    supersedes?}`, written when the claim is opened — by the Reframer, the Prover or the
    human, before any proof or measurement — and never edited: a change to any semantic
    field is a new version with an explicit `supersedes` edge, evidence attached to a
    superseded version does not transfer, and every tag, review verdict, dispute and
    `justify` result names the exact statement hash. *Why:* a tag is only as meaningful as
    the identity of the thing tagged; Lean proves an exact declaration, and the words
    around it must not be free to drift.
  - *Ledger preflight:* before any branch is funded the ledger answers `Allowed | Blocked
    | RequiresNullControl`. `Blocked` = the hypothesis key (§3) matches a REFUTED entry
    whose retry predicate is unmet; `Allowed` = no match, or a match whose retry predicate
    is met, in which case the new branch records the evidence that met it;
    `RequiresNullControl` = a prior refutation rests on a measurement taken without a null
    control and must be re-measured first. Every REFUTED/PARKED entry carries
    `{hypothesis key, refutation_kind ∈ {formal (a machine-checked negation or a §8
    no-go), measured (a ladder or counterexample-hunt result on a declared family, sizes
    and model), implementation (a skill or tool fault, disowned by salt)}, evidence node,
    method, result (+CI where measured), decision, retry predicate, caught_by}`. A
    measured refutation reaches exactly the hypothesis object it was measured on, because
    that object is what was hashed; a broader blacklist needs a formal entry. A
    near-duplicate signal (a 64-bit SimHash over the hypothesis text; no embedding model
    before the Librarian's retrieval stack exists, §15 P7) is advisory only and never sets
    a status: before M4 it routes the proposal to the human, or parks it with blocker
    `near_dup_review`; from M4 it routes to the Librarian, who must state the difference
    in writing before funding. *Why:* "REFUTED is permanent unless the retry predicate is
    met" has to be a query the orchestrator cannot skip, and similarity must never be
    allowed to edit the ledger.
  - *Terminal-status invariant:* every opened branch and every opened claim is a linear
    obligation that must reach a terminal status (refuted / parked / promoted /
    withdrawn). A worker that exits leaving one open produces a `Leaked` record that is
    counted and escalated — fail-fast in tests, logged and escalated in production — and
    is never silently dropped. Withdrawal is terminal and reason-bearing; it erases no gate
    outcome already recorded against the statement hash, and re-opening the same statement
    hash is a re-walk the preflight sees like any other.
- **Orchestrator (mutable brain):** bandit allocation over active branches (fund yield,
  park stalls, revive parked, force periodic pivots so it can't rabbit-hole); self-redesign
  = editing *data* (tree/prompts/subproblems), never gates; cannot mark `proven`, cannot
  bypass a gate. A pivot or a stall never writes REFUTED: it writes PARKED with a blocker
  `∈ {low_yield_pivot, budget_preempt, human_park}` that clears under a stated predicate
  (an epoch count or a budget threshold) and auto-revives like any other blocker. *Why:* a
  yield-based kill is a strategy decision, not evidence of deadness, and REFUTED is
  evidence-only. Allocation mechanics and crash-safe ticks are decided at M3 (§15 P3).
- **Workers (Research-Mode prompt = template):** Librarian (lit-grounding: "tried before /
  why it failed" before any new attack), Reframer (falsifiable subproblems only),
  Experimentalist (small-case → conjecture → counterexample hunt), Prover, Formalizer,
  Skeptic (independent §7). Every worker is a fresh-context agent dispatched by the harness
  as its own top-level query — never composed by a parent model — whose prompt is exactly
  the nodes it is handed, whose tool allow-list and substrate handle are named in its
  dispatch record, and in whose context no gate rubric or detection logic is reachable.
  *Why:* context isolation is a property of the dispatch, not of the model; a parent model
  that composes the prompt is the first thing to fail under pressure (§1), and a worker
  with a general file read can open what its context hides.
- **Gate layer (mechanical, immutable):** submission verifier (`xP==Q` subprocess or no
  submit, ever) · small-scale ladder §6 · no-go checklist §8 · formalization gate §7 ·
  reproducibility gate (no substrate node = inadmissible; §3 re-run) · proportional-scrutiny
  router §7 · tier gate §5.
  - *Gate discipline:* every gate ships a planted-failure self-test (a fixture that must
    FAIL and one that must PASS) run before the gate itself; gates run from a declarative
    plan with expected exit codes and ordered scopes, where an earlier failure blocks
    later ones and records why; invalid or missing gate config fails closed; a waiver is
    explicit, attributed, reason-bearing and expiring, issued only by a human (the
    orchestrator may request one, never grant one), and a waived check never counts as
    satisfied: the admission gates (verifier, ladder, no-go, formalization,
    reproducibility, proportional scrutiny, tier) are non-waivable — a failed, absent or
    waived admission check yields `inadmissible` for promotion, submission and
    higher-tier spend, a waiver may only let an explicitly operational check continue as
    `AuditOnly` output, and each gate's self-test includes a fixture proving that a waiver
    cannot advance a claim or a tier; a green result whose provenance is weaker than
    required (dry run, missing raw output, stale tool digest) cannot strengthen a claim.
    The gate plan, the no-go set, the non-goal sets of skill corpora, the waiver registry,
    the ladder plan (sizes, trial counts, fit and hold-out split) and every worker tool
    allow-list form the **gate bundle**: a content-addressed bundle held in a separate
    store the orchestrator process opens read-only (a separate SQLite file at M0), whose
    hash is pinned at deployment and recorded in every gate-run record; a gate whose bundle
    hash differs from the pin fails closed. *Why:* a gate that silently fails open is worse
    than no gate — it manufactures the appearance of enforcement; "outside the
    orchestrator's write path" is checkable only when the boundary is a store the
    orchestrator cannot write and a hash the ledger shows. Every documented way a prior
    autonomous research system fabricated or gamed (editing its own time limit,
    hallucinating an ablation table, overfitting a single evaluator input, removing the
    instrumentation that detected it) maps onto one of these gates; the discipline is
    what keeps them from being dissolved by the worker they gate.

---

## 5. Compute tiers & allocation

Tier the whole surface; each tier's admission ticket is a result from the tier below.

- **Tier 0 — instant (ms–s):** typechecks, `xP==Q`, small-field arithmetic, "does the
  claim even cohere." Nearly every refutation and orchestration decision lives here. Free;
  run constantly.
- **Tier 1 — one core, minutes:** toy DLPs 30–50 bit, small Gröbner bases, a Lean compile,
  bounded counterexample sweeps. **The research lives here.** The ladder's distribution
  rungs (§6, ≤ 50 bits) are Tier-1; its 60-bit rung is tiered by its own declared cost
  profile. Fail here → never see another core.
- **Tier 2 — many cores, hours:** larger linear algebra, rho up to ≈ 90 bits for
  *validation* (the ceiling is arithmetic: at ≈ 0.11 µs per iteration, 0.886√n costs ≈ 30
  core-hours at 80 bits, ≈ 10³ at 90 and ≈ 3×10⁴ at 100), big families, substantial
  formalization. Entered only holding the Tier-1 ticket defined below. A declared cost
  profile above ≈ 10³ core-hours is a Tier-3 request whatever the skill is called. *Why:*
  a 100-bit run admitted as Tier 2 skips the one tier that demands a payoff justification
  and a certificate plan, and it is exactly the class that cannot be bit-replayed.
- **Tier 3 — cluster, days:** record-scale. Almost nothing reaches it; reaching it requires
  an explicit predicted-cost-vs-payoff justification, a certificate verification plan
  (§3 — you can't bit-replay it) and the expert sign-off of §10.

**Mechanism:** every skill declares its **cost profile** (complexity in inputs, expected
tier) as part of its typed interface, so the orchestrator *predicts* spend before launch
and the tier gate enforces cheap-before-expensive automatically. A spawned worker's budget
is the meet of its parent's remaining budget and the skill's declared profile; a retry or
restart is launched only if the remaining budget can afford it. **Allocation currency is
expected information per compute-dollar**, not raw yield — a cheap experiment that halves a
conjecture's probability outranks an expensive one that nudges a bound; until M3 decides
its mechanics (§15 P3) it is implemented as gate-outcome reward per measured cost, and no
model probability, e-value, posterior or similarity term ever enters it. Compute is a
tracked, finite resource flowing through the DAG exactly like claims. Measured cost is
compared against the declared profile; a persistent mismatch is a strategy-layer alarm
(§15 P4), never a gate.

**Tier gate predicate.** The gate reads three things and nothing else: the skill's declared
cost profile, the spawning budget (the meet above), and the branch's *ticket* — the most
recent admissible substrate node (status OK, replay grade ≥ Verifiable,
reproducibility-checked under the §3 policy) produced under the same branch at the tier
below. A launch is refused when the declared tier exceeds the ticket's tier by more than
one, when the declared cost exceeds the remaining budget, or when the required ticket is
absent: for Tier 2 on an algorithmic claim the ticket is a ladder result table with
verdict KEEP (§6); for Tier 2 on a conjecture it is the counterexample-hunt record of §7
(plus the P1 floor, if adopted); Tier 3 adds the justification, certificate plan and
sign-off named above. A refusal is a `TierRefused` record the ledger keeps, not an
exception the orchestrator can catch and retry around; a branch flagged by §8 holds no
ticket above Tier 1. *Why:* "each tier's admission ticket is a result from the tier below"
is a gate only if the ticket is a named node the gate can read.

---

## 6. The small-scale ladder (top anti-fabrication device)

Any claimed *algorithmic* advance must, mechanically, before it earns attention at full
size: run end-to-end on prime-order toy curves (~30/40/50/60 bit), actually recover `x`
(`xP==Q`), and show measured cost matching its *pre-registered* cost model on the sizes
measured. A "subexponential attack" that can't beat baby-step-giant-step at 50 bits is
refuted on the spot. Cheap, mechanical, near-impossible to fake; kills the dominant failure
mode (proof-shaped text that's subtly wrong). Finite sizes test a declared model; they do
not establish an asymptotic — a ladder pass is evidence for the model on the sizes measured
(at most STRONG-EMPIRICAL, §7), and an asymptotic claim as a theorem goes through the
formalization gate.

**Protocol.** (0) The claim pre-registers its cost model — exponent, constant or crossover,
and memory — in its hypothesis object (§3) before any rung runs; the ladder tests that
model and never a curve fitted afterward. (1) The ladder generates its own instances: a
fresh random prime-order curve and random `(P, Q)` per run, at each size, from a
gate-owned instance-maker whose entropy the worker never sees before committing its method
— never a fixed instance the worker has seen (the documented exploit class for automated
evaluators is overfitting a fixed input). (2) It gates on distributions, not runs: at the
30/40/50-bit rungs at least 10² independent trials per size (for rho the standard
deviation is ≈0.5× the mean, so a single run calibrates nothing), the sorted-distribution
shape compared to the claimed model, and an A/A null arm — the baseline run against itself
in the same harness, same trial count, same instance stream — whose CI radius sets the
decision band. The band is always a ratio against the **best generic baseline the harness
ships, measured in the same harness on the same instances** — plain rho (≈ 1.25√n ops,
O(1) memory), never BSGS — and a speedup is KEPT only if the whole claim CI clears
`1 + 2·radius` (floor 1%) on group operations *and* memory stays inside the same band;
otherwise INCONCLUSIVE or REJECT. (2b) The 60-bit rung is the completion-and-extrapolation
rung: the model fitted on the ≤ 50-bit rungs must predict the measured 60-bit mean inside
the band, and the method must complete and recover `x` on at least 10 fresh instances; the
fit-on / hold-out split is fixed in the ladder plan (gate bundle, §4), never chosen by the
worker, and a clean in-sample fit that misses out of sample is REJECT. A 60-bit generic
trial is ≈ 1.3×10⁹ group ops (minutes in compiled code, a quarter hour interpreted), so a
full 10²-trial distribution check at 60 bits is Tier-2 work by its own declared profile,
not Tier-1, and runs only when the tier gate grants that budget. (3) It reports group
operations against `√n`, never seconds. (4) Two thresholds. *Refutation floor:* at 50 bits
BSGS ≈ 1.5√n ops with ≈ 3×10⁷ table entries; failing to beat it (~5×10⁷ group ops, under
1 GB) refutes on the spot, and the method must *complete* at 60 bits, where BSGS needs 2³⁰
entries. *Acceptance bar:* the KEEP band above, against rho (≈ 1.25√n ≈ 4×10⁷ ops at 50
bits). The ≤ 50-bit figures are STRONG-EMPIRICAL; the 60-bit figures carry the CONJECTURE
tag their source assigns them. (5) The result table (size, trials, mean and sd of ops,
memory, success rate, fit to the pre-registered model, out-of-sample prediction and its
band) is the ladder's artifact, the Tier-2 ticket (§5) when its verdict is KEEP, and the
template for a negative-results entry (§11). *Why two thresholds:* BSGS is the right floor
because a method that cannot beat a table lookup at 50 bits is not an advance, and the
wrong bar because a method costing 4.9×10⁷ ops and 900 MB would "beat BSGS" while being
worse than plain rho on both axes.

---

## 7. Epistemic mechanics (humility made mechanical)

- **Calibration taxonomy (mandatory per claim):** `PROVEN` (formalized) · `STRONG-EMPIRICAL`
  (ladder + repro node) · `CONJECTURE` · `SPECULATION`. No green Lean check → not `PROVEN`.
  - **"Green Lean" is the challenge/solution protocol.** The gate *compiles* the Challenge
    module from the claim statement node (§4) with a gate-side renderer and pinned
    prelude, both inside the gate bundle and outside every worker's write path; the
    Formalizer never creates or edits Challenge text and submits a Solution module that
    names the Challenge's statement hash — a Solution naming any other hash fails closed
    before kernel replay. The statement hash is computed over what the comparator
    compares (the theorem's `ConstantVal` and the full `ConstantInfo` of every constant in
    its transitive closure), never over raw export bytes, which carry position-dependent
    names. The gate (i) rebuilds in a sandbox under the pinned `lean-toolchain` and
    `lake-manifest` mathlib revision recorded in the artifact, (ii) kernel-replays the
    result (`leanchecker --fresh`, the checker shipped inside the toolchain; comparator
    with an external kernel at the gold tier, which needs a Linux `landrun` sandbox — the
    macOS fallback runs unsandboxed and is development-only), (iii) requires `#print axioms`
    ⊆ {`propext`, `Classical.choice`, `Quot.sound`} — which rejects `sorryAx`, the
    per-computation axioms of `decide +native` / `bv_decide`, and any custom axiom — and
    (iv) requires the Challenge and Solution theorem statements to be identical over the
    statement's transitive constant closure, so a redefined constant anywhere under the
    statement fails the check. "No error messages" or an empty `sorries` list is never a
    PROVEN criterion (both have leaked `sorry`/`admit` in published systems). A REFUTED
    ledger entry may carry a machine-matched proof of the Challenge's *negation*. *Why:*
    this mechanizes "the thing proved is the thing stated" and "the statement was fixed
    before the proof"; "the Challenge says what we mean" is the human/Skeptic half below.
  - **The tag is derived, never set.** Each evidence kind has a maximum class it may
    justify: green Lean via the protocol above → PROVEN; ladder + repro node →
    STRONG-EMPIRICAL; sampled or statistical evidence → at most STRONG-EMPIRICAL on its
    declared population; a Lean proof about a *model* of the system → at most CONJECTURE.
    A claim version's tag = the strongest class some evidence node justifies via
    `justify(evidence, statement hash)`, which checks that the evidence's declared target,
    assumptions and population cover that exact statement and returns a typed
    justification or a lattice violation, never a boolean; the tag is a derived column the
    gate layer computes at write time, and no worker or orchestrator writes it. A weaker
    class may *inform* a stronger claim; it may never *justify* it. The foundations
    auditor's core query is the transitive form: no claim, of any class, may carry a
    `justified_by` edge at any depth to a strictly weaker premise, and a failed
    re-verification downgrades the node *and* re-derives every claim transitively
    justified by it.
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
    derive `False` from the hypotheses (certified vacuous ⇒ reject); linters for some forms
    of the `∃ x, P x → Q` trap (binder-predicate and conjunction-nested forms pass them
    silently, so the Skeptic's checklist still carries that item), stubs and new axioms; a
    bounded prove/disprove attempt with a weak prover (trivially provable or disprovable ⇒
    flag); a blind round-trip
    informalization diffed against the source claim (divergence ⇒ flag). The Skeptic's
    rubric is the quantifier-order / strict-vs-non-strict / implication-direction /
    domain-and-boundary checklist (`ZMod 0`, `x/0`, `sInf ∅`, impossible hypotheses). The
    human verdict remains the gate.
- **Independent skeptic:** sees only the *statement*, never the prover's reasoning; rewarded
  solely for gaps/counterexamples. If it reads the proof it just agrees — independence is
  the whole value.
  - *By construction, at both layers.* Context: the skeptic is dispatched by the harness
    as its own top-level query whose entire prompt is the statement node, with inherited
    settings sources disabled — never composed by a parent model. Capability: an explicit
    tool allow-list for counterexample search, no general file read, no shell, and a
    substrate handle scoped to the statement node's closure, so no prover output, panel
    feedback or gate rubric is reachable. Both are gate-bundle config (§4), and the
    dispatch record names the allow-list it ran under, so a widened one is visible in the
    ledger. Its re-runs of any experiment set `skip_cache_lookup` (§3). *Why:* context
    isolation is not filesystem isolation — the cheapest way to find a gap is to read the
    proof, and a worker with a file-read tool over the substrate can.
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
  fraction `f` has probability below `2^−bits`; `f` and `bits` are named in the gate
  bundle (M0: `f = 0.01`, `bits = 20`), the bound is applied per tier stratum so that
  cheap Tier-0/1 nodes cannot absorb the whole sample, and within the Tier-2/3 stratum the
  nodes with the largest `justified_by` fan-in are drawn first. The re-run it performs is
  the §3 policy; what it audits is every claim's evidence, not a report.

---

## 8. No-go checklist (auto-flag tripwire)

Any proposed attack on the target must state how it evades all three or be flagged
almost-certainly-broken. The gate is mechanical in the presence dimension — a missing or
empty declaration is an automatic flag — and the flag has a consumer: the
proportional-scrutiny router (§7) routes a flagged attack to the top scrutiny class and
the tier gate (§5) grants it no ticket above Tier 1 until the declaration exists and has
been reviewed; the *content* of a declared evasion is reviewed by the Skeptic and the
human, never by this gate alone. The three: (1) **Shoup √n** — must exploit named
curve-specific structure, not generic ops; (2) **isogeny invariance** — order & embedding
degree are invariant, walking
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
  expert signing off on expensive, high-commitment calls**. When no human session is open,
  a gate input that requires a human (expert sign-off, a statement-review verdict, a
  waiver) is absent and the gate blocks: the claim waits at its pre-review tag and
  surfaces on the human queue; absence never defaults to pass. Whether Tier-2 spend also
  requires an open operator session is an operator knob in the gate bundle, not a default
  this plan sets.
- **The selector is itself audited.** Problem-selection is a *pluggable, measured* component:
  track whether greenlit problems panned out, score its calibration, and swap it (single
  strong model / debate / cheap heuristic) if that beats the panel on record. Taste is held
  to the system's own standard. "Panned out" is adjudicated by a gate, never by the
  selector; the measurement protocol (a calibration test martingale on greenlight
  probabilities, with the outcome-lag caveat) is decided at M4 (§15 P2); the swap itself
  is a human decision informed by that monitor, never an automatic trigger, because the
  selector is the taste component and the human is the taste anchor.
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
  ledger record of §4 (hypothesis key, refutation kind, evidence node, method, result with
  CI, decision, retry predicate, caught_by) plus, for measured negatives, the ladder's
  result table and
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
into automated pipelines. Cairn's standing policy — an operator ruling recorded here, not
a conclusion derived from the license text — is to borrow *mechanisms* re-implemented from
the primary paper or spec each brief cites and never to vendor code from, or depend on,
those repositories. Every borrowed mechanism is small (tens to a few hundred lines) and
textbook, so this costs little.

---

## 13. Build order (each milestone gated by a demonstrable property)

- **M0 — the real slice.** Substrate schema (§3) + **one exemplar skill built end-to-end**
  (content-addressed I/O, captured seed, self-test, declared cost profile) + Tier-0 verifier
  + tier gate. M0 begins by executing the stack facts it stands on and recording them, with
  their tags, in `research/grounding/` (§16). *Done when:* it runs the exemplar skill on a
  40-bit toy curve; a deterministic M0 fixture (an integration fixture, not a second
  research skill) derives `x` and `Q = xP` from that output; the subprocess verifier
  accepts that pair, rejects a one-coordinate and a one-scalar negative fixture, and
  classifies a forced backend crash as FAIL; and the generator output, derivation receipt,
  verifier result and gate-run record are hashed, self-tested, cost-tagged substrate nodes.
  Everything else plugs into this shape — get it right once, the verifier included.
  - *Exemplar skill:* `toy_curve(bits, seed) → (p, a, b, n, P)` — a random prime `p` of
    `bits` bits, random `(a, b)`, group order via PARI `ellcard` (Shanks–Mestre through
    50 bits, milliseconds per curve; at 60 bits `ellcard` is SEA at ≈ 75 ms per curve and
    overflows PARI's default stack, so the search uses `ellsea(E, 1)` early-abort with an
    explicit stack ceiling and confirms with `ellcard`), accept if the order is prime
    (acceptance ≈ c/ln p, so expected tries grow like `ln p` with a geometric spread whose
    sd equals its mean; observed draws span 20–220 at 30–50 bits and are not a profile —
    M0 measures the constant over ≥ 50 seeds per size before declaring one), with a
    BSGS-vs-SEA *algorithm* cross-check on the order, valid for `bits ≤ 50` only (at 60
    bits PARI's generic path is SEA and the two agree by construction); a second
    *implementation* needs a non-PARI backend, an M0 install decision and not an
    assumption (§2 axis rule). Its known-answer corpus is seeded from Sage/PARI doctests
    (`corpus_origin = upstream_vendored`); its cost profile is "Tier-0, ≈ c·ln p tries".
  - *Tier-0 verifier:* subgroup membership (`n·Q = O`) then `xP == Q`, in a subprocess
    with decimal-string inputs and a one-line result; PARI's generic discrete log can
    loop when no solution exists, so membership precedes any log call. *Acceptance is
    affirmative, never residual:* the driver validates arity and every field before
    spawning (the backend zero-fills missing arguments), passes an explicit stack ceiling
    (60-bit `ellcard` overflows PARI's default), and accepts only `exit == 0` **and**
    `stdout == "OK"` **and** empty stderr — a zero exit code is not evidence of anything,
    since the backend exits 0 on fatal errors including stack overflow. The gate's
    planted-failure self-test (§4) includes a forced backend crash that must classify FAIL.
  - *M0 schema includes:* the §3 recipe-key construction, attempt records and cache bits,
    the hypothesis key, the replay grade and certificate slot, the claim statement node
    (§4), the §7 derived-tag rule (`justify`) with append-only tag history, a GC roots
    table, and the gate-bundle pin (§4). The first gate self-tests (§4) are the verifier's
    planted `xP ≠ Q` and forced-crash fixtures and the canonicalizer's known-answer
    vectors for both keys.
- **M1 — single track.** Prover + independent skeptic + ladder, with the ladder's baseline
  skills — `rho_dp` (rho with distinguished points and the §3 witness certificate), `bsgs`
  (the refutation floor) and the gate-owned instance-maker — each shipping the §2
  self-test. *Done when:* every fixture in the M1 planted corpus is caught under a cold
  cache (`skip_cache_lookup`), INCONCLUSIVE counting as an escape, and no matched true
  advance is rejected; minimum corpus, ≥ 30 plantings across it: (a) a BSGS-beating claim
  whose ops at 50 bits are ≥ generic rho; (b) a correct-ops claim that fails `xP == Q` on
  a fresh ladder instance; (c) a Lean Solution with `sorryAx` or an extra axiom; (d) a
  Lean Solution proving a strictly weaker statement than the Challenge; (e) a small-numbers
  pattern that dies under the counterexample hunt; (f) a claim seeking STRONG-EMPIRICAL
  with no repro node; (g) statistical evidence offered for PROVEN; (h) a PROVEN claim with
  a weaker premise in its transitive closure; (i) a non-reproducible measurement. Adds the
  ladder protocol (§6) with its pre-registered model, A/A null arm and out-of-sample rung,
  the formalization gate's challenge/solution protocol (§7) with its gate-compiled
  Challenge and planted-`sorry` and wrong-statement fixtures, the statement pre-filters,
  the reproducibility gate's re-run policy (§3), the §7 disagreement protocol, the
  proportional-scrutiny router and the no-go checklist's presence check (§8) with the
  router as its consumer, and the M1 decision on the small-numbers floor (§15 P1).
- **M2 — memory.** Dead-end ledger (refuted-by-hypothesis-key vs parked) + formalizer +
  statement-level review. *Done when:* a parked branch auto-revives on blocker-clear; a
  refuted one is never re-walked. Adds the ledger preflight and hash-chained log (§3, §4),
  the terminal-status invariant, and the near-duplicate advisory routed to the human or to
  a `near_dup_review` park (Librarian routing arrives with the Librarian at M4).
- **M3 — orchestrator.** Branch tree + bandit + info-per-dollar allocation + structured
  self-redesign (data, not gates). *Done when:* on ≥ 20 seeded runs each containing a
  stalled branch — a branch whose gate-outcome yield over the last `k` ticks is
  indistinguishable from zero — funding is withdrawn from it within `m` ticks unaided,
  with `k` and `m` pinned in the M3 test plan. Decides the allocation mechanics and
  crash-safe tick shape (§15 P3, P6) against that bar, including whether a bandit earns
  its place at all.
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
  probability `q_t` vs gate-adjudicated outcome `Y_t`; `M_t = ∏(1 + λ_t(Y_t − q_t))` with
  predictable stakes `λ_t ∈ [−1/(1−q_t), 1/q_t]`, recorded before `Y_t` is observed, is a
  test martingale under "calibrated" (each factor is nonnegative with conditional mean one
  only inside that range); with outcome lag the stopping rule needs the lagged correction,
  and the filtration under which `q_t`, `λ_t` and the adjudication become known is written
  down. *Decides:* power at realistic greenlight volume; it is a monitor plus a confidence
  sequence on mean Brier difference, never a swap trigger on its own.
- **P3 · Orchestrator mechanics (M3).** (i) The forced pivot as a periodic, mechanical
  reset that force-parks the worst half of *active* branches (blocker `low_yield_pivot`,
  §4) regardless of agent opinion — REFUTED stays evidence-only; (ii) reward computed only
  from gate outcomes, with a relative-improvement baseline and a cost-aware blend as the
  nearest prior for info-per-dollar; (iii) one tick = one short idempotent step sequence
  with its RNG draws stored and the source hash of each step in the tick record, so a
  crash resumes from the last step and a recorded output is never replayed for a step
  whose body has changed (a tick table in SQLite; not a workflow server). *Decides:* M3's
  bar; branch-level bandits are unvalidated in the literature, so the bar, not the prior
  art, decides — including whether a priority queue plus forced park and human taste beats
  a bandit, in which case the bandit is dropped.
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
  dives; `research/grounding/` holds stack facts established by executing them on the
  build machine. A reviewer who can read the repository should check a mechanism's
  evidence there before proposing to remove or replace it.
- **Stack facts carry their source's tag.** A fact about a tool (a timing, an exit code,
  an installed backend, a checker's flag) is stated in this plan with the tag its brief or
  probe assigns it, never in the voice of a verified mechanism; a stack fact no probe has
  executed is CONJECTURE until `research/grounding/` records the run. *Why:* inherited
  stack claims are wrong at a meaningful rate when executed (a second implementation that
  is one library twice, a verifier backend that exits 0 on fatal errors, an isolation
  property that is a parent's discipline), and each such claim sits under a gate; a
  harness that tags its own claims less carefully than it requires of its workers has a
  credibility problem on day one.
- **Operator defaults (challengeable with evidence, otherwise standing):** the name
  *Cairn*; Sage/PARI as the Tier-0/1 arithmetic backend; the M0 exemplar skill is the
  toy-curve generator; SQLite + BLAKE3 as the M0 store; Lean 4 + mathlib as the
  formalization stack.
- **Invariants (not revisable by review):** §0, the gate layer's existence and immutability,
  the calibration taxonomy, the no-go checklist, the ladder, the verifier, and the honest
  baseline of §14 and `HANDOFF.md`. A proposed change that weakens any of them is flagged
  and rejected, not integrated.
