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
    parser.addoption("--cairn-ci-lane", choices=("all", "python", "lean", "solution", "container"), default="all")


def pytest_ignore_collect(collection_path, config):
    if config.getoption("--cairn-ci-lane") != "container" or not collection_path.is_file():
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
    if lane == "all":
        return
    selected = []
    deselected = []
    for item in items:
        path = item.path.relative_to(config.rootpath).as_posix()
        if path in SOLUTION_TEST_PATHS:
            item_lane = "lean" if item.originalname in LEAN_SOLUTION_TESTS else "solution"
        elif path in LEAN_TEST_PATHS:
            item_lane = "lean"
        elif path in CONTAINER_TEST_PATHS:
            item_lane = "container"
        else:
            item_lane = "python"
        (selected if item_lane == lane else deselected).append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)
