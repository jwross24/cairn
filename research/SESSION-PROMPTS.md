# Session types and their kickoff prompts

Paste-ready openers for a fresh Claude Code session in `~/Documents/cairn`. The
session-start hook injects the vault's `projects/cairn/hot.md` plus any fragments captured
since the last rollup, so the prompt only has to name the *mode* and the invariants.

Every mode assumes the standing constraints: `CLAUDE.md` invariants are not revisable;
`/just-say-no-to-process-porn-and-ceremony` applies throughout; borrow mechanisms never
code (ADR-024); Python via `uv` only; zero explanatory comments.

**Skills each mode loads.** Name them in the prompt — a fresh session has none of them
loaded, and the file paths below (`scripts/polish-round.sh`, `references/POLISH-ROUND.md`)
live *inside* `/beads-workflow`, so they are dangling references until it is invoked.

| skill | what it carries | modes |
|---|---|---|
| `/beads-br` | `br` CLI: always `--json`, sync is explicit, git is yours, no cycles | A B C D |
| `/beads-bv` | `bv` graph triage: which bead is most accretive, and why | A B |
| `/beads-workflow` | conversion + polish rounds; owns `scripts/polish-round.sh` and `references/POLISH-ROUND.md` | B C |
| `/beads-compliance-and-completion-verification` | closed-bead audit; Mode D's subject. Mode A gets it from the pre-commit hook, which runs unprompted | D |
| `/optimal-tests` | the pre-close test audit that found a broken gate on every bead | A |
| `/testing-metamorphic` · `/testing-fuzzing` · `/testing-golden-artifacts` · `/testing-conformance-harnesses` · `/testing-real-service-e2e-no-mocks` | the shape a declared test type actually takes; load the ones the bead's TEST PLAN names | A |
| `/just-say-no-to-process-porn-and-ceremony` | honesty inventory, credit floor | all |

## Keeping the main context clear

A long session dies from reading, not from writing. What fills a context window is surveys —
which modules exist, what the CLI registry expects, how a sibling test builds its fixtures —
and the main agent needs a digest of those, never the file bodies. Modes B and C already push
every polish round into a fresh subagent for the same reason; A and D get the same treatment.

Delegate, and keep only the digest:

- the pre-build survey: the modules the bead names, their public signatures, the conventions a
  new file has to match (import style, mutant and corpus layout, fixture names)
- the `/optimal-tests --audit` pass, which is read-only and whose product is a triage table
- any "where is X defined" question whose answer is one line

Keep in the main context, always:

- every edit to source or tests
- every command whose output becomes close evidence
- each disagreement with the bead text, and the decision on each finding

**A subagent's report is a claim, not evidence** (`/just-say-no-to-process-porn-and-ceremony`).
Re-execute anything it cites before that output reaches a close comment, and read any diff it
produced for weakened assertions, new mocks and regenerated goldens. A fresh subagent auditing
tests the main agent wrote beats the main agent re-reading its own — that is the reason to
delegate the audit, and it is still short of independent verification.

The anti-ceremony rule binds here too: delegate to save context, never to look thorough. A
subagent whose digest nobody reads is ceremony with a bigger token bill.

## Deferred findings need an owner in the graph

A finding recorded only in a close comment is a finding nobody picks up. Anything declined
during the test audit, and every gap the No-Claim line names, has to be reachable from the bead
graph: name the downstream bead that owns it, or create one with `br create` plus a `br dep`
edge and name that.

The owning bead must still be **open** when the note is needed. A comment on the bead you are
about to close is lost the moment you close it: pick the bead that will act on the finding, not
the one you happen to be holding.

