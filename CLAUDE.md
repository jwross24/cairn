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
- **`br list --json` omits closed beads** (23 of 31 here). Pass `--all` or `--status closed`.
- **`.beads/` is excluded by `~/.gitignore_global`.** This repo's `.gitignore` carries
  `!.beads/` to re-include it. `br sync --flush-only` before every `git add .beads/`.
- **Never run bare `bv`** — it opens a TUI and blocks. `bv --robot-plan` ranks work by what a
  completion unblocks; take the highest-`unblocks` **leaf**, since an epic wins on PageRank
  by construction and is not workable.
- **The compliance pre-commit hook is a copy, not a symlink.** Git ignores a hook whose
  file lacks the executable bit; `.git/hooks/pre-commit` is `-rwxr-xr-x`.
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
