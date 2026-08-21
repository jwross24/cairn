# Session types and their kickoff prompts

Paste-ready openers for a fresh Claude Code session in `~/Documents/cairn`. The
session-start hook injects the vault's `projects/cairn/hot.md` plus any fragments captured
since the last rollup, so the prompt only has to name the *mode* and the invariants.

Every mode assumes the standing constraints: `CLAUDE.md` invariants are not revisable;
`/just-say-no-to-process-porn-and-ceremony` applies throughout; borrow mechanisms never
code (ADR-024); Python via `uv` only; zero explanatory comments.

---

## Mode A — Build the next M0 bead (the current mode)

```
Read CLAUDE.md and `br show <bead-id> --json` in full. Claim it with `br update <bead-id> --claim`.

Build it exactly as the bead specifies, integration test first (real PARI via cypari2,
real gp subprocess through cairn.pari.run_gp, real SQLite under tmp_path), unit tests
second. Zero mocks; the only fault injection allowed is at a seam the bead declares.
Every subcommand registers through `cli.register(...)` and inherits the contract in
cairn-m0-e0s.17 (stdout data / stderr diagnostics, exits from cairn/exits.py, CliError
with a copy-pasteable next_command).

If a probed fact disagrees with the bead text, do NOT force the test green: assert the
observed truth, and tell me the disagreement.

Before you propose closing: run `/optimal-tests --audit` over the bead's test files against
its acceptance criteria. Treat any "this protection is untested" finding as a hypothesis
until you delete that protection in a scratch copy and show a test go red — then restore
and verify byte-identical. Apply the findings, then close with evidence: every acceptance
bullet re-executed, raw output pasted, bound to the commit SHA, file:line for each touched
file, and a No-Claim line.
```

**Checklist before you say the bead is done**

- [ ] `uv run pytest -q` green, tail pasted
- [ ] The bead's own positive observable run and pasted
- [ ] The planted negative observed *failing* (not assumed)
- [ ] `/optimal-tests --audit` run; every finding applied or explicitly declined with a reason
- [ ] Any "untested protection" finding mutation-proved on a scratch copy, repo restored byte-identical
- [ ] Close comment: commands + raw output + file:line + No-Claim + what was *not* independently verified
- [ ] `br sync --flush-only`, `.beads/` committed (the pre-commit hook audits the close)

---

## Mode B — Decompose the next milestone (only when its predecessor closes)

PLAN §13 decomposes a milestone when the prior one closes; `CLAUDE.md` forbids
pre-decomposing the research tree at any time.

```
M<N-1> is closed. Read CLAUDE.md, PLAN.md §13 M<N>, and the M<N> epic's children (they are
component-grain placeholders labeled needs-decomposition).

Decompose each placeholder into granular beads under the epic — every bead self-contained
(an implementer never opens PLAN.md), with a positive observable, a planted negative, a
No-Claim line, named test types, and the two close-evidence bullets. Add real `br dep`
edges. Do NOT pre-decompose the research tree.

Then run polish rounds until a round finds nothing: each round is a FRESH subagent (not
you re-reading your own work), fed by `scripts/polish-round.sh`, applying the seven checks
in the beads-workflow skill's references/POLISH-ROUND.md — especially "probe any doubtful
stack fact on this machine before prescribing it". Require a ROUND VERDICT line and tell
each round that finding nothing is a successful result. Commit each round.
```

---

## Mode C — Polish-only session (no implementation)

```
Run polish rounds over the bead graph until a round finds nothing. Each round is a fresh
subagent fed by scripts/polish-round.sh, applying references/POLISH-ROUND.md. The bar for
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
Step back from everything this project's sessions have done. With fresh, impartial eyes and
nothing to defend, apply /just-say-no-to-process-porn-and-ceremony in full: fill out all
three worksheets in writing, and surface anything that could reasonably be construed as
deceptive, not-entirely-truthful, or hiding the ball — including ceremony loops that spent
time and tokens without shipping capability. Report the verdicts plainly, uncomfortable
truths first. Do not soften findings about your own behavior.
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
