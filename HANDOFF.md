# Structured Mathematical Research Harness — Context Handoff

## What this is

A design for an agent-operated system that conducts open-ended research on hard
mathematics problems — built so it never stops researching, never fabricates results, and
can redesign its own search strategy without ever redesigning what counts as truth. The
detailed architecture lives in the companion design doc (`research_harness_design.md`,
"v2"); **this** document is the reasoning, the load-bearing decisions, and the
non-negotiables a fresh agent needs before touching the plan.

## Origin and the honest baseline (read first — this framing is load-bearing)

The project began from a concrete instance: recover `x` from a 254-bit prime-order
elliptic-curve discrete log (ECDLP), given `(p, a, b, P, Q, n, h)`. The honest baseline,
established and not to be softened:

- The instance was checked against every standard weakness (anomalous/Smart, MOV/Frey-Rück,
  singular, smooth order, small/structured/low-Hamming-weight scalar, small-CM). None apply.
  It's a generic prime-order curve.
- Generic ECDLP at this size costs ≈ √(πn/2) ≈ 2¹²⁷ group operations — beyond all real
  compute. No prompt, agent, or cleverness changes that.
- Over prime fields there is no known efficient index calculus (Semaev's factor base has no
  working decomposition); Weil-descent / summation-polynomial methods need extension fields.
  The field's own consensus (Galbraith–Gaudry survey) is that subexponential ECDLP may not
  exist here at all.
- **Therefore the specific 254-bit curve almost certainly stays standing.** The worthy,
  achievable target is real, publishable *increments on open subproblems*: an LFD bound for
  ECDLP polynomial systems, a low-storage low-Hamming-weight DLP result, a sharp negative
  result, a rigorous partial analysis.

A system that cannot say "this stands" is one that will eventually tell its operator what
they want to hear. Preserving this baseline **is** the honesty of the system.

## The central tension the design resolves

Three requirements — never give up, never fabricate, keep epistemic humility — collide if
"giving up" is defined as "outputting a negative conclusion." An agent with no honest
forward move is under structural pressure to manufacture the appearance of one. Resolution:

- Persistence lives at the **program** level; honesty at the **claim** level.
- *Never give up* = there is always a legitimate next action: reframe, prove an
  impossibility, pivot to an adjacent open subproblem, tighten a bound, or map a dead end.
  It does **not** mean never concluding a path is dead or never reporting a negative.
- **Progress = knowledge gained** (a proven lemma, a tighter bound, a refuted approach, a
  reproducible regularity, a reduction), not distance to the summit. Measured this way the
  agent never runs out of honest moves.
- The single forbidden terminal state: **manufacturing progress.**

## The one principle

**Mutable strategy, immutable epistemics.** The orchestrator may rewrite the branch tree,
funding, worker prompts, and subproblems freely. It may **never** edit what counts as
proven, the gates, the no-go checklist, the ladder, the verifier, or the calibration
taxonomy. Meta-level fixed, object-level fluid. (Compute corollary: cheap results gate
expensive ones, and cost is predicted before it is spent.)

## Architecture essentials (full detail in design doc)

- **Prompt ⊂ harness.** A prompt is a worker's job description; the harness is durable state
  + mechanical gates + scheduler + self-redesign loop. Honesty properties must be *enforced*
  checks, not requests — under "never give up" pressure, requested compliance is the first
  thing that fails.
- **Thin agents, fat skills.** Agents carry judgment, skills carry capability; every skill
  ships a known-answer self-test and a declared cost profile; grain a skill at "a capability
  with a stable interface, a self-test, and a cost profile" — no finer.
- **Content-addressed substrate.** Every artifact hashed by `(skill@version, inputs-by-hash,
  seed, tool-versions, container-digest)`. Provenance becomes a storage property; a REFUTED
  branch is recognized by hash collision (dead-ends structural, not memory-dependent);
  replayable ≠ verifiable → store cheap certificates for nondeterministic/expensive work;
  keep lineage + certificates forever, GC the big blobs.
- **Compute tiers 0–3** (instant / one-core-minutes / many-core-hours / cluster-days), each
  admitted by a result from the tier below; allocation currency = **expected information per
  compute-dollar**; compute is a tracked, finite resource.
