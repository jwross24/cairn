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
- **`br show --json` returns a JSON array; `br list --json` returns an object.** `jq '.title'`
  on a `show` fails with "Cannot index array with string"; index `.[0]` first. `list` wraps its
  rows: `{"issues": [...], "total", "limit", "offset", "has_more"}`, so `.issues` is the array
  and `has_more` decides whether the page is the whole answer. A caller that indexes `list`
  like an array gets a dict key and no error. Under br 0.2.22 both returned bare arrays, and a
  defensive `if (.[0]|type)=="array" then .[0] else . end` was needed for `show`.
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
- **`src/cairn/challenge.py` and `bundle/challenge_prelude.lean` are hashed into the gate bundle** as
  the raw objects `challenge_renderer` and `challenge_prelude`, beside `src/cairn/gp/verify.gp` and
  `lean/lake-manifest.json`, so any edit to them, a formatting pass included, moves
  `tests/goldens/gate_bundle_hash.golden` and every deployed pin. Regenerate the golden in the same
  attributed commit.
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
  `sync-rubric-from-policy.py` folds in from `audit-policy.yaml`. It also separates an `n/a` note,
  which means the extractor looked and found nothing, from a `WAIVED` note, which means the phase
  never ran: `NA_MEASURED_DIMENSIONS` counts the first as measured for `docs_etc` alone, because
  the same note on `implementation` awards 250 points to a body the extractor could not read. An
  unverifiable pass is its own verdict rather than a false close, and the `unverifiable` flag it
  emits is what `scripts/audit_attribution.py` blocks on, so a revert leaves that gate keyed on a
  field nobody sets. `.githooks/pre-commit` greps for `NA_MEASURED_DIMENSIONS` and denies without
  it. `scripts/scorecard_coherence.py`
  is the cairn-owned half: `.githooks/pre-commit` reads the newest pass's scorecards back and
  denies a table that disagrees with its own denominator, so a reverted presentation fork is
  visible rather than silent. Re-apply after any
  skill update. See `cairn-cue`.
- **`score-bead.py` takes a bead *directory*, never a bead id**, and only the pass that targeted a
  bead holds its `spec.json` — the other passes leave `show.json` and `git_xref.txt` alone. An
  unforked `score-bead.py` handed a path with no `spec.json` reports `1000/1000 Verified` and
  creates the directory to hold the scorecard it wrote.
- **Which commit closed a bead is `scripts/closing_commit.py`'s answer, not the skill's.**
  The vendored `anomaly-scan.sh` picks it by `git log --grep`, which names another bead's
  commit and moves whenever anyone commits. `scripts/audit_attribution.py` re-derives the
  attributed anomalies against the real closing commit and supplies the hook's exit code.
- **A closing bead's body carries an ARTIFACTS block**, and `.githooks/pre-commit` refuses the
  close without one. `scripts/bead-artifact-block.sh <bead-id>` is the gate; every decision it
  makes lives in `scripts/bead_artifact_block.py`, because `tests/conftest.py` refuses a `bash`
  subprocess and logic in the shell file would be logic no test can reach. The block's paths are
  backticked so the compliance skill's `PATH_HINT_RE` extracts them; a path with no extension
  (`.githooks/pre-commit`) is invisible to that regex, and the gate names it while accepting the
  block as long as one visible path is present. Bypass, logged to `.check.log`:
  `CAIRN_ARTIFACT_BLOCK_SKIP='<reason>'`.
- **`br doctor health` reports healthy on a database `integrity_check` calls malformed**, so
  health is not the check. `sqlite3 .beads/beads.db "PRAGMA integrity_check"` is.
- **`br` is 0.5.7, and `ci.yml` carries the matching `BR_VERSION`.** The 0.5 line publishes its
  release asset as `beads_rust-<version>-darwin_<arch>.tar.gz`; the 0.2 line published `br-`, so
  a version bump that leaves the asset name alone 404s. beads_rust#457 is fixed as of 0.5.6.
  `scripts/beads_doctor_gate.py`'s benign-value allowlist was established on 0.2.22 and accepts
  0.5.7's output unchanged: 55 `ok`, 1 `warn`, `workspace_health: healthy`, verdict advisory.
- **`br doctor` is the first move on any `br` failure**; it names the missing `.beads/.gitignore`
  patterns verbatim and reports a database whose schema the binary refuses. The one thing it will
  not do is recover that case: `--repair` fails closed at exit 4, and its remediation text loops back
  to itself. `beads.db` is untracked derived state, so move the family aside and `br sync --import-only`
  rebuilds it from `issues.jsonl`, which then round-trips byte-identically through a flush.
- **`br list --json` omits closed beads.** Pass `--all` or `--status closed`. `--all` also
  omits tombstones: 58 rows against 66 in `issues.jsonl`, the gap being 8 deleted beads, so the
  JSONL is the only place a tombstone is visible.
- **A `br` run outside a repo fails `NOT_INITIALIZED` and creates nothing.** br walks upward for
  a workspace, so a command run while the repo's `.beads` is absent, or from another directory
  such as the vault, binds to whatever store sits on that path. The empty schema-10 store that
  used to sit at `~/.beads` is parked at `~/.beads.stale-2026-09-02`; a `br` error naming
  schema 17 against 10 means such a store is on the walk-up path again.
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

§0 principle 15 · §1 prompt⊂harness 30 · §2 skills 40 · §3 substrate 122 · §4 components 288 ·
§5 tiers 526 · §6 ladder 702 · §7 epistemics 914 · §8 no-go 1146 · §9 never-give-up 1172 ·
§10 problem selection 1185 · §11 compounding 1272 · §12 research-software 1297 ·
§13 build order 1339 · §14 outcomes 1594 · §15 deferred 1605 · §16 evidence/defaults 1665

`MAP.md` is the system as one tower (layer, authority language, identity primitive, record
kinds, verbs, refusals); read it between this file and PLAN.md.

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
