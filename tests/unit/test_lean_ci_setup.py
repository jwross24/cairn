import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
MATHLIB_CACHE = "Restore the pinned mathlib cache"
MATHLIB_SETUP = "Provision the pinned mathlib prerequisite"
LEAN_CACHE = "Restore the Lean toolchain"
LEAN_INSTALL = "Install the Lean toolchain"
LEAN_RESOLVE = "The Lean toolchain the gate resolves"
COMPARATOR_CACHE = "Restore the pinned comparator build"
COMPARATOR_BUILD = "Build pinned comparator and exporter"
GATES = "Gates"
LINUX_CACHE_KEY = "Identify Linux prerequisite cache"
LINUX_CACHE_RESTORE = "Restore Linux prerequisite cache"
LINUX_CACHE_IMPORT = "Import cached Linux prerequisites"
LINUX_CACHE_PREPARE = "Prepare Linux prerequisites"
LINUX_CACHE_EXPORT = "Export Linux prerequisites"
LINUX_CACHE_SAVE = "Save Linux prerequisite cache"
LINUX_CACHE_ACTION = "55cc8345863c7cc4c66a329aec7e433d2d1c52a9"
LINUX_CACHE_PATHS = (
    "${{ runner.temp }}/cairn-linux-prerequisites/dependencies",
    "${{ runner.temp }}/cairn-linux-prerequisites/image.tar",
    "${{ runner.temp }}/cairn-linux-prerequisites/image.tar.metadata.json",
)
LINUX_CACHE_INPUTS = (
    "bundle/Containerfile",
    "bundle/container.json",
    "bundle/lean.json",
    "lean/lake-manifest.json",
    "lean/lean-toolchain",
    "tests/_linux_dependencies.py",
    "src/cairn/container.py",
    "src/cairn/lean.py",
    "src/cairn/solutionbuild.py",
)
CONTAINER_LANES = (
    "lane: [container, container-replay-exact, container-replay-refusals, "
    "container-plan-exact, container-plan-refusals]"
)
MODULE = "Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point"
LEAN_SETUP_CONDITION = "matrix.lane != 'python' && matrix.lane != 'm0' && matrix.lane != 'gateplan'"
LEAN_SETUP_STEPS = (
    LEAN_CACHE,
    LEAN_INSTALL,
    LEAN_RESOLVE,
    MATHLIB_CACHE,
    MATHLIB_SETUP,
    "Read comparator pins",
    "Provision comparator source",
    "Provision exporter source",
    COMPARATOR_CACHE,
    COMPARATOR_BUILD,
)
MACOS_LANES = (
    "lane: [python, m0, gateplan, lean, solution, solution-library, solution-plan-exact, solution-plan-refusals]"
)


def _steps(text: str) -> dict[str, int]:
    return {match.group(1): match.start() for match in re.finditer(r"^      - name: (.+)$", text, re.MULTILINE)}


def _step(text: str, name: str) -> str:
    marker = f"- name: {name}"
    assert marker in text, f"CI has no {name.lower()} step"
    return text.split(marker, 1)[1].split("\n      - ", 1)[0]


def _step_body(text: str, name: str) -> str:
    return _step(text, name).split("run: |\n", 1)[1]


def _assert_mathlib_prerequisite(text: str) -> None:
    steps = _steps(text)
    assert MATHLIB_CACHE in steps, "CI has no mathlib cache step"
    assert MATHLIB_SETUP in steps, "CI has no mathlib prerequisite step"
    assert GATES in steps, "CI has no Gates step"
    assert steps[MATHLIB_CACHE] < steps[MATHLIB_SETUP] < steps[GATES]

    cache = _step(text, MATHLIB_CACHE)
    assert "actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9" in cache
    assert "lean/.lake" in cache
    assert "~/.cache/mathlib" in cache
    assert "runner.os" in cache
    assert "runner.arch" in cache
    for path in ("lean/lean-toolchain", "lean/lake-manifest.json", "lean/lakefile.toml"):
        assert path in cache

    setup_step = _step(text, MATHLIB_SETUP)
    setup = _step_body(text, MATHLIB_SETUP)
    assert "working-directory: lean" in setup_step
    assert "set -euo pipefail" in setup
    assert 'toolchain="$(cat lean-toolchain)"' in setup
    assert f'"$HOME/.elan/bin/lake" "+$toolchain" exe cache get {MODULE}' in setup
    assert "git diff --exit-code -- lake-manifest.json" in setup


