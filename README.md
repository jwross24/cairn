# Cairn

A harness for running AI agents on open mathematics problems, built so that fabricating a
result is mechanically harder than reporting an honest negative.

**Status: M0 in progress. Nothing here has produced a research result yet, and by design it
cannot until M1.** This is a private, personal research project, not a released tool.

## The problem

Tell an agent to never give up and never fabricate, and the two instructions collide the
moment it runs out of honest moves. The cheapest way to resolve that pressure is to
manufacture the appearance of progress: a hallucinated ablation table, an agent editing its
own time limit, an agent deleting the instrumentation that caught it. These are documented
failure modes, not hypothetical ones, and no amount of asking more nicely changes the
incentive.

## The solution

Cairn puts persistence at the **program** level and honesty at the **claim** level. Progress
is redefined as knowledge gained: a proven lemma, a tighter bound, a refuted approach, a
mapped dead end, never distance to the goal. Defined that way, an agent always has an honest
move available, and "this approach is dead" is a result rather than a failure. The one
forbidden terminal state is manufacturing the appearance of progress, and that state is closed
off by mechanism, not by prompt:

| Property | How it holds |
|---|---|
| A claim can't outrun its evidence | Every claim carries a calibration tag (`PROVEN` / `STRONG-EMPIRICAL` / `CONJECTURE` / `SPECULATION`) computed by a gate from typed evidence nodes; no worker or orchestrator sets its own tag. |
| A numeric result can't be faked | The Tier-0 verifier runs `xP == Q` in a subprocess and accepts only on exit 0, stdout `OK`, and empty stderr. The verifier itself exits 0 on fatal errors, so acceptance is checked affirmatively. |
| Provenance can't be an afterthought | Every result is stored under a BLAKE3 key over `(skill identity, inputs, seed, tool versions, container digest, salt)`. Provenance is a storage property, not an audit run later. |
| The orchestrator can rewrite strategy, never truth | It may rewrite the branch tree, the funding, and the prompts. It may never touch the gates, the calibration taxonomy, the ladder, the verifier, or what counts as proven. |
| Compute is spent cheap-before-expensive | Compute is tiered; each tier's admission ticket is a result from the tier below. |

## Quick example

```bash
uv sync
uv run pytest -q                       # unit + integration, integration-first, zero mocks

uv run cairn capabilities --json       # the CLI contract: commands, exit codes, env vars
uv run cairn robot-docs                # agent handbook, printed in-tool
uv run cairn env --json                # toolchain: python, cypari2/libpari, blake3, gp
uv run cairn kat canon                 # canonicalizer known-answer vectors (a gate self-test)
uv run cairn measure toy-curve-tries --sizes 30,40,50 --seeds 50 --json
```

`cairn kat canon` recomputes twelve canonical-encoding vectors and reports `"match": true`
against the pinned digests, or fails the whole vector set on any drift. `cairn env --json`
reports the exact toolchain versions the substrate was built against
(`{"python": "3.14.0", "cypari2": "2.2.4", "libpari": "2.17.2", ...}`), so a stack mismatch is
a diff, not a guess.

## Design philosophy

**Mutable strategy, immutable epistemics.** The dividing line above is the whole design in
one sentence, and it is written into `AGENTS.md` as a project invariant that no review round
may soften.

**Thin agents, fat skills.** Agents carry judgment (which subproblem, which approach). Skills
carry capability, with a typed interface and a fixed version, so they are testable, cacheable,
and reproducible in a way an agent never is. A "skill" here is a deterministic Python module
under `src/cairn/skills/`, not a prompt.

**Every skill ships a known-answer self-test.** Decomposition multiplies the places a subtle
error can hide, so each unit validates itself on cases where the answer is known. A corpus
supplied only by the worker that wrote the skill is not a self-test, and caps that skill's
results at `CONJECTURE`.

**A cross-check declares its axis.** Two builds of one library are one implementation, not
two: `gp` and `cypari2` both wrap libpari, so agreement between them tests the plumbing, not
the arithmetic. A cross-check that has never disagreed is reported as untested, not as
passing.

**Scrutiny scales with claim size.** A run announcing it broke the target has produced
evidence that it erred, not evidence that it succeeded.

**No claim without a reproducibility node.** A result that is not in the substrate does not
exist to the claims layer.

## Why this exists

