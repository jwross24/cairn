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
  profile}` — the interface version names the method a hypothesis is about (§3); the whole
  bundle names the executable that a recipe key, a ladder run and a tier ticket bind (§3,
  §5, §6). Its self-test is (i) a vendored known-answer corpus with a per-case ledger
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
  `author_supplied` alone caps the skill's results at CONJECTURE (a ceiling `justify` reads
  from the revision's self-test record, §7) — STRONG-EMPIRICAL needs
  an upstream corpus, an independent implementation under the axis rule below, or a
  postcondition or metamorphic relation checked on inputs drawn from a seed committed
  *after* the implementation revision is content-addressed. Tier-0 arithmetic skills verify
  their own answer before returning (the randomized postcondition; Sage's `discrete_log_rho`
  checks `base^res == a` before it returns and `discrete_log(verify=True)` re-checks its CRT
  result). Where a cross-check is claimed the skill
  declares its axis — `implementation` (distinct codebases) or `algorithm` (distinct
  methods in one codebase) — and the input range over which that axis is independent;
  outside that range it declares no cross-check and its result is capped accordingly. Two
  builds of one library (`gp` and `cypari2` both wrap libpari) are one implementation, and
  a cross-check that has never disagreed is reported as untested, not as passing. On
  disagreement the skill returns `status = DISAGREE` (not OK, so never cached), writes both
  transcripts and digests to a substrate node, and the caller must park or refute; a silent
  retry with a third tool is forbidden. A self-test failure (a floor miss, a certificate
  mismatch, a double-run divergence — or a ladder trial under §6 that returns `xP ≠ Q` or a
  self-reported count diverging from the gate's, a known-answer failure the corpus missed)
  yanks the implementation revision: the tier gate refuses
  new launches of it, an in-flight attempt completes with status `SKILL_YANKED` (≠ OK: never
  cached, never a ticket, never evidence), the yank record names the fault's reach as a
  predicate over recipe-key fields — by default the whole implementation revision, every
  recipe key naming it; a narrower predicate (an input range where the fault is
  input-dependent, a parameter slice) is installed only by an attributed human ruling
  recorded through the human path (§4) beside the yank, which workers and the orchestrator
  may propose and never
  install — and every attempt inside that reach is disowned (§3), and only an
  attributed new revision with a fresh certificate clears the yank. A revision is launchable
  only once its self-test has passed and its certificate is recorded: the tier gate refuses
  an uncertified revision exactly as it refuses a yanked one, and who may admit a revision
  whose cost profile reaches Tier 2 is an operator ruling the gate bundle records. *Why:* the
  known-answer corpus is the self-test
  only when its author could not tune it; the floor keeps a skill from quietly regressing;
  the certificate makes "which implementation produced this" a checkable fact rather than
  a label; and a cross-check that cannot disagree is a silent-fail-open gate at the tier
  where nearly every refutation lives; a revision that keeps minting OK results after its
  own self-test fails is a gate that fails open; an uncertified revision is a yanked one
  that was never tested; and a yank whose reach the faulting party narrows fails open on
  the slice it left unnamed.
- **Granularity rule:** grain a skill at *"a capability with a stable interface, a
  self-test, and a declared cost profile" (§5)* — no finer. Too fine and the orchestrator
  burns its budget gluing skills; too coarse and they stop being reusable.
- **A skill's language is a property of its contract, not of the harness.** The contract is
  a process boundary — canonical JSON on stdin and stdout — so the identity bundle above
  names the executable whatever wrote it. Python is the reference implementation language
  (§16 operator defaults). A compiled skill (Rust, C, a PARI-native program) is admitted
  under exactly the same self-test, certificate, double-run and yank discipline when a cost
  grade demands it (§16 decision 2): its implementation revision is the hash of its sources
  plus its lockfile, its tool digest is the digest of the static binary that runs, and its
  container digest is the input-addressed environment identity of §16 decision 14. A skill
  whose language differs from its neighbors changes nothing a gate reads. *Why:* a gate that
  binds to a language rather than to an identity hash cannot admit the faster implementation
  the ladder's cost model may require, and a harness that reads language as a proxy for
  trust has a gate that is a label (evidence: `research/briefs/language-and-agent-ergonomics.md` §1).

---

## 3. Content-addressed substrate (provenance as a storage property)

- **Every recipe is hashed by `(skill@version, inputs-by-hash, seed, tool-versions,
  container-digest, salt)`.** Provenance stops being an audit you run afterward and becomes
  how results are stored. A result not in the substrate does not exist to the claims DB.
  The recipe key names a requested computation, never a mutable result slot: every launch
  appends an *attempt* `{recipe key, attempt id, output-manifest hash, execution receipt,
  status, replay grade, verifier result}`, and a cached value is served only from a
  verified attempt. The execution receipt is the harness's own record of the run, written by
  the writer and never by the skill: `{gate-bundle hash, start and end monotonic times, CPU
  seconds (user plus system) over the process tree, wall-clock seconds, peak RSS over the
  process tree, bytes written to the scratch path, exit status, stdout and stderr digests,
  tool digests}`; its readers are the budget ceiling (§5), the ladder's clock and memory
  measurements (§6) and the provenance check of §4 (a dry run, missing raw output or a stale
  tool digest is read from it). *Why:* two attempts at one recipe that disagree are the
  evidence of non-reproducibility; a slot that is overwritten destroys exactly that
  evidence; and a receipt the skill writes about itself is a number from the gated party.
  - *Key construction:* the key is BLAKE3-256 over a canonical, typed, domain-separated
    encoding of that tuple (fields in fixed order, sorted maps and sets, length-prefixed
    variable-length fields, no unknown fields, `(hash, size)` digests for inputs; where no
    container runs, as on the M0 build machine, `container-digest` is the digest of the
    runtime's environment manifest — OS, interpreter and library versions — never an empty
    field; `skill@version` in the recipe key is the hash of the full §2 identity bundle,
    so a changed executable is a different recipe), enforced at write time and covered by a
    known-answer test vector. Two logically equal
    recipes that hash differently are a canonicalizer bug, never a feature. *Why:*
    REFUTED-by-hash (below) is exactly as sound as the canonicalizer; a key computed from
    non-canonical bytes silently under-reports dead ends.
  - *Cache bits on every node:* `do_not_cache` (never memoize; set by a skill whose
    interface declares its output non-memoizable — the gate's instance-maker and nonce
    draws, any sampler without a committed seed — and read by the cache's serve path),
    `skip_cache_lookup` (run
    even if cached and record a fresh attempt — never overwrite; the Skeptic's re-runs,
    the foundations auditor's re-runs (§7) and every reproducibility-gate re-run set it),
    `status ≠ OK ⇒ never cached` (a failure is a record, not a memo), and
    the `salt` key field that moves a whole class of results into a fresh namespace when a
    tool version is found faulty: a yank record (§2) names its reach as a predicate over
    recipe-key fields; every attempt inside the reach gains an append-only `disowned` mark —
    rows and blobs stay, nothing is overwritten — and a disowned node is served from no
    cache, is absent to `justify` (§7), which re-derives every claim transitively justified
    by it, and is no ticket; the class's `salt` is bumped so fresh attempts take fresh keys;
    attempts outside the named reach stand. For a `Replayable` recipe, two successful,
    non-disowned attempts with
    different output manifests mark the recipe non-reproducible and inadmissible, both
    attempts kept and rooted; for a `Verifiable` recipe each witness is its own attempt and
    must pass its verifier. A cached result is served only if every blob it references is
    present; otherwise it is recomputed. *Why:* a cache hit must never stand in for a gate
    pass, a poisoned class must be disownable without rewriting history, and "disowned" must
    be a mark code reads, not a memo about a tool version.
- **Dead-ends become structural, not memory-dependent.** When the orchestrator proposes a
  branch whose *hypothesis key* matches a `REFUTED` ledger entry, the system recognizes it
  instantly — same hypothesis, same key, already dead — with no agent needing to *remember*
  that two approaches are secretly the same. This is what gives the ledger teeth.
  - *Hypothesis key:* BLAKE3-256, under its own domain tag and with the same canonicalizer
    rules and known-answer vector as the recipe key, over a typed hypothesis object
    `{target family, claimed property or cost model (exponent, constant, crossover — or the
    claim statement hash of §4), method identity (the skill named by its §2 *interface
    version* with its canonical parameters — never its implementation revision — or the
    statement hash of the approach), declared parameter ranges, declared sampling
    distribution D where one exists}`. Per-run seeds and ladder instances are excluded, so
    two honest attempts at one hypothesis collide; free-text fields are excluded, so the
    key is about structure — paraphrase is the near-duplicate advisory's job (§4). The
    method identity names the interface version and not the implementation revision because
    the hypothesis is about a method: a measured refutation of it reaches every
    implementation revision and a revision bump cannot mint a clean key; the executable is
    bound elsewhere — the recipe key, the ladder's dispatch record (§6) and every tier
    ticket (§5) name the full identity bundle, so a new implementation revision re-ladders
    before it spends. The
    hypothesis object is an immutable, content-addressed node like the claim statement node
    (§4): written by the worker or human that opens the branch, at branch open, naming the
    claim statement hash where a claim exists; the branch points at it by hash; an amendment
    is a new object with an explicit `supersedes` edge that the ledger preflight (§4)
    follows; and because it is appended to the substrate's append-only record sequence when
    the branch opens (an order the hash-chained log below carries tamper-evidently from
    M2), pre-registration (§6 step 0) is an order of records — the ladder refuses a rung
    whose hypothesis object does not precede the gate's entropy commitment for that run —
    never a statement of intent. *Why:* the recipe key carries the seed and can never match
    across the ladder's fresh instances, so a ledger keyed on it would have no teeth; and
    "tests the model and never a curve fitted afterward" is checkable only if the model's
    commitment is timestamped by something the worker cannot rewrite.
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
    evidence. `Verifiable` is assigned only where the verifier is a gate-bundle object (the
    Tier-0 verifier; the rho witness check below) or a certified skill whose §2 identity
    bundle differs from the witness producer's and whose self-test carries a must-FAIL
    witness; a witness whose only verifier ships in its producer's own revision is graded
    `AuditOnly`. *Why:* a re-check that runs the producer's verifier is a count reported by
    the party being gated (§6), and it is the one ladder-shaped input the other rules leave
    to the producer.
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
    at Tier 2/3 ⇒ re-run at the moment `justify` (§7) would derive a class above
    CONJECTURE from the node (the derivation waits on it), otherwise sampled by the foundations
    auditor (§7) with the
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
    length-prefixed) with compare-and-swap head advancement, re-verifiable from origin; a
    rewritten or reordered record fails verification. Truncation to an earlier valid prefix
    is the one edit a hash chain cannot see, so the chain head is also appended, at every
    gate run, to a checkpoint outside the orchestrator's write authority — in the M0
    deployment shape (the log and its checkpoint are built at M2, §13) a file
    beside the gate-bundle pin (§4), owned by the operator, carrying the append-only flag
    that only its owner can clear, and writable by the orchestrator's process user, a user
    distinct from the operator as the pin already requires, so that process can extend the
    file and can neither truncate it nor clear the flag (that the flag binds against a
    non-owner writer is the stack fact M0 grounds before relying on it, §16; a checkpoint
    the orchestrator's process can truncate is no checkpoint); from M4 a writer the
    substrate's own process cannot truncate — and a log that does not extend every
    checkpointed head (each recorded head is a prefix head of the current chain, so the
    checkpoint's own sequence is monotone along it) fails verification at startup and before
    any promotion, while a checkpoint
    that cannot be reached or extended blocks promotion rather than disabling
    checkpointing; the last head alone is no check, because the process that can extend the
    file can append a forked head after truncating the log behind it, and only the older
    heads it cannot remove expose the fork. *Why:* "the orchestrator may rewrite the tree but
    never REFUTED entries" needs a tamper-evident form, not a convention; the orchestrator's
    model components reach the substrate only through typed appends and hold no raw handle,
    so the checkpoint guards the one path — a raw write — the chain itself cannot.
- **Store:** SQLite (blobs, lineage edges, roots table) keyed by BLAKE3 at M0. Off-the-shelf
  content-addressed caches (REAPI servers, cacache) retain by LRU and have no roots or
  lineage; their *semantics* (canonical keys, cache bits, completeness check, fixed-output
  certificates, `--check` re-runs, GC roots) are adopted, their binaries are not.
  - *Concurrency contract (M0–M4):* one writer connection, in the harness process (WAL mode
    and a busy timeout are stack facts M0 grounds, §16); every worker is a subprocess that
    returns artifacts to that writer and holds no substrate write capability — the scoped
    handle of §4 is read-only; the hash-chained log is advanced only by that writer. M4's
    parallel tracks run under the same contract and its done-when stresses it (§13). *Why:*
    lost attempt rows and interleaved chain heads are the failure a second writer
    introduces, and the remedy is queue depth or a write proxy, never a second database
    (§12).

Skills are the nodes; the substrate is the edges + store. The admissible evidence graph is
one replayable-or-verifiable DAG (`AuditOnly` nodes are kept and are not in it) — which is
the only thing that makes a `STRONG-EMPIRICAL`
tag mean something.

---

## 4. Components

- **State layer:** branch tree (`{id, parent, hypothesis, status∈{active,parked,refuted,
  promoted,withdrawn}, priors, effort, yield, blocker?}`); **dead-end ledger** with `REFUTED`
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
    `justify` result names the exact statement hash. The *claim statement hash* is the
    node's content address and the identity every other object names; where the node
    carries a formal statement the formalization gate derives a second, *formal statement
    hash* when it compiles the Challenge (§7), and its gate-run record binds the two under
    the bundle hash — the Solution names the formal statement hash, everything else names
    the claim statement hash, and a binding absent from the record is a gate that has not
    run. *Why:* a tag is only as meaningful as
    the identity of the thing tagged; Lean proves an exact declaration, and the words
    around it must not be free to drift — and two hashes under one name are a join no
    implementer can write.
  - *Ledger preflight:* before any branch is funded the ledger answers `Allowed | Blocked
    | RequiresNullControl`, and before a branch is opened it also answers `AlreadySettled`.
    `Blocked` = the hypothesis key (§3) matches a REFUTED entry
    whose retry predicate is unmet, or the proposal's declared parameter region contains a
    measured parameter point at which a REFUTED entry records the same method identity
    failing the same cost model (axis-aligned inclusion on numeric fields, equality on
    categorical ones; the measured points are fields of the entry); `Allowed` = no match,
    or a match whose retry predicate is met, in which case the new branch records the
    evidence that met it;
    `RequiresNullControl` = a prior refutation rests on a measurement taken without a null
    control — a field of its evidence node, since a ladder table carries its A/A arm and a
    hunt record KILLED by a verified counterexample needs none — and must be re-measured
    first: the proposal is parked with blocker `null_control_pending`, a gate-owned
    re-measurement of the refuted hypothesis object under the current ladder plan is
    enqueued (on the human queue before M4, on the foundations auditor's queue from M4, never
    with the proposing worker), its table is appended to the entry as a new evidence node,
    and the blocker clears when it lands, after which the preflight re-runs to `Allowed` or
    `Blocked` under the existing rules: a REJECT under the current ladder plan confirms the
    entry, whose evidence carries the null arm from that table on, and the answer is `Blocked`;
    any other verdict is a
    gate-owned measurement that meets the entry's retry predicate — the answer is `Allowed`,
    the new branch records the re-measurement table as the evidence that met it, and the
    original evidence node keeps its rows and gains an append-only `superseded_by` pointer
    to the new table; the entry itself is never rewritten.
    `AlreadySettled` = the proposal opens a new branch on a hypothesis key that a branch
    already holds — an active or parked one — or on a key whose claim statement stands at
    PROVEN or STRONG-EMPIRICAL, whatever the status of the branch that earned it (promoted,
    or withdrawn afterwards: a withdrawal erases no gate outcome, below, so a worker that
    withdraws its branch once the KEEP has landed frees no key), or opens a branch whose
    method identity and claimed cost model equal such a standing holder's and whose declared
    parameter region is contained in the holder's (the axis-aligned inclusion the REFUTED
    reach below uses), a claim the holder's evidence already covers under `justify`'s
    population rule (§7) — and is not a superseding object: it is parked with blocker
    `already_settled`, which clears when a superseding hypothesis object with the attributed
    difference statement the `supersedes_refuted_review` path requires is recorded, when the
    standing claim statement moves to `refuted` (§7), or when the holding branch withdraws
    while its claim statement stands below STRONG-EMPIRICAL; the holding branch's own launches
    never see this answer, and gate-owned re-runs (the Skeptic's, the auditor's, a null-control
    re-measurement) are not branch fundings. Every REFUTED/PARKED entry carries
    `{hypothesis key, refutation_kind ∈ {formal (a machine-checked negation or a §8
    no-go), measured (a ladder or counterexample-hunt result on a declared family, sizes
    and model), implementation (a skill or tool fault — a self-test failure, or a ladder
    trial with `xP ≠ Q` or a diverging self-reported count (§6) — disowned by salt)},
    evidence node,
    method, measured parameter points, result (+CI where measured), decision, retry
    predicate, caught_by}`. A measured refutation reaches the hypothesis object it was
    measured on and every object asserting the same cost model for the same method identity
    over a declared region that contains the measured point — the minimal logical reach of
    the measurement, recorded as fields so that range jitter cannot mint a clean key — and
    nothing broader; a broader blacklist needs a formal entry; an `implementation` entry's
    retry predicate is met by an attributed new certified revision of the faulting skill
    (§2), so it blocks the faulting executable and never the method; a `measured` entry's
    retry predicate is met only by a gate-owned re-measurement of the same hypothesis object
    under the current ladder plan whose verdict is not REJECT — enqueued by the human before
    M4 and by the foundations auditor from M4, never by the proposing worker, the
    `null_control_pending` path below being one instance — and a `formal` entry has none (a
    superseding statement is a new key); the gate that writes an entry writes its retry
    predicate, never the refuted party, because a predicate the refuted party authors is a
    ledger it can unlock. A
    near-duplicate signal (a 64-bit SimHash over the hypothesis text; no embedding model
    before the Librarian's retrieval stack exists, §15 P7) is advisory only and never sets
    a status: before M4 it routes the proposal to the human, or parks it with blocker
    `near_dup_review`; from M4 it routes to the Librarian, who must state the difference
    in writing before funding. A hypothesis object, or the claim statement it names, whose
    `supersedes` chain reaches a version carrying a REFUTED entry with an unmet retry
    predicate is parked with blocker `supersedes_refuted_review` until an attributed written
    statement of which semantic field changed and why the refutation does not reach the new
    version is recorded — by the human before M4, by the Librarian from M4; the refutation
    itself does not transfer, since a measured refutation reaches what was measured, but a
    declared version relation is a structural signal the preflight never ignores. *Why:*
    "REFUTED is permanent unless the retry predicate is met" has to be a query the
    orchestrator cannot skip; similarity must never be allowed to edit the ledger, while
    structure — a measured point, a declared version edge — may route, because structure is
    what the ledger is about; and a refutation without a null arm is a measurement the
    ladder's own standard would not accept, so the party that wants it re-examined must not
    be the party that re-measures it; and REFUTED stops known failures, while a settled
    success re-funded unchanged buys no knowledge and is the cheapest loop a gate-outcome
    reward can find, and a sub-region of a measured success re-laddered mints a KEEP its
    existing table already justifies — the range-jitter loop on the success side.
  - *Prior-art note before Tier 2 (pre-M4):* a hypothesis object that names a claim statement
    carries an attributed `prior_art` note (a human-path record with citations, or "none
    found") before Tier-2 funding; absent, the tier gate refuses Tier 2 as it refuses an
    absent no-go declaration (§8). The human writes the note before M4, matching decision 4
    of §16; from M4 the Librarian writes it. *Why:* an increment is only an increment if the
    combination is unpublished, and §14 promises publishable increments from M1 onward while
    the Librarian arrives at M4.
  - *Terminal-status invariant:* every opened branch and every opened claim is a linear
    obligation that must be resolved — a terminal status (refuted / promoted / withdrawn)
    — or handed off to a park under a typed blocker, which holds the obligation until its
    clearing predicate revives the branch; a park is a hand-off and not a terminal status.
    `promoted` is written by the gate layer when `justify` (§7) first derives STRONG-EMPIRICAL
    or PROVEN for the branch's claim statement, never by a worker or the orchestrator (which
    cannot mark `proven`, below), so the status follows the tag and no party can hold a key
    by declaring success.
    A worker that exits leaving one neither resolved nor handed off produces a `Leaked`
    record that is
    counted and escalated — fail-fast in tests; in production a human-queue item of class
    `leaked` (§10) while the obligation stays with the branch, which remains active for the
    orchestrator's next tick exactly as after a harness-terminated attempt — and
    is never silently dropped. Withdrawal is terminal and reason-bearing, the act of the
    branch's worker or of the human and never of the orchestrator, whose own vocabulary is
    PARKED (§13 M3); it erases no gate
    outcome already recorded against the statement hash, and re-opening the same statement
    hash is a re-walk the preflight sees like any other. A harness-terminated attempt
    (`BUDGET_EXCEEDED`, `SKILL_YANKED`, or `INTERRUPTED` — the status a restart scan gives
    every attempt that was in flight when the harness process died, assigned before any new
    launch, and ≠ OK like the others: never cached, never a ticket, never evidence) is not a
    leak: the obligation stays with the branch,
    which remains active for the orchestrator's next tick to fund within budget or park with
    `budget_preempt`. *Why:* a subprocess that dies with its harness is neither
    a worker exit nor a ceiling, and an attempt row left at a non-terminal status is a slot
    the cache or the tier gate could read as pending forever.
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
  the nodes it is handed (these handed nodes and the subproblem text are the "worker
  prompts" §0 lets the orchestrator rewrite; a role template is bundle config it cannot
  touch), whose tool allow-list and substrate handle are named in its
  dispatch record, and in whose context no detection logic of a gate that judges its output
  is reachable — a role's own fixed procedure (the Skeptic's checklist, §7) ships as a
  read-only, claim-agnostic role template in the gate bundle. The dispatch record names the
  hashes of the nodes handed over, the role-template hash, the allow-list and — where the
  dispatch path exposes the request it emits to the model provider — the hash of those
  request bytes. That a dispatched worker's
  context holds nothing but the nodes it is handed — no settings source, no skill file, no
  working-tree snapshot — is a stack fact the dispatch canary of §13 M1 grounds before the
  dispatch path is trusted and re-grounds on every toolchain or SDK change; the canary is
  decided on the emitted request bytes where they are observable and on the worker's echoed
  context otherwise, an echo that omits a planted token being a regression signal and not a
  proof, and the grounding record names which form ran. *Why:* context
  isolation is a property of the dispatch, not of the model; a parent model
  that composes the prompt is the first thing to fail under pressure (§1), and a worker
  with a general file read can open what its context hides.
- **Gate layer (mechanical, immutable):** submission verifier (`xP==Q` subprocess or no
  submit, ever) · small-scale ladder §6 · no-go checklist §8 · formalization gate §7 ·
  reproducibility gate (no substrate node = inadmissible; §3 re-run) · proportional-scrutiny
  router §7 · tier gate §5.
  The submission verifier's instance is gate-read: a verifier run takes the curve, `n`, `P`
  and `Q` from the claim statement node it is invoked against (or from the ladder's dispatch
  record for a ladder trial), never from the submitter, who supplies `x` alone; its passing
  node records the instance it verified, and a submission whose verifier node names any
  other instance is refused by the egress renderer (§10). *Why:* `xP == Q` on an instance
  the worker chose is a true statement about the wrong problem, and a passing node attached
  to prose about the target is the easy-instance substitution the ladder's instance-maker
  already forbids.
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
    The gate plan, the no-go set, the non-goal sets of skill corpora, the waivable-check set
    (which operational checks a waiver may let continue as `AuditOnly`; a waiver itself is a
    human-path record, below, never a pinned field, since the bundle is pinned at deployment
    and a waiver is issued at runtime),
    the ladder plan (sizes, trial counts, the comparison protocol of §6 with its tolerances,
    the hold-out instance count `m`, the per-rung memory cap, the per-trial patience ceiling,
    the fit and hold-out split), the worker role templates, the budget ceiling multiplier
    (§5), the tier cost boundaries of §5 with their cumulative edges, the formalization
    gate's checker configuration
    (challenge module, theorem and definition names, the permitted-axiom set, external-kernel
    commands) with its `lean-toolchain` and `lake-manifest` pins (§7), the Tier-0 verifier's
    invocation (backend path, stack ceiling, accept predicate; §13), the scrutiny router's
    class predicate (§7), the auditor's `f`, `bits`, critical-set cutoff, cadence and
    per-cycle audit line (§7), the egress renderer and its refusal predicate (§10), every
    worker tool allow-list and the ladder-tested method's allow-list with its scratch path
    (§6) form the **gate bundle**: a
    content-addressed bundle held in a separate
    store the orchestrator process opens read-only (a separate SQLite file at M0), whose
    hash is pinned at deployment and recorded in every gate-run record; a gate whose bundle
    hash differs from the pin fails closed. The pin is a deployment constant held with the
    bundle in an operator-owned location the orchestrator's process user cannot write (a
    file mode at M0), never a substrate row; the orchestrator's model components reach the
    state layer only through typed writes and hold no file handle at all, so a separate
    gate process is not required while every gate run checks the pin — a rewritten bundle
    fails closed whoever rewrote it. *Why:* a gate that silently fails open is worse
    than no gate — it manufactures the appearance of enforcement; "outside the
    orchestrator's write path" is checkable only when the boundary is a store the
    orchestrator cannot write and a hash the ledger shows. Every documented way a prior
    autonomous research system fabricated or gamed (editing its own time limit,
    hallucinating an ablation table, overfitting a single evaluator input, removing the
    instrumentation that detected it) maps onto one of these gates; the discipline is
    what keeps them from being dissolved by the worker they gate.
  - *Human path:* every human-attested node — a `review_verdict` (§7), a `nogo_review` (§8),
    a waiver, an expert sign-off (§10), a yank-reach ruling or a Tier-2 revision admission
    (§2), an acknowledgment that closes a human-queue item holding no blocker (§10) — enters
    the system through one route. The operator, as the operator's own OS user,
    appends the canonical record to an operator-owned, append-only **attestation file** held
    beside the gate-bundle pin, a file the orchestrator's process user can read and cannot
    write; the harness writer mirrors the record as a substrate row carrying the record's
    digest and file offset; and every reader of such a row — `justify`, the tier gate, the
    waiver check, the preflight — treats the row as absent unless the digest matches the
    record at that offset. No typed write exposed to a worker or to the orchestrator's model
    components produces one of these rows. The two OS users (operator, orchestrator process)
    are the M0 deployment shape the pin and the checkpoint (§3) already assume, and that the
    orchestrator's process user can write neither the pin nor the attestation file is a
    stack fact M0 grounds and fixes (§13, §16). *Why:* PROVEN's floor is a human verdict
    and the substrate has one writer, the harness process; a verdict that process can mint
    for itself is a floor the gated party sets, so the attribution has to be a boundary the
    process cannot cross rather than a column it fills.

---

## 5. Compute tiers & allocation

Tier the whole surface; each tier's admission ticket is a result from the tier below.

- **Tier 0 — instant (ms–s):** typechecks, `xP==Q`, small-field arithmetic, "does the
  claim even cohere." Nearly every refutation and orchestration decision lives here. Free;
  run constantly.
- **Tier 1 — one core, minutes:** toy DLPs 30–50 bit, small Gröbner bases, a Lean compile,
  bounded counterexample sweeps. **The research lives here.** The ladder's distribution
  rungs (§6, ≤ 50 bits) are Tier-1 — admitted on the Tier-1 ticket whatever tier the
  boundary table would assign their ladder-plan-bounded cost, because they are gate-owned
  launches whose count, arms and patience ceiling are ladder-plan fields and the launches
  that mint the Tier-2 ticket (a rung the table assigned Tier 2 would otherwise need the
  very KEEP it exists to produce); its 60-bit rung is tiered by its own declared cost
  profile. Fail here → never see another core.
- **Tier 2 — many cores, hours:** larger linear algebra, rho up to ≈ 90 bits for
  *validation* (the ceiling is arithmetic: at ≈ 0.11 µs per iteration a negation-map rho
  at 0.886√n costs ≈ 30 core-hours at 80 bits, ≈ 10³ at 90 and ≈ 3×10⁴ at 100 — CONJECTURE,
  the tag its source assigns the extrapolation above 50 bits), big families,
  substantial
  formalization. Entered only holding the Tier-1 ticket defined below. A declared cost
  profile above ≈ 10³ core-hours is a Tier-3 request whatever the skill is called. *Why:*
  a 100-bit run admitted as Tier 2 skips the one tier that demands a payoff justification
  and a certificate plan, and it is exactly the class that cannot be bit-replayed.
- **Tier 3 — cluster, days:** record-scale. Almost nothing reaches it; reaching it requires
  an explicit predicted-cost-vs-payoff justification, a certificate verification plan
  (§3 — you can't bit-replay it) and the expert sign-off of §10.

**Mechanism:** every skill declares its **cost profile** (complexity in inputs, expected
tier) as part of its typed interface, so the orchestrator *predicts* spend before launch
and the tier gate enforces cheap-before-expensive automatically. The declared tier is a
claim the gate checks, never its input: the gate derives the launch's tier from the
profile's production cost at the launch's inputs under the bundle's boundary table (§4) and
refuses, with a `TierRefused` record, a launch declaring a lower tier than the table assigns
— the ≈ 10³ core-hour rule above is that table's Tier-2/Tier-3 edge. *Why:* a profile that
names Tier 1 for hours of work has skipped the ticket Tier 2 demands, and the ceiling below
stops it only after the spend has begun. A cost profile names two
components: *production* (the expected cost of the run and its spread) and *verification*
(what the node's replay grade and tier will cost under the §3 re-run policy); the tier gate
reserves the verification component from the grant at launch, refuses a launch whose
verification the remaining budget cannot cover, and binds the reservation to the *node*,
never to the branch: it is spent where the §3 policy's first check runs (a witness checked
at admission, a Tier-0/1 re-run, a Tier-2/3 re-run at `justify` time or on the foundations
auditor's first draw — the last two routinely after the attempt, and sometimes after its
branch, reached a terminal status) and released unspent only where the attempt ended with
status ≠ OK or the node was disowned; a branch reaching a terminal status returns its
unreserved grant and never the escrow of an admissible node it produced, so a withdrawn
branch's Tier-2 node stays re-runnable when `justify` waits on it months later, and the
auditor's exhaustive Tier-2/3 pass (§7) spends every such escrow within one audit cycle, so
an unspent reservation outlives its branch by at most that cycle from M4 (before the
auditor exists it stands until `justify` draws it); every later
re-verification of a node is funded from
the standing per-cycle audit line the gate bundle names (§7), never from the node's escrow.
*Why:* a gate whose compute is unbudgeted
is a gate skipped under load — silent fail-open by a slower route; a reservation released at
terminal status leaves the deferred re-run of a `Replayable` Tier-2/3 node unfunded at the
moment the derivation waits on it; a reservation never
released shrinks a long run's usable budget toward zero; and a node whose escrow is spent
must stay drawable by the auditor, or the published `bits` degrade for a reason unrelated
to rot. A spawned worker's budget
is the meet of its parent's remaining budget and the skill's declared profile; a retry or
restart is launched only if the remaining budget can afford it. The gate also charges every
non-refused launch's production cost to its hypothesis key under the ticket that admitted
it — the declared cost at launch, reconciled to the execution receipt's measured cost (§3)
when the attempt closes, so an understated declaration misstates the key's charge by no more
than the attempt in flight — and the boundary table names a *cumulative edge* per ticket
tier over the charge of a worker's fresh launches: the worker launch that would carry that
charge under the key's current best ticket past the edge is `TierRefused` until the next
tier's ticket exists. Gate-owned launches — the ladder's rungs, a null-control or
retry-predicate re-measurement, the auditor's draws — and re-runs of recorded recipes (the
Skeptic's, the reproducibility gate's) are charged to the key and never compared against the
edge: their counts, arms and patience ceilings are ladder-plan fields and a re-run of a
recorded recipe is no new work, so neither is a launch a worker can shard, while an edge that
metered them would refuse the second ladder run on a key — after INCONCLUSIVE, for a new
revision, or as the re-measurement a retry predicate names — and the refused run is the one
that mints the ticket that lifts the edge. M1 sets the Tier-1 edge as a multiple of the
ladder's measured per-run cost and records it beside the trial count it derives (§6). *Why:*
a tier derived per launch is satisfiable by sharding — a 90-bit validation rho
as a thousand honest one-core-minute walks, each on the Tier-1 ticket, no `TierRefused`, no
drift signal, no KEEP ever required — and §0 lets the orchestrator set the branch grant
that funds it, so the per-launch rule alone is not cheap-before-expensive. The granted budget is a hard
ceiling the harness enforces at runtime, set at a multiplier of the declared expectation
named in the gate bundle (M0 default 4×, CONJECTURE: with rho's sd ≈ 0.5× its mean a 2×
ceiling aborts ≈ 4 % of honest trials and a 4× ceiling well under 0.1 %; M1 re-sets it from
the baseline skills' measured distributions); exhaustion stops the attempt with status
`BUDGET_EXCEEDED` (≠ OK: never cached, never a ticket, never evidence), and the ladder
counts such a trial as a failure in its success-rate column. The ceiling and the boundary
table read the same declared profile, so an understated declaration buys a bounded overrun:
a launch runs past the tier its declaration earned by at most the multiplier before it is
stopped, and that overrun, visible as the measured-versus-declared ratio, is what the drift
monitor of §15 P4 watches. *Why:* an admission check on a
self-declared cost is fail-open under the pressure of §1 — a skill declaring Tier 1 and
running for hours has skipped the ticket Tier 2 demands — and the ceiling makes the
declaration a gate input with a stated bound. **Allocation currency is
expected information per compute-dollar**, not raw yield — a cheap experiment that halves a
conjecture's probability outranks an expensive one that nudges a bound; until M3 decides
its mechanics (§15 P3) it is implemented as gate-outcome reward per measured cost — a gate
outcome being a terminal resolution of either sign: a ladder KEEP or a REJECT that writes a
ledger entry, a hunt SURVIVED or KILLED, a tag `justify` derives or a machine-checked
negation, while INCONCLUSIVE, a harness-terminated attempt and a refused launch are not
outcomes — and no
model probability, e-value, posterior or similarity term ever enters it (*why:* §9 counts a
refuted approach as knowledge gained, and a reward that paid only for positive verdicts
would teach the orchestrator to starve the Skeptic and the ladder's REJECT paths). Compute is a
tracked, finite resource flowing through the DAG exactly like claims. Measured cost is
compared against the declared profile; a persistent mismatch across runs is a
strategy-layer alarm (§15 P4), never a gate on a claim — the ceiling above is the per-run
enforcement, the alarm is the drift monitor.

**Tier gate predicate.** The gate reads three launch-supplied inputs and no others — the
skill's declared cost profile evaluated at the launch's inputs, the spawning budget (the
meet above), and the launch's
hypothesis key and method
identity (and its statement hash where a claim exists; §3, §4) — resolves two more from the
substrate itself, the launch revision's
self-test standing — certified and not yanked (§2) — and the launch's *ticket*, which the
gate selects by the rule below and the launching party never supplies — and
judges them against three gate-owned objects: the bundle's tier-boundary table, the §8 flag
with its `nogo_review` node, and the scrutiny class the §7 router assigned; nothing the
launching party writes reaches the gate except those three. The ticket is
the most recent admissible substrate node of the kind the tier requires (status OK, replay
grade ≥ Verifiable, reproducibility-checked under the §3 policy) produced at the tier below
for that same hypothesis key and method identity (or statement hash), where "most recent"
ranges over every node of that kind for the hypothesis whatever its verdict — a later
REJECT or INCONCLUSIVE ladder table displaces an older KEEP — and the verdict rule below is
applied to the node so selected. A ticket is bound to a
hypothesis, never to a branch: the gate compares the ticket's recorded key and method
identity with the launch's — and, where the ticket is a ladder table, the implementation
revision it ran (§6) with the launch's, so a new revision re-ladders before it spends — and
refuses a mismatch, so a method laddered as A cannot spend
Tier 2 as B under a repointed branch. A launch is refused when the declared tier exceeds the
ticket's tier by more than one, when the declared cost exceeds the remaining budget, when
the required ticket is absent, when the launch revision is yanked or holds no recorded
self-test certificate, or when the declared tier is lower than the tier the bundle's
boundary table assigns its production cost (the ladder's ≤ 50-bit rungs, admitted on the
Tier-1 ticket above, excepted). The ticket lattice is total, so the gate has a
branch for
every launch: Tier 0 needs no ticket; Tier 1's ticket is the launch's hypothesis object — and
the claim statement node where a claim exists — recorded in the substrate, with the §8
presence check passed for an attack on the target and the §7 statement pre-filters passed
for a theorem statement, each a Tier-0 result; for Tier 2 on an algorithmic claim the ticket
is a ladder result table with verdict KEEP (§6), with one scoped exception — a table with
verdict KEEP_IN_SAMPLE is a Tier-2 ticket valid for the 60-bit rung of the same hypothesis
key and for no other launch; the ticket records that purpose and the gate refuses a launch
whose skill and inputs name any other; for Tier 2 on a conjecture it is a counterexample-hunt record
(§7) with verdict SURVIVED (plus the P1 floor, if adopted); for Tier 2 on a theorem claim
whose formalization-gate run declares a Tier-2 profile it is the claim statement node with a
`review_verdict` of `approve` (§7) — the human reads the statement before the kernel replays
its closure for hours — and never a ladder table unless the claim is also algorithmic; a
claim whose typed fields carry more than one of these kinds (a cost model and a correctness
conjecture, a cost model and a theorem statement) needs the ticket of each kind it carries
and is refused while any is absent, a scoped KEEP_IN_SAMPLE admitting only the 60-bit rung
whatever else is held; Tier 3's ticket is the most recent admissible Tier-2 node for the
same hypothesis key and method identity (for an algorithmic claim a validation attempt with
status OK whose witness verified, launched under a KEEP ticket) together with the
justification, certificate plan and sign-off named above — a ladder table's tier is the tier
the gate assigned the launch that completed it, so KEEP is the prerequisite of Tier 3 and
reaches it only through that Tier-2 node, which is the one-tier rule above applied. A
refusal is a
`TierRefused` record the ledger keeps, not an exception the orchestrator can catch and retry
around: the branch stays active, and the orchestrator's next tick funds the tier-below work
that would produce the ticket or parks the branch with `budget_preempt` (never withdraws
it; withdrawal is the worker's or the human's act, §4) — where the absent ticket is a human
verdict (a Tier-2 formalization run without its `review_verdict`, a Tier-3 request without
its sign-off) no tier-below work produces it, and the refusal enqueues the human-queue item
of that class (§10) for the statement hash — an
unchanged re-submission is refused again, and repeated `TierRefused` records on one
hypothesis key are an input to the drift monitors of §15 P4, never a claim input; a branch
flagged by §8 holds no ticket above Tier 1. *Why:* "each tier's admission
ticket is a result from the tier below" is a gate only if the ticket is a named node the gate
can read for every tier and claim kind; a ticket that followed the branch rather than the
hypothesis would be a club card; and KEEP requires the 60-bit rung while that rung costs
Tier-2 budget, so an unscoped rule is satisfiable by no honest claim.

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
model and never a curve fitted afterward. The object declares which of the model's
parameters are fixed and which the ≤ 50-bit rungs fit — the exponent and the memory model's
shape are always fixed; a constant or crossover may be left to the fit — so "fitted on the
≤ 50-bit rungs" in (2b) names exactly the declared free parameters and nothing else. The
hypothesis object's hash, its method identity (the skill's interface version with its
canonical parameters, §3)
and the implementation revision under test (the full §2 identity bundle) are named in the
ladder's dispatch record;
the ladder runs exactly that identity — every trial recipe key is built from it, a different
identity or revision is refused before any trial, and a mismatched identity is a
planted-failure class
the ladder's self-test must FAIL (the counterexample hunt of §7 freezes its sampler against
the declared `D` the same way); the object's position in the substrate's append order
precedes the gate's entropy commitment of step (1); the ladder refuses to start otherwise.
(1) The ladder
generates its own instances: a fresh random prime-order curve and random `(P, Q)` per run,
at each size, from a gate-owned instance-maker whose entropy the worker never sees before
committing its method — the gate draws a fresh nonce at the start of each ladder run,
after the hypothesis object is recorded and never derived from it, and never reuses a nonce
across runs of the same object (a rung re-run after INCONCLUSIVE sees fresh instances, since
the first run's table published its seeds); it derives the seed of trial `i` at size `s` as
`H(nonce ‖ hypothesis hash ‖ s ‖ i)`, keeps
the nonce outside every worker allow-list until the run completes, and records nonce and
seeds in the result table so every trial replays afterward; a worker-supplied instance
list is a planted-failure fixture the ladder's self-test must FAIL — never a fixed instance
the worker has seen (the documented exploit class for automated evaluators is overfitting a
fixed input). (2) It gates on distributions, not runs: at the 30/40/50-bit rungs at least
10² independent trials per size (for rho the standard deviation is ≈0.5× the mean, so a
single run calibrates nothing), each rung's mean checked against the pre-registered model
(the in-sample check below), the sorted-distribution shape recorded against the model's
declared shape as a diagnostic column — a departure beyond the ladder plan's tolerance
surfaces on the human queue as a `shape_departure` item (§10) and is never a verdict
predicate; the defect class is a truncated or bimodal distribution a mean check cannot see,
the short-walk bias the source protocol sorts its walks to avoid, and the class retires if
by M3 no such item has preceded a REJECT or yank the verdict predicates missed, the column
staying as table data — and an A/A null arm — the
baseline run against itself in the same harness, same
trial count, same instance stream, the two arms differing only in the method seeds the gate
draws for them — whose CI radius sets the decision band. The ladder plan fixes the
comparison protocol as one versioned object: the estimator (a CI on the speedup factor —
baseline group-operation cost divided by claim group-operation cost, so that a real advance
is above 1 — in the source's median-CI form or a mean CI, named), the pairing (claimant
and both baseline arms on the same gate-generated instance stream, each arm under its own
gate-drawn method seeds), the CI method and its coverage, the per-rung trial count and the
rule that every rung must pass, the tolerances of step (3), and the baseline skill revision;
the trial count is sized at M1 so that positive control (j) of §13 is KEPT and control (k)
INCONCLUSIVE with margin — the 10² figure is a floor and not that count: at rho's
sd ≈ 0.5·mean the A/A radius at 10² trials is ≈ 0.14, the band ≈ 1.28 and the √2 control's
CI lower bound ≈ 1.22, so 10² returns INCONCLUSIVE on a known-true advance; solving the KEEP
inequality for the √2 control under independent arms gives n ≳ 130, and M1 measures the
paired variance on the shared instance stream and records the count it derives — and each
rung's
budget follows its declared cost profile under the chosen count (an interpreted 50-bit
baseline at that count runs for hours, a compiled one for minutes; M1 records which), while
its ticket is the Tier-1 ticket whatever that cost (§5). The
band is always a ratio against the **best generic baseline the harness ships, measured in
the same harness on the same instances** — plain rho without the negation map (≈ 1.25√n
ops, O(1) memory) at M1, never BSGS; a negation-map rho (≈ 0.886√n, the constant §5 uses to
price Tier 2), once shipped as a baseline skill, is the baseline from the day it lands — and
a speedup is KEPT only if the whole claim CI clears `1 + 2·radius` — its lower bound
exceeds the band, the floor `1.01` guarding a degenerate null arm — on group operations
*and* peak memory both stays under the cap at the rungs where the refutation floor is
measured — the 50-bit rung and the 60-bit completion rung, the cap fixed in the ladder plan
as the BSGS table for that size (≈ 1 GB at 50 bits, 2³⁰ entries at 60) — and at every rung
matches the pre-registered memory model on the sizes measured — growth the model did not
declare is a model miss and REJECT, never KEEP — measured by the harness, from the
execution receipt (§3), as peak RSS over the trial's process tree less the A/A arm's peak
on the same instances (at the 60-bit rung, less the clock calibration run's) plus the bytes
written to the gate-owned scratch path (the only writable location on a ladder-tested
method's allow-list, step (3)), the table bytes a method reports about itself being a
diagnostic column; a storage channel the allow-list does not name — another writable path,
network egress — is a planted-failure fixture the ladder's self-test must FAIL; otherwise
INCONCLUSIVE or REJECT. The harness cannot see a method's "algorithmic table" except
through what the method reports, so the quantity it can measure is the predicate and the
reported one the diagnostic, never the reverse. The cap binds where the floor lives
because at 30 bits the BSGS table is 2¹⁵ entries and a cap there would refuse an honest
constant-memory model that the 50-bit cap admits; the memory-model check carries the small
rungs. The *in-sample check* has the band form of the out-of-sample check in (2b): the
declared free parameters are fit by least squares on the logarithm of the rung means over
the ≤ 50-bit rungs, and each of those rungs' measured mean must sit inside
`1 ± 2·√(radius² + (sd_s/(mean_s·√n))²)` of the fitted model's prediction at that size,
`radius` being that rung's A/A radius and `n` its trial count; a rung outside the band is
an in-sample model miss (REJECT, 2c) — the predicate is fixed here because a model miss
each implementer defines for itself is a different ladder under one name. A pre-registered
model that fixes a parameter the
measurement contradicts — an exponent below ½ for a method whose operations grow as √n (at
exponent 0.4 the miss between 30 and 50 bits is ≈ 4× against a band of a few tens of
percent), or a fixed constant below the measured one — misses in sample, which is how
fixture (a) of §13 is caught, while control (j)'s √n model with a free constant fits.
A trial that hits the per-trial patience
ceiling of the ladder plan (the §5 budget ceiling) counts as a failure in the success-rate
column and enters the model check at the ceiling value as a lower bound on its cost; a rung
with any failed trial is at most INCONCLUSIVE — never KEEP, and REJECT where the ceiling
value already misses the model or the floor. (2b) The 60-bit rung is the
completion-and-extrapolation rung: the model fitted on
the ≤ 50-bit rungs must predict the measured 60-bit mean inside a band widened by the
rung's own sampling error, `1 ± 2·√(radius² + (sd₆₀/(mean₆₀·√m))²)` over the `m` hold-out
instances — at `m = 10` and rho's `sd ≈ 0.5·mean` the rung's standard error (≈ 16 %)
exceeds the A/A radius, and a point-against-band comparison would REJECT an honest method
about one run in five — and the method must complete and recover `x` on all `m` fresh
instances (`m = 10` at M1); `m` and the fit-on / hold-out split are fixed in the ladder
plan (gate bundle, §4), never chosen by the worker, and a clean in-sample fit that misses
out of sample is REJECT. The 60-bit rung runs the claimant's method on the `m` hold-out
instances only — no baseline and no A/A arm run there, since the check is the claim's own
fitted model against its own measured mean — and is tiered by its declared profile. A 60-bit
generic trial is ≈ 1.3×10⁹ group ops (minutes in compiled code, a quarter hour
interpreted), so a full 10²-trial distribution check at 60 bits is Tier-2 work by its own
declared profile, not Tier-1, is no part of the rung, and runs only when the tier gate
grants that budget. (2c) Verdicts are typed and fixed in the ladder plan: `REJECT`
(refutation floor failed, `xP ≠ Q` on any trial, memory cap exceeded, a self-reported count
diverging from the gate's, or an in-sample or out-of-sample miss of the pre-registered
model, the table recording which predicate fired and the measured points of §4's reach; the
ledger entry a REJECT writes takes its `refutation_kind` from the predicate — `xP ≠ Q` or a
count divergence is an `implementation` entry against the revision the dispatch record
names, whose retry predicate is a new certified revision, and yanks that revision (§2),
since a wrong answer on a gate-generated instance is a known-answer failure the corpus
missed and says nothing about the method's cost; the floor, the memory predicates and the
model misses are `measured` entries on the hypothesis key, the ones §7's `refuted` status
and the preflight's reach read),
`INCONCLUSIVE` (inside the band, or a count the clock cannot support, step (3)),
`KEEP_IN_SAMPLE` (every ≤ 50-bit rung passes — floor beaten, claim CI clears the band on
group operations, memory under cap, `x` recovered on every trial, model fits in sample) and
`KEEP` (`KEEP_IN_SAMPLE` plus the 60-bit completion and out-of-sample check).
`KEEP_IN_SAMPLE` is the Tier-2 ticket for the 60-bit rung of the same hypothesis key and
for nothing else (§5); `KEEP` is the ticket for every other Tier-2 launch and the
prerequisite of any Tier-3 request built on the claim, whose own ticket is the Tier-2 node
of §5. *Why:* the 60-bit rung costs Tier-2 budget and KEEP
needs the 60-bit rung, so a single verdict deadlocks the first honest claim; the scoped
ticket keeps cheap-before-expensive — the 50-bit floor still fires first — while letting
the hold-out run. (3) It reports group operations against `√n`, never seconds, and the
count is the gate's measurement, never the claimant's: the ladder runs every method —
claimant and baseline alike — against a gate-owned group-arithmetic object (the baseline
arithmetic skill, instrumented) that counts every addition, doubling and inversion, and a
ladder-tested method's allow-list (a gate-bundle template, §4, instantiated per dispatch
and named in the dispatch record) names no arithmetic backend but the gate-owned counted
object and the uncounted backends the hypothesis object declares (whose rungs are
INCONCLUSIVE at best, below), no network egress and no writable path but the gate-owned
scratch path. A count
the method
reports about itself is a diagnostic column, and a divergence from the gate's count beyond
the ladder plan's tolerance is REJECT. The harness records CPU-seconds per trial — user and
system time summed over the trial's
whole process tree, a ladder-tested method's allow-list permitting no process spawn beyond
the backends its hypothesis object declares — and wall-clock seconds beside the count, and
a trial whose CPU time
exceeds what its counted operations would take at the gate's per-operation reference rate
for that rung, by more than the ladder plan's tolerance, or whose wall-clock exceeds its CPU
time by more than that tolerance (an idle wait on a channel the counter cannot see), marks
the rung INCONCLUSIVE — never
KEEP, never REJECT — and surfaces on the human queue: the counter cannot see arithmetic
done around it, but the clock can. The clock bounds uncounted arithmetic to the tolerance
times the counted work *at the reference rate*, which is a bound only while no arithmetic a
method can carry is faster per operation than the gate's object — a method that computes on
extracted coordinates with its own faster arithmetic and issues dummy counted calls sits
inside the tolerance; so the counted object is compiled, M1 records the ratio of its
per-operation cost to the fastest implementation available on the build machine, the ladder
plan's clock tolerance times that ratio must stay below the KEEP band's excess over 1
(`2·radius`, the most a method could hide and still be caught by the band) — checked at plan
load against the design radius the plan's trial count targets (a ladder-plan field M1
records with the count), a plan failing it refusing to start (§4: invalid gate config fails
closed), and again at every rung against the measured A/A radius, the tolerance applied
there being the smaller of the plan's value and `2·radius/ratio`, so a tighter band tightens
the clock rather than opening a gap beneath it — and the ladder's
self-test plants a method that does its own coordinate arithmetic and issues dummy counted
calls, which must not reach KEEP. The reference rate is measured by the gate on the rung's
own instances: at the ≤ 50-bit rungs it is the A/A arm's rate; at the 60-bit rung, which
runs no baseline arm, it is a gate-owned calibration run of the counted arithmetic object —
a fixed operation count on the rung's instances, never a baseline distribution — recorded
in the table, so the clock check applies at every rung including the one where the
claimant runs alone. A method
that needs an uncounted backend declares it in its hypothesis object (the allow-list above
admits it on that declaration and on nothing else), and its rungs are INCONCLUSIVE at best
until a counted implementation exists. *Why:* every other ladder input —
instances, nonce, seeds, patience ceiling, memory, verdict — is gate-owned, and the KEEP
band is computed from this one; a number produced by the party being gated is the
hallucinated-ablation-table failure under another name. (4) Two
thresholds. *Refutation floor:* at 50 bits BSGS ≈ 1.5√n ops with ≈ 3×10⁷ table entries;
failing to beat it (~5×10⁷ group ops, under 1 GB) refutes on the spot, and the method
must *complete* at 60 bits, where BSGS needs 2³⁰ entries. *Acceptance bar:* the KEEP band
above, against rho (≈ 1.25√n ≈ 4×10⁷ ops at 50 bits). The ≤ 50-bit figures are
STRONG-EMPIRICAL; the 60-bit figures carry the CONJECTURE tag their source assigns them.
(5) The result table (size, trials, mean and sd of ops, CPU-seconds and the reference rate
of step (3), memory, success rate, fit to the pre-registered model, out-of-sample prediction
and its band, the nonce and seeds, the hypothesis hash, method identity and implementation
revision it ran, the gate-bundle hash it ran under) is the ladder's artifact, the Tier-2
ticket (§5) under the verdict rule of (2c), and the template for a negative-results entry
(§11); a verdict is never recomputed under a later bundle. The table's replay grade is the
weakest grade among its trials — a rho trial with its DP witness is `Verifiable`, a
deterministic trial `Replayable` — and its reproducibility record (§3, §7) is the §3 policy
applied per trial (every witness checked; every `Replayable` trial re-run under the Tier-1
rule) plus a recomputation of the table's statistics and verdict from the verified trial
rows; that is the verification component the table's launch escrows (§5). *Why
two thresholds:* BSGS is the right floor because a method that cannot beat a table lookup
at 50 bits is not an advance, and the wrong bar because a method costing 4.9×10⁷ ops and
900 MB would "beat BSGS" while being worse than plain rho on both axes.

---

## 7. Epistemic mechanics (humility made mechanical)

- **Calibration taxonomy (mandatory per claim):** `PROVEN` (formalized) · `STRONG-EMPIRICAL`
  (ladder + repro node) · `CONJECTURE` · `SPECULATION`. No green Lean check → not `PROVEN`.
  - **"Green Lean" is the challenge/solution protocol.** The gate *compiles* the Challenge
    module from the claim statement node (§4) with a gate-side renderer and pinned
    prelude, both inside the gate bundle and outside every worker's write path; the
    Formalizer never creates or edits Challenge text and submits a Solution module that
    names the Challenge's *formal statement hash* — a Solution naming any other hash fails
    closed before kernel replay. The formal statement hash is computed by the gate when it
    compiles the Challenge, over what the comparator
    compares (the theorem's `ConstantVal` and the full `ConstantInfo` of every constant in
    its transitive closure), never over raw export bytes, which carry position-dependent
    names (that raw exports are unstable is PROVEN by probe; that this closure is the right
    hash is CONJECTURE — the hasher is inferred from the comparator's `compareAt` and does
    not exist yet, so M1 builds and probes it before the gate is trusted). The hash names and
    binds; it decides nothing — check (iv) below is the comparator's own closure comparison,
    and a hash match with a comparator mismatch fails closed. The gate-run record binds the
    claim statement hash (§4) to the formal statement hash under the bundle hash, and a
    `lean_artifact` evidence node reaches its claim statement through that binding. The
    gate declares
    a cost profile like any skill: `leanchecker --fresh` replays the statement's whole
    transitive closure from empty (32.3 s on a mathlib-free module, unmeasured with
    mathlib), so M1 measures it on a mathlib-importing Challenge before sizing its fixture
    corpus, and "a Lean compile" at Tier 1 (§5) names the compile only, never this gate.
    The gate (i) rebuilds in a sandbox under the pinned `lean-toolchain` and
    `lake-manifest` mathlib revision recorded in the artifact, (ii) kernel-replays the
    result (`leanchecker --fresh`, the checker shipped inside the toolchain; comparator
    with an external kernel at the gold tier, which needs a Linux `landrun` sandbox — the
    macOS fallback runs unsandboxed and is development-only), (iii) computes the axiom set
    itself — the comparator's own axiom check at the gold tier, and on the ordinary path a
    gate-owned module in the bundle that imports the Solution and runs `Lean.collectAxioms`
    over the Challenge's theorem names, never a list read from output the Solution's own
    compilation emits, since `leanchecker` rejects neither `sorryAx` nor extra axioms — and
    requires it ⊆ {`propext`, `Classical.choice`, `Quot.sound`} — which rejects `sorryAx`, the
    per-computation axioms of `decide +native` / `bv_decide`, and any custom axiom; the
    permitted-axiom set, the checker command and its external kernels are fields of the
    gate bundle (§4), never a per-run literal, and a run whose checker configuration differs
    from the bundle's fails closed before compilation — and
    (iv) requires the Challenge and Solution theorem statements to be identical over the
    statement's transitive constant closure, so a redefined constant anywhere under the
    statement fails the check. The gate plan orders these cheapest-first — the pin and
    formal-statement-hash check, the statement pre-filters below, the Tier-≥ 2 review
    verdict (§5), the sandbox build, the axiom computation, the kernel replay, the closure
    comparison — and an earlier failure blocks the later steps (§4's ordered scopes), so a
    `sorry`-shaped Solution never reaches `--fresh`. "No error messages" or an empty
    `sorries` list is never a
    PROVEN criterion (both have leaked `sorry`/`admit` in published systems). A REFUTED
    ledger entry may carry a machine-matched proof of the Challenge's *negation*. *Why:*
    this mechanizes "the thing proved is the thing stated" and "the statement was fixed
    before the proof"; an axiom list emitted by the Solution's own build is a count reported
    by the party being gated (§6); "the Challenge says what we mean" is the human/Skeptic
    half below.
  - **The tag is derived, never set.** Each evidence kind has a maximum class it may
    justify: green Lean via the protocol above, together with an `approve` `review_verdict`
    on the same statement hash (statement-level review, below) → PROVEN; ladder + repro node
    → STRONG-EMPIRICAL — a `ladder_table` whose verdict is KEEP, or KEEP_IN_SAMPLE for a
    statement whose scope is the in-sample sizes, on the population it measured; a table
    with any other verdict justifies nothing — where "repro node" means the reproducibility
    record the §3 policy
    attaches to the table's own attempt (a second agreeing attempt or a passed witness check)
    and a table without it has ceiling CONJECTURE, and the class a table justifies is about
    the typed statement — the method identity the table names, its cost model, the
    population measured — and never about why the executable is fast, so a mechanism or
    novelty attribution carried in the informal statement is the Librarian's and the human's
    question (§10), not a calibration class; sampled or statistical evidence → at most
    STRONG-EMPIRICAL on its declared population — except for a statement whose typed fields
    carry a cost model, which takes STRONG-EMPIRICAL from a `ladder_table` produced by a
    ladder gate run and from no other kind (a `statistical` or `repro_node` offered for it
    caps at CONJECTURE, since a cost measured by the party claiming it is the §6 (3) failure
    and the taxonomy's own definition of the class for such a claim is "ladder + repro
    node"); a Lean proof about a *model* of the system →
    at most CONJECTURE.
    An evidence node is typed: `{kind ∈ {lean_artifact, ladder_table, repro_node (a
    Verifiable or Replayable attempt, §3), counterexample_hunt_record, statistical,
    model_proof}, target statement hash, declared population and assumptions (the same
    typed family, size and range fields the hypothesis object and the claim statement
    node's scope field use — concretely the record `{target family (categorical), size
    interval, declared parameter ranges (axis-aligned intervals), assumption set
    (content-addressed assumption identifiers)}`), producer identity (the §2 identity
    bundle hash or the gate-run record), the
    producer's own tag}`; the maximum class is a function of `kind` and — where the producer
    is a certified skill rather than a gate-bundle object or a gate run — of that revision's
    self-test standing (§2): a revision whose self-test record carries no STRONG-EMPIRICAL
    basis covering the attempt's inputs (every corpus origin `author_supplied`, no
    randomized-postcondition arm, no cross-check whose declared independent range contains
    them) caps the node at CONJECTURE, the ceiling §2 states and `justify` enforces, since a
    bit-identical re-run of an author-tuned skill proves determinism and not correctness; and
    coverage is a
    structural comparison of the population and assumption fields against the statement's
    scope field, never a text match — interval containment on numeric fields, equality on
    categorical ones and set inclusion on assumptions, the comparison the §4 reach uses — so
    `justify` is implementable at M0 from two
    synthetic evidence kinds and a synthetic statement (§13).
    A claim version's tag = the strongest class some evidence node justifies via
    `justify(evidence, statement hash)`, which checks that the evidence's declared target
    names that exact statement, that its declared population is a superset of the
    statement's scope (it was measured or proved on everything the statement ranges over)
    and that its assumptions are a subset of the statement's (it needed no more than the
    statement grants — evidence under weaker assumptions is stronger and covers it), and
    returns a typed justification or a lattice violation, never a boolean; the tag is a derived
    column the
    gate layer computes at write time, and no worker or orchestrator writes it. A weaker
    class may *inform* a stronger claim; it may never *justify* it (`justified_by` is the
    only typed edge; "inform" names no edge). A verified refutation of
    the statement — a `counterexample_hunt_record` KILLED by a counterexample that passed its
    verifier, a machine-checked proof of the Challenge's negation, a ladder REJECT on the
    claim's own pre-registered model (a REJECT whose predicate is `xP ≠ Q` or a count
    divergence yanks the revision and refutes no claim version, §6) — moves the claim
    version to terminal status `refuted`
    with that evidence pointer in its tag history, and `justify` returns a lattice violation
    for any positive class offered on a refuted version. The foundations
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
    human verdict remains the gate, and it is a typed substrate node the gate reads:
    `review_verdict {statement hash, reviewer (a human identity or role), verdict ∈ {approve,
    reject, needs_revision}, checklist template hash, gate-bundle hash, time, supersedes?}`,
    immutable, written only through the human path of §4 (as a waiver is) and never by a
    worker or the orchestrator; a verdict names one statement hash and does not transfer to a
    superseding version. `justify` derives PROVEN only from a `lean_artifact` node and an
    `approve` verdict naming the same statement hash; a green artifact without one leaves
    the claim at its pre-review tag on the human queue (§10), and an absent or `reject`
    verdict is a gate input that blocks, never a default. *Why:* "nothing is PROVEN without a
    green Lean check and a statement-level match review" (HANDOFF.md) is enforceable only
    when the review is a node the derivation reads.
