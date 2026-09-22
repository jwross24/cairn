import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
MATHLIB_CACHE = "Restore the pinned mathlib cache"
MATHLIB_SETUP = "Provision the pinned mathlib prerequisite"
COMPARATOR_CACHE = "Restore the pinned comparator build"
COMPARATOR_BUILD = "Build pinned comparator and exporter"
GATES = "Gates"
MODULE = "Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point"


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
    assert "\n        if:" not in setup_step
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


def _assert_comparator_cache(text: str) -> None:
    steps = _steps(text)
    assert COMPARATOR_CACHE in steps, "CI has no comparator build cache step"
    assert steps["Provision exporter source"] < steps[COMPARATOR_CACHE] < steps[COMPARATOR_BUILD] < steps[GATES]

    cache = _step(text, COMPARATOR_CACHE)
    assert "if: matrix.lane != 'python'" in cache
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
    assert "if: matrix.lane != 'python'" in build
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
    assert "lane: [container, container-replay-exact, container-replay-refusals]" in text
    assert 'run: scripts/check.sh --ci-lane "${{ matrix.lane }}"' in _step(text, "Linux container gates")
    assert "lane: [python, lean, solution, solution-plan-exact, solution-plan-refusals]" in text
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
        assert "if: matrix.lane != 'python'" in _step(text, name)
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
    assert "lane: [container, container-replay-exact, container-replay-refusals]" in job
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
    ):
        assert path in types
    assert "if:" not in types


def test_container_lane_runs_real_tests_without_an_optional_gate():
    _assert_container_lane(WORKFLOW.read_text())


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
        ("lane: [container, container-replay-exact, container-replay-refusals]", "lane: [container]"),
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
