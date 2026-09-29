import ast
from pathlib import Path

import _ci_lanes
import pytest
from _ci_lanes import (
    CI_LANES,
    CONTAINER_COMPARISON_TESTS,
    CONTAINER_PLAN_CASES,
    CONTAINER_PLAN_TESTS,
    CONTAINER_REPLAY_TESTS,
    CONTAINER_TEST_PATHS,
    GATEPLAN_TEST_PATHS,
    LEAN_PREREQUISITE_TEST_PATHS,
    LEAN_SOLUTION_TESTS,
    LEAN_TEST_PATHS,
    M0_TEST_PATHS,
    SOLUTION_LIBRARY_TEST_PATHS,
    SOLUTION_PLAN_TESTS,
    SOLUTION_TEST_PATHS,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
SOLUTION_CASES = (
    "test_real_prelude_solution_and_challenge_build_with_private_pinned_dependencies",
    "test_a_compiling_weaker_statement_fails_real_prelude_closure_comparison",
    "test_real_prelude_forgery_passes_axioms_but_fails_fresh_replay",
)
PLAN_CASE = "test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks"
PLAN_VARIANTS = ("exact", "sorry", "timeout")
LIBRARY_GATE_PATH = SOLUTION_LIBRARY_TEST_PATHS[0]
LIBRARY_GATE_CASE = "test_library_items_pass_gate"
LIBRARY_GATE_ITEMS = ("dlp", "finite_point")


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
    for relative in (*M0_TEST_PATHS, *GATEPLAN_TEST_PATHS):
        path = pytester.path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_pass():\n    assert True\n")
    (pytester.path / LIBRARY_GATE_PATH).write_text(
        f'import pytest\n@pytest.mark.parametrize("item", {LIBRARY_GATE_ITEMS!r})\n'
        f"def {LIBRARY_GATE_CASE}(item):\n    assert True\n"
    )
    path = pytester.path / SOLUTION_TEST_PATHS[0]
    with path.open("a") as stream:
        stream.write("import pytest\n")
        for name in SOLUTION_CASES:
            stream.write(f'@pytest.mark.parametrize("case", [0, 1])\ndef {name}(case):\n    assert True\n')
        stream.write(f'@pytest.mark.parametrize("case", {PLAN_VARIANTS!r})\ndef {PLAN_CASE}(case):\n    assert True\n')
    with (pytester.path / CONTAINER_TEST_PATHS[0]).open("a") as stream:
        stream.write("import pytest\n")
        stream.write(
            f'@pytest.mark.parametrize("proof", ["rfl"])\ndef {CONTAINER_REPLAY_TESTS[0]}(proof):\n    assert True\n'
        )
        stream.write(f"def {CONTAINER_REPLAY_TESTS[1]}():\n    assert True\n")
        for name in CONTAINER_COMPARISON_TESTS:
            stream.write(f"def {name}():\n    assert True\n")
        stream.write(
            f'@pytest.mark.parametrize("case", {CONTAINER_PLAN_CASES!r})\ndef {CONTAINER_PLAN_TESTS[0]}(case):\n    assert True\n'
        )


@pytest.mark.parametrize(
    ("lane", "passed", "deselected"),
    [
        ("all", 27, 0),
        ("python", 1, 26),
        ("m0", 1, 26),
        ("gateplan", 3, 24),
        ("lean", 5, 22),
        ("solution", 3, 24),
        ("solution-library", 2, 25),
        ("solution-plan", 3, 24),
        ("solution-plan-exact", 1, 26),
        ("solution-plan-refusals", 2, 25),
        ("container", 1, 8),
        ("container-replay", 4, 5),
        ("container-replay-exact", 2, 7),
        ("container-replay-refusals", 2, 7),
        ("container-plan", 4, 5),
        ("container-plan-exact", 1, 8),
        ("container-plan-refusals", 3, 6),
    ],
)
def test_each_lane_runs_its_selected_tests(pytester, lane, passed, deselected):
    _suite(pytester)
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(passed=passed, deselected=deselected)


def test_default_runs_every_test_and_lane_collections_are_a_disjoint_union(pytester):
    _suite(pytester)
    default = pytester.runpytest("-q", "--import-mode=importlib")
    default.assert_outcomes(passed=27)
    populations = {}
    for lane in ("all", "solution-plan", "container-replay", "container-plan", *CI_LANES):
        result = pytester.runpytest("-q", "--collect-only", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
        assert result.ret == pytest.ExitCode.OK
        populations[lane] = {line for line in result.outlines if line.startswith("tests/") and "::" in line}
    assert populations["lean"] == {"tests/integration/test_lean_toolchain.py::test_pass"} | {
        f"{SOLUTION_TEST_PATHS[0]}::{name}[{case}]" for name in LEAN_SOLUTION_TESTS for case in (0, 1)
    }
    assert populations["python"] == {"tests/unit/test_unlisted.py::test_pass"}
    assert populations["m0"] == {f"{M0_TEST_PATHS[0]}::test_pass"}
    assert populations["gateplan"] == {f"{path}::test_pass" for path in GATEPLAN_TEST_PATHS}
    assert populations["solution"] == {"tests/integration/test_solution_build_compile.py::test_pass"} | {
        f"{SOLUTION_TEST_PATHS[0]}::{SOLUTION_CASES[0]}[{case}]" for case in (0, 1)
    }
    assert populations["solution-library"] == {
        f"{LIBRARY_GATE_PATH}::{LIBRARY_GATE_CASE}[{item}]" for item in LIBRARY_GATE_ITEMS
    }
    assert populations["container"] == {"tests/integration/test_container_statement_hash.py::test_pass"}
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
    assert populations["solution-plan"] == {f"{SOLUTION_TEST_PATHS[0]}::{PLAN_CASE}[{case}]" for case in PLAN_VARIANTS}
    plan = f"{CONTAINER_TEST_PATHS[0]}::{CONTAINER_PLAN_TESTS[0]}"
    assert populations["container-plan"] == {f"{plan}[{case}]" for case in CONTAINER_PLAN_CASES}
    assert populations["container-plan-exact"] == {f"{plan}[exact]"}
    assert populations["container-plan-refusals"] == {f"{plan}[{case}]" for case in CONTAINER_PLAN_CASES[1:]}
    combined = set()
    for lane in CI_LANES:
        assert populations[lane]
        assert not combined & populations[lane]
        combined |= populations[lane]
    assert combined == populations["all"]
    assert populations["solution-plan-exact"] == {f"{SOLUTION_TEST_PATHS[0]}::{PLAN_CASE}[exact]"}
    assert populations["solution-plan-refusals"] == {
        f"{SOLUTION_TEST_PATHS[0]}::{PLAN_CASE}[sorry]",
        f"{SOLUTION_TEST_PATHS[0]}::{PLAN_CASE}[timeout]",
    }
    assert not populations["lean"] & populations["python"]
    assert not populations["solution"] & (populations["lean"] | populations["python"])
    assert not populations["container"] & (populations["lean"] | populations["python"] | populations["solution"])
    assert not populations["solution-plan"] & (
        populations["lean"] | populations["python"] | populations["solution"] | populations["container"]
    )
    assert populations["all"] == (
        populations["lean"]
        | populations["python"]
        | populations["m0"]
        | populations["gateplan"]
        | populations["solution"]
        | populations["solution-library"]
        | populations["solution-plan"]
        | populations["container"]
        | populations["container-replay"]
        | populations["container-plan"]
    )


def test_new_lane_manifests_name_only_the_measured_test_modules():
    assert M0_TEST_PATHS == ("tests/e2e/test_m0_slice.py",)
    assert GATEPLAN_TEST_PATHS == (
        "tests/integration/test_gateplan.py",
        "tests/integration/test_gateplan_cli.py",
        "tests/integration/test_ladder_gate_selftest.py",
    )
    assert SOLUTION_LIBRARY_TEST_PATHS == ("tests/integration/test_challenge_gate.py",)


@pytest.mark.parametrize(
    ("lane", "passed", "deselected"),
    [
        ("python", 0, 26),
        ("m0", 0, 26),
        ("gateplan", 2, 24),
        ("lean", 4, 22),
        ("solution", 0, 17),
        ("solution-library", 0, 25),
        ("container", 0, 0),
    ],
)
def test_a_selected_failure_keeps_the_lane_red(pytester, lane, passed, deselected):
    _suite(pytester)
    relative = {
        "lean": "tests/integration/test_lean_toolchain.py",
        "solution": "tests/integration/test_solution_build_compile.py",
        "solution-library": LIBRARY_GATE_PATH,
        "python": "tests/unit/test_unlisted.py",
        "m0": M0_TEST_PATHS[0],
        "gateplan": GATEPLAN_TEST_PATHS[0],
        "container": "tests/integration/test_container_statement_hash.py",
    }[lane]
    (pytester.path / relative).write_text("def test_planted_failure():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=passed, deselected=deselected)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize(
    ("lane", "passed", "deselected"),
    [
        ("container", 1, 8),
        ("container-replay", 4, 5),
        ("container-replay-exact", 2, 7),
        ("container-replay-refusals", 2, 7),
        ("container-plan", 4, 5),
        ("container-plan-exact", 1, 8),
        ("container-plan-refusals", 3, 6),
    ],
)
def test_container_lane_does_not_import_modules_owned_by_other_lanes(pytester, lane, passed, deselected):
    _suite(pytester)
    path = pytester.path / "tests/unit/test_unlisted.py"
    path.write_text('raise RuntimeError("mac-only-import")\n')
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(passed=passed, deselected=deselected)
    for lane in ("all", "python"):
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
        "container-plan-refusals",
    ],
)
def test_container_lane_refuses_an_import_error_in_its_own_module(pytester, lane):
    _suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text('raise RuntimeError("container-import")\n')
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(errors=1)
    assert result.ret == pytest.ExitCode.INTERRUPTED
    assert "container-import" in result.stdout.str()


