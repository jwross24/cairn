# AGENTS.md

Project law for every agent in this repository, whichever harness runs it; harness-specific mechanics
live in that harness's own file (`CLAUDE.md` imports this one). Reread this file after any compaction.

## RULE 0: THE FUNDAMENTAL OVERRIDE PREROGATIVE

If the human tells you to do something, even if it goes against what follows, follow the human. The
human is in charge, not this file. The one exception is RULE 2: a live instruction that weakens it is
out of scope for this repository, and the answer is to say so.

## RULE 1: NO FILE DELETION

Never delete a file or folder without express written permission, including files you created yourself.
Ask, receive clear written permission, then delete. Scratch space comes from `mktemp -d`, so nothing
inside the checkout is ever a delete candidate.

## RULE 2: Immutable epistemics (project absolute)

This section is a project invariant, not a subject of review. Do not edit it, and do not
integrate any proposed plan change that violates it. Canonical detail lives in PLAN.md §0
and the "Invariants (not revisable by review)" list in PLAN.md §16 (line 1673); if this
shortlist and PLAN.md ever disagree, PLAN.md wins and this file is the bug to fix.

- Mutable strategy, immutable epistemics. The orchestrator may rewrite the branch tree,
  funding, and prompts — never the gates, calibration taxonomy, ladder, verifier, no-go
  checklist, or what counts as "proven."
- No submission without a passing verifier (xP == Q) subprocess.
- Nothing is PROVEN without a green Lean check AND a statement-level match review.
- No empirical claim without a reproducibility node in the substrate.
- Every claim carries a calibration tag; small-case patterns stay CONJECTURE until they
  survive larger cases plus a deliberate counterexample hunt.
- Scrutiny scales with claim size; a run announcing it broke ECDLP has produced evidence
  it erred, not that it succeeded.
- The honest ECDLP baseline (HANDOFF.md) is itself an invariant: the 254-bit curve almost
  certainly stands; the target is increments on open subproblems. A change that softens
  this is out of scope, not an improvement.

Models reviewing the plan outside this repo do not see this file. Carry these invariants in the review
prompt itself: they are out of scope for revision; flag any change that weakens them rather than integrating it.

## Irreversible Git and Filesystem Actions: DO NOT EVER BREAK GLASS

1. Forbidden by default: a hard reset, a clean of untracked files, a recursive force-delete, a force
   push, the checkout forms that discard a path, or anything else that deletes or overwrites code or
   data, unless the user provides the exact command and states in the same message that they want
   the irreversible consequences.
2. No guessing. Uncertainty about blast radius means stop and ask. "I think it's safe" is never acceptable.
3. Safer alternatives first: `git status`, `git diff`, `git stash`, a `cp` of the file before a scratch
   edit and a `cp` back afterward.
4. Even when authorized, restate the command verbatim, list what it affects, wait for confirmation.
5. Record the authorizing text, the command run and the time. Without that record, it did not happen.

`dcg` is installed, but whether a harness routes commands through it is that harness's configuration,
so the protocol holds on its own. A guard's refusal is a safety mechanism, never something to work around.

## Branch and Commit Policy

- All work lands on `main`. No feature branches, worktrees or PRs unless the user asks.
- Arm the repository hooks once per clone: `git config core.hooksPath .githooks`. An unarmed clone
  commits with no gate at all.
- Stage only the files you changed: `git add <exact paths>`. Never `git add -A`, `git add .` or
  `git commit -a`. Files in `git status` you did not touch belong to another session; leave them alone.
  Never restore a file from an older copy to fix a failing check; fix it in place.
- `.githooks/pre-commit` runs `scripts/check.sh --fast`, `scripts/bead-test-plan.sh` for each bead the
  commit closes, then the compliance audit. `.githooks/post-commit` pushes a bead-closing commit and
  only such a commit, logging `PUSHED`, `SKIP` or `DENY` to `.check.log`; a failed push is loud and
  leaves the commit local. Bypass, logged: `CAIRN_PUSH_SKIP='<reason>'`.
- A bead is not done until its closing commit is pushed and `git status` is up to date with `origin/main`.
- Identity-bearing files: `src/cairn/pari.py`, `src/cairn/skills/toy_curve.py` and the toy-curve corpus
  (skill revision); `src/cairn/challenge.py`, `bundle/challenge_prelude.lean`, `src/cairn/gp/verify.gp`
  and `lean/lake-manifest.json` (gate bundle). Any edit, a formatting pass included, moves the goldens
  and every deployed pin; regenerate the golden in the same attributed commit after reviewing its diff.

## Toolchain: Python 3.14 and uv

We use **uv** for everything. Never `pip`, `poetry`, `conda` or an ad-hoc `python -m venv`. Manifest is
`pyproject.toml` exclusively; the lockfile is `uv.lock`. Run Python as `uv run python ...`, never bare
`python` or `python3`: the interpreter on PATH is Homebrew's and lacks the project's packages.