There is no adjacent open project that combines an agent orchestration loop with an immutable
epistemics layer for a single hard math instance. The closer comparisons are formal-proof
assistants (Lean/mathlib, which the formalization gate calls out to rather than reimplements)
and generic agent harnesses (which have no calibration taxonomy or verifier gate at all).
Neither is a substitute; Cairn is the layer that would sit on top of either.

## Installation

Cairn is not published anywhere; it is run from a clone.

### From source (the only supported path)

```bash
git clone git@github.com:jwross24/cairn.git
cd cairn
uv sync
git config core.hooksPath .githooks   # arms the commit-time gates; an unarmed clone commits with none
```

`uv sync` reads `pyproject.toml` and `uv.lock` and installs both the runtime dependencies
(`blake3`, `cypari2`) and the dev group (`pytest`, `pytest-timeout`, `hypothesis`, `ruff`,
`ty`, `codespell`). There is no `pip`, `poetry`, or `conda` path; `uv` is the only supported
installer, and the project's own rules forbid the others.

### Requirements

- Python 3.14 (`requires-python = ">=3.14"` in `pyproject.toml`; `uv sync` provisions it).
- PARI/GP: `gp` on `PATH` for the Tier-0 verifier subprocess, plus `cypari2` (installed by
  `uv sync`) for in-process arithmetic. `cairn env --json` reports whether both are found and
  which versions.

The Lean integration suite requires the comparator and exporter pinned in
`bundle/container.json`. Provision them outside pytest, from the repository root:

```bash
comparator_work="$(mktemp -d)"
comparator_rev="$(uv run python -c 'import json; print(json.load(open("bundle/container.json"))["comparator"]["rev"])')"
exporter_rev="$(uv run python -c 'import json; print(json.load(open("bundle/container.json"))["comparator"]["lean4export_rev"])')"
git clone https://github.com/leanprover/comparator "$comparator_work/comparator"
git -C "$comparator_work/comparator" checkout --detach "$comparator_rev"
git clone https://github.com/leanprover/lean4export "$comparator_work/comparator/.lake/packages/lean4export"
git -C "$comparator_work/comparator/.lake/packages/lean4export" checkout --detach "$exporter_rev"
(cd "$comparator_work/comparator" && "$HOME/.elan/bin/lake" "+$(cat lean-toolchain)" build lean4export comparator)
export CAIRN_COMPARATOR_CHECKOUT="$comparator_work/comparator"
```

CI provisions the same pins under `.doctor/comparator`, the default lookup path.
Missing prerequisites fail the tests. Developer-mode comparator tests use upstream
`fake-landrun.sh` with reviewed fixtures; they establish comparison behavior, not containment.
The real-prelude ordered-plan test requires fresh kernel replay, rejects `sorry` before
replay, and distinguishes replay timeout from rejection. Its per-test watchdog is 900 seconds,
including setup and teardown; the replay subprocess retains its 600-second bound.
CI runs seven disjoint lanes: Python, Lean, Solution, three ordered-plan cases, and container. The Lean lane includes the
real-prelude closure-comparison and fresh-replay forgery cases from
`tests/integration/test_solution_build_compile.py`; `solution-plan-exact`, `solution-plan-sorry`, and
`solution-plan-timeout` each run one ordered-plan case on an isolated runner. The Solution lane owns the
remaining cases in that file. Each lane has a 1080-second session deadline
and 20-minute job ceiling. The default local check runs every lane's tests;
`scripts/check.sh --ci-lane solution-plan` runs the three ordered-plan cases locally in sequence.

`solutionchecks.prepare_dev` compiles a gate-owned Challenge-only project and computes
its formal statement hash with the bundled Lean hasher. Its prepared value binds the
claim, bundle, pin, renderer, prelude, theorem selection, and input fingerprints.
`solutionchecks.run_dev` validates that handoff and the submitted hash before any
candidate files or subprocesses. It checks imports, assembles a private project,
builds, checks axioms, performs fresh kernel replay, and compares statement closures.
Rejection or timeout blocks subsequent steps.

`solutionchecks.prepare_container` renders the gate-owned Challenge in a private
project and computes its hash inside the pinned Linux image without host Lean.
It validates inputs and copied dependencies before returning a prepared value
bound to the claim and image. `assert_prepared(..., image=image)` checks this
handoff; `run_dev` refuses container-prepared values before candidate work.

