import pytest
from _ci_lane_suite import M0_GATE_PATH, m0_source, write_suite
from _ci_lanes import (
    GATEPLAN_TEST_PATHS,
    M0_ABORT_TEST,
    M0_TEST_CASES,
    PROVEN_DEV_TEST,
    PROVEN_GOLD_TEST,
    PROVEN_TEST_PATH,
)


@pytest.mark.parametrize(
    ("lane", "passed", "deselected"),
    [
        ("all", 48, 0),
        ("python", 1, 47),
        ("python-integration", 1, 47),
        ("m0", 17, 31),
        ("m0-lineage", 4, 44),
        ("m0-replay", 2, 46),
        ("m0-transcript", 3, 45),
        ("m0-boundaries", 8, 40),
        ("gateplan", 3, 45),
        ("lean", 5, 43),
        ("lean-core", 3, 45),
        ("lean-replay", 2, 46),
        ("solution", 3, 45),
        ("solution-library", 3, 45),
        ("solution-library-dlp", 1, 47),
        ("solution-library-finite-point", 1, 47),
        ("solution-library-binding", 1, 47),
        ("solution-plan", 5, 43),
        ("solution-plan-exact", 3, 45),
        ("solution-plan-refusals", 2, 46),
        ("container", 1, 10),
        ("container-replay", 4, 7),
        ("container-replay-exact", 2, 9),
        ("container-replay-refusals", 2, 9),
        ("container-plan", 5, 6),
        ("container-plan-exact", 1, 10),
        ("container-plan-proven", 1, 10),
        ("container-plan-refusals", 3, 8),
    ],
)
def test_each_lane_runs_its_selected_tests(pytester, lane, passed, deselected):
    write_suite(pytester)
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(passed=passed, deselected=deselected)


@pytest.mark.parametrize(
    ("lane", "expected"),
    [
        ("container-plan-exact", set()),
        ("container-plan-proven", {PROVEN_GOLD_TEST}),
        ("container-plan", {PROVEN_GOLD_TEST}),
        ("solution-plan-exact", {PROVEN_DEV_TEST}),
        ("python-integration", set()),
    ],
)
def test_proven_derivation_arms_run_with_their_real_prerequisites(pytester, lane, expected):
    write_suite(pytester)
    result = pytester.runpytest("-q", "--collect-only", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    assert result.ret == 0
    assert {line.split("::")[1] for line in result.outlines if line.startswith(PROVEN_TEST_PATH + "::")} == expected


@pytest.mark.parametrize(
    ("lane", "passed", "deselected"),
    [("container-plan-proven", 0, 10), ("container-plan", 4, 6)],
)
def test_a_gold_proven_failure_keeps_its_leaf_and_aggregate_red(pytester, lane, passed, deselected):
    write_suite(pytester)
    (pytester.path / PROVEN_TEST_PATH).write_text(
        f"def {PROVEN_GOLD_TEST}():\n    assert False\ndef {PROVEN_DEV_TEST}():\n    assert True\n"
    )
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=passed, deselected=deselected)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


def test_an_unassigned_proven_derivation_arm_refuses_collection(pytester):
    write_suite(pytester)
    (pytester.path / PROVEN_TEST_PATH).write_text("def test_unassigned():\n    assert True\n")
    result = pytester.runpytest(
        "-q", "--collect-only", "--import-mode=importlib", "--cairn-ci-lane=container-plan-exact"
    )
    assert result.ret != 0
    assert "unassigned PROVEN derivation test" in result.stderr.str()


@pytest.mark.parametrize(
    ("lane", "passed", "deselected"),
    [
        ("python", 0, 47),
        ("python-integration", 0, 47),
        ("gateplan", 2, 45),
        ("lean", 4, 43),
        ("solution", 0, 38),
        ("container", 0, 2),
    ],
)
def test_a_selected_failure_keeps_the_lane_red(pytester, lane, passed, deselected):
    write_suite(pytester)
    relative = {
        "lean": "tests/integration/test_lean_toolchain.py",
        "solution": "tests/integration/test_solution_build_compile.py",
        "python": "tests/unit/test_unlisted.py",
        "python-integration": "tests/integration/test_unlisted.py",
        "gateplan": GATEPLAN_TEST_PATHS[0],
        "container": "tests/integration/test_container_statement_hash.py",
    }[lane]
    (pytester.path / relative).write_text("def test_planted_failure():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=passed, deselected=deselected)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize(
    ("lane", "failing_test", "passed", "deselected"),
    [
        ("m0", M0_TEST_CASES["m0-lineage"][0], 16, 31),
        ("m0-lineage", M0_TEST_CASES["m0-lineage"][0], 3, 44),
        ("m0-replay", M0_TEST_CASES["m0-replay"][0], 1, 46),
        ("m0-transcript", M0_TEST_CASES["m0-transcript"][0], 2, 45),
        ("m0-boundaries", M0_ABORT_TEST, 7, 40),
    ],
)
def test_selected_m0_failures_keep_their_leaf_and_aggregate_red(pytester, lane, failing_test, passed, deselected):
    write_suite(pytester)
    (pytester.path / M0_GATE_PATH).write_text(m0_source(failing_test))
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=passed, deselected=deselected)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


def test_invalid_lane_refuses(pytester):
    write_suite(pytester)
    result = pytester.runpytest("--cairn-ci-lane=leam")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "invalid choice" in result.stderr.str()