- **Independent skeptic:** sees only the *statement*, never the prover's reasoning; rewarded
  solely for gaps/counterexamples. If it reads the proof it just agrees — independence is
  the whole value.
  - *By construction, at both layers.* Context: the skeptic is dispatched by the harness
    as its own top-level query whose entire prompt is the statement node plus the Skeptic's
    own checklist (a read-only, claim-agnostic role template in the gate bundle), with
    inherited settings sources disabled — never composed by a parent model. Capability: an
    explicit tool allow-list for counterexample search, no general file read, no shell, and a
    substrate handle scoped to the statement node's closure and filtered by evidence kind —
    the statement, plus the recipes and certificates of `repro_node`, `ladder_table` and
    `counterexample_hunt_record` evidence, which a re-run needs; for `lean_artifact` evidence
    the Challenge's formal statement hash and the gate-run verdict only, never the Solution blob or
    its recipe inputs, the checker re-run being the gate's job; never the Prover's transcript
    or proof text — so no prover output, panel feedback or detection logic of the
    gates that judge the Prover is reachable. Both are gate-bundle config (§4), and the
    dispatch record names the allow-list it ran under, so a widened one is visible in the
    ledger. Its re-runs of any experiment set `skip_cache_lookup` (§3). *Why:* context
    isolation is not filesystem isolation — the cheapest way to find a gap is to read the
    proof, and a worker with a file-read tool over the substrate can.
  - *Disagreement protocol:* a Prover/Skeptic or panel disagreement is never resolved by
    vote; it is recorded with both artifacts' hashes, classified (statement error, proof
    gap, harness bug, out-of-scope, inconclusive), routed to an owner (the human for
    statement errors), and the claim's tag stays at its pre-dispute level until resolved.