def test_ci_provisions_pinned_mathlib_before_the_gates():
    _assert_mathlib_prerequisite(WORKFLOW.read_text())


def test_ci_contract_refuses_a_missing_mathlib_prerequisite():
    broken = WORKFLOW.read_text().replace(f"- name: {MATHLIB_SETUP}", "- name: mathlib prerequisite absent", 1)
    with pytest.raises(AssertionError, match="no mathlib prerequisite step"):
        _assert_mathlib_prerequisite(broken)


def _assert_non_lean_lanes_skip_prerequisites(text: str) -> None:
    for name in LEAN_SETUP_STEPS:
        step = _step(text, name)
        condition = f"if: {LEAN_SETUP_CONDITION}"
        if name == LEAN_INSTALL:
            condition += " && steps.elan-cache.outputs.cache-hit != 'true'"
        assert [line.strip() for line in step.splitlines() if line.strip().startswith("if:")] == [condition]


def test_python_m0_and_gateplan_lanes_skip_lean_and_comparator_provisioning():
    _assert_non_lean_lanes_skip_prerequisites(WORKFLOW.read_text())


@pytest.mark.parametrize("step", LEAN_SETUP_STEPS)
@pytest.mark.parametrize("lane", ["python", "m0", "gateplan", "solution-library"])
def test_non_lean_lane_setup_contract_refuses_accidental_provisioning(step, lane):
    text = WORKFLOW.read_text()
    body = _step(text, step)
    conditional = next(line for line in body.splitlines() if "if:" in line)
    if lane == "python":
        replacement = conditional.replace("matrix.lane != 'python' && ", "", 1)
    elif lane == "solution-library":
        replacement = conditional.replace(
            LEAN_SETUP_CONDITION,
            f"{LEAN_SETUP_CONDITION} && matrix.lane != 'solution-library'",
            1,
        )
    else:
        replacement = conditional.replace(f" && matrix.lane != '{lane}'", "", 1)
    assert replacement != conditional
    with pytest.raises(AssertionError):
        _assert_non_lean_lanes_skip_prerequisites(text.replace(conditional, replacement, 1))


def _assert_comparator_cache(text: str) -> None:
    steps = _steps(text)
    assert COMPARATOR_CACHE in steps, "CI has no comparator build cache step"
    assert steps["Provision exporter source"] < steps[COMPARATOR_CACHE] < steps[COMPARATOR_BUILD] < steps[GATES]

    cache = _step(text, COMPARATOR_CACHE)
    assert f"if: {LEAN_SETUP_CONDITION}" in cache
    assert "actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9" in cache
    assert ".doctor/comparator/.lake/build" in cache
    assert ".doctor/comparator/.lake/packages/lean4export/.lake/build" in cache
    for identity in (
        "runner.os",
        "runner.arch",
        "steps.comparator-pins.outputs.revision",
        "steps.comparator-pins.outputs.exporter",
        "lean/lean-toolchain",
        ".doctor/comparator/lean-toolchain",
    ):
        assert identity in cache

    build = _step(text, COMPARATOR_BUILD)
    assert f"if: {LEAN_SETUP_CONDITION}" in build
    assert "cache-hit" not in build
    assert "build lean4export comparator" in build


def test_ci_caches_identity_bound_comparator_outputs_and_revalidates_them():
    _assert_comparator_cache(WORKFLOW.read_text())


