import pytest
from _ci_lanes import LEAN_LANES, M0_LANES, SOLUTION_LIBRARY_LANES
from _ci_workflow import (
    COMPARATOR_BUILD,
    COMPARATOR_CACHE,
    CONTAINER_LANES,
    GATES,
    LEAN_INSTALL,
    LEAN_SETUP_CONDITION,
    LEAN_SETUP_STEPS,
    MATHLIB_CACHE,
    MATHLIB_SETUP,
    MODULE,
    SOLUTION_PLAN_EXACT_JOB_TIMEOUT,
    SOLUTION_PLAN_EXACT_SESSION_DEADLINE,
    WORKFLOW,
    _assert_ci_lanes,
    _assert_container_lane,
    _step,
    _step_body,
    _steps,
)


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
@pytest.mark.parametrize("lane", ["python", "python-integration", *M0_LANES, "gateplan"])
def test_non_lean_lane_setup_contract_refuses_accidental_provisioning(step, lane):
    text = WORKFLOW.read_text()
    body = _step(text, step)
    conditional = next(line for line in body.splitlines() if "if:" in line)
    if lane == "python":
        replacement = conditional.replace("matrix.lane != 'python' && ", "", 1)
    else:
        replacement = conditional.replace(f" && matrix.lane != '{lane}'", "", 1)
    assert replacement != conditional
    with pytest.raises(AssertionError):
        _assert_non_lean_lanes_skip_prerequisites(text.replace(conditional, replacement, 1))


def test_lean_and_library_leaves_keep_all_lean_and_comparator_prerequisites():
    assert set(LEAN_LANES) == {"lean-core", "lean-replay"}
    assert set(SOLUTION_LIBRARY_LANES) == {
        "solution-library-dlp",
        "solution-library-finite-point",
        "solution-library-binding",
    }
    assert all(
        f"matrix.lane != '{lane}'" in LEAN_SETUP_CONDITION
        for lane in ("python", "python-integration", *M0_LANES, "gateplan")
    )
    assert all(lane not in LEAN_SETUP_CONDITION for lane in (*LEAN_LANES, *SOLUTION_LIBRARY_LANES))
    _assert_non_lean_lanes_skip_prerequisites(WORKFLOW.read_text())


@pytest.mark.parametrize("step", LEAN_SETUP_STEPS)
@pytest.mark.parametrize("lane", [*LEAN_LANES, *SOLUTION_LIBRARY_LANES])
def test_lean_dependent_leaf_setup_contract_refuses_accidental_skip(step, lane):
    text = WORKFLOW.read_text()
    conditional = next(line for line in _step(text, step).splitlines() if "if:" in line)
    replacement = conditional.replace(
        LEAN_SETUP_CONDITION,
        f"{LEAN_SETUP_CONDITION} && matrix.lane != '{lane}'",
        1,
    )
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


def test_all_ci_lanes_run_the_same_gates_with_independent_deadlines():
    _assert_ci_lanes(WORKFLOW.read_text())


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
        ("timeout-minutes: 41", "timeout-minutes: 20"),
        ("timeout-minutes: 41", "timeout-minutes: 410"),
        ('--ci-lane "${{ matrix.lane }}"', "--fast"),
        (CONTAINER_LANES, "lane: [container]"),
        ("container-plan-proven, ", ""),
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
        (SOLUTION_PLAN_EXACT_JOB_TIMEOUT, "timeout-minutes: 20"),
        (SOLUTION_PLAN_EXACT_JOB_TIMEOUT, SOLUTION_PLAN_EXACT_JOB_TIMEOUT.replace("|| 20", "|| 30")),
        (SOLUTION_PLAN_EXACT_SESSION_DEADLINE, 'CAIRN_SESSION_DEADLINE: "1080"'),
        (
            SOLUTION_PLAN_EXACT_SESSION_DEADLINE,
            SOLUTION_PLAN_EXACT_SESSION_DEADLINE.replace("|| '1080'", "|| '1962'"),
        ),
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
