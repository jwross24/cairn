# Development and verification

Run commands from the repository root. Project rules live in [AGENTS.md](../AGENTS.md);
the system map is [MAP.md](../MAP.md).

## Deployment

The canonical operator sequence in `uv run cairn robot-docs` compiles and pins a bundle,
initializes attestations, certifies the exemplar skill, checks the planted failures, and runs
the M0 slice. Run these commands in order from the repository root:

```bash
uv run cairn bundle build --bundle deploy/gate-bundle.sqlite
uv run cairn bundle pin --bundle deploy/gate-bundle.sqlite --pin deploy/gate-bundle.pin
uv run cairn attest init --attest deploy/attestations.log --bundle deploy/gate-bundle.sqlite --pin deploy/gate-bundle.pin
uv run cairn selftest toy-curve --db var/substrate.sqlite --bundle deploy/gate-bundle.sqlite --pin deploy/gate-bundle.pin
uv run cairn gate selftest --db var/substrate.sqlite --bundle deploy/gate-bundle.sqlite --pin deploy/gate-bundle.pin --attest deploy/attestations.log
uv run cairn m0-run --bits 40 --seed 1 --db var/substrate.sqlite --bundle deploy/gate-bundle.sqlite --pin deploy/gate-bundle.pin --attest deploy/attestations.log
```

The pin carries mode `0444` and the user append-only flag; attestations are append-only.
Deployment artifacts under `deploy/` and the substrate under `var/` are git-ignored and
operator-owned. These commands initialize a deployment; replacing a pinned bundle requires
deliberate operator review. Read-only `uv run cairn doctor --json` reports plan refusals and
the matching rebuild-and-repin sequence without executing it. `cairn doctor --fix` owns only
its mode and directory repairs, not bundle replacement or substrate migration.

An invalid plan refuses with exit 2. A substrate that differs from the shipped schema refuses
with `SchemaMismatch`, exit 4; Cairn ships no migration. Run `uv run cairn doctor --json`
to inspect either refusal before deciding how to preserve or replace operator-owned data.

## Fresh campaign deployment

The [GIANTS examples](../examples/giants/README.md) preserve three AuditOnly historical
campaign configurations and their frozen modules. From the repository root, inspect one
with `uv run python -m cairn.campaign --spec examples/giants/campaign1.json --plan-only`.
The examples document the identity, replay, and scoring limits.

Prepare the bundle, operator pin, and fixture-waiver attestation with one module command:

```bash
campaign_work="$(mktemp -d)"
uv run python -m cairn.deployment --src bundle/ --directory "$campaign_work/deployment"
```

The destination must not exist, and its parent must exist. The command exclusively creates
a directory with mode `0700` containing `gate-bundle.sqlite`, `gate-bundle.pin`, and
`attestations.log`. It reads source objects and validates the fixture hypothesis before
creation, compares the built hash with the preflight hash before pinning, and checks the
bundle, pin, and exact fixture waiver at offset 0 before success. `--src` selects the JSON
source directory; verifier, Lean, renderer, container, and linter inputs come from the
repository paths used by `cairn bundle build`.

Successful stdout is one JSON document with `bundle`, `pin`, and `attest` paths,
`bundle_hash`, `waiver_offset`, `waiver_digest`, and `status: "ready"`. Pass the three paths
as `--bundle`, `--pin`, and `--attest` to the campaign runner. The bundle and pin carry
mode `0444`; pin and attestation carry append-only flags where the existing writers
support them. A platform without flag support emits a warning and relies on mode bits.

Existing destinations, including dangling symlinks, refuse without modification.
A failure exits nonzero and reports its `stage` and `retained` paths on stderr. Partial
files remain in place; retries require a different absent destination. The command does
not replace a deployment, create a substrate, run a campaign, certify an evaluator, or
issue an operator session, statement ratification, or review verdict.

A spec whose verifier names a self-test skill (`skill` and `skill_identity_hash`) runs only
against a substrate holding that verifier's certificate. Run `cairn selftest <skill>` with the
same `--db`, `--bundle` and `--pin` before the campaign; an uncertified verifier refuses with
exit 2 before any record is written or any nonce is drawn. The run checks the verifier's
certificate, not the executor's. `--plan-only` checks neither certification nor runtime readiness.

`module_dir` resolves against the working directory. For a skill-backed spec it must name the
installed checkout's `src`, so `"module_dir": "src"`, run from the checkout root, serves every
snapshot on one machine whose identity sources are byte-identical, with one spec file and one
spec hash; an absolute path ties the spec to one snapshot. The spec pins the source digest and
the skill identity hash, and the identity also folds in the machine's gp binary and environment
manifest, so a spec carries to another snapshot or machine only when all of these match.

