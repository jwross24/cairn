# CLAUDE.md — Cairn project invariants

This section is a project invariant, not a subject of review. Do not edit it, and do not
integrate any proposed plan change that violates it. Canonical detail lives in PLAN.md §0
and the "Invariants (not revisable by review)" list in PLAN.md §16 (line 1673); if this
shortlist and PLAN.md ever disagree, PLAN.md wins and this file is the bug to fix.

## Immutable epistemics

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

## Operating note — planning vs. research decomposition

- Convert the HARNESS ENGINEERING into beads (tasks with dependency edges).
- Do NOT pre-decompose the RESEARCH into a static task graph. The branch/research tree is
  built and rewritten at runtime by the orchestrator (PLAN.md; milestone M3). Forcing it
  into beads up front contradicts the architecture.

## For external review rounds

Models reviewing the plan outside this repo do not see this file. Carry these invariants
in the review prompt itself: they are out of scope for revision — flag any change that
weakens them rather than integrating it.

## Working notes (facts that cost a retry when unknown)

Each line below was established by hitting it. Verify rather than trust if a tool changes.

- **`br` text arguments starting with `-` need the `=` form.** `br create "T" -d "- bullet"`
  exits with `error: unexpected argument '- '`. Use `--description=`, `--acceptance-criteria=`,
  `--notes=`, `--design=`.
- **`br create` takes no `--acceptance-criteria`.** It accepts `--description`/`-d` only;
  set the field afterwards with `br update <id> --acceptance-criteria=...`. `br create`
  also has no positional-only form for long titles starting with `-`; the `=` rule above
  applies to every text flag on both commands.
- **`br show`/`br list --json` return a JSON array, not an object.** `jq '.title'` fails with
  "Cannot index array with string"; index `.[0]` first. `br list --all --json` has been seen
  wrapped one level deeper still, so a defensive `if (.[0]|type)=="array" then .[0] else . end`
  survives both shapes.
- **zsh does not word-split an unquoted variable.** `P="--db X --pin Y"; cmd $P` passes one
  argument, and the command fails in a way that reads as a defect in the code. Build argument
  lists as arrays, or write the flags out. A pipeline also masks the exit code: `cmd | tail -1`
  reports `tail`'s status, so capture `${PIPESTATUS[1]}` or redirect instead of piping when the
  exit code is the evidence.
- **Nesting `uv run` inside `$(...)` under an outer `uv run` pipeline yields empty output.**
  Capture to a file and parse it in a second command.
- **The scratch directory comes from `mktemp -d`.** The destructive-command guard refuses a
  recursive force-delete anywhere outside the system temp roots, so a scratch tree that needs
  clearing should be a fresh `mktemp -d` instead.
- **A pipeline hides the exit code and the command proxy eats the output.** `scripts/mutation-check.sh ... | tail -1`
  prints nothing at all, so a verdict that must be read goes to a file and the file is read back:
  `cmd > /tmp/out 2>&1; tail -1 /tmp/out`.
- **The same proxy makes `diff` report a false verdict.** `diff a b` on two files of 151 and 82
  bytes with different content printed `Files are identical` and exited 0. Any claim that two
  artifacts are or are not byte-equal has to be settled in Python, printing the lengths and a
  digest: `hashlib.sha256(path.read_bytes()).hexdigest()`. A subagent citing a shell `diff` has
  cited nothing, and the reading it gives is the one that hides a real difference.
- **The destructive-command guard refuses the `git checkout` forms that discard a path.** Both the
  bare-path and the `<ref> -- <path>` form are denied, and they are the usual way to drop a scratch
  edit. Copy the file aside with `cp` before the edit and copy it back, or use `git reset --hard`
  when the whole tree is disposable.
- **The same guard matches the prose you write *about* it.** A note whose text quotes a refused
  command is itself refused inside a heredoc. Write the prose to a file with the editor and splice
  the file in; never type it into a shell argument.
