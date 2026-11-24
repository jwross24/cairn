# Checks, CI lanes and Linux prerequisites

Local checks, the CI lane partition, and the Lean and Linux prerequisites the gates need.
`docs/development.md` carries the other development procedures.

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

CI partitions its regression tests into 22 disjoint lanes. The full sweep validation is
an explicit manual exception described in [development.md](development.md#slope-sweep-evaluators).

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
- `container`: Linux compilation, axiom, project-mutation, lifecycle, and pinned-kernel negative tests.
- `container-image`: the gold image build and its own checker, challenge hashing, preparation, and the
  dependency cache.
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
