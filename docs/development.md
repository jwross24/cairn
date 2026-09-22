# Development and verification

Run commands from the repository root. Project rules live in [AGENTS.md](../AGENTS.md);
the system map is [MAP.md](../MAP.md).

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
The pinned toolchain and mathlib prerequisite are described in
[ADR-002](../research/decisions/adr-002-lean-ci-prerequisites.md).

## Checks and parallel CI

```bash
scripts/check.sh --fast
scripts/check.sh
```

The full local check runs every test and requires Docker. CI partitions that same test
population into nine disjoint lanes:

- `python`: tests outside the explicit Lean, Solution, and container manifests.
- `lean`: toolchain tests plus real-prelude closure-comparison and fresh-replay forgery cases.
- `solution`: remaining candidate preparation and build tests.
- `solution-plan-exact`, `solution-plan-sorry`, `solution-plan-timeout`: one ordered-plan case each.
- `container`: Linux hashing, preparation, compilation, axiom, dependency-cache, and lifecycle tests.
- `container-replay-exact`: successful Linux fresh replay.
- `container-replay-refusals`: axiom refusal, forged-proof rejection, and stage-specific timeouts.

Each CI lane has a 1,080-second session deadline and a 20-minute job ceiling. The local
`--ci-lane solution-plan` and `--ci-lane container-replay` forms aggregate their respective
cases. Lane membership is defined in `tests/_ci_lanes.py` and tested as a disjoint union.
The real-prelude ordered-plan test has a 900-second watchdog including setup and teardown;
the replay subprocess retains its 600-second bound.

Whole-project typing targets macOS. Linux CI also checks the container adapter, preparation
code, Lean invocation code, dependency helper, and container tests against Linux APIs.

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

CI provisions temporary Linux dependencies. Cross-run seed reuse requires persistence of
the exact Docker image and dependency cache; a matching tag does not establish image identity.

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
