# Autonomous Math-Research Harness — Architecture & Implementation Plan (v2)

*A system for open-ended attack research on hard problems (target: ECDLP), built so it
never stops researching and never fabricates, redesigns its own search tree without ever
redesigning what counts as truth, and spends compute cheap-before-expensive with a human
supplying taste where models are weakest.*

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
- **Granularity rule:** grain a skill at *"a capability with a stable interface, a
  self-test, and a declared cost profile" (§5)* — no finer. Too fine and the orchestrator
  burns its budget gluing skills; too coarse and they stop being reusable.

---

## 3. Content-addressed substrate (provenance as a storage property)

- **Every artifact is hashed by `(skill@version, inputs-by-hash, seed, tool-versions,
  container-digest)`.** Provenance stops being an audit you run afterward and becomes how
  results are stored. A result not in the substrate does not exist to the claims DB.
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
- **Retention:** keep lineage + certificates forever (cheap, load-bearing); GC the giant
  intermediate blobs once their derivation is recorded and the result verified. Keep the
  edges, prune the mass.

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
- **Orchestrator (mutable brain):** bandit allocation over active branches (fund yield,
  prune stalls, revive parked, force periodic pivots so it can't rabbit-hole); self-redesign
  = editing *data* (tree/prompts/subproblems), never gates; cannot mark `proven`, cannot
  bypass a gate.
- **Workers (Research-Mode prompt = template):** Librarian (lit-grounding: "tried before /
  why it failed" before any new attack), Reframer (falsifiable subproblems only),
  Experimentalist (small-case → conjecture → counterexample hunt), Prover, Formalizer,
  Skeptic (independent §7).
- **Gate layer (mechanical, immutable):** submission verifier (`xP==Q` subprocess or no
  submit, ever) · small-scale ladder §6 · no-go checklist §8 · formalization gate §7 ·
  reproducibility gate (no substrate node = inadmissible) · proportional-scrutiny router §7
  · tier gate §5.

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
and the tier gate enforces cheap-before-expensive automatically. **Allocation currency is
expected information per compute-dollar**, not raw yield — a cheap experiment that halves a
conjecture's probability outranks an expensive one that nudges a bound. Compute is a
tracked, finite resource flowing through the DAG exactly like claims.

---

## 6. The small-scale ladder (top anti-fabrication device)

Any claimed *algorithmic* advance must, mechanically, before it earns attention at full
size: run end-to-end on prime-order toy curves (~30/40/50/60 bit), actually recover `x`
(`xP==Q`), and show measured scaling matching its *claimed* asymptotic. A "subexponential
attack" that can't beat baby-step-giant-step at 50 bits is refuted on the spot. Cheap,
mechanical, near-impossible to fake; kills the dominant failure mode (proof-shaped text
that's subtly wrong).

---

## 7. Epistemic mechanics (humility made mechanical)

- **Calibration taxonomy (mandatory per claim):** `PROVEN` (formalized) · `STRONG-EMPIRICAL`
  (ladder + repro node) · `CONJECTURE` · `SPECULATION`. No green Lean check → not `PROVEN`.
- **Statement-level review:** Lean verifies a proof is valid, not that you stated the
  theorem you meant. Verified-but-wrong-statement (weaker/trivial, smuggled hypothesis,
  wrong quantifier) is *more* dangerous than an open gap. Check the statement separately.
- **Independent skeptic:** sees only the *statement*, never the prover's reasoning; rewarded
  solely for gaps/counterexamples. If it reads the proof it just agrees — independence is
  the whole value.
- **Proportional scrutiny + the paradox, written in:** tightened bound → clean argument;
  claimed break of the target → formalization + ladder + expert sign-off. **State it in the
  orchestrator: a run announcing it broke ECDLP has produced evidence it *erred*.** The
  bigger the claim, the more the burden inverts against it.
- **Strong law of small numbers (hard gate):** a small-case pattern is a conjecture until it
  survives larger cases + a deliberate counterexample hunt.
- **Standing foundations-auditor (above the per-claim skeptic):** the per-claim skeptic
  catches bad proofs; it can't catch a bad *premise* the whole tree rests on (an FFDA-style
  heuristic everyone assumed). Periodically re-audit the shared assumptions — a tall tower
  on a cracked base is the failure no local check sees.

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
  emits final verdicts.
- **Two non-LLM anchors:** (a) cheap empirical reality — a candidate must yield a Tier-0/1
  testable prediction before "the models like it" counts; (b) a human ruling at the meta
  level (the reasons above are checkable without understanding the proof), with a **domain
  expert signing off on expensive, high-commitment calls**.
- **The selector is itself audited.** Problem-selection is a *pluggable, measured* component:
  track whether greenlit problems panned out, score its calibration, and swap it (single
  strong model / debate / cheap heuristic) if that beats the panel on record. Taste is held
  to the system's own standard.
- **Legible state** is what makes this workable *and* engaging: the branch tree, open
  conjectures, and dead-end map are visible and reach-in-able, so the human contributes
  exactly where they're strong (taste, catching a wrong-statement formalization, challenging
  a calibration tag).

---

## 11. Compounding assets (what makes it accretive across runs)

- **Formalized-lemma library (shared, mathlib-style):** every `PROVEN` lemma lands here, so
  month N is cheaper than month 1 — deeper scaffolding is what "accretive" means.
- **Negative-results map (first-class, citable):** "approach X provably fails on prime-field
  curves, here's why" is a durable artifact, not a ledger footnote. A well-mapped landscape
  of what-doesn't-work-and-why saves the next researcher years.

Without these the system accumulates only *within* a run; with them it accumulates across
them.

---

## 12. Where `research-software` fits

It designs none of the above. Its one job: current, code-level truth on the stack before
you wire it — Lean/mathlib, Sage/PARI/Magma, the orchestration framework, Claude Code's
subagent/Task interface. Output: commands/config/gotchas per tool from the latest stable
tag. De-risks the stack; touches no math.

---

## 13. Build order (each milestone gated by a demonstrable property)

- **M0 — the real slice.** Substrate schema (§3) + **one exemplar skill built end-to-end**
  (content-addressed I/O, captured seed, self-test, declared cost profile) + Tier-0 verifier
  + tier gate. *Done when:* it runs one skill on a 40-bit toy curve end to end, and the
  result is a hashed, self-tested, cost-tagged substrate node. Everything else plugs into
  this shape — get it right once.
- **M1 — single track.** Prover + independent skeptic + ladder. *Done when:* a
  deliberately-planted false "advance" is caught every time.
- **M2 — memory.** Dead-end ledger (refuted-by-hash vs parked) + formalizer + statement-level
  review. *Done when:* a parked branch auto-revives on blocker-clear; a refuted one is never
  re-walked.
- **M3 — orchestrator.** Branch tree + bandit + info-per-dollar allocation + structured
  self-redesign (data, not gates). *Done when:* it reallocates off a stall unaided.
- **M4 — scale-out + taste.** Parallel tracks, Librarian gate, problem queue + measured
  selector + human/expert loop, lemma library + negative-results map, foundations-auditor.
  *Done when:* multi-track portfolio runs with ledger + calibration coherent, and the
  selector's calibration is being tracked.

**Anti-over-engineering:** the remaining real gaps are the ones you can't see from the
whiteboard — they appear on contact with a running system. Build M0 before adding another
design layer; a running 40-bit slice will reveal more than more architecture will.

---

## 14. Honest expected outcomes

This can plausibly produce **real, publishable increments on open subproblems** — an LFD
bound, a low-Hamming-weight result, a clean negative result, a rigorous partial analysis.
Your specific 254-bit curve almost certainly **stays standing**, because only a general
algorithmic breakthrough moves it and the field's consensus is that such a breakthrough may
not exist. That sentence is load-bearing: a harness that can't tell you "this stands" is one
that will eventually tell you what you want to hear.
