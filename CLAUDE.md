# CLAUDE.md

@AGENTS.md

## Claude Code session mechanics

Facts below hold only under Claude Code on this machine; each was established by hitting it.

- The global destructive-command guard refuses a recursive force-delete outside the system temp roots
  and both checkout forms that discard a path. It also matches the prose that quotes such a command
  inside a heredoc, so a bead comment or note goes through a file written with the editor.
- The command proxy hides a pipeline's output and exit code, mangles a patch written through it, and
  makes shell `diff` report identical files that differ. Read verdicts from a file; park work in
  progress as whole-file copies; settle byte-equality in Python.
- A subagent whose reply exceeds the output cap dies mid-run; an interrupted subagent resumes with its
  context via `SendMessage` to its agent id.
- The compliance audit runs a forked copy of a vendored skill under `~/.claude/skills/`; the local
  changes and their reasons are the paragraph below. Re-apply after any skill update.
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
