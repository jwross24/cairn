import pytest
from _ci_lane_suite import (
    FULL_SWEEP_TEST,
    LIBRARY_GATE_BINDING_CASE,
    LIBRARY_GATE_CASE,
    LIBRARY_GATE_IDS,
    LIBRARY_GATE_PATH,
    M0_GATE_PATH,
    PLAN_CASE,
    PLAN_VARIANTS,
    SOLUTION_CASES,
    SWEEP_PATH,
    full_sweep_source,
    write_suite,
)
from _ci_lanes import (
    CI_LANES,
    CONTAINER_COMPARISON_TESTS,
    CONTAINER_IMAGE_TEST_PATHS,
    CONTAINER_PLAN_CASES,
    CONTAINER_PLAN_TESTS,
    CONTAINER_REPLAY_TESTS,
    CONTAINER_TEST_PATHS,
    GATEPLAN_TEST_PATHS,
    LEAN_LANES,
    LEAN_REPLAY_TEST,
    LEAN_SOLUTION_TESTS,
    M0_ABORT_CASES,
    M0_ABORT_TEST,
    M0_LANES,
    M0_TEST_CASES,
    PROVEN_DEV_TEST,
    PROVEN_GOLD_TEST,
    PROVEN_TEST_PATH,
    SOLUTION_LIBRARY_LANES,
    SOLUTION_PLAN_EXACT_TEST_PATHS,
    SOLUTION_TEST_PATHS,
)


