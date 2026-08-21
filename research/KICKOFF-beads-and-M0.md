# Kickoff for the next session: beads conversion + M0 build

Paste-ready context for a FRESH Claude Code session started in `~/Documents/cairn`
(repo `jwross24/cairn`, branch `main`). The session-start hook injects the vault's
`projects/cairn/hot.md`; this file is the longer form.

## State

- `PLAN.md` is the converged v3 (1,659 lines; 5 council rounds + 2 guard rounds; promoted
  from `research/convergence/plan-r7.md`; v2 frozen at `research/PLAN-v2-frozen.md`).
  Rounds 6–7 accepted no HIGH item, added no component and moved no milestone; the
  synthesizer's strict LOW-only rule still read NEEDS-ANOTHER-ROUND on two MED operand
  changes, and the machinery was frozen there on purpose (an eighth governance round
  with M0 unbuilt is the meta-trap named in `/just-say-no-to-process-porn-and-ceremony`).
  Ledgers: `research/convergence/r1..r7/ledger-r*.md`; seat reviews beside them.
- Invariants: `CLAUDE.md` and PLAN §0 / §16. The honest baseline (the 254-bit curve almost
  certainly stands) is not a mood to be talked out of.
- Evidence: `research/PROPOSALS.md` (why each mechanism is there, with tags), `research/briefs/`
  (13 deep dives), `research/grounding/` (facts probed on this Mac: PARI 2.17.4 installed via
  brew, cypari2 via uv in a scratch venv, elan/lean absent, comparator runs unsandboxed on
  macOS, leanchecker --fresh does not reject `sorryAx`).
- Standing constraints: borrow mechanisms never code (ADR-024; all six mined repos carry the
  MIT + OpenAI/Anthropic rider); `/just-say-no-to-process-porn-and-ceremony` on every step;
  operator defaults (name Cairn; Sage/PARI backend; toy-curve M0 exemplar; SQLite+BLAKE3;
  Lean 4 + mathlib) stand unless challenged with evidence.

## Operator decisions the council left open — proposed defaults (confirm in one batch)

| # | Question (ledger) | Proposed default |
|---|---|---|
| 1 | Second arithmetic implementation at M0? (r1 Q1) | PARI-only at M0 with the algorithm-axis cross-check (BSGS vs SEA) through 50 bits; add the gmpy2 Hasse-interval BSGS from the session script as the implementation axis at M1 |
| 2 | Compiled rho/BSGS baseline skills for the 60-bit rung? (r1 Q5, r2 Q1, r3 Q1) | Measure one 60-bit rho with cypari2 at M0; fund a compiled baseline at M1 only if the interpreted rung cannot finish inside the Tier-1 budget |
| 3 | Tier-2 spend requires an open operator session? (r1 Q2) | Yes until M3; revisit when the orchestrator exists |
| 4 | Author of claim-statement nodes (r1 Q3) | Reframer drafts; human ratifies through the human path |
| 5 | Who yanks a skill / issues a `salt` (r2 Q3, r3 Q2) | Human-only, like waivers |
| 6 | Linux host/container for the PROVEN gold tier (r1 Q4) | A Linux container enters at M1 with the formalization gate; macOS `fake-landrun` is dev-only before that |
| 7 | Prune §15 P5–P7 now? (r3 Q6) | Leave them to their decide-by milestones; pruning is churn |
| 8 | Separate OS user for the orchestrator at M0 (r3 Q3) | Defer to M3 (no orchestrator before M3); the gate-bundle pin is read-only by file permission at M0 |
| 9 | Tickets minted under a prior gate bundle (r6 Q1) | A ticket carries its bundle hash; mismatch ⇒ re-mint |
| 10 | Tier-1 cumulative edge value (r6 Q2, r7 Q1) | Set at M1 as a multiple of the measured ladder per-run cost (start 4×, CONJECTURE) |
| 11 | Human review throughput (items/week) to size queues (r4 Q3, r5 Q4) | Operator states a number before M4; none assumed |
| 12 | Fastest arithmetic implementation on the build machine for the clock-tolerance check (r6 Q3) | Measure gmpy2 vs cypari2 vs a C reference at M1; record in the gate bundle |

Anything not confirmed stays an open question in the plan; nothing above changes §0.

## Sequence for this session

1. **Beads conversion** — `/beads-workflow` with its exact prompt over `PLAN.md` §13 (harness
   engineering only: M0 first, then M1–M4 epics with dependency edges; the research tree is
   never pre-decomposed, per `CLAUDE.md`). `br init` in the repo first; commit `.beads/`.
   Use `/beads-br` for the CLI and `/beads-bv` for the graph view; polish rounds until a
   round finds nothing; arm `/beads-compliance-and-completion-verification` before the first
   implementation close. Every bead carries a positive observable, a planted negative, and a
   No-Claim line (what green does not prove).
2. **M0 build** (PLAN §13 M0, exemplar `toy_curve`; Tier-0 verifier; substrate schema with the
   §3 key construction, cache bits, replay grade, `justify`, tag history, roots table; the
   first gate self-tests: the verifier's planted `xP ≠ Q` fixture and the canonicalizer's
   known-answer vector). Integration test first (real PARI subprocess, real SQLite), unit
   tests second. Python via `uv`; PARI via cypari2 (`pari.allocatemem(64_000_000)` before
   any 60-bit work; `ellsea(E,1)` early-abort for 60-bit searches).
3. **Done when** (from the plan): one skill runs on a 40-bit toy curve end to end and yields a
   hashed, self-tested, cost-tagged substrate node; the verifier refuses the planted fixture.
4. Commit on green; push to `jwross24/cairn`; `/wrap` at session end (vault fragment +
   status patch).

## What is and is not independently verified (honesty inventory, short form)

- Verified by execution this session: OpenRouter seats respond (smoke test 4/4); PARI
  timings at 30–60 bits (grounding brief, commands recorded); comparator/SafeVerify/
  leanchecker behavior on this Mac (grounding brief, commands recorded); e-process primitive
  math read and checked by the reviewer (`fsqlite-types/src/eprocess.rs:173-215`).
- Claims, not evidence: every council seat review (LLM output; dispositions were
  evidence-checked by the synthesizer against briefs, which are themselves agent reads of
  code at pinned commits with file:line); the plan's numbers at 60 bits are CONJECTURE by
  the plan's own tags.
- Nothing in the plan has been built or run; no gate exists yet; no bead exists yet. The
  plan is a plan.