`solutionchecks.compile_container` checks that handoff, the submitted hash, and
the import allowlist before assembling a separate candidate project. It copies
pinned Linux dependencies, builds both Solution and Challenge by image ID without
network access, and checks input and dependency integrity before returning the
compilation result. The prepared project is not mounted during candidate execution.
A successful compilation, including one containing `sorry`, is not proof acceptance.
This step does not run the axiom check, fresh replay, or statement comparison.

`solutionchecks.check_container_axioms` accepts a successful compilation bound to
the same bundle and pin. It checks candidate inputs and dependencies, builds the
bundled axiom extractor in a separate Linux project, and validates its canonical
theorem-indexed output against the permitted axioms. Candidate compilation does
not mount the extractor; inspection mounts it read-only. A `sorryAx` dependency
fails this check. Input and dependency integrity are checked before returning.
This is axiom evidence only, not fresh replay, statement comparison, or PROVEN.

The prepared value is an in-process handoff owned by the trusted gate caller, not
authentication of an arbitrary caller-constructed value or a persisted gate-run row.
The caller selects the theorem names. Fingerprints cover tracked inputs, not cached
artifact certification or concurrent-write containment. A passing developer-arm
result does not provide containment, persist evidence, or grant PROVEN.

`container.formal_statement_hash` builds the bundled hasher and a caller-prepared
Challenge project in the pinned ARM64 Linux image, then computes the formal digest.
It checks the toolchain version and commit, executes by OCI image ID with networking
disabled as the caller's non-root UID/GID, and logs that ID beside the digest.
Private project permissions remain unchanged; build caches use the mounted project.
Each container run has a unique owned name. A client timeout stops that container
before returning the timeout; an unsuccessful stop raises a cleanup error naming
the container, so termination is not claimed when the daemon cannot confirm it.
Its project dependencies must be
provisioned for Linux by the trusted caller. It does not execute a Solution or emit
a gold verification result. The `container` CI lane runs the real elliptic-curve
hash pair and rejection cases on a native Linux ARM64 runner; absent Docker is a failure.
The check script's whole-project typing targets macOS, the M0 host platform. The Linux job also checks
the container adapter, preparation code, Lean invocation code, and container tests against Linux APIs.

Linux test dependencies support an explicitly provisioned local cache:

```bash
uv run python tests/_linux_dependencies.py --cache .cache/linux-dependencies
CAIRN_LINUX_DEPENDENCY_CACHE="$PWD/.cache/linux-dependencies" scripts/check.sh
```

Provisioning runs outside pytest. Tests only read the configured cache, validate every
file including ignored compiled artifacts, and copy dependencies into private temporary
projects. The key binds the actual Docker image ID, Lean pins, manifest, project
configuration, and requested modules. Missing or corrupt configured entries fail;
without the variable, tests provision a temporary seed. Failed provisioning directories
remain available for diagnosis. Cache records require a trusted local producer and
are not proof certificates. Every proof check retains its execution requirements.
The provisioning command records the exact local image ID; warm runs inspect and
validate that image without rebuilding it. A cache-specific Docker tag retains the
image independently of the build tag. A removed image requires provisioning
into a fresh cache directory. Changing bundle identity selects a separate image record.

CI provisions temporary Linux dependencies. Cross-run CI seed reuse requires persistence
of the exact Docker image as well as the dependency cache; a matching image tag alone
does not establish that identity.

## Quick start

```bash
uv sync
uv run cairn capabilities --json       # read this first: every command, exit code, env var
uv run cairn robot-docs                # the same contract as a handbook, meant to be pasted into an agent's context
uv run pytest -q                       # confirm the checkout is green before touching anything
```

`cairn capabilities --json` and `cairn robot-docs` are the canonical entry points for an
agent driving this CLI; both are generated from the same command registry, so they cannot
drift from what the parser actually accepts.

## Command reference

Global flags, valid before or after the subcommand:

```
--db PATH        substrate SQLite file       (default: var/substrate.sqlite)
--bundle PATH    gate bundle SQLite file      (default: deploy/gate-bundle.sqlite)
--pin PATH       gate-bundle pin file         (default: deploy/gate-bundle.pin)
--attest PATH    attestation file             (default: deploy/attestations.log)
--log LEVEL      log level for JSON records on stderr (default: INFO)
--version        print the version and exit
--robot-help     print the agent handbook (same as: cairn robot-docs)
```