A run touches every point its executor evaluates, whatever its deployment. A pre-registration
that calls a range untouched holds only when no earlier run drew from it: put a negative or a
rehearsal on a disjoint range, or run it after the registered draw. Separate deployments keep
separate substrates and do not see each other's draws, so no gate checks this; the run report
lists each trial's point for the record.

## Lean prerequisites

The Lean integration suite requires the comparator and exporter pinned in
`bundle/container.json`. Provision them outside pytest:

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
The gold arm's comparator config lists `external_kernels` from `bundle/lean.json`, so the Linux
image's `nanoda_bin` (nanoda_lib at the `bundle/container.json` `nanoda` commit, built from the
pinned `rust` toolchain) checks the export in addition to the in-toolchain kernel. The dev arm
writes `enable_nanoda: false` and checks with the in-toolchain kernel only.
The pinned toolchain and mathlib prerequisite are described in
[ADR-002](../research/decisions/adr-002-lean-ci-prerequisites.md).

## Linux runner measurements

The Linux runner compiles `src/cairn/rss_reporter.c` once per Python process using
`/usr/bin/cc`. The compiler must resolve to a root-owned executable without group or
world write permission. The build has a 20-second timeout. Source, compiler, and binary
SHA-256 digests appear in the `rss_reporter_build` log event; changed build inputs within
the process refuse execution. Compilation happens outside the trial's wall-clock interval.

The helper runs from a sealed memory file and obtains the worker's `wait4` usage. Its
authenticated Unix socket binds measurement packets to the helper's PID. Linux execution
requires `/proc`, executable memory files with seals, and Unix sequenced-packet sockets
with sender credentials. The caller must lack `CAP_SYS_ADMIN` and `CAP_SYS_PTRACE` in
its inheritable, permitted, effective, and ambient capability sets. Workers inherit
`no_new_privs`; malformed or incomplete reports refuse a measurement.

The helper receives the caller's `env` dictionary. The caller must supply a trusted
environment; sender authentication does not establish trust in hostile loader configuration.

This measures the worker's peak resident size. Descendant coverage remains subject to
the receipt's `measurement_scope`; allocation tests do not establish complete process-tree
coverage. macOS uses the direct `wait4` path. The pinned formalization image removes its
C compiler and does not satisfy the Linux runner's compilation prerequisite.

## Checks and parallel CI

```bash
scripts/check.sh --fast
uv run pytest -q tests/<affected-test-module>.py
```

Use focused local tests for the changed behavior and its callers, and CI for broad regression
coverage. Run a relevant `--ci-lane` locally when test selection is uncertain, and local-only
checks for affected behavior CI cannot exercise. A full local `scripts/check.sh` is available
for a named cross-suite risk or investigation; it runs every test and requires Docker.
Shared fixture and collection changes require their contract tests and all affected CI lanes.
Record the tested revision, scope, and exclusions. An interrupted run is incomplete; skipped
tests are not passed. These development checks do not replace Cairn's mathematical gates.

CI partitions its regression tests into 21 disjoint lanes. The full sweep validation is
an explicit manual exception described below.

- `python`: fallback tests outside `tests/integration/` and the explicit lane manifests.
- `python-integration`: tests in `tests/integration/` outside the explicit lane manifests
  and the full sweep validation.
- `m0-lineage`: the four operator sequence, derivation lineage, and human rendering cases.
- `m0-replay`: the two same-seed and different-seed replay cases.
- `m0-transcript`: the three cache-bypass, step-log, and golden transcript cases.
- `m0-boundaries`: the eight abort, refusal, attestation, entry-point, and path-boundary cases.
- `gateplan`: the 28 cases in `tests/integration/test_gateplan.py`, `test_gateplan_cli.py`, and
  `test_ladder_gate_selftest.py`.
- `lean-core`: Lean toolchain tests plus the weaker-statement closure-comparison case.
- `lean-replay`: the fresh-replay forgery case.
- `solution`: remaining candidate preparation and build tests.
- `solution-library-dlp`: the DLP library challenge-gate case.
- `solution-library-finite-point`: the finite-point library challenge-gate case.
- `solution-library-binding`: the stale formal statement binding refusal case.
- `solution-plan-exact`: the successful ordered-plan case, approved-dev artifact tag case, and
  the 23 slope skill certification and campaign cases in
  `tests/integration/test_slope_weight_selftest.py`.