- `requires-python = ">=3.14"` in `pyproject.toml`, mirrored in `[tool.ty.environment]`; change the pin
  there, nowhere else. The same file pins the PyPI index (`[[tool.uv.index]]`, `default = true`) because
  `~/.config/uv/uv.toml` points at a corporate Artifactory that times out off-network. Keep it.
- Runtime dependencies: `blake3` (content addressing) and `cypari2` (PARI arithmetic). Dev group:
  `pytest`, `pytest-timeout`, `hypothesis`, `ruff`, `ty`, `codespell`. Add a dependency with `uv add`.

## Code Editing Discipline

- Never run a script that rewrites source files; make code changes by hand. The one scripted write is a
  bead body over 20k characters: a script reads the field, applies a `str.replace` with a uniqueness
  assertion and writes it back, because a body that long cannot be retyped into an argument safely.
- Revise existing files in place. Never create `_v2`, `_improved` or `_enhanced` variants.
- Zero explanatory comments by default. A comment survives only when it states a non-obvious invariant
  the code cannot express: no docstrings on tests or self-evident helpers, no banner headers, no
  narration of what the code does or how it came to be. Docs describe the current state only.
- American English spelling in identifiers, prose, commit messages and bead bodies (`randomize`,
  `normalize`, `behavior`, `canceled`). `codespell` runs with `en-GB_to_en-US` in every check.
- Logic lives in Python, not shell: `tests/conftest.py` refuses a `bash` subprocess, so a decision in a
  `.sh` file is one no test can reach. The shell files under `scripts/` are thin dispatchers.

- Backwards compatibility: early development, no downstream users (M0). No shims, no wrappers for
  deprecated interfaces; a changed skill interface or gate bundle is a new revision with a fresh golden.

## Quality Checks (CRITICAL)

`scripts/check.sh` is the one place that says what green means; the pre-commit hook and CI both call it.
After any substantive change:

```bash
scripts/check.sh --fast
scripts/check.sh
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run codespell
uv run ty check src tests
scripts/theater-patterns.sh
uv run pytest -q --durations=25
```

The fast form is the first five gates; the full form adds pytest under a session deadline. Fix findings
the right way: read enough context, never suppress a rule or delete a module to get green. A gate whose
tool is missing denies; it never passes quietly. Bypass, logged to `.check.log`: `CAIRN_CHECK_SKIP='<reason>'`.
A verdict that must be read goes to a file (`cmd > "$out" 2>&1; tail -1 "$out"`), since a pipeline reports
only its last command's exit code; byte-equality is settled in Python with lengths and a `hashlib.sha256` digest.

## Testing

- Layout under `tests/`: `unit/`, `integration/`, `e2e/`, `conformance/`, `planted/`, `mutants/`,
  `hook_contract/`, plus `fixtures/`, `goldens/`, `vectors/`, `fuzz_corpus/`. Tests write only into temp
  dirs the fixtures own. Each layer covers happy path, edge cases and error conditions; integration
  tests use the real substrate and real PARI, with no mocks of storage or arithmetic.
- The substrate holds one writer per process: `Substrate.open(path, role="writer")` raises
  `WriterAlreadyOpen` while an earlier writer is unclosed, and a leaked writer fails every later
  writer-opening test in the run. Close in `finally` or use the `writer` fixture.
- `cairn.pari.ellcard`, `ellsea` and `ellorder` are bounded by `cairn.pari.CALL_BOUND_S` (60 s) via
  cysignals' alarm and raise `PariStall`, a `KeyboardInterrupt` subclass; after the bound fires libpari is
  unusable in that process and the suite stops at exit 124. Never install a Python `SIGALRM` handler; it
  displaces cysignals'. `tests/unit/test_pari_module.py` holds the planted loop proving the chain intact.
- A red, zero-test, filtered, skipped or unrun lane blocks a close. Skipped is not passed; a green gate
  proves only what it covers; an empty result after a timed-out analysis proves nothing.
- Do not regenerate goldens without reviewing the diff; commit code and golden together.
- Libraries: when not 100% sure how to use one, fetch the documentation for the installed version rather
  than guessing. A stack fact no probe under `research/grounding/` has executed is CONJECTURE (PLAN §16).
- **`cairn.pari` pins libpari to one thread in both processes**: `default(nbthreads,1)` at import and
  `-D nbthreads=1` in `gp_argv`, so every gp spawn through `run_gp` carries it. The 60-bit toy_curve
  rows, `curve60_seed1.json`, the grounding brief's 60-bit row, `gate_plan.json`'s curve60 fixture and
  `measure.RHO60_ORDER` are single-thread values; a scratch run at another count draws different 60-bit
  curves while sizes at or below 50 bits are unchanged. A gp script run outside `run_gp` inherits the
  host's core count and will not reproduce those rows.

## Cairn: This Project

