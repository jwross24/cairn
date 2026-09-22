from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEAN_TEST_PATHS = (
    "tests/integration/test_lean_toolchain.py",
    "tests/integration/test_axiom_computation.py",
    "tests/integration/test_challenge_compile.py",
    "tests/integration/test_hasher_stability.py",
    "tests/integration/test_solution_forgery_steps.py",
    "tests/integration/test_lean_container.py",
    "tests/integration/test_prefilters_in_gate.py",
    "tests/unit/test_formal_statement_hasher.py",
)
SOLUTION_TEST_PATHS = ("tests/integration/test_solution_build_compile.py",)
CONTAINER_TEST_PATHS = ("tests/integration/test_container_statement_hash.py",)
LEAN_SOLUTION_TESTS = (
    "test_a_compiling_weaker_statement_fails_real_prelude_closure_comparison",
    "test_real_prelude_forgery_passes_axioms_but_fails_fresh_replay",
)
SOLUTION_PLAN_TESTS = ("test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks",)
SOLUTION_PLAN_CASES = ("exact", "sorry", "timeout")
SOLUTION_PLAN_LANES = ("solution-plan-exact", "solution-plan-refusals")
CONTAINER_REPLAY_TESTS = (
    "test_linux_candidate_fresh_replay",
    "test_linux_replay_timeouts_keep_their_stage_and_check_inputs",
)
CONTAINER_COMPARISON_TESTS = (
    "test_linux_candidate_closure_comparison_matches_exact_statement",
    "test_linux_candidate_closure_comparison_refuses_weaker_statement",
)
CI_LANES = (
    "python",
    "lean",
    "solution",
    *SOLUTION_PLAN_LANES,
    "container",
    "container-replay-exact",
    "container-replay-refusals",
)


def validate_manifest(root, paths):
    if not paths or len(set(paths)) != len(paths):
        raise pytest.UsageError("CI lane manifest must be nonempty and contain no duplicate paths")
    for path in paths:
        relative = Path(path)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not path.startswith("tests/")
            or not relative.name.startswith("test_")
            or relative.suffix != ".py"
            or not (root / relative).is_file()
        ):
            raise pytest.UsageError(f"CI lane manifest has an invalid or missing test file: {path}")


def pytest_addoption(parser):
    parser.addoption("--cairn-ci-lane", choices=("all", "solution-plan", "container-replay", *CI_LANES), default="all")


def pytest_ignore_collect(collection_path, config):
    if not config.getoption("--cairn-ci-lane").startswith("container") or not collection_path.is_file():
        return None
    if not collection_path.is_relative_to(config.rootpath):
        return None
    if collection_path.relative_to(config.rootpath).as_posix() not in CONTAINER_TEST_PATHS:
        return True
    return None


def pytest_collection_modifyitems(config, items):
    validate_manifest(ROOT, LEAN_TEST_PATHS)
    validate_manifest(ROOT, SOLUTION_TEST_PATHS)
    validate_manifest(ROOT, CONTAINER_TEST_PATHS)
    validate_manifest(ROOT, (*LEAN_TEST_PATHS, *SOLUTION_TEST_PATHS, *CONTAINER_TEST_PATHS))
    lane = config.getoption("--cairn-ci-lane")
    selected = []
    deselected = []
    for item in items:
        path = item.path.relative_to(config.rootpath).as_posix()
        if path in SOLUTION_TEST_PATHS:
            if item.originalname in SOLUTION_PLAN_TESTS:
                case = getattr(item, "callspec", None)
                case = case.params.get("case") if case is not None else None
                if case not in SOLUTION_PLAN_CASES:
                    raise pytest.UsageError(f"invalid ordered-plan case: {item.nodeid}: {case!r}")
                item_lane = "solution-plan-exact" if case == "exact" else "solution-plan-refusals"
            else:
                item_lane = "lean" if item.originalname in LEAN_SOLUTION_TESTS else "solution"
        elif path in LEAN_TEST_PATHS:
            item_lane = "lean"
        elif path in CONTAINER_TEST_PATHS:
            if item.originalname in CONTAINER_REPLAY_TESTS:
                case = getattr(item, "callspec", None)
                proof = case.params.get("proof") if case is not None else None
                item_lane = "container-replay-exact" if proof == "rfl" else "container-replay-refusals"
            elif item.originalname in CONTAINER_COMPARISON_TESTS:
                item_lane = (
                    "container-replay-exact"
                    if item.originalname == CONTAINER_COMPARISON_TESTS[0]
                    else "container-replay-refusals"
                )
            else:
                item_lane = "container"
        else:
            item_lane = "python"
        matches = (
            lane == "all"
            or item_lane == lane
            or (lane in ("solution-plan", "container-replay") and item_lane.startswith(f"{lane}-"))
        )
        (selected if matches else deselected).append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)
