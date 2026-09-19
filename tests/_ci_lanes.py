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
    parser.addoption("--cairn-ci-lane", choices=("all", "python", "lean", "solution"), default="all")


def pytest_collection_modifyitems(config, items):
    validate_manifest(ROOT, LEAN_TEST_PATHS)
    validate_manifest(ROOT, SOLUTION_TEST_PATHS)
    validate_manifest(ROOT, (*LEAN_TEST_PATHS, *SOLUTION_TEST_PATHS))
    lane = config.getoption("--cairn-ci-lane")
    if lane == "all":
        return
    selected = []
    deselected = []
    for item in items:
        path = item.path.relative_to(config.rootpath).as_posix()
        if path in SOLUTION_TEST_PATHS:
            item_lane = "solution"
        elif path in LEAN_TEST_PATHS:
            item_lane = "lean"
        else:
            item_lane = "python"
        (selected if item_lane == lane else deselected).append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)