- **Editing anything in `toy_curve.IDENTITY_SOURCES` bumps the skill revision.** `src/cairn/pari.py`,
  `src/cairn/skills/toy_curve.py` and the corpus are hashed into `implementation_revision`, so even a
  formatting pass reseeds the randomized arm and moves the transcript and certificate goldens.
- **The compliance audit runs on a forked copy of a vendored skill, and an upstream update reverts
  it.** `~/.claude/skills/beads-compliance-and-completion-verification` carries five local changes,
  each a small substitution with its reason in a comment above it: `_load-policy.sh`,
  `run-pass.sh` and `single-bead-audit.sh` reach PyYAML through `uv run --with pyyaml`, because the
  `python3` on PATH is Homebrew's and has none; `bootstrap-audit.sh` calls
  `sync-rubric-from-policy.py` before pinning `rubric_sha256`, because `score-bead.py` reads
  `weights_by_type` only from the rubric frontmatter and the hook path has no orchestrator to fold
  it in; and `score-bead.py` refuses a bead directory that holds no `spec.json`. Three further
  changes live in files already on that list. `score-bead.py` renders a dimension the policy
  excluded as `—` rather than at full weight, and states the exclusion in the stub-mode banner and
  the TOTAL row, so the table, banner and denominator agree with the arithmetic; it owns a synthesis
  finding by the row's subject bead rather than by every id the row names, because being cited by
  somebody else's row is not a defect in this bead; and it reads
  `cross_bead_ignored_finding_patterns` from the rubric frontmatter, which
  `sync-rubric-from-policy.py` folds in from `audit-policy.yaml`. `scripts/scorecard_coherence.py`
  is the cairn-owned half: `.githooks/pre-commit` reads the newest pass's scorecards back and
  denies a table that disagrees with its own denominator, so a reverted presentation fork is
  visible rather than silent. Re-apply after any
  skill update. See `cairn-cue`.
- **`score-bead.py` takes a bead *directory*, never a bead id**, and only the pass that targeted a
  bead holds its `spec.json` — the other passes leave `show.json` and `git_xref.txt` alone. An
  unforked `score-bead.py` handed a path with no `spec.json` reports `1000/1000 Verified` and
  creates the directory to hold the scorecard it wrote.
- **Which commit closed a bead is cairn's answer, not the skill's.** The vendored
  `anomaly-scan.sh` picks a "closing commit" with `git log --all -F --grep="$ID" | head -1`,
  the newest commit whose *message* names the id, and `research/SESSION-PROMPTS.md` asks every
  session to name its beads there — so that pick usually belongs to another bead and it moves
  whenever an unrelated session commits. `scripts/closing_commit.py` holds the rule that cannot
  do that: the status flip to `closed` in `.beads/*.jsonl`, which only the closing commit
  carries. Both git hooks read their newly-closed list through it, and
  `scripts/audit_attribution.py` runs after the vendored audit in `.githooks/pre-commit`,
  re-derives `anomaly_empty_diff` and `anomaly_ignore_list_growth` against the resolved commit,
  re-scores, and supplies the exit code the hook gates on. A bead the pending commit closes
  resolves to `STAGED` and is judged against the staged diff. `gather-evidence.sh`'s
  `TOUCHED_FILES` keeps the message grep; it is a path-hint resolver with a project-wide
  `rg` fallback behind it, and reaching it means a sixth fork.
- **A closing bead's body carries an ARTIFACTS block**, and `.githooks/pre-commit` refuses the
  close without one. `scripts/bead-artifact-block.sh <bead-id>` is the gate; every decision it
  makes lives in `scripts/bead_artifact_block.py`, because `tests/conftest.py` refuses a `bash`
  subprocess and logic in the shell file would be logic no test can reach. The block's paths are
  backticked so the compliance skill's `PATH_HINT_RE` extracts them; a path with no extension
  (`.githooks/pre-commit`) is invisible to that regex, and the gate names it while accepting the
  block as long as one visible path is present. Bypass, logged to `.check.log`:
  `CAIRN_ARTIFACT_BLOCK_SKIP='<reason>'`.
