# AGENTS.md

Project law for every agent in this repository, whichever harness runs it (`CLAUDE.md` imports this file). Reread this file after any compaction.

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
and the "Invariants (not revisable by review)" list in PLAN.md §16 (line 1750); if this
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
- Arm the repository hooks once per clone: `git config core.hooksPath .githooks`.- Stage only the files you changed: `git add <exact paths>`. Never `git add -A`, `git add .` or
  `git commit -a`. Files in `git status` you did not touch belong to another session; leave them alone.
  Never restore a file from an older copy to fix a failing check; fix it in place.
- `.githooks/pre-commit` runs `scripts/check.sh --fast --paths <the commit's staged paths>`,
  `scripts/bead-test-plan.sh` for each bead the commit closes, then the compliance audit. The gates
  see the index, not the working tree; the tree-wide run belongs to CI. An index that stages nothing
  takes the tree-wide form. `.githooks/post-commit` pushes a bead-closing commit and only such a
  commit, logging `PUSHED`, `SKIP` or `DENY` to `.check.log`; a failed push leaves the commit local. Bypass, logged: `CAIRN_PUSH_SKIP='<reason>'`.
- A bead is not done until its closing commit is pushed and `git status` is up to date with `origin/main`.
- Identity-bearing files, skill revision: `src/cairn/__init__.py`, `src/cairn/canon.py`,
  `src/cairn/ec.py`, `src/cairn/env.py`,
  `src/cairn/instances.py`, `src/cairn/keys.py`, `src/cairn/log.py`,
  `src/cairn/pari.py`, `src/cairn/profile.py`, `src/cairn/skills/__init__.py`, `src/cairn/skills/bsgs.py`, `src/cairn/skills/bsgs_corpus.json`,
  `src/cairn/skills/bsgs_schema.py`, `src/cairn/skills/instance_maker.py`, `src/cairn/skills/instance_maker_corpus.json`,
  `src/cairn/skills/order_bsgs_gmpy2.py`,
  `src/cairn/skills/rho_dp.py`, `src/cairn/skills/rho_dp_corpus.json`,
  `src/cairn/skills/rho_dp_schema.py`, `src/cairn/skills/slope_weight_a.py`, `src/cairn/skills/slope_weight_a_corpus.json`,
  `src/cairn/skills/slope_weight_b.py`, `src/cairn/skills/slope_weight_b_corpus.json`,
  `src/cairn/slopemodel/__init__.py`, `src/cairn/slopemodel/slopemodel_a.py`,
  `src/cairn/slopemodel/slopemodel_b.py`,
  `src/cairn/slopemodel/slope_predicates.py`, `src/cairn/slopemodel/slope_hunt_executor.py`,
  `src/cairn/slopemodel/slope_hunt_verifier.py`,
  `src/cairn/skills/toy_curve.py`, `src/cairn/skills/toy_curve_corpus.json`.
- Identity-bearing files, gate bundle: `bundle/Containerfile`, `bundle/allow_lists.json`,
  `bundle/auditor.json`, `bundle/challenge_prelude.lean`, `bundle/container.json`,
  `bundle/gate_plan.json`, `bundle/ladder_plan.json`, `bundle/lean.json`,
  `bundle/role_templates.json`, `bundle/scrutiny.json`, `bundle/skeptic_scope.json`,
  `bundle/tiers.json`, `bundle/verifier.json`, `bundle/waivable_checks.json`,
  `bundle/worker_roles.json`, `lean/Cairn/Axioms.lean`,
  `lean/Cairn/StatementHash.lean`, `lean/lake-manifest.json`, `src/cairn/challenge.py`,
  `src/cairn/gp/verify.gp`, and the four vendored prefilter linter sources
  `lean/vendor/formal_conjectures/FormalConjecturesForMathlib/Lean/Elab/InfoTree/Util.lean`,
  `lean/vendor/formal_conjectures/FormalConjecturesForMathlib/Tactic/Linter/Term.lean`,
  `lean/vendor/formal_conjectures/FormalConjecturesUtil/Linters/ExistsImplicationLinter.lean`,
  `lean/vendor/formal_conjectures/FormalConjecturesUtil/Linters/StubLinter.lean`.
