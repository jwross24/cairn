# Cairn

A harness for running AI agents on open mathematics problems, built so that fabricating a
result is mechanically harder than reporting an honest negative.

**Status: M0 in progress, 8 of 18 beads closed, 741 tests green.** Nothing here has produced
a research result yet, and by design it cannot until M1 (see [Milestones](#milestones)).

---

## The problem

An agent told to keep working on a hard problem, and also never to fabricate, is under
structural pressure the moment it runs out of honest moves. "Never give up" plus "never
fabricate" collide, and the cheapest resolution available to the agent is to manufacture the
appearance of progress. This is not a prompting failure. Asking more nicely does not change
the incentive.

The documented failure modes in this plan's evidence base are concrete: a hallucinated
ablation table in a written paper, an agent editing its own time limit, an agent removing the
instrumentation that caught it.

## The approach

Persistence lives at the **program** level; honesty lives at the **claim** level.

Progress is defined as *knowledge gained* — a proven lemma, a tighter bound, a refuted
approach, a reproducible regularity, a mapped dead end — never distance to the summit.
Defined that way, an agent can always make an honest move, and "this approach is dead" is a
result rather than a failure. The single forbidden terminal state is manufacturing the
appearance of progress.

Everything else is enforcement. The organizing principle:

> **Mutable strategy, immutable epistemics.** The orchestrator may rewrite the branch tree,
> the funding and the prompts. It may never touch the gates, the calibration taxonomy, the
> ladder, the verifier, or what counts as proven.

## The gates

Each of these is a mechanism, not a guideline. Where one exists today, the bead that built it
is named.

| Gate | What it does | Built |
|---|---|---|
| **Derived calibration tag** | Every claim carries `PROVEN` / `STRONG-EMPIRICAL` / `CONJECTURE` / `SPECULATION`, computed by a gate from typed evidence nodes. No worker or orchestrator can set its own tag. | schema `.5` |
| **Tier-0 verifier** | `xP == Q` in a subprocess, with the instance read from the claim statement node and only the scalar supplied by the submitter. Acceptance is affirmative: exit 0 **and** stdout `OK` **and** empty stderr, because the backend exits 0 on fatal errors. | `.8` |
| **Content-addressed substrate** | Every result is stored under a BLAKE3 recipe key over `(skill identity, inputs, seed, tool versions, container digest, salt)`. Provenance is a storage property, not an audit you run later. | `.3` `.4` |
| **Dead-end ledger** | Refuted hypotheses are keyed by a canonical hash, so two approaches that are secretly the same collide without any agent having to remember. | M2 |
| **Small-scale ladder** | A claim runs against planted-false corpora at small sizes before it may spend a compute tier. | M1 |
| **Formalization gate** | The gate compiles the theorem statement itself and computes the axiom set itself, requiring it to be a subset of `propext`, `Classical.choice`, `Quot.sound`. Nothing reaches `PROVEN` without that *and* a human confirming the statement says what was meant. | M1 |
| **Tier gate** | Compute is tiered; each tier's admission ticket is a result from the tier below. Cheap refutations happen before expensive ones. | `.10` |

## What runs today

```bash
uv sync
uv run pytest -q                       # 741 tests: 318 unit, 423 integration

uv run cairn capabilities --json       # the CLI contract: commands, exit codes, env vars
uv run cairn robot-docs                # agent handbook, printed in-tool
uv run cairn env --json                # toolchain: python, cypari2/libpari, blake3, gp
uv run cairn kat canon                 # canonicalizer known-answer vectors (a gate self-test)
uv run cairn measure toy-curve-tries --sizes 30,40,50 --seeds 50 --json
```

The CLI's caller is assumed to be an agent: stdout is data, stderr is JSON log records, every
read-side command takes `--json`, exit codes are a documented dictionary, and every refusal
names the exact command that resolves it.

## Repo map

```
PLAN.md                     the design, 1,676 lines, converged over 7 review rounds
CLAUDE.md                   project invariants; law for every session, not revisable by review
HANDOFF.md                  the honest baseline and the central tension the design resolves

src/cairn/                  M0 implementation
  canon.py  keys.py         typed canonical encoding + BLAKE3 content addressing
  substrate.py  schema.sql  append-only store: nodes, blobs, lineage, attempts, receipts
  claims.py                 claim statements, evidence nodes, tag history, review verdicts
  verifier.py  gp/          Tier-0 verifier and its PARI script
  skills/toy_curve.py       the exemplar skill: deterministic, self-testing, cost-tagged
  cli.py  exits.py          the agent-facing CLI contract

tests/                      741 tests; integration-first, zero mocks
  vectors/  goldens/        known-answer corpora and golden artifacts, with provenance

research/
  grounding/                stack facts established by executing them on the build machine
  briefs/                   per-source deep dives behind each borrowed mechanism
  PROPOSALS.md              rationale and evidence tag for every mechanism in the plan
  convergence/              audit trail of the 7 review rounds that produced PLAN.md
  SESSION-PROMPTS.md        kickoff prompts for each kind of work session

.beads/                     the task graph (br), with dependency edges
```

`research/convergence/` is large and is not part of the product. It is the record of how the
plan was reviewed, kept so that "seven rounds reviewed this" is a checkable claim rather than
an assertion.

## Design principles

**Thin agents, fat skills.** Agents carry judgment (which subproblem, which approach). Skills
carry capability, with a typed interface and a fixed version, so they are testable, cacheable
and reproducible in a way an agent never is. A "skill" here is a deterministic Python module,
not a prompt.

**Every skill ships a known-answer self-test.** Decomposition multiplies the places a subtle
error can hide, so each unit validates itself on cases where the answer is known. A corpus
supplied only by the worker that wrote the skill is not a self-test, and caps that skill's
results at `CONJECTURE`.

**A cross-check declares its axis.** Two builds of one library are one implementation, not
two. `gp` and `cypari2` both wrap libpari, so agreement between them tests the plumbing and
says nothing about the arithmetic. A cross-check that has never disagreed is reported as
untested, not as passing.

**Scrutiny scales with claim size.** A run announcing it broke the target has produced
evidence that it erred, not evidence that it succeeded. The bigger the claim, the more the
burden inverts against it.

**No claim without a reproducibility node.** A result that is not in the substrate does not
exist to the claims layer.

## Milestones

| | | Status |
|---|---|---|
| **M0** | Substrate, exemplar skill, Tier-0 verifier, tier gate. *Done when* one skill runs on a 40-bit toy curve end to end and yields a hashed, self-tested, cost-tagged node, and the verifier refuses a planted `xP ≠ Q` fixture. | 8/18 beads |
| **M1** | Prover, independent skeptic, ladder, formalization gate. *Done when* every fixture in a planted corpus of 30+ is caught under a cold cache, with 4+ positive controls that must pass. | not started |
| **M2** | Dead-end ledger preflight, hash-chained log, statement review. | not started |
| **M3** | Orchestrator: branch tree, allocation, self-redesign of data only. | not started |
| **M4** | Parallel tracks, problem queue with a measured selector, foundations auditor. | not started |

No research can run before M1. Without the ladder nothing can earn `STRONG-EMPIRICAL`, and
without the formalization gate nothing can be `PROVEN`, so claims produced now would be
claims no gate can grade.

## Honest limitations

The motivating instance is a 254-bit prime-order ECDLP. **That curve almost certainly stays
standing**, and this is written into the project as an invariant that no review round may
soften. The achievable target is publishable increments on open subproblems: an LFD bound for
ECDLP polynomial systems, a low-storage low-Hamming-weight DLP result, a sharp negative
result, a rigorous partial analysis.

A system that cannot say "this stands" is one that will eventually tell its operator what it
wants to hear.

Also true, and worth stating plainly:

- Every stack fact in `research/grounding/` was measured on one machine (arm64 macOS, APFS,
  PARI 2.17.4, libpari 2.17.2). Nothing is claimed for Linux, a second OS user, or another
  filesystem; those rows are marked OPEN with the milestone that will ground them.
- At M0 the pin and attestation file are protected by file mode and flags under a single OS
  user, which refuses overwrite, truncation and rename but does not bind against a process
  that clears the flag first. The second OS user arrives at M3.
- Problem selection is the weakest layer and is deliberately human-anchored. Model panels
  propose and rank with legible reasons; they never return verdicts, because ensembling cuts
  variance rather than shared bias.

## Development

Python 3.14 via `uv`. PARI/GP for arithmetic (`cypari2` in process, `gp` as the verifier
subprocess). Tests are integration-first against real PARI, real `gp` and real SQLite, with
zero mocks; the one permitted fault injection is a seam that a bead declares.

Work is tracked as beads (`br`). `research/SESSION-PROMPTS.md` has a kickoff prompt for each
kind of session, and `CLAUDE.md` carries the invariants plus the working notes that cost a
retry to learn.

## About Contributions

Please don't take this the wrong way, but I do not accept outside contributions for any of my
projects. I simply don't have the mental bandwidth to review anything, and it's my name on the
thing, so I'm responsible for any problems it causes; thus, the risk-reward is highly
asymmetric from my perspective. I'd also have to worry about other "stakeholders," which seems
unwise for tools I mostly make for myself for free. Feel free to submit issues, and even PRs
if you want to illustrate a proposed fix, but know I won't merge them directly. Instead, I'll
have Claude or Codex review submissions via `gh` and independently decide whether and how to
address them. Bug reports in particular are welcome. Sorry if this offends, but I want to
avoid wasted time and hurt feelings. I understand this isn't in sync with the prevailing
open-source ethos that seeks community contributions, but it's the only way I can move at this
velocity and keep my sanity.
