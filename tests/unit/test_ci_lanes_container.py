import pytest
from _ci_lane_suite import write_suite
from _ci_lanes import (
    CONTAINER_COMPARISON_TESTS,
    CONTAINER_IMAGE_TEST_PATHS,
    CONTAINER_PLAN_CASES,
    CONTAINER_PLAN_TESTS,
    CONTAINER_REPLAY_TESTS,
    CONTAINER_TEST_PATHS,
)


@pytest.mark.parametrize(
    ("lane", "passed", "deselected"),
    [
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
def test_container_lane_does_not_import_modules_owned_by_other_lanes(pytester, lane, passed, deselected):
    write_suite(pytester)
    path = pytester.path / "tests/unit/test_unlisted.py"
    path.write_text('raise RuntimeError("mac-only-import")\n')
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(passed=passed, deselected=deselected)
    for lane in ("all", "python", "python-integration"):
        result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
        assert result.ret == pytest.ExitCode.INTERRUPTED
        assert "mac-only-import" in result.stdout.str()


@pytest.mark.parametrize(
    "lane",
    [
        "container",
        "container-replay",
        "container-replay-exact",
        "container-replay-refusals",
        "container-plan",
        "container-plan-exact",
        "container-plan-proven",
        "container-plan-refusals",
    ],
)
def test_container_lane_refuses_an_import_error_in_its_own_module(pytester, lane):
    write_suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text('raise RuntimeError("container-import")\n')
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(errors=1)
    assert result.ret == pytest.ExitCode.INTERRUPTED
    assert "container-import" in result.stdout.str()


def test_a_container_image_failure_keeps_its_own_lane_red_and_no_other(pytester):
    write_suite(pytester)
    for relative in CONTAINER_IMAGE_TEST_PATHS:
        (pytester.path / relative).write_text("def test_planted_failure():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=container-image")
    result.assert_outcomes(failed=2, deselected=11)
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=container")
    result.assert_outcomes(passed=1, deselected=12)


@pytest.mark.parametrize("name", [*CONTAINER_REPLAY_TESTS, *CONTAINER_COMPARISON_TESTS])
def test_container_replay_failure_keeps_its_lane_red(pytester, name):
    write_suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text(f"def {name}():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=container-replay")
    result.assert_outcomes(failed=1)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize("proof", ["rfl", "sorry", "forged"])
def test_container_replay_shards_route_proof_parameters_and_propagate_failure(pytester, proof):
    write_suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text(
        'import pytest\n@pytest.mark.parametrize("proof", ["rfl", "sorry", "forged"], ids=["a", "b", "c"])\n'
        f"def {CONTAINER_REPLAY_TESTS[0]}(proof):\n    assert proof != {proof!r}\n"
    )
    exact = proof == "rfl"
    lane = "container-replay-exact" if exact else "container-replay-refusals"
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=0 if exact else 1, deselected=4 if exact else 3)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize("case", CONTAINER_PLAN_CASES)
def test_container_plan_shards_route_by_case_and_propagate_failure(pytester, case):
    write_suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", {CONTAINER_PLAN_CASES!r})\n'
        f"def {CONTAINER_PLAN_TESTS[0]}(case):\n    assert case != {case!r}\n"
    )
    exact = case == "exact"
    lane = "container-plan-exact" if exact else "container-plan-refusals"
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=0 if exact else 2, deselected=5 if exact else 3)
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    aggregate = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=container-plan")
    aggregate.assert_outcomes(failed=1, passed=4, deselected=1)
    assert aggregate.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize(
    "lane", ["all", "container-plan", "container-plan-exact", "container-plan-proven", "container-plan-refusals"]
)
@pytest.mark.parametrize("case", ["unknown", None, 1])
def test_unknown_container_plan_parameters_refuse_collection(pytester, lane, case):
    write_suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", [{case!r}])\n'
        f"def {CONTAINER_PLAN_TESTS[0]}(case):\n    assert True\n"
    )
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "invalid container plan case" in result.stderr.str()