- **`br list --json` omits closed beads** (23 of 31 here). Pass `--all` or `--status closed`.
- **`.beads/` is excluded by `~/.gitignore_global`.** This repo's `.gitignore` carries
  `!.beads/` to re-include it. `br sync --flush-only` before every `git add .beads/`.
- **Never run bare `bv`** — it opens a TUI and blocks. `bv --robot-plan` ranks work by what a
  completion unblocks; take the highest-`unblocks` **leaf**, since an epic wins on PageRank
  by construction and is not workable.
- **The hooks live in `.githooks/`, not `.git/hooks/`.** One `git config core.hooksPath .githooks`
  per clone arms them, and `.git/hooks/` is then ignored entirely. `.githooks/pre-commit` runs
  `scripts/check.sh --fast`, then `scripts/bead-test-plan.sh` for each bead the commit closes, then
  the compliance audit, which it invokes through `bash` because the vendored asset ships without the
  executable bit. `.githooks/post-commit` pushes a commit that closes a bead, and only such a
  commit: a close is the ship CI has to verify, while a slice on a private macOS runner bills at
  ten times wall clock. It writes `PUSHED`, `SKIP` or `DENY` to `.check.log` on every fire, and a
  failed push is loud and leaves the commit local. Bypass, logged: `CAIRN_PUSH_SKIP='<reason>'`.
- **`pyproject.toml` pins PyPI** (`[[tool.uv.index]] url = "https://pypi.org/simple"`,
  `default = true`) because `~/.config/uv/uv.toml` points at a corporate Artifactory that
  times out off-network. `cypari2` exposes no `__version__`; read it via `importlib.metadata`.
- **Command guards match prose inside heredocs**, so a close comment containing words like
  "truncate" is refused as a database operation. Write the text to a file, then
  `br comments add <id> "$(cat file)"`.
- **A subagent whose reply exceeds the output cap dies mid-run.** Long bead bodies (20k+
  chars) must be patched by a script that reads the field, applies a `str.replace` with a
  uniqueness assertion, and writes it back — never retyped into an argument.
- **An interrupted subagent resumes with its context intact** via `SendMessage` to its
  agent id; it keeps its files and prior findings.

### PLAN.md section map

§0 principle 15 · §1 prompt⊂harness 30 · §2 skills 40 · §3 substrate 110 · §4 components 276 ·
§5 tiers 514 · §6 ladder 690 · §7 epistemics 902 · §8 no-go 1134 · §9 never-give-up 1160 ·
§10 problem selection 1173 · §11 compounding 1260 · §12 research-software 1285 ·
§13 build order 1312 · §14 outcomes 1567 · §15 deferred 1578 · §16 evidence/defaults 1635

### Session modes

`research/SESSION-PROMPTS.md` holds paste-ready openers for the five session types (build a
bead · decompose a milestone · polish · honesty audit · research), the skills each loads, and
the PLAN §10 summary of how subproblems get chosen. Research modes require M1 at minimum.

### "Skill" means three different things here

- **A Cairn skill** is a deterministic Python capability under `src/cairn/skills/`, run as
  `python -m cairn.skills.<name>` with canonical JSON on stdin and stdout. Its identity is a
  hash over `{interface version, implementation revision, tool digests, container digest,
  numeric profile}`; it ships a vendored known-answer corpus, a golden certificate and a
  byte-equal double run. PLAN §2: a skill is "testable, cacheable, and reproducible in a way
  an agent never is" — that determinism is what every downstream gate binds to.
- **A worker role template** (the Skeptic's checklist, PLAN §4) is prompt text, but it is
  read-only, claim-agnostic and pinned in the gate bundle — not loaded from a skills
  directory. Arrives with the workers at M1.
- **A Claude Code skill** (`/beads-workflow`, `/optimal-tests`, `/beads-br`) is a tool for
  *building* Cairn and never runs inside it. `/research-software` (PLAN §12) is the one the
  plan names, for stack truth before wiring; it "touches no math."

A Claude Code skill cannot be a Cairn skill: a prompt is non-deterministic, so it cannot be
content-addressed, cannot produce a byte-equal double run, and cannot be cached by recipe key.