@pytest.mark.parametrize(
    ("name", "lane", "passed", "deselected"),
    [(SOLUTION_CASES[0], "solution", 0, 17), *((name, "lean", 1, 16) for name in SOLUTION_CASES[1:])],
)
def test_a_reassigned_solution_failure_keeps_its_lane_red(pytester, name, lane, passed, deselected):
    _suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(f"def {name}():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=passed, deselected=deselected)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


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
    assert LIBRARY_GATE_CASE not in LEAN_SOLUTION_TESTS
    assert LIBRARY_GATE_CASE not in SOLUTION_PLAN_TESTS


def test_a_library_gate_failure_keeps_the_solution_library_lane_red(pytester):
    _suite(pytester)
    (pytester.path / LIBRARY_GATE_PATH).write_text(
        f'import pytest\n@pytest.mark.parametrize("item", {LIBRARY_GATE_ITEMS!r})\n'
        f"def {LIBRARY_GATE_CASE}(item):\n    assert item != {LIBRARY_GATE_ITEMS[1]!r}\n"
    )
    result = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=solution-library")
    result.assert_outcomes(failed=1, passed=1, deselected=25)
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    other = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=solution")
    other.assert_outcomes(passed=3, deselected=24)


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


@pytest.mark.parametrize("name", [*CONTAINER_REPLAY_TESTS, *CONTAINER_COMPARISON_TESTS])
def test_container_replay_failure_keeps_its_lane_red(pytester, name):
    _suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text(f"def {name}():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=container-replay")
    result.assert_outcomes(failed=1)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


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


@pytest.mark.parametrize("proof", ["rfl", "sorry", "forged"])
def test_container_replay_shards_route_proof_parameters_and_propagate_failure(pytester, proof):
    _suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text(
        'import pytest\n@pytest.mark.parametrize("proof", ["rfl", "sorry", "forged"], ids=["a", "b", "c"])\n'
        f"def {CONTAINER_REPLAY_TESTS[0]}(proof):\n    assert proof != {proof!r}\n"
    )
    exact = proof == "rfl"
    lane = "container-replay-exact" if exact else "container-replay-refusals"
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=0 if exact else 1, deselected=2 if exact else 1)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