def test_default_runs_every_test_and_lane_collections_are_a_disjoint_union(pytester):
    write_suite(pytester)
    (pytester.path / SWEEP_PATH).write_text(full_sweep_source(range(396)))
    for relative in CONTAINER_IMAGE_TEST_PATHS:
        (pytester.path / relative).write_text("def test_pass():\n    assert True\n")
    default = pytester.runpytest("-q", "--import-mode=importlib")
    default.assert_outcomes(passed=446)
    populations = {}
    for lane in (
        "all",
        "m0",
        "lean",
        "solution-library",
        "solution-plan",
        "container-replay",
        "container-plan",
        *CI_LANES,
    ):
        result = pytester.runpytest("-q", "--collect-only", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
        assert result.ret == pytest.ExitCode.OK
        populations[lane] = {line for line in result.outlines if line.startswith("tests/") and "::" in line}
    assert populations["lean-core"] == {"tests/integration/test_lean_toolchain.py::test_pass"} | {
        f"{SOLUTION_TEST_PATHS[0]}::{name}[{case}]"
        for name in LEAN_SOLUTION_TESTS
        if name != LEAN_REPLAY_TEST
        for case in (0, 1)
    }
    assert populations["lean-replay"] == {f"{SOLUTION_TEST_PATHS[0]}::{LEAN_REPLAY_TEST}[{case}]" for case in (0, 1)}
    assert populations["lean"] == set().union(*(populations[lane] for lane in LEAN_LANES))
    assert populations["python"] == {"tests/unit/test_unlisted.py::test_pass"}
    assert populations["python-integration"] == {"tests/integration/test_unlisted.py::test_pass"}
    old_python = populations["python"] | populations["python-integration"]
    assert not populations["python"] & populations["python-integration"]
    assert old_python == {
        "tests/unit/test_unlisted.py::test_pass",
        "tests/integration/test_unlisted.py::test_pass",
    }
    assert populations["m0"] == set().union(*(populations[lane] for lane in M0_LANES))
    assert populations["m0-lineage"] == {f"{M0_GATE_PATH}::{name}" for name in M0_TEST_CASES["m0-lineage"]}
    assert populations["m0-replay"] == {f"{M0_GATE_PATH}::{name}" for name in M0_TEST_CASES["m0-replay"]}
    assert populations["m0-transcript"] == {f"{M0_GATE_PATH}::{name}" for name in M0_TEST_CASES["m0-transcript"]}
    assert populations["m0-boundaries"] == {f"{M0_GATE_PATH}::{M0_ABORT_TEST}[{case}]" for case in M0_ABORT_CASES} | {
        f"{M0_GATE_PATH}::{name}" for name in M0_TEST_CASES["m0-boundaries"] if name != M0_ABORT_TEST
    }
    assert populations["gateplan"] == {f"{path}::test_pass" for path in GATEPLAN_TEST_PATHS}
    assert populations["solution"] == {"tests/integration/test_solution_build_compile.py::test_pass"} | {
        f"{SOLUTION_TEST_PATHS[0]}::{SOLUTION_CASES[0]}[{case}]" for case in (0, 1)
    }
    assert populations["solution-library"] == {
        f"{LIBRARY_GATE_PATH}::{LIBRARY_GATE_CASE}[{test_id}]" for test_id in LIBRARY_GATE_IDS
    } | {f"{LIBRARY_GATE_PATH}::{LIBRARY_GATE_BINDING_CASE}"}
    assert populations["solution-library-dlp"] == {f"{LIBRARY_GATE_PATH}::{LIBRARY_GATE_CASE}[{LIBRARY_GATE_IDS[0]}]"}
    assert populations["solution-library-finite-point"] == {
        f"{LIBRARY_GATE_PATH}::{LIBRARY_GATE_CASE}[{LIBRARY_GATE_IDS[1]}]"
    }
    assert populations["solution-library-binding"] == {f"{LIBRARY_GATE_PATH}::{LIBRARY_GATE_BINDING_CASE}"}
    assert populations["solution-library"] == set().union(*(populations[lane] for lane in SOLUTION_LIBRARY_LANES))
    assert populations["container"] == {"tests/integration/test_container_statement_hash.py::test_pass"}
    assert populations["container-image"] == {f"{path}::test_pass" for path in CONTAINER_IMAGE_TEST_PATHS}
    assert populations["container-replay"] == {
        f"{CONTAINER_TEST_PATHS[0]}::{CONTAINER_REPLAY_TESTS[0]}[rfl]",
        f"{CONTAINER_TEST_PATHS[0]}::{CONTAINER_REPLAY_TESTS[1]}",
        *(f"{CONTAINER_TEST_PATHS[0]}::{name}" for name in CONTAINER_COMPARISON_TESTS),
    }
    assert populations["container-replay-exact"] == {
        f"{CONTAINER_TEST_PATHS[0]}::{CONTAINER_REPLAY_TESTS[0]}[rfl]",
        f"{CONTAINER_TEST_PATHS[0]}::{CONTAINER_COMPARISON_TESTS[0]}",
    }
    assert populations["container-replay-refusals"] == {
        f"{CONTAINER_TEST_PATHS[0]}::{CONTAINER_REPLAY_TESTS[1]}",
        f"{CONTAINER_TEST_PATHS[0]}::{CONTAINER_COMPARISON_TESTS[1]}",
    }
    gold_node = f"{PROVEN_TEST_PATH}::{PROVEN_GOLD_TEST}"
    dev_node = f"{PROVEN_TEST_PATH}::{PROVEN_DEV_TEST}"
    slope_nodes = {f"{path}::test_pass" for path in SOLUTION_PLAN_EXACT_TEST_PATHS}
    assert (
        populations["solution-plan"]
        == {f"{SOLUTION_TEST_PATHS[0]}::{PLAN_CASE}[{case}]" for case in PLAN_VARIANTS} | {dev_node} | slope_nodes
    )
    plan = f"{CONTAINER_TEST_PATHS[0]}::{CONTAINER_PLAN_TESTS[0]}"
    assert populations["container-plan"] == {f"{plan}[{case}]" for case in CONTAINER_PLAN_CASES} | {gold_node}
    assert populations["container-plan-exact"] == {f"{plan}[exact]"}
    assert populations["container-plan-proven"] == {gold_node}
    assert populations["container-plan-refusals"] == {f"{plan}[{case}]" for case in CONTAINER_PLAN_CASES[1:]}
    assert populations["container-plan"] == (
        populations["container-plan-exact"]
        | populations["container-plan-proven"]
        | populations["container-plan-refusals"]
    )
    assert len(populations["container-plan"]) == 5
    combined = set()
    for lane in CI_LANES:
        assert populations[lane]
        assert not combined & populations[lane]
        combined |= populations[lane]
    manual_validation = {f"{SWEEP_PATH}::{FULL_SWEEP_TEST}[{ell}]" for ell in range(396)}
    assert not combined & manual_validation
    assert combined | manual_validation == populations["all"]
    assert (
        populations["solution-plan-exact"] == {f"{SOLUTION_TEST_PATHS[0]}::{PLAN_CASE}[exact]", dev_node} | slope_nodes
    )
    assert populations["solution-plan-refusals"] == {
        f"{SOLUTION_TEST_PATHS[0]}::{PLAN_CASE}[sorry]",
        f"{SOLUTION_TEST_PATHS[0]}::{PLAN_CASE}[timeout]",
    }
    assert not populations["lean"] & (populations["python"] | populations["python-integration"])
    assert not populations["solution"] & (
        populations["lean"] | populations["python"] | populations["python-integration"]
    )
    assert not populations["container"] & (
        populations["lean"] | populations["python"] | populations["python-integration"] | populations["solution"]
    )
    assert not populations["solution-plan"] & (
        populations["lean"]
        | populations["python"]
        | populations["python-integration"]
        | populations["solution"]
        | populations["container"]
    )
    assert populations["all"] == (
        populations["lean"]
        | populations["python"]
        | populations["python-integration"]
        | populations["m0"]
        | populations["gateplan"]
        | populations["solution"]
        | populations["solution-library"]
        | populations["solution-plan"]
        | populations["container"]
        | populations["container-image"]
        | populations["container-replay"]
        | populations["container-plan"]
        | manual_validation
    )
    (pytester.path / SOLUTION_PLAN_EXACT_TEST_PATHS[0]).write_text("def test_pass():\n    assert False\n")
    for lane, passed in (("solution-plan-exact", 2), ("solution-plan", 4)):
        result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
        result.assert_outcomes(failed=1, passed=passed, deselected=443 if lane == "solution-plan-exact" else 441)
        assert result.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize(
    "lane",
    [None, "all", "m0", "lean", "solution-library", "solution-plan", "container-replay", "container-plan", *CI_LANES],
)
def test_named_lanes_exclude_only_the_exact_manual_sweep_validation(pytester, lane):
    write_suite(pytester)
    source = full_sweep_source([5, 7, 11])
    (pytester.path / SWEEP_PATH).write_text(
        source
        + f"def {FULL_SWEEP_TEST}_neighbor():\n    assert True\n"
        + "@pytest.mark.slow\ndef test_other_slow_validation():\n    assert True\n"
        + "def test_sweeps_agree_with_both_point_sequence_references():\n    assert True\n"
        + '@pytest.mark.parametrize("fault", ["giant-one-arrives-early", "round-point-order-reversed"])\n'
        + "def test_agreement_refuses_planted_point_order_faults(fault):\n    assert fault\n"
        + f"class TestNeighbor:\n    def {FULL_SWEEP_TEST}(self):\n        assert True\n"
    )
    (pytester.path / "tests/integration/test_unlisted.py").write_text(source)
    for relative in CONTAINER_IMAGE_TEST_PATHS:
        (pytester.path / relative).write_text("def test_pass():\n    assert True\n")
    pytester.makeini("[pytest]\nmarkers = slow: slow validation")
    args = ["-q", "--collect-only", "--import-mode=importlib"]
    if lane is not None:
        args.append(f"--cairn-ci-lane={lane}")
    result = pytester.runpytest(*args)
    assert result.ret == pytest.ExitCode.OK
    nodes = {line for line in result.outlines if line.startswith("tests/") and "::" in line}
    manual = {f"{SWEEP_PATH}::{FULL_SWEEP_TEST}[{ell}]" for ell in [5, 7, 11]}
    if lane in (None, "all"):
        assert manual <= nodes
    else:
        assert not manual & nodes
    if lane in (None, "all", "python-integration"):
        retained = {
            f"{SWEEP_PATH}::{FULL_SWEEP_TEST}_neighbor",
            f"{SWEEP_PATH}::TestNeighbor::{FULL_SWEEP_TEST}",
            f"{SWEEP_PATH}::test_other_slow_validation",
            f"{SWEEP_PATH}::test_sweeps_agree_with_both_point_sequence_references",
            f"{SWEEP_PATH}::test_agreement_refuses_planted_point_order_faults[giant-one-arrives-early]",
            f"{SWEEP_PATH}::test_agreement_refuses_planted_point_order_faults[round-point-order-reversed]",
            *(f"tests/integration/test_unlisted.py::{FULL_SWEEP_TEST}[{ell}]" for ell in [5, 7, 11]),
        }
        assert retained <= nodes