- `solution-plan-refusals`: the `sorry` and replay-timeout ordered-plan cases with shared setup.
- `container`: Linux hashing, preparation, compilation, axiom, dependency-cache, and lifecycle tests.
- `container-replay-exact`: successful Linux fresh replay and exact closure comparison.
- `container-replay-refusals`: axiom refusal, forged-proof rejection, weaker-statement closure
  mismatch, and stage-specific timeouts.
- `container-plan-exact`: the successful gold-arm ordered-plan case.
- `container-plan-proven`: the gold PROVEN artifact review and binding case.
- `container-plan-refusals`: the gold-arm ordered-plan `sorry`, weaker-statement and stale-hash
  cases.

The `python`, `python-integration`, four M0, and `gateplan` lanes do not provision Lean, mathlib,
comparator, or exporter prerequisites. The M0 and `gateplan` suites use PARI/GP. Both Lean leaves and
all three solution-library leaves keep the Lean and comparator prerequisites required by their tests.

CI lanes have a 1,080-second session deadline, except `solution-plan-exact`, whose deadline is
1,962 seconds. macOS jobs have a 20-minute ceiling, except `solution-plan-exact` at 45 minutes;
Linux container jobs have a 41-minute ceiling. The local
`--ci-lane m0`, `--ci-lane lean`, `--ci-lane solution-library`, `--ci-lane solution-plan`,
`--ci-lane container-replay` and `--ci-lane container-plan` forms aggregate their respective cases.
The `container-plan` aggregate includes all three leaves, retaining five tests.
Lane membership is defined in `tests/_ci_lanes.py`; contracts check the disjoint CI
population and its exact manual validation exception.
The real-prelude ordered-plan test has a 1,800-second watchdog including setup and teardown;
the replay subprocess retains its 600-second bound.

Whole-project typing targets macOS. Linux CI also checks the container adapter, preparation
code, Lean invocation code, dependency helper, and container tests against Linux APIs.

## Slope sweep evaluators

The independent `cairn.slopemodel.slopemodel_sweep_a` and
`cairn.slopemodel.slopemodel_sweep_b` modules read `{"l": ..., "n": ...}` from stdin and
write `{"W": ..., "last": ...}` to stdout:

```bash
printf '%s\n' '{"l":971153,"n":556}' | uv run python -m cairn.slopemodel.slopemodel_sweep_a
printf '%s\n' '{"l":971153,"n":556}' | uv run python -m cairn.slopemodel.slopemodel_sweep_b
```

Both require integer prime `l >= 3` and integer `1 <= n <= l - 2`. A accepts
`l <= 2**62`; B accepts `l <= 4294967311` and refuses horizons above `125000` or
correction-stream counts above `250000`. Input bounds provide no guarantee that an
evaluation fits available time or memory. Both expose `weight(ell, n)` and
`weight_chain_free(ell, n)` in Python; the JSON entry points compute `weight`.

The routed regression module contains 146 cases, including agreement on the 105 frozen
validation primes below `2**18`, both planted point-order faults, and supporting checks:

```bash
uv run pytest -q tests/integration/test_slopemodel_sweep.py --cairn-ci-lane=python-integration --durations=10
```

Only `tests/integration/test_slopemodel_sweep.py::test_all_validation_primes_agree`
is excluded from named CI lanes. Default collection and `--cairn-ci-lane=all` retain
its 396 slow-marked cases. The full test compares both sweeps with both point-sequence
references on the frozen primes from 5 through 4194007, with
`n = (564 * isqrt(l) + 500) // 1000`. Run it once on committed code and record the
revision and wall time in the commit body. A complete passing result is recorded as
`ALL_AGREE 396`:

```bash
uv run pytest -q tests/integration/test_slopemodel_sweep.py::test_all_validation_primes_agree --cairn-ci-lane=all --durations=10
```

Finite agreement is reproducible empirical evidence. It does not establish a mathematical
proof, certify a Cairn skill, or grant PROVEN.

## Scratch and diagnostics

Pytest uses `tmp_path_retention_policy = "failed"` to remove successful scratch automatically.
On macOS, teardown clears user append-only flags inside each passing test's `tmp_path`
before pytest removes it. Symlinks are not followed; failed-call scratch retains its flags.
JSONL diagnostics live separately under `pytest-of-<user>/cairn-test-logs/`, with unique
session and test directories collected by CI. Records are written as events occur, so an
interrupted process can leave readable diagnostics without completing teardown.