- Any edit to a file on either list, a formatting pass included, moves the goldens and every
  deployed pin; regenerate the golden in the same attributed commit after reviewing its diff.
  `tests/unit/test_identity_sources.py` holds both lists against the code.

## Toolchain: Python 3.14 and uv

We use **uv** for everything. Never `pip`, `poetry`, `conda` or an ad-hoc `python -m venv`. Manifest is
`pyproject.toml` exclusively; the lockfile is `uv.lock`. Run Python as `uv run python ...`, never bare
`python` or `python3`.

- `requires-python = ">=3.14"` in `pyproject.toml`, mirrored in `[tool.ty.environment]`; change the pin there, nowhere else. Keep the PyPI index pin (`[[tool.uv.index]]`, `default = true`). Add a dependency with `uv add`.
  Before changing a dependency, the pin or the index, read `docs/agents/toolchain.md`.

## Code Editing Discipline

- Never run a script that rewrites source files; make code changes by hand. The one scripted write is a
  bead body over 20k characters: a script reads the field, applies a `str.replace` with a uniqueness
  assertion and writes it back.
- Revise existing files in place. Never create `_v2`, `_improved` or `_enhanced` variants.
- Zero explanatory comments by default. A comment survives only when it states a non-obvious invariant
  the code cannot express: no docstrings on tests or self-evident helpers, no banner headers, no
  narration of what the code does or how it came to be. Docs describe the current state only.
- American English spelling in identifiers, prose, commit messages and bead bodies.
  `codespell` runs with `en-GB_to_en-US` in every check.
- Logic lives in Python, not shell: `tests/conftest.py` refuses a `bash` subprocess. The shell files
  under `scripts/` are thin dispatchers.

- Backwards compatibility: early development, no downstream users (M0). No shims, no wrappers for
  deprecated interfaces; a changed skill interface or gate bundle is a new revision with a fresh golden.
  Substrate stores are the exception, because they hold research records that cannot be rebuilt: every substrate schema change ships an additive, forward-only migration under `src/cairn/migrations/`, planned with `cairn substrate migrate plan` and applied only with `cairn substrate migrate apply` after a verified backup; never migrate on open. `cairn substrate migrate undo` restores the verified backup and quarantines the current store without deleting it; it never runs a down-migration. A
  change that cannot be additive is a new store, never a rewrite of an existing one (`cairn-ecij`).

- Documentation placement: README covers purpose, installation, user entry points, and limitations.
  Detailed test setup, CI/cache mechanics, scratch retention, and adapter notes belong in
  `docs/development.md`, with a short README link. Per-slice progress belongs in beads.
## Quality Checks (CRITICAL)

`scripts/check.sh` is the one place that says what green means.
`--paths <path> ...` scopes every gate to that list and is the form the hook uses; with no `--paths`
each gate has the scope it always had. CI runs one
`--ci-lane <lane>` per lane declared in `tests/_ci_lanes.py`; their test sets are disjoint and
exhaustive. With no lane argument, the local check runs every set and requires Docker.
Before choosing a local CI lane or aggregate, or editing CI lanes, `scripts/check.sh` lane wiring, or `.github/workflows/ci.yml` test jobs, read `docs/agents/ci-lanes.md`.
During development, run `scripts/check.sh --fast` and `uv run pytest -q tests/<affected-test-module>.py`.
Choose tests from the changed behavior and its callers, including a positive case and a refusal.
If the affected scope is unclear, run the relevant CI lane locally. CI supplies broad regression coverage on the pushed commit; a full local `scripts/check.sh` is for a named cross-suite risk or investigation, not an automatic prerequisite to every commit or bead close.
Run local-only checks when CI cannot exercise the affected behavior. Report exclusions explicitly; a skipped test is not passed. Shared fixture or collection changes
require their contract tests and all affected CI lanes. Record the tested revision and scope; edits invalidate evidence for the behavior they change, not unrelated results.
Mathematical verification under RULE 2 always runs as required and is never replaced by developer
checks or cached verdicts.
Before deciding which checks to run, or interpreting a bypass or exclusion, read `docs/agents/quality-checks.md`.

