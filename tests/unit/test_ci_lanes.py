import ast
from pathlib import Path

import _ci_lanes
import pytest
from _ci_lanes import LEAN_TEST_PATHS, SOLUTION_TEST_PATHS, validate_manifest

ROOT = Path(__file__).resolve().parents[2]


def _suite(pytester):
    pytester.makeconftest('pytest_plugins = ["_ci_lanes"]')
    for relative in (
        "tests/integration/test_lean_toolchain.py",
        "tests/integration/test_solution_build_compile.py",
        "tests/unit/test_unlisted.py",
    ):
        path = pytester.path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_pass():\n    assert True\n")


@pytest.mark.parametrize(
    ("lane", "passed", "deselected"), [("all", 3, 0), ("python", 1, 2), ("lean", 1, 2), ("solution", 1, 2)]
)
def test_each_lane_runs_its_selected_tests(pytester, lane, passed, deselected):
    _suite(pytester)
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(passed=passed, deselected=deselected)


def test_default_runs_every_test_and_lane_collections_are_a_disjoint_union(pytester):
    _suite(pytester)
    default = pytester.runpytest("-q", "--import-mode=importlib")
    default.assert_outcomes(passed=3)
    populations = {}
    for lane in ("all", "python", "lean", "solution"):
        result = pytester.runpytest("-q", "--collect-only", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
        assert result.ret == pytest.ExitCode.OK
        populations[lane] = {line for line in result.outlines if line.startswith("tests/") and "::" in line}
    assert populations["lean"] == {"tests/integration/test_lean_toolchain.py::test_pass"}
    assert populations["python"] == {"tests/unit/test_unlisted.py::test_pass"}
    assert populations["solution"] == {"tests/integration/test_solution_build_compile.py::test_pass"}
    assert not populations["lean"] & populations["python"]
    assert not populations["solution"] & (populations["lean"] | populations["python"])
    assert populations["all"] == populations["lean"] | populations["python"] | populations["solution"]


@pytest.mark.parametrize("lane", ["python", "lean", "solution"])
def test_a_selected_failure_keeps_the_lane_red(pytester, lane):
    _suite(pytester)
    relative = {
        "lean": "tests/integration/test_lean_toolchain.py",
        "solution": "tests/integration/test_solution_build_compile.py",
        "python": "tests/unit/test_unlisted.py",
    }[lane]
    (pytester.path / relative).write_text("def test_planted_failure():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, deselected=2)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


def test_invalid_lane_refuses(pytester):
    _suite(pytester)
    result = pytester.runpytest("--cairn-ci-lane=leam")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "invalid choice" in result.stderr.str()


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
    _suite(pytester)
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
        "tests/unit/test_identity_sources.py",
        "tests/unit/test_lean_pins.py",
        "tests/unit/test_solution_build.py",
        "tests/unit/test_solution_comparison.py",
    }
    indirect_lean = {"tests/integration/test_prefilters_in_gate.py"}
    assert not set(LEAN_TEST_PATHS) & set(SOLUTION_TEST_PATHS)
    lean = set(LEAN_TEST_PATHS) | set(SOLUTION_TEST_PATHS)
    validate_manifest(ROOT, (*LEAN_TEST_PATHS, *SOLUTION_TEST_PATHS))
    assert not python_only & lean
    assert imports == (lean - indirect_lean) | python_only
    assert indirect_lean <= lean