def test_container_plan_cases_exist_in_the_declared_file():
    definitions = {
        node.name
        for node in ast.walk(ast.parse((ROOT / CONTAINER_TEST_PATHS[0]).read_text()))
        if isinstance(node, ast.FunctionDef)
    }
    assert set(CONTAINER_PLAN_TESTS) <= definitions
    assert CONTAINER_PLAN_CASES[0] == "exact"
    assert len(set(CONTAINER_PLAN_CASES)) == len(CONTAINER_PLAN_CASES)


@pytest.mark.parametrize("case", CONTAINER_PLAN_CASES)
def test_container_plan_shards_route_by_case_and_propagate_failure(pytester, case):
    _suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", {CONTAINER_PLAN_CASES!r})\n'
        f"def {CONTAINER_PLAN_TESTS[0]}(case):\n    assert case != {case!r}\n"
    )
    exact = case == "exact"
    lane = "container-plan-exact" if exact else "container-plan-refusals"
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=0 if exact else 2, deselected=3 if exact else 1)
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    aggregate = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=container-plan")
    aggregate.assert_outcomes(failed=1, passed=3)
    assert aggregate.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize("lane", ["all", "container-plan", "container-plan-exact", "container-plan-refusals"])
@pytest.mark.parametrize("case", ["unknown", None, 1])
def test_unknown_container_plan_parameters_refuse_collection(pytester, lane, case):
    _suite(pytester)
    (pytester.path / CONTAINER_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", [{case!r}])\n'
        f"def {CONTAINER_PLAN_TESTS[0]}(case):\n    assert True\n"
    )
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "invalid container plan case" in result.stderr.str()