Failed-call scratch is retained for diagnosis. Pytest can remove scratch for setup or teardown
errors, so their logs do not depend on scratch retention. Active sibling runs and the shared
dependency cache are outside this cleanup. Explicit `--basetemp` disables pytest's
successful-session base cleanup. This policy does not sweep historical scratch directories.

## Local Linux dependency cache

```bash
uv run python tests/_linux_dependencies.py --cache .cache/linux-dependencies
CAIRN_LINUX_DEPENDENCY_CACHE="$PWD/.cache/linux-dependencies" scripts/check.sh
```

Provisioning runs outside pytest. Tests read the configured cache, validate every file
including ignored compiled artifacts, and copy dependencies into private temporary projects.
The key binds the actual Docker image ID, Lean pins, manifest, project configuration, and
requested modules. Missing or corrupt configured entries fail; without the variable, tests
provision a temporary seed. Failed provisioning directories remain available for diagnosis.

Cache records require a trusted local producer and are not proof certificates. Every proof
check retains its execution requirements. Warm runs inspect and validate the recorded local
image without rebuilding it. A cache-specific Docker tag retains that image independently
of the build tag. A removed image requires provisioning into a fresh cache directory;
changing bundle identity selects a separate image record.

Linux CI caches the dependency seed, the exact Docker image archive, and its metadata under
`runner.temp`. The key includes the runner OS and architecture, the Docker server version and
storage backend, and the files that bind the image and seed. A hit imports the saved image ID
and validates the complete seed before any gate runs; an invalid hit fails without rebuilding.
Each lane prepares its own seed on a miss. The `container` lane publishes the cache only after
its gates and Linux type check pass on a push to `main`; pull requests and manual runs do not
publish it. Submitted candidates, proof executions, replay results, and verification verdicts
remain uncached. CI transfer cost and speedup remain unmeasured.

## Formalization adapters

These are implementation interfaces in `src/cairn/solutionchecks.py`, not proof-acceptance APIs.

`prepare_dev` compiles a gate-owned Challenge-only project and computes its formal statement
hash with the bundled hasher. The prepared value binds the claim, bundle, pin, renderer,
prelude, theorem selection, and input fingerprints. `run_dev` validates that binding and the
submitted hash before candidate work, then checks imports, builds a private project, checks
axioms, performs fresh replay, and compares statement closures. Refusal or timeout blocks
subsequent steps.

`prepare_container` prepares and hashes the Challenge inside the pinned Linux image without
host Lean, validating inputs and copied dependencies. `assert_prepared(..., image=image)`
checks the image-bound handoff; `run_dev` refuses container-prepared values.

`compile_container` validates the handoff, submitted hash, and import allowlist before
assembling a separate candidate project. It copies pinned Linux dependencies, builds Solution
and Challenge by image ID without network access, and checks input/dependency integrity.
The prepared project is not mounted during candidate execution. Successful compilation,
including compilation with `sorry`, is not proof acceptance.

`check_container_axioms` accepts a successful compilation bound to the same bundle and pin.
It checks candidate inputs/dependencies, builds the bundled extractor in a separate Linux
project, and validates canonical theorem-indexed output against permitted axioms. Compilation
does not mount the extractor; inspection mounts it read-only. `sorryAx` fails this check.
Input and dependency integrity are checked before returning.

`observe_container_replay` runs that axiom check before the pinned `leanchecker --fresh`
command by image ID, without network or host Lean. Offending axioms block replay. Input or
dependency changes refuse, including after nonzero replay or confirmed replay timeout.
Axiom and replay timeouts name their respective stages; unconfirmed container cleanup remains
an infrastructure error. Successful replay does not establish statement equivalence or PROVEN.

The prepared value is a trusted in-process handoff, not authentication of an arbitrary
caller-constructed value or a persisted gate-run row. The caller selects theorem names.
Fingerprints cover tracked inputs, not cached artifact certification or concurrent-write
containment. Developer-arm results do not provide containment, persist evidence, or grant PROVEN.

`container.formal_statement_hash` builds the bundled hasher and a caller-prepared Challenge
in the pinned ARM64 Linux image. It checks the Lean version and commit, executes by OCI image
ID without network as the caller's non-root UID/GID, and logs that ID beside the digest.
Private project permissions remain unchanged; build caches use the mounted project. Linux
dependencies must be provisioned by the trusted caller. This function does not execute a
Solution or emit a gold verification result.

Every container run has a unique owned name. A client timeout stops it before returning a
timeout; unsuccessful termination raises a cleanup error naming the container. The Linux CI
tests exercise real elliptic-curve hashes and refusals; absent Docker fails the lane.