- **Proportional scrutiny + the paradox, written in:** tightened bound → clean argument;
  claimed break of the target → formalization + ladder + expert sign-off. The router's
  classes are a predicate in the gate bundle over the typed fields of the hypothesis object
  and claim statement node (target family, claimed property or cost model, scope) and the §8
  flag, never over prose: the top class — a claim whose scope names the target family and
  whose claimed property is a solve below the generic bound, by any method — requires ladder
  KEEP where the claim is algorithmic, the formalization gate and statement review where it
  is a theorem, reproducibility, and the §10 expert sign-off; the tier gate issues no Tier-3
  ticket without all of them, and the orchestrator may request a class and can never lower
  one. **A run announcing it broke ECDLP has produced evidence it *erred*** is that routing
  rule, not a sentence in a worker prompt. The bigger the claim, the more the burden inverts
  against it. *Why:* a scrutiny class carried by prompt text is the first thing to fail
  under §1's pressure; carried by a bundle predicate over typed fields, it fails closed.
- **Strong law of small numbers (hard gate):** a small-case pattern is a conjecture until it
  survives larger cases + a deliberate counterexample hunt. Whether this gate also gains a
  pre-registered quantitative floor (an anytime-valid e-process on sampled cases, used as a
  *resource* gate before Tier-2 spend) is decided at M1 with planted-false conjectures
  (§15 P1); the floor, if adopted, never promotes a tag and never enters the orchestrator's
  reward. The hunt's artifact is a *counterexample-hunt record*, a substrate node
  `{statement hash, sampling distribution D (content-addressed), pre-registered budget
  (trial count, family bounds), the gate's entropy commitment and seeds (the §6
  instance-maker rule), per-trial outcomes, any counterexample with its verifier status,
  verdict ∈ {SURVIVED, KILLED, INCOMPLETE}}`; SURVIVED under the declared budget is
  the Tier-2 ticket for a conjecture (§5), KILLED writes the ledger entry of §4,
  INCOMPLETE — the §5 ceiling stopped the hunt before its declared trial count, the
  attempt's status being `BUDGET_EXCEEDED` — is no ticket, and without this node the
  conjecture's tag ceiling is
  CONJECTURE. *Why:* the algorithmic ticket has a table shape the gate can read; the
  conjecture ticket needs one too, or the tier gate reads an orchestrator's prose.