- **Gate layer (mechanical + immutable):** submission verifier (`xP==Q` or no submit),
  small-scale ladder (toy-curve end-to-end + measured scaling before full size), no-go
  checklist (Shoup √n / isogeny invariance / prime-field obstruction), formalization gate
  (Lean + statement-level review), reproducibility gate, proportional-scrutiny router.
- **Epistemic mechanics:** calibration taxonomy (PROVEN / STRONG-EMPIRICAL / CONJECTURE /
  SPECULATION); statement-level review (verified-but-wrong-statement is worse than an open
  gap); independent skeptic (sees only the statement); standing foundations-auditor
  (re-audits shared premises the whole tree rests on); strong-law-of-small-numbers gate.
  Written-in paradox: **a run announcing it broke ECDLP has produced evidence it *erred*.**
- **Problem selection & taste (the real bottleneck, human-anchored):** a human-rankable
  problem queue scored `tractability × payoff × novelty`; a mixture-of-models panel used as
  a **filter** that surfaces disagreement and ranks with legible reasons — never as an
  oracle, because ensembling cuts variance, not shared bias. Anchored by cheap empirical
  reality (a Tier-0/1 testable prediction) and human/expert sign-off on expensive calls. The
  selector is itself pluggable and measured against whether its greenlit problems panned out.
- **Compounding assets:** a shared formalized-lemma library (month N cheaper than month 1)
  and a first-class, citable negative-results map (what fails and why).

## Non-negotiables (the immutable set)

1. No submission without a passing verifier subprocess.
2. Nothing is PROVEN without a green Lean check **and** a statement-level match review.
3. No empirical claim without a reproducibility node in the substrate.
4. Every claim carries a calibration tag; small-case patterns are CONJECTURE until they
   survive larger cases + a deliberate counterexample hunt.
5. Scrutiny scales with claim size; the bigger the claim, the more the burden inverts
   against it.
6. The orchestrator can rewrite strategy but not the epistemics above.

## Where the named skills / tools fit

- **research-software:** produces current, code-level truth on the stack to be assembled
  (Lean/mathlib, Sage/PARI/Magma, the orchestration framework, Claude Code's subagent/Task
  interface). De-risks tooling; designs no math.
- **Candidate external techniques to evaluate for specific roles** — *hypotheses to verify
  during the deep dives, not established fits:*
  - **e-values / conformal e-martingales / testing-by-betting** → strong candidate for the
    sequential-evidence and calibration layer: e-processes give anytime-valid evidence
    accumulation with optional stopping, which maps cleanly onto "keep gathering evidence
    for a conjecture without inflating error" and onto how STRONG-EMPIRICAL is scored.
  - **RaptorQ / fountain codes** → candidate for reliable, economical replication and
    durability in the content-addressed substrate and the distributed Tier-2/3 layer.
  - The referenced repos are to be deep-dived one at a time; extract only mechanisms that are
    accretive to a named component above, verified against the design — not adopted wholesale
    because they're clever.

## Live open decisions

- Single-track vs. parallel instances (determines how the portfolio and independent-skeptic
  pieces are wired).
- Formalization stack: Lean/mathlib assumed; confirm coverage for the relevant number
  theory before committing.
- The exact measurement protocol for the problem-selection panel (what "panned out" means,
  over what horizon).
- Skill grain size (the granularity trap: too fine burns budget on glue, too coarse kills
  reuse).
- M0 scope and the first exemplar skill.

## Build order (detail in design doc §13)

**M0 = the real first slice:** substrate schema + one exemplar skill (content-addressed I/O,
captured seed, self-test, cost profile) + Tier-0 verifier + tier gate, demonstrated
end-to-end on a 40-bit toy curve. Then M1 single track (prover + independent skeptic +
ladder), M2 memory (ledger + formalizer), M3 orchestrator (bandit + self-redesign), M4
scale-out + taste layer + compounding assets. Build M0 before adding more design; a running
slice reveals more than more whiteboard does.

## Honest expected outcome

Real, publishable increments on open subproblems are plausible. The specific 254-bit curve
almost certainly does not fall. Keeping that distinction sharp is not pessimism — it is the
mechanism that keeps every calibration tag in the system meaningful.