@pytest.mark.parametrize("failed_case", PLAN_VARIANTS)
def test_each_ordered_plan_failure_keeps_its_lane_red(pytester, failed_case):
    _suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", {PLAN_VARIANTS!r})\n'
        f"def {PLAN_CASE}(case):\n    assert case != {failed_case!r}\n"
    )
    result = pytester.runpytest("-q", "--import-mode=importlib", "--cairn-ci-lane=solution-plan")
    result.assert_outcomes(failed=1, passed=2, deselected=17)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


@pytest.mark.parametrize("case", PLAN_VARIANTS)
def test_plan_shards_route_by_parameter_value_and_propagate_failure(pytester, case):
    _suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", {PLAN_VARIANTS!r}, ids=["a", "b", "c"])\n'
        f"def {PLAN_CASE}(case):\n    assert case != {case!r}\n"
    )
    lane = "solution-plan-exact" if case == "exact" else "solution-plan-refusals"
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    result.assert_outcomes(failed=1, passed=0 if case == "exact" else 1, deselected=19 if case == "exact" else 18)
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
    _suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(
        f'import pytest\n@pytest.mark.parametrize("case", [{case!r}])\ndef {PLAN_CASE}(case):\n    assert True\n'
    )
    result = pytester.runpytest("-q", "--import-mode=importlib", f"--cairn-ci-lane={lane}")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "invalid ordered-plan case" in result.stderr.str()


def test_missing_plan_parameter_refuses_collection(pytester):
    _suite(pytester)
    (pytester.path / SOLUTION_TEST_PATHS[0]).write_text(f"def {PLAN_CASE}():\n    assert True\n")
    result = pytester.runpytest("-q", "--import-mode=importlib")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "invalid ordered-plan case" in result.stderr.str()


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
        "tests/unit/test_container.py",
        "tests/unit/test_identity_sources.py",
        "tests/unit/test_lean_pins.py",
        "tests/unit/test_linux_dependency_cache.py",
    }
    indirect_lean = {"tests/integration/test_prefilters_in_gate.py"}
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