- **Standing foundations-auditor (above the per-claim skeptic):** the per-claim skeptic
  catches bad proofs; it can't catch a bad *premise* the whole tree rests on (an FFDA-style
  heuristic everyone assumed). Periodically re-audit the shared assumptions — a tall tower
  on a cracked base is the failure no local check sees. Its mechanical core is the
  transitive `justified_by` query above; its sampling cadence for re-verifying substrate
  nodes uses the spot-check bound `l ≥ ln(2^bits)/ln(1/(1−f))` so that undetected rot at
  fraction `f` has probability below `2^−bits`; `f` and `bits` are named in the gate
  bundle (M0: `f = 0.01`, `bits = 20`), and the bound is applied per tier stratum so that
  cheap Tier-0/1 nodes cannot absorb the whole sample. The bound holds for uniform random
  draws and for nothing else, so each stratum is partitioned before drawing into a critical
  set — the nodes with the largest `justified_by` fan-in, above a cutoff named in the gate
  bundle — audited exhaustively, and a residual set sampled uniformly without replacement
  from gate-owned committed entropy (a seed recorded in the audit record); the `bits`
  guarantee is stated for the residual alone, and the audit record names the population
  size, the cutoff, the critical-set coverage, the seed and the sampled identifiers, so a
  priority audit is never booked as part of the random guarantee. At the M0 parameters the
  bound is `l ≈ 1.4×10³` per stratum per cycle, which exceeds any plausible Tier-2/3
  population, so that stratum is checked exhaustively — a witness check for Verifiable
  nodes, a full re-run for Replayable ones — from each node's escrow on its first draw and
  from the standing per-cycle audit line the gate bundle names on every later one (§5);
  where that line cannot fund `l`, the auditor draws what it can
  afford and records the achieved `bits` in its audit record, and a stratum below the
  bundle's target surfaces on the human queue (§10) — an unmet target is published, never
  silent. The cadence is a gate-bundle parameter set at M4 from the measured
  re-verification cost. The re-run it performs is the §3 policy; what it audits is every
  claim's evidence, not a report. *Why:* the spot-check bound is a statement about random
  draws, and a deterministic priority draw counted toward it reports a confidence it does
  not have.

