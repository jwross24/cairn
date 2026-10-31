import ast
from pathlib import Path

import _ci_lanes
import pytest
from _ci_lane_suite import (
    LIBRARY_GATE_BINDING_CASE,
    LIBRARY_GATE_CASE,
    LIBRARY_GATE_PATH,
    M0_GATE_PATH,
    PLAN_CASE,
    SOLUTION_CASES,
    write_suite,
)
from _ci_lanes import (
    CONTAINER_COMPARISON_TESTS,
    CONTAINER_PLAN_CASES,
    CONTAINER_PLAN_TESTS,
    CONTAINER_REPLAY_TESTS,
    CONTAINER_TEST_PATHS,
    GATEPLAN_TEST_PATHS,
    LEAN_PREREQUISITE_TEST_PATHS,
    LEAN_SOLUTION_TESTS,
    LEAN_TEST_PATHS,
    M0_ABORT_CASES,
    M0_TEST_CASES,
    M0_TEST_PATHS,
    PROVEN_TEST_PATH,
    SOLUTION_LIBRARY_TEST_PATHS,
    SOLUTION_PLAN_EXACT_TEST_PATHS,
    SOLUTION_PLAN_TESTS,
    SOLUTION_TEST_PATHS,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[2]


def test_new_lane_manifests_name_only_the_measured_test_modules():
    assert M0_TEST_PATHS == ("tests/e2e/test_m0_slice.py",)
    assert GATEPLAN_TEST_PATHS == (
        "tests/integration/test_gateplan.py",
        "tests/integration/test_gateplan_cli.py",
        "tests/integration/test_ladder_gate_selftest.py",
    )
    assert SOLUTION_LIBRARY_TEST_PATHS == ("tests/integration/test_challenge_gate.py",)
    assert SOLUTION_PLAN_EXACT_TEST_PATHS == ("tests/integration/test_slope_weight_selftest.py",)
    assert not set(SOLUTION_PLAN_EXACT_TEST_PATHS) & set(LEAN_TEST_PATHS)


def test_m0_case_groups_are_disjoint_and_name_existing_tests():
    names = [name for tests in M0_TEST_CASES.values() for name in tests]
    definitions = {
        node.name
        for node in ast.walk(ast.parse((ROOT / M0_GATE_PATH).read_text()))
        if isinstance(node, ast.FunctionDef)
    }
    assert len(names) == len(set(names))
    assert set(names) <= definitions
    assert len(M0_TEST_CASES["m0-lineage"]) == 4
    assert len(M0_TEST_CASES["m0-replay"]) == 2
    assert len(M0_TEST_CASES["m0-transcript"]) == 3
    assert len(M0_TEST_CASES["m0-boundaries"]) + len(M0_ABORT_CASES) - 1 == 8


def test_the_library_gate_test_is_declared_in_the_solution_library_lane_and_defined_in_its_file():
    assert SOLUTION_LIBRARY_TEST_PATHS == (LIBRARY_GATE_PATH,)
    assert LIBRARY_GATE_PATH not in SOLUTION_TEST_PATHS
    assert LIBRARY_GATE_PATH not in LEAN_TEST_PATHS
    definitions = {
        node.name
        for node in ast.walk(ast.parse((ROOT / LIBRARY_GATE_PATH).read_text()))
        if isinstance(node, ast.FunctionDef)
    }
    assert LIBRARY_GATE_CASE in definitions
    assert LIBRARY_GATE_BINDING_CASE in definitions
    assert LIBRARY_GATE_CASE not in LEAN_SOLUTION_TESTS
    assert LIBRARY_GATE_CASE not in SOLUTION_PLAN_TESTS


def test_reassigned_solution_cases_exist_in_the_declared_file():
    definitions = {
        node.name
        for node in ast.walk(ast.parse((ROOT / SOLUTION_TEST_PATHS[0]).read_text()))
        if isinstance(node, ast.FunctionDef)
    }
    assert LEAN_SOLUTION_TESTS
    assert len(set(LEAN_SOLUTION_TESTS)) == len(LEAN_SOLUTION_TESTS)
    assert set(LEAN_SOLUTION_TESTS) <= definitions
    assert set(SOLUTION_CASES) <= definitions
    assert PLAN_CASE in definitions


def test_container_replay_cases_exist_in_the_declared_file():
    definitions = {
        node.name
        for node in ast.walk(ast.parse((ROOT / CONTAINER_TEST_PATHS[0]).read_text()))
        if isinstance(node, ast.FunctionDef)
    }
    assert CONTAINER_REPLAY_TESTS
    assert len(set(CONTAINER_REPLAY_TESTS)) == len(CONTAINER_REPLAY_TESTS)
    assert set(CONTAINER_REPLAY_TESTS) <= definitions
    assert CONTAINER_COMPARISON_TESTS
    assert len(set(CONTAINER_COMPARISON_TESTS)) == len(CONTAINER_COMPARISON_TESTS)
    assert set(CONTAINER_COMPARISON_TESTS) <= definitions


def test_container_plan_cases_exist_in_the_declared_file():
    definitions = {
        node.name
        for node in ast.walk(ast.parse((ROOT / CONTAINER_TEST_PATHS[0]).read_text()))
        if isinstance(node, ast.FunctionDef)
    }
    assert set(CONTAINER_PLAN_TESTS) <= definitions
    assert CONTAINER_PLAN_CASES[0] == "exact"
    assert len(set(CONTAINER_PLAN_CASES)) == len(CONTAINER_PLAN_CASES)


@pytest.mark.parametrize("defect", ["empty", "duplicate", "missing", "outside"])
def test_invalid_manifests_refuse(tmp_path, defect):
    path = tmp_path / "tests/test_case.py"
    path.parent.mkdir()
    path.write_text("def test_case():\n    assert True\n")
    paths = {
        "empty": (),
        "duplicate": ("tests/test_case.py", "tests/test_case.py"),
        "missing": ("tests/test_missing.py",),
        "outside": ("../tests/test_case.py",),
    }
    with pytest.raises(pytest.UsageError, match="CI lane manifest"):
        validate_manifest(tmp_path, paths[defect])


def test_manifest_validation_accepts_existing_test_files(tmp_path):
    path = tmp_path / "tests/test_case.py"
    path.parent.mkdir()
    path.write_text("def test_case():\n    assert True\n")
    validate_manifest(tmp_path, ("tests/test_case.py",))


def test_a_stale_manifest_stops_collection(pytester, monkeypatch):
    pytester.makeconftest('pytest_plugins = ["_ci_lanes"]')
    monkeypatch.setattr(_ci_lanes, "LEAN_TEST_PATHS", ("tests/test_missing.py",))
    pytester.makepyfile("def test_must_not_run():\n    assert False\n")
    result = pytester.runpytest("-q", "--cairn-ci-lane=lean")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "missing test file: tests/test_missing.py" in result.stderr.str()


def test_a_test_assigned_to_two_lanes_stops_collection(pytester, monkeypatch):
    write_suite(pytester)
    monkeypatch.setattr(_ci_lanes, "SOLUTION_TEST_PATHS", (LEAN_TEST_PATHS[0],))
    result = pytester.runpytest("-q", "--cairn-ci-lane=all")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "contain no duplicate paths" in result.stderr.str()


def _imports_lean(path):
    return any(
        (isinstance(node, ast.Import) and any(alias.name == "cairn.lean" for alias in node.names))
        or (
            isinstance(node, ast.ImportFrom)
            and (
                node.module == "cairn.lean"
                or (node.module == "cairn" and any(alias.name == "lean" for alias in node.names))
            )
        )
        for node in ast.walk(ast.parse(path.read_text()))
    )


def test_every_direct_lean_import_has_one_explicit_lane_classification():
    imports = {path.relative_to(ROOT).as_posix() for path in (ROOT / "tests").rglob("test_*.py") if _imports_lean(path)}
    python_only = {
        "tests/unit/test_challenge_renderer.py",
        "tests/unit/test_container.py",
        "tests/unit/test_identity_sources.py",
        "tests/unit/test_lean_pins.py",
        "tests/unit/test_linux_dependency_cache.py",
    }
    indirect_lean = {
        "tests/integration/test_kernel_negatives.py",
        "tests/integration/test_prefilters_in_gate.py",
        PROVEN_TEST_PATH,
    }
    assert not set(LEAN_TEST_PATHS) & set(SOLUTION_TEST_PATHS)
    assert not set(LEAN_TEST_PATHS) & set(SOLUTION_LIBRARY_TEST_PATHS)
    assert not set(M0_TEST_PATHS) & set(GATEPLAN_TEST_PATHS)
    lean = (
        set(LEAN_TEST_PATHS) | set(SOLUTION_TEST_PATHS) | set(SOLUTION_LIBRARY_TEST_PATHS) | set(CONTAINER_TEST_PATHS)
    )
    validate_manifest(
        ROOT,
        (
            *LEAN_TEST_PATHS,
            *M0_TEST_PATHS,
            *GATEPLAN_TEST_PATHS,
            *SOLUTION_TEST_PATHS,
            *SOLUTION_LIBRARY_TEST_PATHS,
            *CONTAINER_TEST_PATHS,
        ),
    )
    assert not python_only & lean
    assert imports == (lean - indirect_lean) | python_only
    assert indirect_lean <= lean


def test_tests_that_assemble_solution_projects_run_with_lean_prerequisites():
    assert set(LEAN_PREREQUISITE_TEST_PATHS) == {
        "tests/unit/test_solution_build.py",
        "tests/unit/test_solution_comparison.py",
    }
    assert set(LEAN_PREREQUISITE_TEST_PATHS) <= set(LEAN_TEST_PATHS)