Fix findings the right way: never suppress a rule or delete a module to get green. A gate whose
tool is missing denies; it never passes quietly. Bypass, logged to `.check.log`: `CAIRN_CHECK_SKIP='<reason>'`.
A verdict that must be read goes to a file (`cmd > "$out" 2>&1; tail -1 "$out"`), since a pipeline reports
only its last command's exit code; byte-equality is settled in Python with lengths and a `hashlib.sha256` digest.

- zsh does not word-split an unquoted variable: build argument lists as arrays. Never nest `uv run`
  inside `$(...)` under an outer `uv run` pipeline. Capture to a file and parse it in a second command.
  Before writing a shell one-liner whose exit code is the evidence, or when a command's output is empty, read `docs/agents/shell-pitfalls.md`.

## Testing

- Tests write only into temp dirs the fixtures own. Each layer covers happy path, edge cases and error
  conditions; integration tests use the real substrate and real PARI, with no mocks of storage or arithmetic.
- Close a substrate writer in `finally` or use the `writer` fixture (one writer per process).
  Before adding a test layer, a fixture that opens the substrate, or a test that writes files, read `docs/agents/testing.md`.
- Never install a Python `SIGALRM` handler; it displaces cysignals' alarm that bounds `cairn.pari` calls.
- A red, zero-test, filtered, skipped or unrun lane blocks a close. Skipped is not passed; a green gate
  proves only what it covers; an empty result after a timed-out analysis proves nothing.
- Do not regenerate goldens without reviewing the diff; commit code and golden together.
- Libraries: when not 100% sure how to use one, fetch the installed version's documentation; never guess. A stack fact no probe under `research/grounding/` has executed is CONJECTURE (PLAN §16).
- **`cairn.pari` pins libpari to one thread in both processes**, and the 60-bit toy_curve rows and
  fixtures are single-thread values. Before touching `cairn.pari`, 60-bit fixtures or `gp` invocations, or writing a test that can hit the PARI call bound, read `docs/agents/pari.md`.

## Cairn: This Project

A harness for running AI agents on open mathematics problems. Honest ECDLP baseline: `HANDOFF.md`. `MAP.md` is the system as one tower; read it between this file and `PLAN.md`.
`research/SESSION-PROMPTS.md` holds openers for the five session types; research modes require M1.
Before starting a research session or implementing a Cairn skill or worker role template, or when locating a PLAN section or distinguishing skill types, read `docs/agents/plan-map.md`.

### Planning versus research decomposition

- Convert the HARNESS ENGINEERING into beads (tasks with dependency edges).
- Do NOT pre-decompose the RESEARCH into a static task graph: the orchestrator builds and rewrites the
  branch/research tree at runtime (PLAN.md; milestone M3).