---

## 8. No-go checklist (auto-flag tripwire)

Any proposed attack on the target must state how it evades all three or be flagged
almost-certainly-broken. The gate is mechanical in the presence dimension — a missing or
empty declaration is an automatic flag — and the flag has a consumer: the
proportional-scrutiny router (§7) routes a flagged attack to the top scrutiny class and
the tier gate (§5) grants it no Tier-1 ticket while the declaration is absent (the §5
presence check) and no ticket above Tier 1 until a
`nogo_review` node records `accept_for_tiering` — `{hypothesis hash, declaration hash,
reviewer, verdict ∈ {accept_for_tiering, reject, needs_revision}, gate-bundle hash, time,
supersedes?}`, immutable, written only through the human path of §4 as a `review_verdict`
is (§7); absence is the flag. The declaration is a content-addressed node the branch points
at, outside the hypothesis key because its words are prose; the *content* of a declared
evasion is reviewed by the Skeptic, who may attach notes, and the human, never by this
gate alone; and `accept_for_tiering` restores ordinary ticket eligibility only — it is no
claim tag and satisfies none of the top scrutiny class's obligations (§7). *Why:* "has been
reviewed" carried in prose is a bit the orchestrator could set; carried as a node the tier
gate reads, it fails closed. The three: (1) **Shoup √n** — must exploit named
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
  expert signing off on expensive, high-commitment calls**, every such ruling recorded
  through the human path of §4. When no human session is open,
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
- **Human queue and autonomy envelope.** The human queue is a typed substrate object, not a
  phrase: each item names its class (`statement_review`, `nogo_review`, `waiver_request`,
  `yank_ruling`, `revision_admission`, `expert_signoff`, `disagreement`, `near_dup_review`,
  `supersedes_refuted_review`, `null_control_pending`, `clock_inconclusive`,
  `shape_departure` (§6), `leaked` (§4), `cost_drift` (§15 P4),
  `audit_shortfall`), the branch or statement hash it blocks and the blocker that holds it,
  and its enqueue time; an item closes by a human-path record (§4), by its blocker clearing,
  or — for an item that holds no blocker (`leaked`, `clock_inconclusive`, `shape_departure`,
  `cost_drift`, `audit_shortfall`) — when the branch, rung or audit cycle it names reaches a
  terminal status, re-runs or next meets its target, or by an attributed `acknowledgment`
  record through the human path naming the item; it closes by no other path, so the depth
  and age below cannot be edited down. The orchestrator may read queue depth and age and
  prefer branches whose next
  step needs no human input — a strategy choice it makes freely, never a reason to lower a
  scrutiny class, skip a gate or request a waiver — and depth and age are drift-monitor
  inputs (§15 P4), never gate inputs. *Autonomy envelope:* with no human session open the
  harness may open, fund, ladder, refute and park Tier-0/1 work, write REFUTED and PARKED
  entries, run Tier-2 launches that hold their tickets where the operator knob above
  permits, and accumulate CONJECTURE and STRONG-EMPIRICAL tags under the mechanical gates;
  it may not derive PROVEN, admit Tier 3, accept a no-go declaration for tiering or clear a
  `*_review` blocker — those wait on the queue at their pre-review tag, and "never give up"
  (§9) names this envelope, not unattended promotion. *Why:* the human is the bottleneck
  this section names, and a bottleneck the system cannot see is one it fails closed into
  without a report; a "never stops researching" sentence without the envelope reads as a
  promise of unattended PROVEN.
