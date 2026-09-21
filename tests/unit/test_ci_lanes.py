import ast
from pathlib import Path

import _ci_lanes
import pytest
from _ci_lanes import CONTAINER_TEST_PATHS, LEAN_SOLUTION_TESTS, LEAN_TEST_PATHS, SOLUTION_TEST_PATHS, validate_manifest

ROOT = Path(__file__).resolve().parents[2]
SOLUTION_CASES = (
    "test_real_prelude_solution_and_challenge_build_with_private_pinned_dependencies",
    "test_a_compiling_weaker_statement_fails_real_prelude_closure_comparison",
    "test_real_prelude_forgery_passes_axioms_but_fails_fresh_replay",
)
PLAN_CASE = "test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks"
PLAN_VARIANTS = ("exact", "sorry", "timeout")


def _suite(pytester):
    pytester.makeconftest('pytest_plugins = ["_ci_lanes"]')
    for relative in (
        "tests/integration/test_lean_toolchain.py",
        "tests/integration/test_solution_build_compile.py",
        "tests/integration/test_container_statement_hash.py",
        "tests/unit/test_unlisted.py",
    ):
        path = pytester.path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_pass():\n    assert True\n")
    path = pytester.path / SOLUTION_TEST_PATHS[0]
    with path.open("a") as stream:
        stream.write("import pytest\n")
        for name in SOLUTION_CASES:
            stream.write(f'@pytest.mark.parametrize("case", [0, 1])\ndef {name}(case):\n    assert True\n')
        stream.write(f'@pytest.mark.parametrize("case", {PLAN_VARIANTS!r})\ndef {PLAN_CASE}(case):\n    assert True\n')


@pytest.mark.parametrize(
    ("lane", "passed", "deselected"),
    [
        ("all", 13, 0),
        ("python", 1, 12),
        ("lean", 5, 8),
        ("solution", 3, 10),
        ("solution-plan", 3, 10),
        ("container", 1, 0),
    ],
)
def test_each_lane_runs_its_selected_tests(pytester, lane, passed, deselected):
    _suite(pytester)
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(passed=passed, deselected=deselected)


def test_default_runs_every_test_and_lane_collections_are_a_disjoint_union(pytester):
    _suite(pytester)
    default = pytester.runpytest("-q", "--import-mode=importlib")
    default.assert_outcomes(passed=13)
    populations = {}
    for lane in ("all", "python", "lean", "solution", "solution-plan", "container"):
        result = pytester.runpytest("-q", "--collect-only", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
        assert result.ret == pytest.ExitCode.OK
        populations[lane] = {line for line in result.outlines if line.startswith("tests/") and "::" in line}
    assert populations["lean"] == {"tests/integration/test_lean_toolchain.py::test_pass"} | {
        f"{SOLUTION_TEST_PATHS[0]}::{name}[{case}]" for name in LEAN_SOLUTION_TESTS for case in (0, 1)
    }
    assert populations["python"] == {"tests/unit/test_unlisted.py::test_pass"}
    assert populations["solution"] == {"tests/integration/test_solution_build_compile.py::test_pass"} | {
        f"{SOLUTION_TEST_PATHS[0]}::{SOLUTION_CASES[0]}[{case}]" for case in (0, 1)
    }
    assert populations["container"] == {"tests/integration/test_container_statement_hash.py::test_pass"}
    assert populations["solution-plan"] == {f"{SOLUTION_TEST_PATHS[0]}::{PLAN_CASE}[{case}]" for case in PLAN_VARIANTS}
    assert not populations["lean"] & populations["python"]
    assert not populations["solution"] & (populations["lean"] | populations["python"])
    assert not populations["container"] & (populations["lean"] | populations["python"] | populations["solution"])
    assert not populations["solution-plan"] & (
        populations["lean"] | populations["python"] | populations["solution"] | populations["container"]
    )
    assert populations["all"] == (
        populations["lean"]
        | populations["python"]
        | populations["solution"]
        | populations["solution-plan"]
        | populations["container"]
    )


@pytest.mark.parametrize(
    ("lane", "passed", "deselected"),
    [("python", 0, 12), ("lean", 4, 8), ("solution", 0, 3), ("container", 0, 0)],
)
def test_a_selected_failure_keeps_the_lane_red(pytester, lane, passed, deselected):
    _suite(pytester)
    relative = {
        "lean": "tests/integration/test_lean_toolchain.py",
        "solution": "tests/integration/test_solution_build_compile.py",
        "python": "tests/unit/test_unlisted.py",
        "container": "tests/integration/test_container_statement_hash.py",
    }[lane]
    (pytester.path / relative).write_text("def test_planted_failure():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=passed, deselected=deselected)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


def test_container_lane_does_not_import_modules_owned_by_other_lanes(pytester):
    _suite(pytester)
    path = pytester.path / "tests/unit/test_unlisted.py"
    path.write_text('raise RuntimeError("mac-only-import")\n')
    result = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=container")
    result.assert_outcomes(passed=1)
    for lane in ("all", "python"):
        result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
        assert result.ret == pytest.ExitCode.INTERRUPTED
        assert "mac-only-import" in result.stdout.str()


def test_container_lane_refuses_an_import_error_in_its_own_module(pytester):
    _suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text('raise RuntimeError("container-import")\n')
    result = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=container")
    result.assert_outcomes(errors=1)
    assert result.ret == pytest.ExitCode.INTERRUPTED
    assert "container-import" in result.stdout.str()


@pytest.mark.parametrize(
    ("name", "lane", "passed", "deselected"),
    [(SOLUTION_CASES[0], "solution", 0, 3), *((name, "lean", 1, 2) for name in SOLUTION_CASES[1:])],
)
def test_a_reassigned_solution_failure_keeps_its_lane_red(pytester, name, lane, passed, deselected):
    _suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(f"def {name}():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=passed, deselected=deselected)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


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


@pytest.mark.parametrize("failed_case", PLAN_VARIANTS)
def test_each_ordered_plan_failure_keeps_its_lane_red(pytester, failed_case):
    _suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", {PLAN_VARIANTS!r})\n'
        f"def {PLAN_CASE}(case):\n    assert case != {failed_case!r}\n"
    )
    result = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=solution-plan")
    result.assert_outcomes(failed=1, passed=2, deselected=3)
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
    lean = set(LEAN_TEST_PATHS) | set(SOLUTION_TEST_PATHS) | set(CONTAINER_TEST_PATHS)
    validate_manifest(ROOT, (*LEAN_TEST_PATHS, *SOLUTION_TEST_PATHS, *CONTAINER_TEST_PATHS))
    assert not python_only & lean
    assert imports == (lean - indirect_lean) | python_only
    assert indirect_lean <= lean