- **A Cairn skill** is a deterministic Python capability under `src/cairn/skills/`, run as `uv run python -m cairn.skills.<name>` with canonical JSON on stdin and stdout, content-addressed by its identity bundle and shipped with a known-answer corpus, golden certificate and byte-equal double run.
- **A worker role template** (the Skeptic's checklist, PLAN §4) is read-only, claim-agnostic prompt text pinned in the gate bundle, not loaded from a skills directory.
- An agent skill (Claude Code or Codex) builds Cairn and never runs inside it. A prompt is non-deterministic, so it cannot be content-addressed or cached by recipe key; an agent skill can never be a Cairn skill.

## Issue Tracking (br)

The beads tracker is the single source of truth for status, priority and dependencies. `.beads/` is
committed. `br` never runs git.

- Flow: `br ready --json` -> `br update <id> --status in_progress` -> work -> `br close <id> --reason "..."`
  -> `br sync --flush-only` -> `git add .beads/ <exact code paths>` -> commit.
- Text arguments starting with `-` need the `=` form (`--description=`, `--notes=`, `--design=`,
  `--acceptance-criteria=`). `br create` takes `--description`/`-d` only; acceptance criteria are set afterward with `br update <id> --acceptance-criteria=...`.
- `br doctor` is the first move on any `br` failure; `sqlite3 .beads/beads.db "PRAGMA integrity_check"`
  is the real health check. `beads.db` is derived state: move it aside and `br sync --import-only` rebuilds it.
- A closing bead's body carries an ARTIFACTS block with backticked paths; `.githooks/pre-commit`
  refuses the close without one, and `scripts/closing_commit.py` decides which commit closed a bead.
  Close on outcomes, not tooling: a bead naming a run closes only with the artifact path and source SHA.
  Never close under a cycle with hedge text; resolve the dependency first.
- Bead comments and bodies go through a file, never a shell argument: `br comments add <id> "$(cat "$note")"`.
- Run `br` only from inside this repo; elsewhere it binds to whatever store sits on the walk-up path.
- `br` is 0.7.6 with tracker schema 19, and `ci.yml` carries the matching `BR_VERSION`. Every `br` on
  the machine and in CI runs the same version: a 0.6.0 and a 0.7.x writer on one tracker can leave the
  JSONL export refused until `br sync --flush-only`. Asset names and the doctor gate's accepted
  statuses are in `docs/agents/br.md`. A schema-17 store is migrated with `br doctor migrate-schema plan`, then `apply --plan-token`; ordinary commands refuse it with `SCHEMA_MISMATCH`.
- Before using `br` JSON, creating or recovering beads, upgrading `br`, editing `BR_VERSION` or `scripts/beads_doctor_gate.py`, or handling a schema or asset error, read `docs/agents/br.md`.

## Tool Etiquette

- Never launch an interactive TUI from an agent session. Bare `bv` and bare `cass` block the session.
  Take the highest-`unblocks` leaf from `bv --robot-plan`, never an epic.
- Bug scan before every commit: `ubs $(git diff --name-only --cached)`. Exit 0 is safe; exit 3 (nothing
  scanned) is not a pass; any other nonzero means verify the finding is real, fix the root cause, re-run.
- Run `cass search "<question>" --robot --limit 5` before re-solving a problem another session handled and `cm context "<task>" --json` before non-trivial work, with inline `// [cass: helpful <rule-id>] - reason` feedback in the session; never `cm mark`.
- Search by question shape: `rg` for literals, semantic search for "how does X work". Never `rg` for codemods.
- Classify bead scope with `uv run python scripts/route.py <bead-id>`. Fleet routing owns model assignments.
- `slb`, `ntm` and `agent-mail` are installed but unused: this is a single-agent repository, and no reservation or swarm protocol applies until a second agent works the tree.
- Before using `cass`, `cm`, `bv`, `ubs`, `rg` or `scripts/route.py`, or on any mention of `slb`, `ntm` or `agent-mail`, read `docs/agents/tools.md`.

## Landing the Plane (Session Completion)

1. File beads for remaining work, with the exact hold on anything left in progress.
2. Run `scripts/check.sh --fast` and affected tests under Quality Checks. Verify pushed CI before
   declaring shipped; retain relevant local-only evidence and name any unverified scope.
3. Update bead status; a close carries its ARTIFACTS block. `br sync --flush-only`, then stage `.beads/`
   beside the exact code paths. Batch tracker evidence and closes with implementation or documentation
   changes when acceptance is met; pending verification keeps the bead open. A separate
   bookkeeping-only commit is not a required work step.
4. `git status` -> `git add <exact files>` -> `git commit` -> confirm the post-commit push landed or push
   by hand -> `git status` shows up to date.
5. Hand off: what changed, gates run and their results, remaining risks, concrete next steps.

If the human explicitly asks you to use your built-in TODO tool rather than beads, comply without complaint.