@pytest.mark.parametrize(
    "removed",
    [
        "steps.comparator-pins.outputs.revision",
        "steps.comparator-pins.outputs.exporter",
        ".doctor/comparator/.lake/packages/lean4export/.lake/build",
        ".doctor/comparator/lean-toolchain",
    ],
)
def test_comparator_cache_contract_refuses_incomplete_identity_or_outputs(removed):
    text = WORKFLOW.read_text()
    cache = _step(text, COMPARATOR_CACHE)
    assert removed in cache
    with pytest.raises(AssertionError):
        _assert_comparator_cache(text.replace(cache, cache.replace(removed, "", 1), 1))


def test_comparator_cache_contract_refuses_skipping_build_validation_on_a_hit():
    text = WORKFLOW.read_text()
    marker = f"- name: {COMPARATOR_BUILD}\n"
    assert marker in text
    broken = text.replace(marker, marker + "        if: steps.comparator-build-cache.outputs.cache-hit != 'true'\n", 1)
    with pytest.raises(AssertionError, match="cache-hit"):
        _assert_comparator_cache(broken)


def _assert_ci_lanes(text):
    assert CONTAINER_LANES in text
    assert 'run: scripts/check.sh --ci-lane "${{ matrix.lane }}"' in _step(text, "Linux container gates")
    assert MACOS_LANES in text
    assert "fail-fast: false" in text
    assert "continue-on-error:" not in text
    assert 'CAIRN_SESSION_DEADLINE: "1080"' in text
    assert "timeout-minutes: 20" in text
    assert 'run: scripts/check.sh --ci-lane "${{ matrix.lane }}"' in _step(text, GATES)
    assert "name: cairn-failure-diagnostics-${{ matrix.lane }}" in text
    for name in (
        "Read comparator pins",
        "Provision comparator source",
        "Provision exporter source",
        "Build pinned comparator and exporter",
    ):
        assert f"if: {LEAN_SETUP_CONDITION}" in _step(text, name)
        assert _steps(text)[name] < _steps(text)[GATES]


def test_all_ci_lanes_run_the_same_gates_with_independent_deadlines():
    _assert_ci_lanes(WORKFLOW.read_text())


def _assert_container_lane(text):
    job = text.split("  container:\n", 1)[1].split("  check:\n", 1)[0]
    assert "runs-on: ubuntu-24.04-arm" in job
    assert "timeout-minutes: 20" in job
    assert 'CAIRN_SESSION_DEADLINE: "1080"' in job
    assert "continue-on-error:" not in job
    assert "uv sync --locked --all-groups" in job
    assert "pari-gp libpari-dev" in job
    assert "br sync --import-only" in job
    assert CONTAINER_LANES in job
    assert "fail-fast: false" in job
    assert "name: cairn-failure-diagnostics-${{ matrix.lane }}" in job
    step = _step(job, "Linux container gates")
    assert 'run: scripts/check.sh --ci-lane "${{ matrix.lane }}"' in step
    assert "if:" not in step
    types = _step(job, "Linux adapter types")
    assert "ty check --python-platform linux" in types
    for path in (
        "src/cairn/container.py",
        "src/cairn/lean.py",
        "src/cairn/solutionbuild.py",
        "src/cairn/solutionchecks.py",
        "tests/_linux_dependencies.py",
        "tests/integration/test_container_statement_hash.py",
        "tests/integration/test_lean_container.py",
    ):
        assert path in types
    assert "if:" not in types


def test_container_lane_runs_real_tests_without_an_optional_gate():
    _assert_container_lane(WORKFLOW.read_text())


def _cache_paths(step):
    match = re.search(r"(?m)^          path: \|\n((?:            .*\n)+)", step)
    assert match, "cache step has no bounded path list"
    return tuple(line.strip() for line in match.group(1).splitlines())