- **Egress rule.** What leaves the harness — a negative-results entry (§11), a human-queue
  item, an operator report rendered from the state layer, a submission — is rendered by a
  gate-owned renderer from claim statement nodes and ledger records: every assertion it
  prints names a claim statement hash and carries that version's derived tag (§7) and
  evidence pointer; a sentence that names no statement hash is rendered as prose, never as
  a finding; a version at `refuted` or `withdrawn` is printed as such and never as a
  standing assertion; and a *submission* — the egress of a recovered `x` for the target or
  for any instance — is the verifier's passing node (§13) on the instance the claim
  statement node names, or nothing, which is what "no
  submit, ever" (§4) names — and only where that instance is one the human path registered
  (the target, a problem-queue entry) or the gate's instance-maker drew (§6): a passing node
  on an instance the worker chose is rendered as a finding about that instance, never as a
  submission, since a worker that mints `(P, x·P)` pairs can mint true submissions by
  volume, §9's forbidden state; a passing node on any other instance is not
  egress-eligible.
  The renderer and its refusal predicate are gate-bundle fields
  with the §4 planted pair (an artifact asserting an unregistered claim must FAIL, a fully
  referenced one must PASS); the submission rule lands with the verifier at M0, the renderer
  with the negative-results map at M4. *Why:* the documented fabrication in this plan's
  evidence base was a hallucinated table in a written paper (`research/PROPOSALS.md` C5),
  an output artifact, and a harness that gates only its storage has left its output surface
  ungated.

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
    dedup (a positive signal only). The first library items are authored as M1 Challenge
    fixtures under the §7 protocol; the library mechanism at M4 imports them rather than
    starting empty.
- **Negative-results map (first-class, citable):** "approach X provably fails on prime-field
  curves, here's why" is a durable artifact, not a ledger footnote. A well-mapped landscape
  of what-doesn't-work-and-why saves the next researcher years. Every entry carries the
  ledger record of §4 (hypothesis key, refutation kind, evidence node, method, measured
  parameter points, result with CI, decision, retry predicate, caught_by) plus, for measured negatives, the ladder's
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