The bar is a real capability gap someone will implement — a platform the write boundary does not
cover, a predicate deferred to the next milestone. A property of the system that a downstream
bead simply has to know goes in that bead's comments, not in a bead of its own; `br comments add
<id> "$(cat file)"` avoids the command guard, which reads prose inside a heredoc and refuses
words like "truncate" as database operations.

## Choosing what to work on next (`/beads-bv`)

Never run bare `bv` — it opens a TUI and blocks the session. Use:

```bash
bv --robot-plan | jq '.plan.tracks[].items[] | {id, priority, unblocks}'   # ranked, parallel-safe
bv --robot-insights | jq '.Cycles'                                          # graph health
br ready --json                                                             # unblocked, unranked
```

`--robot-plan` ranks by what a completion unblocks, which is the accretive question.
Observed on this graph: it put `.10` (gate bundle/pin/tier gate, unblocks `.11`/`.12`/`.7`)
above `.9` (unblocks nothing) — the right call, and faster than reading the dep tree.

**Caveat, measured 2026-08-21:** `bv --robot-next` returned the *epic* `cairn-m0-e0s`
(PageRank 71%, "unblocks 3 downstream issues"), which is not workable — an epic has the
highest centrality by construction, since every child hangs off it. Use `--robot-plan` and
take the highest-`unblocks` **leaf**, or filter epics out of `--robot-next` yourself.

---

## Mode A — Build the next M0 bead (the current mode)

```
Load /beads-br, /beads-bv and /just-say-no-to-process-porn-and-ceremony.

First establish a clean baseline: `git status --short` (expect empty) and `uv run pytest -q`
(expect all green). Tell me the numbers before you touch anything — if something is already
red, we deal with that first rather than attributing it to this bead's work later.

Pick the work with `bv --robot-plan` (highest-unblocks LEAF, not the epic — see the caveat
below). Read CLAUDE.md and `br show <bead-id> --json` in full, its `comments` field included —
a prior session carries findings forward there. Claim it with
`br update <bead-id> --claim`.

Then dispatch a subagent to survey what the bead builds on: the modules it names, their public
signatures, the conventions a new file has to match, and anything already shipped that the bead
assumes. Ask for a digest, not file bodies, and read those files yourself only when you are
about to edit them.

Give every survey and audit subagent this clause verbatim; without it a survey reports a
confidently wrong defect roughly as often as a real one:

> Execute a command that settles any claim about whether code is valid, runs, compiles,
> imports or is broken, and cite the command. Your training data may predate this project's
> runtime, so a construct that looks wrong to you may be valid here: the interpreter is the
> authority, not your recollection. Prefix an unexecuted claim with "UNVERIFIED:" and name the
> command that would settle it. Never report an unexecuted suspicion as a defect.

Run through to close-or-blocked in one pass. A committed slice is a checkpoint, not a place to
hand back: surface mid-way only for a disagreement with the bead text or a decision that is the
operator's, never to report progress.

Build in the order the acceptance criteria are written and commit each working slice, whatever
the spec's length: a slice that passes its own tests is the unit of progress, and the commit is
where the reasoning for it lives. If the session ends with the bead unfinished, say plainly
which criteria are met and which are not, and leave it open. Never close it partially.

Read the bead's TEST PLAN before writing any test, and load the `/testing-*` skill for each
shape it names: metamorphic relations, fuzz-shaped robustness, golden artifacts, a conformance
harness, real-service end-to-end. A bead that names a shape and gets a hand-rolled approximation
of it is the failure this step prevents. `scripts/bead-test-plan.sh <bead-id>` reads the file
paths back out of the bead and checks each one exists and collects; the pre-commit hook runs it
for every bead a commit closes, so a plan that was never written blocks the close.

Build it exactly as the bead specifies, integration test first (real PARI via cypari2,
real gp subprocess through cairn.pari.run_gp, real SQLite under tmp_path), unit tests
second. Zero mocks; the only fault injection allowed is at a seam the bead declares.
Every subcommand registers through `cli.register(...)` and inherits the contract in
cairn-m0-e0s.17 (stdout data / stderr diagnostics, exits from cairn/exits.py, CliError
with a copy-pasteable next_command).

If a probed fact disagrees with the bead text, do NOT force the test green: assert the
observed truth, and tell me the disagreement.

