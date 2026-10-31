import pytest
from _ci_lane_suite import (
    LIBRARY_GATE_BINDING_CASE,
    LIBRARY_GATE_CASE,
    LIBRARY_GATE_IDS,
    LIBRARY_GATE_ITEMS,
    LIBRARY_GATE_PATH,
    PLAN_CASE,
    PLAN_VARIANTS,
    SOLUTION_CASES,
    write_suite,
)
from _ci_lanes import SOLUTION_LIBRARY_LANES, SOLUTION_TEST_PATHS


@pytest.mark.parametrize(
    ("name", "lane", "passed", "deselected"),
    [
        (SOLUTION_CASES[0], "solution", 0, 38),
        (SOLUTION_CASES[1], "lean-core", 1, 37),
        (SOLUTION_CASES[2], "lean-replay", 0, 38),
    ],
)
def test_a_reassigned_solution_failure_keeps_its_lane_red(pytester, name, lane, passed, deselected):
    write_suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(f"def {name}():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=passed, deselected=deselected)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize("lane", ["solution-library", *SOLUTION_LIBRARY_LANES])
def test_a_library_gate_failure_keeps_its_lane_red(pytester, lane):
    write_suite(pytester)
    failed_item = "finite_point" if lane == "solution-library-finite-point" else "dlp"
    fail_binding = lane == "solution-library-binding"
    (pytester.path / LIBRARY_GATE_PATH).write_text(
        f'import pytest\n@pytest.mark.parametrize("item", {LIBRARY_GATE_ITEMS!r}, ids={LIBRARY_GATE_IDS!r})\n'
        f"def {LIBRARY_GATE_CASE}(item):\n    assert item != {failed_item!r}\n"
        f"def {LIBRARY_GATE_BINDING_CASE}():\n    assert {not fail_binding}\n"
    )
    selected = {
        "solution-library": (1, 2, 45),
        "solution-library-dlp": (1, 0, 47),
        "solution-library-finite-point": (1, 0, 47),
        "solution-library-binding": (1, 0, 47),
    }[lane]
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=selected[0], passed=selected[1], deselected=selected[2])
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    other = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=solution")
    other.assert_outcomes(passed=3, deselected=45)


@pytest.mark.parametrize("lane", ["all", "solution-library", *SOLUTION_LIBRARY_LANES])
def test_unknown_library_item_refuses_collection_even_when_its_display_id_is_valid(pytester, lane):
    write_suite(pytester)
    (pytester.path / LIBRARY_GATE_PATH).write_text(
        f'import pytest\n@pytest.mark.parametrize("item", ["unknown"], ids=["dlp"])\n'
        f"def {LIBRARY_GATE_CASE}(item):\n    assert True\n"
        f"def {LIBRARY_GATE_BINDING_CASE}():\n    assert True\n"
    )
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "invalid solution-library item" in result.stderr.str()


@pytest.mark.parametrize("failed_case", PLAN_VARIANTS)
def test_each_ordered_plan_failure_keeps_its_lane_red(pytester, failed_case):
    write_suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", {PLAN_VARIANTS!r})\n'
        f"def {PLAN_CASE}(case):\n    assert case != {failed_case!r}\n"
    )
    result = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=solution-plan")
    result.assert_outcomes(failed=1, passed=4, deselected=36)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize("case", PLAN_VARIANTS)
def test_plan_shards_route_by_parameter_value_and_propagate_failure(pytester, case):
    write_suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", {PLAN_VARIANTS!r}, ids=["a", "b", "c"])\n'
        f"def {PLAN_CASE}(case):\n    assert case != {case!r}\n"
    )
    lane = "solution-plan-exact" if case == "exact" else "solution-plan-refusals"
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=2 if case == "exact" else 1, deselected=38 if case == "exact" else 39)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize(
    "lane",
    [
        "all",
        "solution-plan",
        "solution-plan-exact",
        "solution-plan-refusals",
        "python",
        "m0",
        "gateplan",
        "solution-library",
    ],
)
@pytest.mark.parametrize("case", ["unknown", None, 1])
def test_unknown_plan_parameters_refuse_collection(pytester, lane, case):
    write_suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", [{case!r}])\ndef {PLAN_CASE}(case):\n    assert True\n'
    )
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "invalid ordered-plan case" in result.stderr.str()


def test_missing_plan_parameter_refuses_collection(pytester):
    write_suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(f"def {PLAN_CASE}():\n    assert True\n")
    result = pytester.runpytest("-q", "--import-mode=importlib")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "invalid ordered-plan case" in result.stderr.str()