def _assert_linux_prerequisite_cache(text):
    job = text.split("  container:\n", 1)[1].split("  check:\n", 1)[0]
    steps = _steps(job)
    order = (
        "Sync Linux locked environment",
        LINUX_CACHE_KEY,
        LINUX_CACHE_RESTORE,
        LINUX_CACHE_IMPORT,
        LINUX_CACHE_PREPARE,
        "Linux container gates",
        "Linux adapter types",
        LINUX_CACHE_EXPORT,
        LINUX_CACHE_SAVE,
    )
    for name in order:
        assert name in steps, f"CI has no {name.lower()} step"
    assert [steps[name] for name in order] == sorted(steps[name] for name in order)

    key = _step(job, LINUX_CACHE_KEY)
    assert "id: linux-prerequisite-key" in key
    assert "CAIRN_CACHE_RUNNER_OS: ${{ runner.os }}" in key
    assert "CAIRN_CACHE_RUNNER_ARCH: ${{ runner.arch }}" in key
    key_body = _step_body(job, LINUX_CACHE_KEY)
    assert "for name in inputs:" in key_body
    assert "Path(name).read_bytes()" in key_body
    assert "identity_hash = inputs_hash.hexdigest()" in key_body
    assert "os.environ['CAIRN_CACHE_RUNNER_OS']" in key_body
    assert "os.environ['CAIRN_CACHE_RUNNER_ARCH']" in key_body
    for path in LINUX_CACHE_INPUTS:
        assert f'"{path}"' in key_body
    for field in ("ServerVersion", "Driver", "DriverStatus"):
        assert f'info["{field}"]' in key_body
    assert '"server_version": info["ServerVersion"]' in key_body
    assert '"driver": info["Driver"]' in key_body
    assert '"driver_status": info["DriverStatus"]' in key_body
    assert "hashlib.sha256(backend)" in key_body
    assert "{docker_hash}-{identity_hash}" in key_body
    assert '["docker", "info", "--format", "{{json .}}"]' in key_body
    assert "key={key}" in key_body

    cache_key = "key: ${{ steps.linux-prerequisite-key.outputs.key }}"
    restore = _step(job, LINUX_CACHE_RESTORE)
    assert f"actions/cache/restore@{LINUX_CACHE_ACTION}" in restore
    assert "id: linux-prerequisite-cache" in restore
    assert cache_key in restore
    assert "restore-keys:" not in restore
    assert _cache_paths(restore) == LINUX_CACHE_PATHS

    cache_hit = "steps.linux-prerequisite-cache.outputs.cache-hit"
    import_step = _step(job, LINUX_CACHE_IMPORT)
    assert f"if: {cache_hit} == 'true'" in import_step
    assert (
        "run: uv run python tests/_linux_dependencies.py --cache "
        '"$RUNNER_TEMP/cairn-linux-prerequisites/dependencies" --import-archive '
        '"$RUNNER_TEMP/cairn-linux-prerequisites/image.tar"'
    ) in import_step
    assert "--export-archive" not in import_step

    prepare = _step(job, LINUX_CACHE_PREPARE)
    assert f"if: {cache_hit} != 'true'" in prepare
    assert (
        'run: uv run python tests/_linux_dependencies.py --cache "$RUNNER_TEMP/cairn-linux-prerequisites/dependencies"'
    ) in prepare
    assert "--import-archive" not in prepare
    assert "--export-archive" not in prepare

    gates = _step(job, "Linux container gates")
    assert "if:" not in gates
    assert "PYTEST_DEBUG_TEMPROOT: ${{ runner.temp }}" in gates
    assert ("CAIRN_LINUX_DEPENDENCY_CACHE: ${{ runner.temp }}/cairn-linux-prerequisites/dependencies") in gates
    types = _step(job, "Linux adapter types")
    assert "if:" not in types

    writer = (
        "if: success() && matrix.lane == 'container' && github.event_name == 'push' "
        "&& github.ref == 'refs/heads/main' && "
        f"{cache_hit} != 'true'"
    )
    export = _step(job, LINUX_CACHE_EXPORT)
    assert writer in export
    assert (
        "run: uv run python tests/_linux_dependencies.py --cache "
        '"$RUNNER_TEMP/cairn-linux-prerequisites/dependencies" --export-archive '
        '"$RUNNER_TEMP/cairn-linux-prerequisites/image.tar"'
    ) in export
    save = _step(job, LINUX_CACHE_SAVE)
    assert writer in save
    assert f"actions/cache/save@{LINUX_CACHE_ACTION}" in save
    assert cache_key in save
    assert _cache_paths(save) == LINUX_CACHE_PATHS
    assert job.count("actions/cache/save@") == 1
    assert job.count("--export-archive") == 1

    _assert_ci_lanes(text)
    _assert_container_lane(text)