| Command | What it does |
|---|---|
| `capabilities` | Describes the CLI contract: commands, exit codes, env vars, paths. Read-only. |
| `robot-docs` | Prints the paste-ready agent handbook. |
| `env` | Reports the toolchain: Python, cypari2/libpari, blake3, `gp` path. Read-only. |
| `kat` | Runs the canonicalizer known-answer vectors (a gate self-test); exit 2 on any mismatch. |
| `selftest` (alias `self-test`) | Runs a skill's vendored known-answer corpus and records its certificate; exit 2 on any failure. |
| `measure` | Measures a skill's cost constant: `toy-curve-tries`, `rho60`, or `dlp`. Read-only. |
| `gate` | Runs the gate bundle's declarative plan of planted-failure self-tests before any gate is trusted. |
| `ladder` | Loads and validates the ladder plan from the gate bundle, recording the load as a gate run. |
| `bundle` | Compiles, pins, and inspects the content-addressed gate bundle. **Dangerous**, gated by `--force`. |
| `attest` | Creates and appends to the operator-owned, append-only attestation file. |
| `justify` | Derives a claim statement's calibration tag from every evidence node targeting it. |
| `m0-run` (alias `run`) | Runs the M0 slice end to end: gate self-tests, a certified 40-bit generator, a derived instance, a gate-read verification with its negatives. |
| `gc` | Collects blobs unreachable from any root over lineage. **Dangerous**, gated by `--yes` (list-only otherwise). |
| `doctor` | Diagnoses the M0 deploy shape read-only, and repairs the two failure modes it owns with `--fix`. **Dangerous**, gated by `--fix`. Has its own subcommands: `undo`, `capabilities`, `health`, `robot-docs`, `ls`. |
| `startup-scan` | Moves every attempt left `RUNNING` by a dead harness to `INTERRUPTED` before any new launch. |

Every read-side command takes `--json` (`--robot` is an alias). Run `cairn <command> --help`
for a command's own flags; the parser is the source of truth, not this table.

## Configuration

There is no config file. State is read from the default paths above, all overridable per
invocation via the global flags, plus these environment variables (from `cairn
capabilities --json`):

```bash
CAIRN_LOG=DEBUG           # log level when --log is absent (default INFO); JSON lines on stderr
NO_COLOR=1                # honored trivially: cairn never emits ANSI sequences
SOURCE_DATE_EPOCH=...     # any emitted timestamp uses this epoch instead of the wall clock
UPDATE_GOLDENS=1          # test-only: rewrites golden files instead of diffing them
HYPOTHESIS_PROFILE=ci     # test-only: ci (500 examples) or dev (50)
```

`CAIRN_CHECK_SKIP='<reason>'` bypasses `scripts/check.sh` (logged to `.check.log`); it is a
named, logged escape hatch for the commit-time gate, not a runtime setting.

## Architecture

```
                cairn CLI (cli.py, exits.py) -- stdout=data, stderr=JSON logs
                                    |
        +---------------------------+---------------------------+
        |                           |                           |
   Skills layer               Substrate layer               Gates layer
   (skills/toy_curve.py,      (substrate.py, schema.sql:     (bundle.py, gateplan.py,
   pari.py, ec.py) --         nodes, blobs, lineage,         verifier.py, tiergate.py) --
   deterministic, self-       attempts, receipts) --         planted-failure self-tests;
   tested, cost-tagged        one writer per process         pinned bundle hash fails
        |                     content-addressed by            closed on drift
        |                     BLAKE3 recipe key                       |
        +---------------------------+---------------------------+
                                    |
                    Epistemics (justify.py, claims.py)
        calibration tag: SPECULATION -> CONJECTURE -> STRONG-EMPIRICAL -> PROVEN
                (no worker or orchestrator sets its own tag)
                                    |
        Formalization gate (M1, not built) -- Lean kernel replay
        axioms subset of {propext, Classical.choice, Quot.sound}
                                    |
        Orchestrator (M3, not built) -- branch tree, allocation,
                        self-redesign of data only
```

Full layer-by-layer detail, including the authority language and identity primitive for each
layer, lives in `MAP.md`; the design rationale and the seven review rounds behind it live in
`PLAN.md` and `research/convergence/`.

## Troubleshooting

### `GATE_REFUSED` (exit 2) with "bundle hash differs from the pin"