Before you propose closing: dispatch a FRESH subagent to run /optimal-tests in --audit mode over
the bead's test files against its acceptance criteria. Fresh eyes on tests you wrote beat your
own re-reading, and its report is a claim — re-execute what it cites before you believe it.
Treat any "this protection is untested" finding as a hypothesis until a mutation proves it:
`scripts/mutation-check.sh <file> <old-text> <new-text> <pytest-targets>` exits 0 only when the
mutation went red and the file came back byte-identical. CLAUDE.md's working notes carry the
shell constraints it works around.

Apply the findings. Every finding you decline, and every gap your No-Claim line names, has to be
reachable from the bead graph: name the downstream bead that owns it, and create one with
`br create` plus a `br dep` edge where none does.

Then close with evidence: every acceptance bullet re-executed, raw output pasted, bound to the
commit SHA, file:line for each touched file, and a No-Claim line.
```

**Checklist before you say the bead is done**

- [ ] `uv run pytest -q` green, tail pasted
- [ ] The bead's own positive observable run and pasted
- [ ] The planted negative observed *failing* (not assumed)
- [ ] `/optimal-tests --audit` run; every finding applied or explicitly declined with a reason
- [ ] Any "untested protection" finding mutation-proved: `scripts/mutation-check.sh <file> <old> <new> <targets>`
- [ ] Every new assertion proved able to fail. Ask of each: if the thing it guards were perfect,
      would it still pass? If yes the oracle is wrong, not the code
- [ ] Any regenerated golden: its diff read first, and the change is exactly the intended one
- [ ] Honesty inventory filled out in writing before the close comment, and its disposition carried
      into the report (`/just-say-no-to-process-porn-and-ceremony` names closing an item as a trigger)
- [ ] Close comment: commands + raw output + file:line + No-Claim + what was *not* independently verified
- [ ] Survey and test audit ran as subagents; anything they cited re-executed in the main context
- [ ] Every declined finding and every No-Claim gap named in a downstream bead, created where none owned it
- [ ] Every `/testing-*` skill the bead's TEST PLAN names was loaded before those tests were written
- [ ] `scripts/bead-test-plan.sh <bead-id>` exits 0
- [ ] `scripts/check.sh` green (format, lint, spelling, suite)
- [ ] `br sync --flush-only`, `.beads/` committed (the pre-commit hook audits the close)

---

## Mode B — Decompose the next milestone (only when its predecessor closes)

PLAN §13 decomposes a milestone when the prior one closes; `CLAUDE.md` forbids
pre-decomposing the research tree at any time.

```
Load /beads-workflow, /beads-br, /beads-bv and /just-say-no-to-process-porn-and-ceremony.

M<N-1> is closed. Read CLAUDE.md, PLAN.md §13 M<N>, and the M<N> epic's children (they are
component-grain placeholders labeled needs-decomposition).

Decompose each placeholder into granular beads under the epic — every bead self-contained
(an implementer never opens PLAN.md), with a positive observable, a planted negative, a
No-Claim line, named test types, and the two close-evidence bullets. Add real `br dep`
edges. Do NOT pre-decompose the research tree.

Then run polish rounds until a round finds nothing: each round is a FRESH subagent (not
you re-reading your own work), fed by `scripts/polish-round.sh`, applying the seven checks
in /beads-workflow's references/POLISH-ROUND.md — especially "probe any doubtful
stack fact on this machine before prescribing it". Require a ROUND VERDICT line and tell
each round that finding nothing is a successful result. Commit each round.
```

---

## Mode C — Polish-only session (no implementation)

```
Load /beads-workflow and /beads-br.

Run polish rounds over the bead graph until a round finds nothing. Each round is a fresh
subagent fed by /beads-workflow's scripts/polish-round.sh, applying its
references/POLISH-ROUND.md. The bar for
an edit after round ~5 is a concrete defect: a contradiction between two beads or between
a bead and shipped code, a plan clause with no owner, a wrong or unprobed stack fact, a
missing planted negative, a name used but never defined, a relation or observable that
cannot hold. Not taste. Commit each round separately.
```

Use this after any content change (new beads, a test-plan pass) — a content change resets
the round counter, because it adds surface.

---

## Mode D — Honesty audit

```
Load /just-say-no-to-process-porn-and-ceremony and /beads-compliance-and-completion-verification.