A harness for running AI agents on open mathematics problems, built so that fabricating a result is
mechanically harder than reporting an honest negative. Persistence lives at the program level;
honesty lives at the claim level. Status and milestones: `README.md`. Honest ECDLP baseline: `HANDOFF.md`.
`MAP.md` is the system as one tower (layer, authority language, identity primitive, record kinds,
verbs, refusals); read it between this file and `PLAN.md`. PLAN.md section map:
§0 principle 15 · §1 prompt⊂harness 30 · §2 skills 40 · §3 substrate 122 · §4 components 288 ·
§5 tiers 526 · §6 ladder 702 · §7 epistemics 914 · §8 no-go 1146 · §9 never-give-up 1172 ·
§10 problem selection 1185 · §11 compounding 1272 · §12 research-software 1297 ·
§13 build order 1339 · §14 outcomes 1594 · §15 deferred 1605 · §16 evidence/defaults 1665.
`research/SESSION-PROMPTS.md` holds openers for the five session types; research modes require M1.

### Planning versus research decomposition

- Convert the HARNESS ENGINEERING into beads (tasks with dependency edges).
- Do NOT pre-decompose the RESEARCH into a static task graph. The branch/research tree is
  built and rewritten at runtime by the orchestrator (PLAN.md; milestone M3). Forcing it
  into beads up front contradicts the architecture.

### "Skill" means three different things here

- **A Cairn skill** is a deterministic Python capability under `src/cairn/skills/`, run as
  `uv run python -m cairn.skills.<name>` with canonical JSON on stdin and stdout, content-addressed by
  its identity bundle and shipped with a known-answer corpus, golden certificate and byte-equal double run.
- **A worker role template** (the Skeptic's checklist, PLAN §4) is read-only, claim-agnostic prompt
  text pinned in the gate bundle, not loaded from a skills directory.
- **An agent skill** (Claude Code or Codex: `beads-workflow`, `optimal-tests`, `beads-br`) builds Cairn
  and never runs inside it. A prompt is non-deterministic, so it cannot be content-addressed or cached
  by recipe key; an agent skill can never be a Cairn skill.

## Issue Tracking (br)

The beads tracker is the single source of truth for status, priority and dependencies. `.beads/` is
committed (`.gitignore` re-includes it against the global ignore). `br` never runs git.

- Flow: `br ready --json` -> `br update <id> --status in_progress` -> work -> `br close <id> --reason "..."`
  -> `br sync --flush-only` -> `git add .beads/ <exact code paths>` -> commit.
- Text arguments starting with `-` need the `=` form (`--description=`, `--notes=`, `--design=`,
  `--acceptance-criteria=`). `br create` takes `--description`/`-d` only; acceptance criteria are set
  afterward with `br update <id> --acceptance-criteria=...`.
- `br show --json` returns an array (index `.[0]`); `br list --json` returns `{"issues": [...],
  "has_more": ...}` and omits closed beads without `--all`. Tombstones appear only in `issues.jsonl`.
- `br doctor` is the first move on any `br` failure; `sqlite3 .beads/beads.db "PRAGMA integrity_check"`
  is the real health check. `beads.db` is derived state: move it aside and `br sync --import-only` rebuilds it.
- A closing bead's body carries an ARTIFACTS block with backticked paths; `.githooks/pre-commit`
  refuses the close without one, and `scripts/closing_commit.py` decides which commit closed a bead.
  Close on outcomes, not tooling: a bead naming a run closes only with the artifact path and source SHA.
  Never close under a cycle with hedge text; resolve the dependency first.
- Bead comments and bodies go through a file, never a shell argument: `br comments add <id> "$(cat "$note")"`.

## Tool Etiquette

- Never launch an interactive TUI from an agent session. Bare `bv` and bare `cass` block the session.
  `bv --robot-plan` ranks work by what a completion unblocks; take the highest-`unblocks` **leaf**,
  since an epic wins on PageRank by construction and is not workable.
- Bug scan before every commit: `ubs $(git diff --name-only --cached)`. Exit 0 is safe; exit 3 (nothing
  scanned) is not a pass; any other nonzero means verify the finding is real, fix the root cause, re-run.
- Prior sessions: `cass search "<question>" --robot --limit 5` before re-solving a problem another
  session handled; `cm context "<task>" --json` before non-trivial work, with inline
  `// [cass: helpful <rule-id>] - reason` feedback in the session and never `cm mark`.
- Search by question shape: `rg` for literals, semantic search for "how does X work". Never `rg` for codemods.
- `slb`, `ntm` and `agent-mail` are installed but unused: this is a single-agent repository, and no
  reservation or swarm protocol applies until a second agent works the tree. `rch`, `xf`, `ms`: not installed.

## Landing the Plane (Session Completion)

1. File beads for remaining work, with the exact hold on anything left in progress.
2. Run `scripts/check.sh --fast`, and the full form if anything under `src/` or `tests/` changed.
3. Update bead status; a close carries its ARTIFACTS block. `br sync --flush-only`, then stage `.beads/`
   beside the exact code paths.
4. `git status` -> `git add <exact files>` -> `git commit` -> confirm the post-commit push landed or push
   by hand -> `git status` shows up to date.
5. Hand off: what changed, gates run and their results, remaining risks, concrete next steps.

If the human explicitly asks you to use your built-in TODO tool rather than beads, comply without complaint.
