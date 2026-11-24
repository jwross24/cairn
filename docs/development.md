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

## Dispatch canary before a campaign Skeptic

Run this procedure against the campaign's existing substrate before dispatching its Skeptic.
Set the absolute campaign path explicitly; an absent destination refuses rather than initializes
a substrate. The probe requires SDK `0.2.158` and bundled CLI `2.1.280` and checks both versions.

```bash
export CAIRN_CAMPAIGN_DB=/absolute/path/to/campaign/substrate.sqlite
```

The command captures fresh, actual SDK/CLI request bodies at an ephemeral loopback endpoint with
a dummy credential and synthetic `LOCAL_CAPTURE_ONLY` replies. It creates a scratch home,
project, bundle, and substrate. All four ambient sources must appear in the control requests;
none may appear in dispatch requests, which must contain the handed-node control. Both arms
must complete successfully. This measures serialized context isolation only and establishes
no model or provider behavior. No paid provider request or deployed bundle pin is part of it.

```bash
uv run python - <<'PY'
import hashlib
import json
import os
from pathlib import Path

from cairn import canary
from cairn.substrate import Substrate
from research.grounding import probe_dispatch_canary as probe

campaign = Path(os.environ["CAIRN_CAMPAIGN_DB"]).expanduser().resolve()
if not campaign.is_file():
    raise SystemExit("campaign substrate must already exist")

capture = probe.run()
checks = capture["required_source_checks"]
if (
    capture["exit_code"] != 0
    or not capture["capture_complete"]
    or not capture["dispatch_clean_with_handed_control"]
    or not capture["all_arms_completed_synthetic_response"]
    or set(checks) != set(canary.SOURCES)
    or not all(checks.values())
):
    raise SystemExit("capture failed or incomplete; campaign substrate was not opened")

directory = Path(capture["artifact_directory"])
observations = {}
for arm in ("dispatch", "control"):
    bodies = []
    for entry in capture["request_bodies"][arm]:
        body = (directory / entry["file"]).read_bytes()
        if len(body) != entry["byte_length"] or hashlib.sha256(body).hexdigest() != entry["sha256"]:
            raise SystemExit("captured request body differs from its summary")
        bodies.append(body)
    classified = probe._classify_arm(
        bodies, capture["plantings"], canary.control_token(capture["seed"])
    )
    if not bodies or any(classified[key] != capture["arms"][arm][key] for key in classified):
        raise SystemExit("captured request checks differ from their summary")
    observations[arm] = "\n".join(body.decode("utf-8", errors="replace") for body in bodies)

with Substrate.open(campaign, role="writer") as sub:
    recorded = canary.record(
        sub,
        form=canary.FORM_REQUEST_BYTES,
        plantings=capture["plantings"],
        observed=observations["dispatch"],
        control_observed=observations["control"],
        handed_control_detected=capture["arms"]["dispatch"]["handed_control_detected"],
        sdk_version=capture["sdk_cli"]["sdk_version"],
        cli_version=capture["sdk_cli"]["cli_version"],
    )
    grounded = canary.require_grounded(sub)
    print(json.dumps(
        {"capture": str(directory), "record_hash": recorded.hash, "record": grounded.as_dict()},
        sort_keys=True,
    ))
PY
```

`canary.record` writes the captured dispatch and control observations as blobs and appends a
canary record to the selected campaign substrate. Retain the printed record hash and scratch
capture directory, including `summary.json`, request bodies, and init/result diagnostics.
Do not copy a historical PASS record or substitute an echo for captured request bytes.
`require_grounded` requires the newest record to pass with the worker's SDK/CLI versions;
a later failed record or a version change blocks dispatch until a fresh capture passes.
The procedure grounds dispatch only. It does not dispatch a Skeptic or produce findings.

## Dispatching the campaign Skeptic

The Skeptic role, its checklist and its read scope are gate-bundle objects: `bundle/worker_roles.json`,
the `skeptic_hunt_checklist` entry of `bundle/role_templates.json`, and `bundle/skeptic_scope.json`.
A deployment whose pinned bundle lacks them refuses the dispatch with `BundleError`. The role pins
`thinking: adaptive` because its model rejects a request with thinking disabled; a role that omits
the field runs with thinking disabled.

A dispatch is a live, paid provider session. The bundled CLI runs with `--bare` and reads its
credential from `ANTHROPIC_API_KEY` alone. Export it, then name the statement by hash:

```bash
uv run python -m cairn.dispatch --role skeptic --statement <statement-hash> \
  --db <substrate.sqlite> --bundle <gate-bundle.sqlite> --pin <gate-bundle.pin>
```

Exit 0 prints one JSON line with the dispatch id, the recorded cost, `run_metrics` (duration, turns
and token usage as the SDK reported them), the count of nodes read through the scoped tools, and the
typed record with one entry per checklist item. Exit 2 with `refused:` means the dispatch was refused
before any record was written, or the reply was recorded and is not a typed record; the reason names
which. Exit 4 with `failed:` means something failed after the dispatch was recorded (preparing the
worker's directory, the worker itself, or writing its result); it names the dispatch and says whether
an error result was recorded, read back from the substrate. A recorded reply that is not a typed record makes every report for
that statement refuse with the same `malformed skeptic_record` reason.

The typed record attests the recorded audit response: the role, the one handed statement, the
checklist bytes, each numbered answer, and the nodes actually read. It is not approval, not a proof
and not a calibration tag. `python -m cairn.report --kind campaign` refuses with
`missing skeptic_record` until one exists for the statement.

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

## Checks, CI lanes and Linux prerequisites

Local checks, the 22 CI lanes, Lean prerequisites, Linux runner measurements and the local
Linux dependency cache are in [development-ci.md](development-ci.md).

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