Step back from everything this project's sessions have done. With fresh, impartial eyes and
nothing to defend, apply /just-say-no-to-process-porn-and-ceremony in full: fill out all
three worksheets in writing, and surface anything that could reasonably be construed as
deceptive, not-entirely-truthful, or hiding the ball — including ceremony loops that spent
time and tokens without shipping capability. Report the verdicts plainly, uncomfortable
truths first. Do not soften findings about your own behavior.

Delegate the evidence sweeps — what the git log and the bead comments of the window actually
show — to subagents, and keep the three worksheets and their verdicts in your own context: they
are the deliverable, and a verdict assembled from digests you never checked is the failure this
mode exists to catch. Re-execute what a sweep cites before a verdict rests on it.

Where the audit finds work rather than a verdict, that work goes into the graph as a bead, not
into the report alone.
```

Run this when a green result feels too easy, before any milestone is declared done, and
whenever several beads closed in one session.

---

## Mode E — Research (NOT AVAILABLE YET)

The harness cannot run research until the gates that make a research claim meaningful
exist. Concretely:

| capability | needs | milestone |
|---|---|---|
| a claim can be laddered against a planted-false corpus | prover + skeptic + ladder | **M1** |
| a dead end is never re-walked | ledger preflight + hash-chained log | **M2** |
| the tree allocates its own effort | orchestrator | **M3** |
| subproblems are queued, scored and the selector is audited | problem queue + measured selector + Librarian | **M4** |

Before M1 there is no ladder, so nothing can earn STRONG-EMPIRICAL; before the
formalization gate there is no PROVEN. Running "research" now would produce claims no gate
can grade — the exact failure the plan exists to prevent.

---

## How subproblems get chosen (PLAN §10) — read before Mode E ever runs

§10 opens by naming this the hardest part: *"choosing the right problem is the part it does
worst, because models pattern-match to problem-shaped things."* So selection is explicitly
human-anchored:

- **The queue** holds open subproblems scored `tractability × payoff × novelty`, ranked and
  **injectable by a human**.
- **A model panel is a filter, never an oracle.** It proposes and ranks *with legible
  reasons* (tractable? novel? what falsifies it? tried before?) and surfaces its own
  disagreement; it never emits a verdict. Ensembling cuts variance, not shared bias — a
  confident consensus that is wrong is the worst case for a non-expert driver.
- **Two non-LLM anchors gate a candidate:** (a) it must yield a **Tier-0/1 testable
  prediction** before "the models like it" counts for anything; (b) a **human ruling** at
  the meta level, with a **domain expert signing off** on expensive high-commitment calls,
  recorded through the human path of §4.
- **The selector is itself audited** — track whether greenlit problems panned out, score its
  calibration, swap it if a cheaper heuristic beats the panel on record. "Panned out" is
  adjudicated by a gate, never by the selector. The measurement protocol lands at M4 (§15 P2)
  and the swap is always a human decision.

**The candidate classes, from `HANDOFF.md`** (the honest baseline: the 254-bit curve almost
certainly stands, and the target is publishable increments on open subproblems):

- an **LFD bound** for ECDLP polynomial systems
- a **low-storage low-Hamming-weight DLP** result
- a **sharp negative result**
- a **rigorous partial analysis**

**What research is needed to get there:** the Librarian's "tried before / why it failed"
grounding is what turns a candidate into a real subproblem, and it arrives with M4. Until
then, subproblem choice is the operator's, informed by a panel used strictly as a ranked
list of legible reasons. §9's four legitimate moves bound what a session may do with one:
reframe · prove an impossibility · pivot to an adjacent open subproblem · tighten a bound ·
map a dead end. Progress is knowledge gained, never distance to the summit.