Recorded results of the 2026-09 language and agent-ergonomics review
(`research/briefs/language-and-agent-ergonomics.md`, so they are not re-walked): no surveyed
source measures a correctness or cost benefit from a harness written in Rust, Lean 4 or
Elixir/OTP that outweighs the Python-native test discipline of §13 — the coordination language
is an operator default in §16 and the authority-language rule (§16 decision 13) says where
Python is not the implementation; the comparator's transitive-closure statement check is the
state of the art for statement identity (no tool hashes a statement modulo proof), so the F4
hasher hashes what the comparator compares; DBOS on SQLite is the one embeddable
durable-execution runtime and is the comparator spike for P3's tick table at M3 (§15), while
Restate's introspection surface is the bar `cairn status --json` meets without adding a
binary; MCP is not a control surface for driving `cairn` (schema cost is paid on every
prompt; the CLI with `--json` is); a Docker image digest is not a content-addressed
environment identity (§16 decision 14); Bazel and Buck2 do not model floating-point or
CPU-feature drift, which is what the §2 numeric profile records.

---

## 13. Build order (each milestone gated by a demonstrable property)

- **M0 — the real slice.** Substrate schema (§3) + **one exemplar skill built end-to-end**
  (content-addressed I/O, captured seed, self-test, declared cost profile) + Tier-0 verifier
  + tier gate. M0 begins by executing the stack facts it stands on and recording them, with
  their tags, in `research/grounding/` (§16) — among them the §3 facts (WAL mode, the busy
  timeout, the append-only flag refusing truncation by the orchestrator's process user) and
  the §4 write boundary (that user can write neither the pin nor the attestation file). *Done
  when:* it runs the exemplar skill on a
  40-bit toy curve; a deterministic M0 fixture (an integration fixture, not a second
  research skill) derives `x` and `Q = xP` from that output; the subprocess verifier
  accepts that pair, rejects a one-coordinate and a one-scalar negative fixture,
  classifies a forced backend crash as FAIL, and refuses — before the subprocess spawns — a
  submission that names its own `(P, Q)` rather than the statement node's (§4); and the
  generator output, derivation receipt,
  verifier result and gate-run record are hashed, self-tested, cost-tagged substrate nodes;
  the tier gate refuses a fixture launch declaring a tier two above its ticket and records
  `TierRefused`; a gate run against a bundle whose hash differs from the pin fails closed;
  a write to the pin and a write to the attestation file, each attempted as the
  orchestrator's process user, are refused by the operating system, and a `review_verdict`
  row whose digest matches no attestation record is absent to `justify`;
  `justify` returns STRONG-EMPIRICAL from a synthetic `ladder_table` evidence node with
  verdict KEEP whose attempt carries a passed reproducibility record, returns the CONJECTURE
  ceiling for the
  same table with that record absent, returns no justification at all for that table graded
  `AuditOnly` (§3: inadmissible as evidence), returns a coverage violation
  when the table's population does not cover the statement's scope, and returns a lattice
  violation when a synthetic `statistical` node is offered for PROVEN, against a synthetic
  statement hash; and a blob unreachable from the roots table is collectable
  while a rooted one is not.
  Everything else plugs into this shape — get it right once, the verifier included.
  - *Exemplar skill:* `toy_curve(bits, seed) → (p, a, b, n, P)` — a random prime `p` of
    `bits` bits, random `(a, b)`, group order via PARI `ellcard` (Shanks–Mestre through
    50 bits, milliseconds per curve; at 60 bits `ellcard` is SEA at ≈ 75 ms per curve and
    overflows PARI's default stack, so the search uses `ellsea(E, 1)` early-abort with an
    explicit stack ceiling and confirms with `ellcard`), accept if the order is prime
    (acceptance ≈ c/ln p, so expected tries grow like `ln p` with a geometric spread whose
    sd equals its mean; the recorded draws span 11–220 at 30–50 bits and are not a profile —
    M0 measures the constant over ≥ 50 seeds per size before declaring one), with a
    BSGS-vs-SEA *algorithm* cross-check on the order, valid for `bits ≤ 50` only (at 60
    bits PARI's generic path is SEA and the two agree by construction); a second
    *implementation* needs a non-PARI backend, an M0 install decision and not an
    assumption (§2 axis rule). Its known-answer corpus is four cases with origin declared
    per field — one F_p triple whose curve and order are `upstream_vendored` (PARI's
    `y² = x³ − 3x + 1` over F_5, order 7) and whose `P`, `Q = 3P` and `x = 3` are derived
    locally and re-checked by postcondition at every self-test run (`ord(P) = 7`, `3P = Q`),
    never trusted as vendored; two vendored curve-and-order cases (one at 150 bits with
    composite order; the other's `P` is not explicit upstream and is chosen locally under the
    same postcondition, the order being prime) and one negative control (`n·Q ≠ O`); no
    second complete `(P, Q, x)` triple exists upstream and a locally completed one is
    `author_supplied` — plus a `randomized_postcondition` arm on every
    generated curve (`isprime(n)`, `n·P = O`, `n` inside the Hasse interval) and for the
    verifier (draw `x`, set `Q = xP`, assert `OK`; draw `x' ≠ x`, assert `FAIL`); its cost
    profile is "Tier-0, ≈ c·ln p tries".
  - *Tier-0 verifier:* subgroup membership (`n·Q = O`) then `xP == Q`, in a subprocess
    with decimal-string inputs and a one-line result, the curve, `n`, `P` and `Q` read by
    the gate run from the claim statement node or dispatch record and `x` from the
    submitter (§4); PARI's generic discrete log can
    loop when no solution exists, so membership precedes any log call. *Acceptance is
    affirmative, never residual:* the driver validates arity and every field before
    spawning (the backend zero-fills missing arguments), passes an explicit stack ceiling
    (60-bit `ellcard` overflows PARI's default), and accepts only `exit == 0` **and**
    `stdout == "OK"` **and** empty stderr — a zero exit code is not evidence of anything,
    since the backend exits 0 on fatal errors including stack overflow. The gate's
    planted-failure self-test (§4) includes a forced backend crash that must classify FAIL.
  - *M0 schema includes:* the §3 recipe-key construction, attempt records, cache bits and
    the `BUDGET_EXCEEDED`, `SKILL_YANKED` and `INTERRUPTED` statuses, the hypothesis key and
    the immutable
    hypothesis object, the replay grade and certificate slot, the claim statement node
    (§4), the typed evidence node and the §7 derived-tag rule (`justify`) with append-only
    tag history, the `review_verdict` node (§7) with the attestation file and the digest and
    offset fields of every human-attested row (§4), the `disowned` mark (§3), a GC roots
    table, the columns of the budget ceiling and the verification escrow with its release
    rule (§5), and the gate-bundle pin (§4). The behaviors those columns serve — ceiling
    enforcement, escrow reservation, spend and release, yank reach and `disowned`
    propagation — are exercised first at M1, the first milestone that spends above Tier 0,
    yanks a revision and salts a class; M0 asserts only that its schema admits them, with a
    fixture writing and reading each column, because a behavior no M0 test exercises is
    architecture rather than a slice (the closing rule of this section, applied to M0).
    The first gate self-tests (§4) are the verifier's planted `xP ≠ Q` and forced-crash
    fixtures and the canonicalizer's known-answer vectors for both keys.
- **M1 — single track.** Prover + independent skeptic + ladder, with the ladder's baseline
  skills — `rho_dp` (rho with distinguished points and the §3 witness certificate), `bsgs`
  (the refutation floor) and the gate-owned instance-maker — each shipping the §2
  self-test. *Done when:* every fixture in the M1 planted corpus is caught under a cold
  cache (`skip_cache_lookup`), INCONCLUSIVE counting as an escape, and no matched true
  advance is rejected; minimum corpus, ≥ 30 plantings across it: (a) a BSGS-beating claim
  whose ops at 50 bits are ≥ generic rho and whose pre-registered model claims a sub-rho
  cost, so the catch is the in-sample model-miss REJECT — a claim honest about a ≥ rho cost
  sits inside the band, and INCONCLUSIVE is its correct verdict, as for control (k); (b) a
  correct-ops claim that fails `xP == Q` on
  a fresh ladder instance, which must REJECT, yank the revision and write an `implementation`
  entry against it and no `measured` entry on the hypothesis key (§6); (c) a Lean Solution
  with `sorryAx` or an extra axiom; (d) a
  Lean Solution proving a strictly weaker statement than the Challenge; (e) a small-numbers
  pattern that dies under the counterexample hunt; (f) a claim seeking STRONG-EMPIRICAL
  with no repro node; (g) statistical evidence offered for PROVEN; (h) a PROVEN claim with
  a weaker premise in its transitive closure; (i) a non-reproducible measurement; and ≥ 4
  positive controls that must PASS — the must-PASS half of §4's gate discipline, without
  which a gate that rejects everything passes the bar: (j) rho with the negation map,
  pre-registered at ≈ 0.886√n and submitted as a claim against the plain-rho baseline, is
  KEPT (its √2 on group operations at equal memory is a known answer, and the ladder plan's
  trial count is the smallest that KEEPs it with margin); (k) the A/A null arm itself
  submitted as a claim returns INCONCLUSIVE, never KEEP or REJECT; (l) a Lean Solution
  matching its Challenge exactly with axioms inside the allow-list, with an `approve`
  `review_verdict` recorded against the claim statement hash through the human path of §4,
  reaches PROVEN, and the same artifact without the verdict, or with one naming a
  superseded statement hash, stays below it; (m) a reproducible Tier-1 measurement of a
  computed fact (a curve order) with its
  repro node is admitted by `justify` to STRONG-EMPIRICAL, while a `statistical` or
  `repro_node` offered for a statement carrying a cost model returns the CONJECTURE ceiling
  (§7), the same computed fact from a revision whose every corpus origin is `author_supplied`
  with no postcondition arm and no covering cross-check returns that ceiling (§7), and a
  `Verifiable` node whose only verifier ships in its producer's revision is
  graded `AuditOnly` and justifies nothing (§3); the tier-gate fixtures: a
  (synthetic) `KEEP_IN_SAMPLE` table admits the 60-bit rung of its own hypothesis key and
  is refused for every other Tier-2 launch, a KEEP table is refused for a launch whose
  hypothesis key, method identity or implementation revision differs from the table's, a
  launch of a yanked or uncertified revision is refused whatever ticket it holds, a launch
  declaring Tier 1 for a production cost the boundary table assigns Tier 2 is refused, a
  claim carrying both a cost model and a correctness conjecture is refused Tier 2 while
  either its KEEP table or its SURVIVED record is absent, a Tier-3 request holding KEEP and
  no Tier-2 node is refused, a branch on the Tier-1 ticket whose worker launches would carry
  its hypothesis key's charge past the boundary table's Tier-1 cumulative edge is refused at
  the crossing launch while a second ladder run on the same key is admitted (§5), and a
  claim whose hypothesis
  object names the target family with a cost model below the generic bound is routed to the
  router's top class and holds no Tier-3 ticket without the §10 sign-off; the escrow and
  yank fixtures: a launch whose verification component the remaining budget cannot cover is
  refused, a reservation is spent by the §3 policy's first check and released unspent on
  status ≠ OK or disown, a Tier-2/3-grade node with a deferred check keeps its reservation
  after its attempt and its branch reach a terminal status, and a yank disowns every attempt
  inside its reach — served from no cache, no ticket, absent to `justify` — while attempts
  outside it stand; the
  ladder-execution fixtures:
  a dispatch whose method identity differs from its hypothesis object's is refused before any
  trial, a planted method whose self-reported count is below the gate's count by more
  than the tolerance is REJECTed, a planted method that does its own coordinate arithmetic
  and issues dummy counted calls does not reach KEEP, a planted method that opens a network
  socket or writes outside the scratch path fails the ladder's self-test, and a planted
  method holding a BSGS-sized table in process memory while reporting zero table bytes
  exceeds the 50-bit cap on the gate's own measurement (§6); and the dispatch canary: a
  distinct token planted in each
  settings source (project-level and user-level instruction files, a skill file, the
  working tree's status) is absent from the request bytes the dispatch path emits where
  those are observable and from a dispatched worker's echoed context otherwise, the
  grounding record naming which form ran — a gate
  self-test of the dispatch path that re-runs on every toolchain or SDK change and whose
  failure yanks the path as a failed self-test yanks a skill revision (§2). Adds the
  ladder protocol (§6) with its pre-registered model and frozen method identity,
  commit-ordered instance entropy, gate-owned operation counter, comparison protocol and
  trial-count sizing, typed verdicts with the ledger kind each REJECT predicate writes — the
  REFUTED/PARKED entry record of §4 lands here, written by the ladder's REJECT and the
  hunt's KILLED, while the preflight that reads it arrives at M2 — the
  in-sample check, the memory cap at the floor rungs and the memory-model check with the
  gate's RSS-and-scratch measurement, the compiled counted object with its recorded rate
  ratio and the clock and wall-clock checks, the ladder-tested method's allow-list (no
  undeclared arithmetic backend, no network, no writable path but the scratch path), patience
  ceiling,
  A/A null arm and out-of-sample rung, the per-rung reference rate of the clock check,
  per-trial replay grades and the table's reproducibility record, the budget ceiling and
  the verification escrow's reservation, spend and release with yank reach and `disowned`
  propagation (§2, §3, §5),
  the counterexample-hunt
  record (§7), the human queue as a typed object with its closing rule and the
  `acknowledgment` record (§10, §4), the `review_verdict` node and its
  place in the PROVEN derivation (§7),
  the formalization gate's challenge/solution protocol (§7) with its gate-compiled
  Challenge, its gate-owned axiom computation, the claim-statement-to-formal-statement
  binding and planted-`sorry` and wrong-statement fixtures — M1 builds and probes the
  statement hasher and measures the gate's cost on a mathlib-importing Challenge before the
  fixture corpus is sized — the statement pre-filters,
  the reproducibility gate's re-run policy (§3) with the `Verifiable` owner rule, the
  transitive `justified_by` query of §7 that fixture (h) exercises (the auditor's sampling
  cadence arrives at M4), the cost-model scoping of `justify`'s kind map and its
  producer-standing ceiling (§7, §2), the
  cumulative edge of §5, the §7 disagreement protocol, the
  proportional-scrutiny router and the no-go checklist's presence check (§8) with the
  router as its consumer and the `nogo_review` node the tier gate reads, and the M1
  decision on the small-numbers floor (§15 P1). *M1 research exit:* one operator-opened
  hypothesis on a named open subproblem carried to a terminal status by the M1 machinery,
  with its ladder table or hunt record, its Skeptic record and a rendered report; the
  campaign's mathematical verdict is not a completion criterion, its completion and
  legibility are. The first library items of §11 are authored as M1 Challenge fixtures under
  the §7 protocol, so the M4 library imports them rather than starting empty.
- **M2 — memory.** Dead-end ledger (refuted-by-hypothesis-key vs parked) + the Formalizer
  worker + the statement-review workflow (the formalization gate and the pre-filters it
  submits to are M1's). *Done when:* a parked branch auto-revives on blocker-clear; a
  refuted hypothesis key is `Blocked` unaided; a proposal whose declared region contains a
  measured REFUTED point for the same method and cost model is `Blocked` though its key is
  fresh; a `supersedes` edge into a REFUTED version with an unmet retry predicate parks with
  `supersedes_refuted_review` until the attributed difference statement is recorded; a
  refutation without a null arm parks the proposal with `null_control_pending`, the blocker
  clears when the re-measurement lands, and the preflight then answers `Allowed` — with the
  table as the evidence that met the retry predicate — when the re-measurement did not
  REJECT and `Blocked` when it did; a proposal differing from a `measured` REFUTED entry
  only in implementation revision is `Blocked`, while one differing from an
  `implementation` entry by a certified new revision is `Allowed`; a new branch opened on a
  key a promoted branch holds — or whose claim statement stands at STRONG-EMPIRICAL after the
  branch that earned it withdrew — or on a sub-region of such a holder's region with the
  same method identity and cost model, parks with `already_settled` until a superseding
  object with its difference statement is recorded; a log truncated to an earlier valid prefix
  fails startup verification against the checkpoint — also when the truncated log has been
  re-extended and its forked head appended to the checkpoint, since every older checkpointed
  head must remain a prefix head (§3) — and an unreachable checkpoint blocks
  promotion; a worker that returns with a claim it opened still open yields a `Leaked`
  record while a harness-terminated attempt yields none; and a green Lean artifact with no
  `review_verdict` stays below PROVEN while the statement-review workflow routes it to the
  human queue; and a Skeptic dispatched against a claim whose `lean_artifact` was produced
  by a real formalization-gate run sees the formal statement hash and verdict and never the
  Solution blob, asserted on the dispatch record's handed-node hashes. Adds the Reframer and
  Experimentalist role templates in the gate bundle with their allow-lists and dispatch
  records under the M1 dispatch canary, the `prior_art` note at hypothesis open (§4), the
  ledger preflight with its measured-point reach,
  `supersedes_refuted_review`, `null_control_pending` and `already_settled` parks with the
  null-control resolution rule, the hash-chained log and its
  head checkpoint (§3, §4), the terminal-status invariant, the statement-review workflow
  that routes green artifacts to the human queue and records `review_verdict` nodes through
  the human path of §4 (§7), and the near-duplicate
  advisory routed to the human or to a `near_dup_review` park (Librarian routing arrives
  with the Librarian at M4).
- **M3 — orchestrator.** Branch tree + bandit + info-per-dollar allocation + structured
  self-redesign (data, not gates). *Done when:* on ≥ 20 seeded runs each containing a
  stalled branch — a branch whose gate-outcome yield over the last `k` ticks is
  indistinguishable from zero — it is force-parked with blocker `low_yield_pivot` within
  `m` ticks unaided, with `k` and `m` pinned in the M3 test plan, no REFUTED row and no
  terminal `withdrawn` status is written by the orchestrator's path in any run, the parked
  branch auto-revives when its pinned predicate clears, and a crash mid-tick resumes without
  double-applying a completed step (§15 P3), every attempt in flight at the crash standing
  at `INTERRUPTED` on restart — never OK, never a leak; and on seeded runs holding one
  branch whose
  hypothesis is the known true advance of control (j) and one whose hypothesis is fixture
  (a)'s method, the orchestrator's own dispatch carries the first to KEEP and a
  STRONG-EMPIRICAL tag through `justify` and the second to a measured REFUTED entry, unaided
  — the motion half of the bar, since a planted corpus measures only false accepts and a
  harness that refuses everything scores perfectly on it; and on seeded runs where one branch
  family pre-registers `k` junk cost models or jittered regions on one method, that family
  does not out-earn control (j)'s branch under the allocation surrogate — a cheap REJECT at
  the 30-bit rung is a gate outcome, and a surrogate that pays for it per cost would teach
  REJECT farming. Decides the allocation mechanics and
  crash-safe tick shape (§15 P3, P6) against that bar, including whether a bandit earns
  its place at all.
- **M4 — scale-out + taste.** Parallel tracks, Librarian gate, problem queue + measured
  selector + human/expert loop, lemma library + negative-results map rendered under the
  egress rule (§10), foundations-auditor.
  *Done when:* multi-track portfolio runs with ledger + calibration coherent, the
  selector's calibration is being tracked, and ≥ 4 parallel tracks under the §3
  concurrency contract leave zero broken chain heads and zero lost attempt rows in the M4
  stress fixture, and the foundations auditor's audit record names its cycle grant and per-stratum
  charges, which reconcile to that grant, its critical set, its
  residual seed and its achieved `bits` on a seeded population where a planted rotten node
  inside the critical set is always found and one in the residual is found at the declared
  rate. Decides the selector audit protocol and the
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
  whose body has changed (a tick table in SQLite; not a workflow server; DBOS on SQLite is
  the one embeddable alternative and is the comparator spike M3 runs against the tick table,
  on the bar that every tick is inspectable through `cairn status --json` and replayable from
  the substrate). *Decides:* M3's
  bar; branch-level bandits are unvalidated in the literature, so the bar, not the prior
  art, decides — including whether a priority queue plus forced park and human taste beats
  a bandit, in which case the bandit is dropped.
- **P4 · Operational alarms (M1–M2).** A split-conformal anomaly flag on ladder and
  self-test measurements (order-statistic threshold returning +∞ when the sample is too
  small rather than clamping) and a one-sided bounded-mean e-process on
  `log(measured/declared cost)`, with repeated `TierRefused` records on one hypothesis key
  (§5) as a third input. Strategy-layer alarms only; the per-run budget ceiling of
  §5 is enforcement, these are drift monitors. A fired alarm is a human-queue item of class
  `cost_drift` (§10) and a strategy input the orchestrator's tick may read to park with
  `budget_preempt`; it moves no tag, ticket or scrutiny class. *Decides:* whether either
  fires on anything the ladder or the ceiling misses; one that never does is dropped.
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
  formalization stack; Python 3.14 via uv as the coordination language — the substrate,
  gates, CLI, workers' dispatch and the builder's test discipline — because the authors are
  LLM agents whose defect rate is lowest in Python in the surveyed evidence, because
  determinism is a property of content-addressing and canonical encoding rather than of the
  language, and because the suite that keeps the builder honest is Python-native. Revisit
  triggers, each a ledger entry and never an assumption: a cost grade the interpreted rung
  cannot meet (answer: a compiled skill under §2, not a harness rewrite); an orchestrator
  concurrency need P6 names; a defect class in Python-authored gate code that a typed
  language would have refused, recorded with the incident.
- **Operator decisions (confirmed; the ledger questions behind each are listed in
  `research/KICKOFF-beads-and-M0.md`):** (1) PARI-only arithmetic at M0 with the
  BSGS-vs-SEA algorithm-axis cross-check through 50 bits; a gmpy2 Hasse-interval BSGS
  enters as the implementation axis at M1. (2) One 60-bit rho measured with cypari2 at M0;
  a compiled rho/BSGS baseline is funded at M1 only if the interpreted rung cannot finish
  inside the Tier-1 budget. (3) Tier-2 spend requires an open operator session until M3.
  (4) The Reframer drafts claim-statement nodes; a human ratifies through the human path of
  §4. (5) Discretionary yanks, yank-reach narrowing and a `salt` issued after no recorded
  yank are human-only, like waivers; a gate verdict — a §2 self-test failure, a §6
  `xP ≠ Q` or count-divergence REJECT — yanks the faulting revision mechanically with the
  default whole-revision reach and bumps that class's salt with it (§3), since a revision
  still minting OK results after its own self-test fails is a gate failing open (§2), and
  the §4 human path carries the reach ruling, never the gate's own yank. (6) A Linux
  container enters at M1 with the formalization gate for the PROVEN gold tier; macOS
  `fake-landrun` is dev-only before that. (7) §15 P5–P7 stay until their decide-by
  milestones. (8) No separate OS user for the orchestrator before M3; at M0 the gate-bundle
  pin is read-only by file permission. (9) A ticket carries its gate-bundle hash; a mismatch
  re-mints the ticket. (10) The Tier-1 cumulative edge is set at M1 as a multiple of the
  measured ladder per-run cost, starting at 4× (CONJECTURE). (11) Human review throughput
  is a number the operator states before M4; none is assumed. (12) The fastest arithmetic
  implementation for the clock-tolerance check is measured at M1 (gmpy2, cypari2, a C
  reference) and recorded in the gate bundle. (13) **The authority-language rule:** a layer is
  implemented in the language of the thing that has authority over its correctness. Checks
  the Lean kernel has authority over — statement identity, the axiom set, kernel replay — are
  Lean programs pinned in the gate bundle (the comparator, `leanchecker`, the F4 hasher as a
  `lake exe`), and Python invokes and records them, never re-derives them from printed text;
  arithmetic is PARI/GP or a compiled skill under §2; everything with no other authority is
  Python. `MAP.md` names the authority of every layer, and a component that parses another
  authority's output to reconstruct its verdict is a gate that is a label. (14) **The
  container digest is input-addressed.** The environment identity a skill or gate records is
  the hash of the environment's specification plus every pinned input (a Nix closure hash is
  the model; a Dockerfile qualifies only with pinned base digests, no network at build time
  and a recorded input hash), never the digest of one build, so a rebuild from unchanged
  inputs is the same identity and a changed input is a different one; the image digest of the
  build that ran is recorded beside it as an artifact, not as the identity. Decision 6's
  container carries this identity.
- **Invariants (not revisable by review):** §0, the gate layer's existence and immutability,
  the calibration taxonomy, the no-go checklist, the ladder, the verifier, and the honest
  baseline of §14 and `HANDOFF.md`. A proposed change that weakens any of them is flagged
  and rejected, not integrated.