def test_ci_reuses_only_identity_bound_linux_prerequisites_after_validation():
    _assert_linux_prerequisite_cache(WORKFLOW.read_text())


@pytest.mark.parametrize(
    "removed",
    [*LINUX_CACHE_INPUTS, 'info["ServerVersion"]', 'info["Driver"]', 'info["DriverStatus"]'],
)
def test_linux_prerequisite_cache_contract_refuses_incomplete_identity(removed):
    text = WORKFLOW.read_text()
    key = _step(text, LINUX_CACHE_KEY)
    assert removed in key
    with pytest.raises(AssertionError):
        _assert_linux_prerequisite_cache(text.replace(key, key.replace(removed, "", 1), 1))


@pytest.mark.parametrize("step_name", [LINUX_CACHE_EXPORT, LINUX_CACHE_SAVE])
def test_linux_prerequisite_cache_contract_refuses_pull_request_publication(step_name):
    text = WORKFLOW.read_text()
    step = _step(text, step_name)
    assert "github.event_name == 'push'" in step
    broken = text.replace(
        step, step.replace("github.event_name == 'push'", "github.event_name == 'pull_request'", 1), 1
    )
    with pytest.raises(AssertionError):
        _assert_linux_prerequisite_cache(broken)


def test_linux_prerequisite_cache_contract_refuses_unvalidated_hits():
    text = WORKFLOW.read_text()
    import_step = _step(text, LINUX_CACHE_IMPORT)
    assert "--import-archive" in import_step
    broken = text.replace(import_step, import_step.replace("--import-archive", "--export-archive", 1), 1)
    with pytest.raises(AssertionError):
        _assert_linux_prerequisite_cache(broken)


def test_linux_prerequisite_cache_contract_refuses_restore_key_fallbacks():
    text = WORKFLOW.read_text()
    restore = _step(text, LINUX_CACHE_RESTORE)
    assert "restore-keys:" not in restore
    broken = text.replace(
        restore, restore.replace("key: ", "restore-keys: cairn-linux-prerequisites-\n          key: ", 1), 1
    )
    with pytest.raises(AssertionError, match="restore-keys"):
        _assert_linux_prerequisite_cache(broken)


def test_linux_prerequisite_cache_contract_refuses_broad_paths():
    text = WORKFLOW.read_text()
    restore = _step(text, LINUX_CACHE_RESTORE)
    assert LINUX_CACHE_PATHS[0] in restore
    broken = text.replace(
        restore,
        restore.replace(LINUX_CACHE_PATHS[0], "${{ runner.temp }}/cairn-linux-prerequisites", 1),
        1,
    )
    with pytest.raises(AssertionError):
        _assert_linux_prerequisite_cache(broken)