The gate bundle's SQLite file no longer matches the hash in `deploy/gate-bundle.pin`. This
fails closed by design. Rebuild and re-pin deliberately (`cairn bundle build`, then `cairn
bundle pin`), reviewing the diff first. Never hand-edit or `chmod` anything under `deploy/`.

### `ENVIRONMENT` (exit 3): "gp absent" or a PARI stack error

`gp` is not on `PATH`, or a `gp` subprocess hit a stack error. Run `cairn env --json` to see
what was actually found (`gp_bin`, `libpari` version); `cairn doctor` diagnoses the rest of
the M0 deploy shape read-only, and `cairn doctor --fix` repairs the two failure modes it owns.

### `WriterAlreadyOpen` on a substrate call

`Substrate.open(path, role="writer")` allows exactly one writer per process. This fires when
an earlier writer was left unclosed in the same run: close it in a `finally` block, or use
the `writer` fixture in tests. A leaked writer fails every later writer-opening test in the
same run, which reads as many failures from one root cause.

### `PariStall` / the suite exits 124

`cairn.pari.ellcard`, `ellsea`, and `ellorder` are bounded by `CALL_BOUND_S` (60 seconds) via
cysignals' alarm; past that bound they raise `PariStall`, and libpari is unusable in that
process afterward, so the suite stops rather than continuing on a poisoned interpreter. This
is deliberate; do not install a Python `SIGALRM` handler, since it displaces cysignals' own.

### `CONFLICT` (exit 5): database is locked

A second writer holds the substrate past the busy timeout. Only one process should hold a
writer role on a given `--db` file at a time.

## Limitations

- **No research result exists yet, and none can before M1.** Without the small-scale ladder,
  nothing can earn `STRONG-EMPIRICAL`; without the formalization gate, nothing can be
  `PROVEN`. A claim produced before M1 would be a claim no gate can grade.
- **The motivating 254-bit ECDLP instance almost certainly stays standing.** Generic ECDLP at
  this size costs roughly 2¹²⁷ group operations, beyond all realistic compute; this is written
  into the project as an invariant, not a target to be argued down later. The achievable goal
  is publishable increments on open subproblems, not breaking the curve.
- **Every stack fact in `research/grounding/` was measured on one machine**: arm64 macOS,
  APFS, PARI 2.17.4, libpari 2.17.2. Nothing is claimed for Linux, another OS user, or another
  filesystem; those rows are marked `OPEN` with the milestone that will ground them.
- **The write-boundary protection is single-user and macOS-only.** At M0 the pin and
  attestation file are protected by file mode and flags (`os.chflags`, `stat.UF_APPEND`) under
  one OS user on macOS/BSD; this resists overwrite, truncation and rename but not a process
  that clears the flag first, and an Ubuntu CI runner fails before the suite starts. A second
  OS user's worth of protection, and any Linux support, arrives at M3 at the earliest.
- **Problem selection is deliberately human-anchored**, and is called out in the project's own
  design as its weakest layer. Model panels propose and rank candidates with legible reasons;
  they never return verdicts, because ensembling cuts variance, not shared bias.

## FAQ

**Is this an agent framework I can point at my own problem?**
No. It is a harness for one motivating instance (a specific 254-bit ECDLP), with the gates
and epistemics generalized enough to be reusable, but nothing here is packaged for a
different problem today.

**Has it found anything yet?**
No, by design. M0 is substrate and plumbing; the gates that would let a result earn
`STRONG-EMPIRICAL` or `PROVEN` don't exist until M1.

**Why can't the orchestrator just redefine "proven" if it's stuck?**
That is the one thing it is built not to be able to do. The gates, the calibration taxonomy,
the ladder, and the verifier are called out as immutable in `AGENTS.md`, and a proposed plan
change that weakens them is treated as out of scope, not as an improvement to integrate.

**Why PARI/GP instead of Sage or a custom implementation?**
`gp` is the Tier-0 verifier's authority language for arithmetic identity; `cypari2` wraps the
same libpari in-process. Two builds of one library are one implementation for cross-check
purposes, which is why the design tracks the cross-check axis explicitly rather than treating
agreement between the two as independent confirmation.

**What happens if a skill's self-test fails?**
The implementation revision is yanked: the tier gate refuses new launches of it, an in-flight
attempt completes with status `SKILL_YANKED` (never cached, never a ticket, never evidence),
and only a new revision with a fresh certificate clears the yank.

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

## License

MIT, see `LICENSE`.