def _assert_test_diagnostics(text):
    for job in text.split("  container:\n", 1)[1].split("  check:\n", 1):
        assert "${{ runner." not in job.split("    steps:\n", 1)[0]
        gate_name = "Linux container gates" if "Linux container gates" in job else GATES
        assert "PYTEST_DEBUG_TEMPROOT: ${{ runner.temp }}" in _step(job, gate_name)
        assert 'PYTEST_ADDOPTS: "-vv"' in job
        upload = _step(job, "Test diagnostics")
        assert "if: always()" in upload
        assert "include-hidden-files: true" in upload
        assert ".check.log" in upload
        assert "${{ runner.temp }}/pytest-of-*/pytest-[0-9]*/*[0-9]/test.log.jsonl" in upload
        assert "${{ runner.temp }}/pytest-of-*/pytest-[0-9]*/basetemp/*[0-9]/test.log.jsonl" in upload
        assert "${{ runner.temp }}/pytest-of-*/cairn-test-logs/pytest-[0-9]*/*/test.log.jsonl" in upload
        assert "**" not in upload
        assert "retention-days: 7" in upload


def test_ci_retains_gate_and_test_logs_from_every_lane():
    _assert_test_diagnostics(WORKFLOW.read_text())


def test_diagnostics_contract_refuses_runner_context_before_a_runner_exists():
    text = WORKFLOW.read_text().replace("    env:\n", "    env:\n      PYTEST_DEBUG_TEMPROOT: ${{ runner.temp }}\n", 1)
    with pytest.raises(AssertionError):
        _assert_test_diagnostics(text)


@pytest.mark.parametrize(
    "removed",
    [
        "PYTEST_DEBUG_TEMPROOT: ${{ runner.temp }}",
        'PYTEST_ADDOPTS: "-vv"',
        "if: always()",
        "include-hidden-files: true",
        ".check.log",
        "${{ runner.temp }}/pytest-of-*/pytest-[0-9]*/*[0-9]/test.log.jsonl",
        "${{ runner.temp }}/pytest-of-*/pytest-[0-9]*/basetemp/*[0-9]/test.log.jsonl",
        "${{ runner.temp }}/pytest-of-*/cairn-test-logs/pytest-[0-9]*/*/test.log.jsonl",
    ],
)
def test_diagnostics_contract_refuses_lost_test_evidence(removed):
    text = WORKFLOW.read_text()
    assert removed in text
    with pytest.raises(AssertionError):
        _assert_test_diagnostics(text.replace(removed, "", 1))


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("runs-on: ubuntu-24.04-arm", "runs-on: macos-latest"),
        ('--ci-lane "${{ matrix.lane }}"', "--fast"),
        (CONTAINER_LANES, "lane: [container]"),
        ("fail-fast: false", "fail-fast: true"),
        ("name: cairn-failure-diagnostics-${{ matrix.lane }}", "name: cairn-failure-diagnostics"),
        ("ty check --python-platform linux", "ty check --python-platform darwin"),
        (" src/cairn/solutionchecks.py", ""),
        (" tests/_linux_dependencies.py", ""),
        ("- name: Linux container gates", "- name: Linux container gates\n        if: false"),
    ],
)
def test_container_lane_contract_refuses_missing_execution(old, new):
    text = WORKFLOW.read_text()
    assert old in text
    with pytest.raises(AssertionError):
        _assert_container_lane(text.replace(old, new))


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("solution-plan-exact, ", ""),
        (", solution-plan-refusals", ""),
        ("solution-plan-exact, solution-plan-refusals", "solution-plan"),
        ("fail-fast: false", "fail-fast: true"),
        ('CAIRN_SESSION_DEADLINE: "1080"', 'CAIRN_SESSION_DEADLINE: "1800"'),
        ("timeout-minutes: 20", "timeout-minutes: 30"),
        ("if: matrix.lane != 'python'", "if: matrix.lane == 'lean'"),
        ("if: matrix.lane != 'python'", "if: matrix.lane == 'solution'"),
        ('--ci-lane "${{ matrix.lane }}"', "--unit"),
        ("name: cairn-failure-diagnostics-${{ matrix.lane }}", "name: cairn-failure-diagnostics"),
    ],
)
def test_ci_lane_contract_refuses_missing_or_weakened_execution(old, new):
    text = WORKFLOW.read_text()
    assert old in text
    with pytest.raises(AssertionError):
        _assert_ci_lanes(text.replace(old, new))
