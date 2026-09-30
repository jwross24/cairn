import json
import os
import shlex
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from _ci_lanes import (
    CI_LANES,
    CONTAINER_PLAN_CASES,
    CONTAINER_TEST_PATHS,
    GATEPLAN_TEST_PATHS,
    LEAN_LANES,
    LEAN_REPLAY_TEST,
    LEAN_TEST_PATHS,
    M0_ABORT_CASES,
    M0_ABORT_TEST,
    M0_LANES,
    M0_TEST_CASES,
    M0_TEST_PATHS,
    PROVEN_DEV_TEST,
    PROVEN_GOLD_TEST,
    PROVEN_TEST_PATH,
    SOLUTION_LIBRARY_BINDING_TEST,
    SOLUTION_LIBRARY_CASE_TEST,
    SOLUTION_LIBRARY_ITEMS,
    SOLUTION_LIBRARY_LANES,
    SOLUTION_LIBRARY_TEST_PATHS,
    SOLUTION_PLAN_LANES,
    SOLUTION_TEST_PATHS,
)

CONTAINER_PLAN_LANES = ("container-plan-exact", "container-plan-refusals")
CONTAINER_AUTHORITY_NODES = (
    "tests/integration/test_lean_container.py::test_the_gold_image_builds_and_the_checker_runs_under_landrun_inside_it",
    "tests/integration/test_lean_container.py::test_the_chattr_probe_inside_the_container_is_recorded",
)

ROOT = Path(__file__).resolve().parents[2]


def _collect_nodes(lane):
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only", f"--cairn-ci-lane={lane}"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return {line for line in result.stdout.splitlines() if line.startswith("tests/") and "::" in line}


@pytest.fixture
def dispatch(tmp_path: Path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy2(ROOT / "scripts/check.sh", scripts / "check.sh")
    theater = scripts / "theater-patterns.sh"
    theater.write_text("#!/bin/sh\nexit 0\n")
    theater.chmod(0o755)
    commands = tmp_path / "commands.jsonl"
    uv = tmp_path / "uv"
    uv.write_text(
        f"#!{sys.executable}\nimport json, os, sys\n"
        f"with open({str(commands)!r}, 'a') as out:\n    out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "sys.exit(int(os.environ.get('PLANTED_PYTEST_EXIT', '0')) if 'pytest' in sys.argv else 0)\n"
    )
    uv.chmod(0o755)
    env: dict[str, str] = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    env.pop("CAIRN_CHECK_SKIP", None)
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)

    def run(*args: str, pytest_exit: int = 0):
        result = subprocess.run(
            [str(scripts / "check.sh"), *args],
            cwd=tmp_path,
            env={**env, "PLANTED_PYTEST_EXIT": str(pytest_exit)},
            text=True,
            capture_output=True,
            timeout=30,
        )
        calls = [json.loads(line) for line in commands.read_text().splitlines()] if commands.exists() else []
        return result, calls

    return run


@pytest.mark.parametrize(
    "lane",
    [
        *CI_LANES,
        "m0",
        "lean",
        "solution-library",
        "solution-plan",
        "container-replay",
        "container-plan",
        "all",
    ],
)
def test_lane_dispatch_preserves_pytest_arguments(dispatch, lane):
    args = [] if lane == "all" else ["--ci-lane", lane]
    result, calls = dispatch(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    assert [call for call in calls if "pytest" in call] == [
        ["run", "pytest", "-q", "--durations=25", f"--cairn-ci-lane={lane}"]
    ]


@pytest.mark.parametrize(
    "lane",
    [*CI_LANES, "m0", "lean", "solution-library", "solution-plan", "container-replay", "container-plan"],
)
def test_a_failed_lane_refuses_the_gate(dispatch, lane):
    result, calls = dispatch("--ci-lane", lane, pytest_exit=1)
    assert result.returncode == 1
    assert "FAIL tests" in result.stderr
    assert any("pytest" in call for call in calls)


@pytest.mark.parametrize(
    "args",
    [
        ["--ci-lane"],
        ["--ci-lane", "typo"],
        ["--ci-lane", "solution-plan-sorry"],
        ["--ci-lane", "solution-plan-timeout"],
        ["--ci-lane", "container-plan-weaker"],
        ["--ci-lane", "container-plans"],
        ["--ci-lane", "python", "--fast"],
        ["--ci-lane", "python-integration", "--fast"],
        ["--ci-lane", "python-integration", "--unit"],
        ["--ci-lane", "python-integration", "--paths", "src/cairn/lean.py"],
        ["--ci-lane", "m0", "--fast"],
        ["--ci-lane", "gateplan", "--fast"],
        ["--ci-lane", "solution-library", "--fast"],
        ["--ci-lane", "lean", "--unit"],
        ["--ci-lane", "python", "--paths", "src/cairn/lean.py"],
        ["--ci-lane", "solution", "--fast"],
        ["--ci-lane", "solution", "--unit"],
        ["--ci-lane", "solution", "--paths", "src/cairn/lean.py"],
        ["--ci-lane", "solution-plan", "--fast"],
        ["--ci-lane", "solution-plan", "--unit"],
        ["--ci-lane", "solution-plan", "--paths", "src/cairn/lean.py"],
        *(
            ["--ci-lane", lane, *flags]
            for lane in (*SOLUTION_PLAN_LANES, "container-plan", *CONTAINER_PLAN_LANES)
            for flags in (["--fast"], ["--unit"], ["--paths", "src/cairn/lean.py"])
        ),
        *(
            ["--ci-lane", lane, *flags]
            for lane in (*M0_LANES, "gateplan", *LEAN_LANES, *SOLUTION_LIBRARY_LANES)
            for flags in (["--fast"], ["--unit"], ["--paths", "src/cairn/lean.py"])
        ),
        *(
            ["--ci-lane", lane, *flags]
            for lane in ("m0", "lean", "solution-library")
            for flags in (["--unit"], ["--paths", "src/cairn/lean.py"])
        ),
    ],
)
def test_invalid_lane_selection_runs_no_gates(dispatch, args):
    result, calls = dispatch(*args)
    assert result.returncode == 3
    assert "invalid CI lane or incompatible selection flags" in result.stderr
    assert calls == []


@pytest.mark.parametrize(
    ("lane", "test_file"),
    [
        ("python", "tests/unit/test_ci_lanes.py"),
        ("python-integration", "tests/integration/test_grounding_subprocess.py"),
        *((lane, M0_TEST_PATHS[0]) for lane in ("m0", *M0_LANES)),
        ("gateplan", GATEPLAN_TEST_PATHS[0]),
        *((lane, "tests/integration/test_lean_toolchain.py") for lane in ("lean", "lean-core")),
        ("lean-replay", "tests/integration/test_solution_build_compile.py"),
        ("solution", "tests/integration/test_solution_build_compile.py"),
        *((lane, SOLUTION_LIBRARY_TEST_PATHS[0]) for lane in ("solution-library", *SOLUTION_LIBRARY_LANES)),
        ("solution-plan", "tests/integration/test_solution_build_compile.py"),
        *((lane, "tests/integration/test_solution_build_compile.py") for lane in SOLUTION_PLAN_LANES),
        *(
            (lane, "tests/integration/test_container_statement_hash.py")
            for lane in ("container-plan", *CONTAINER_PLAN_LANES)
        ),
    ],
)
def test_the_lane_gate_command_collects_the_real_repository(lane, test_file):
    line = next(
        line
        for line in (ROOT / "scripts/check.sh").read_text().splitlines()
        if line.strip().startswith("gate tests uv run pytest ")
    )
    argv = [arg.replace("$CI_LANE", lane) for arg in shlex.split(line)[4:]]
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(
        [sys.executable, "-m", *argv, "--collect-only"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{test_file}::" in result.stdout
    if lane.startswith("solution-library"):
        selected = [line for line in result.stdout.splitlines() if line.startswith("tests/") and "::" in line]
        case_node = f"{SOLUTION_LIBRARY_TEST_PATHS[0]}::{SOLUTION_LIBRARY_CASE_TEST}"
        binding_node = f"{SOLUTION_LIBRARY_TEST_PATHS[0]}::{SOLUTION_LIBRARY_BINDING_TEST}"
        expected = {
            "solution-library": {f"{case_node}[{item}]" for item in SOLUTION_LIBRARY_ITEMS} | {binding_node},
            "solution-library-dlp": {f"{case_node}[dlp]"},
            "solution-library-finite-point": {f"{case_node}[finite_point]"},
            "solution-library-binding": {binding_node},
        }[lane]
        assert set(selected) == expected
    if lane.startswith("m0-") or lane == "m0":
        selected = [line for line in result.stdout.splitlines() if line.startswith("tests/") and "::" in line]
        path = M0_TEST_PATHS[0]
        m0_nodes = {f"{path}::{name}" for names in M0_TEST_CASES.values() for name in names if name != M0_ABORT_TEST}
        m0_nodes.update(f"{path}::{M0_ABORT_TEST}[{case}]" for case in M0_ABORT_CASES)
        expected = {
            "m0": m0_nodes,
            **{
                group: (
                    {f"{path}::{M0_ABORT_TEST}[{case}]" for case in M0_ABORT_CASES}
                    if group == "m0-boundaries"
                    else set()
                )
                | {f"{path}::{name}" for name in names if name != M0_ABORT_TEST}
                for group, names in M0_TEST_CASES.items()
            },
        }[lane]
        assert set(selected) == expected
    if lane in ("lean", *LEAN_LANES):
        selected = [line for line in result.stdout.splitlines() if line.startswith("tests/") and "::" in line]
        replay_node = f"tests/integration/test_solution_build_compile.py::{LEAN_REPLAY_TEST}"
        if lane == "lean-replay":
            assert selected == [replay_node]
        elif lane == "lean":
            assert replay_node in selected
        else:
            assert replay_node not in selected
    if lane.startswith("container-plan"):
        selected = [line for line in result.stdout.splitlines() if line.startswith("tests/") and "::" in line]
        cases = {
            "container-plan": CONTAINER_PLAN_CASES,
            "container-plan-exact": CONTAINER_PLAN_CASES[:1],
            "container-plan-refusals": CONTAINER_PLAN_CASES[1:],
        }[lane]
        expected = [
            f"tests/integration/test_container_statement_hash.py::test_linux_ordered_plan_runs_each_step_in_order[{case}]"
            for case in cases
        ]
        if lane in ("container-plan", "container-plan-exact"):
            expected.append(f"{PROVEN_TEST_PATH}::{PROVEN_GOLD_TEST}")
        assert selected == expected
    if lane.startswith("solution-plan-"):
        selected = [line for line in result.stdout.splitlines() if line.startswith("tests/") and "::" in line]
        cases = ("exact",) if lane == "solution-plan-exact" else ("sorry", "timeout")
        expected = [
            "tests/integration/test_solution_build_compile.py::"
            f"test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks[{case}]"
            for case in cases
        ]
        if lane == "solution-plan-exact":
            expected.append(f"{PROVEN_TEST_PATH}::{PROVEN_DEV_TEST}")
        assert set(selected) == set(expected)


def test_python_lanes_partition_the_previous_fallback_population():
    all_nodes = _collect_nodes("all")
    unit_nodes = _collect_nodes("python")
    integration_nodes = _collect_nodes("python-integration")
    explicit_paths = {
        *LEAN_TEST_PATHS,
        *M0_TEST_PATHS,
        *GATEPLAN_TEST_PATHS,
        *SOLUTION_TEST_PATHS,
        *SOLUTION_LIBRARY_TEST_PATHS,
        *CONTAINER_TEST_PATHS,
    }
    previous_python_nodes = {node for node in all_nodes if node.split("::", 1)[0] not in explicit_paths}
    assert unit_nodes
    assert integration_nodes
    assert unit_nodes.isdisjoint(integration_nodes)
    assert unit_nodes | integration_nodes == previous_python_nodes
    assert all(not node.split("::", 1)[0].startswith("tests/integration/") for node in unit_nodes)
    assert all(node.split("::", 1)[0].startswith("tests/integration/") for node in integration_nodes)


@pytest.mark.parametrize(
    ("lane", "paths", "count"),
    [
        ("m0", M0_TEST_PATHS, 17),
        *((lane, M0_TEST_PATHS, len(M0_TEST_CASES[lane]) + (2 if lane == "m0-boundaries" else 0)) for lane in M0_LANES),
        ("lean", LEAN_TEST_PATHS, 122),
        ("lean-core", LEAN_TEST_PATHS, 121),
        ("lean-replay", ("tests/integration/test_solution_build_compile.py",), 1),
        ("gateplan", GATEPLAN_TEST_PATHS, 28),
        ("solution-library", SOLUTION_LIBRARY_TEST_PATHS, 3),
        *((lane, SOLUTION_LIBRARY_TEST_PATHS, 1) for lane in SOLUTION_LIBRARY_LANES),
    ],
)
def test_new_lane_population_and_ownership_are_exact(lane, paths, count):
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only", f"--cairn-ci-lane={lane}"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    selected = [line for line in result.stdout.splitlines() if line.startswith("tests/") and "::" in line]
    assert len(selected) == count
    expected_paths = set(paths)
    if lane in ("lean", "lean-core"):
        expected_paths.add("tests/integration/test_solution_build_compile.py")
    assert {node.split("::", 1)[0] for node in selected} == expected_paths


def test_lean_container_authority_nodes_have_one_linux_owner():
    nodes = CONTAINER_AUTHORITY_NODES
    owners = {node: [] for node in nodes}
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    for lane in CI_LANES:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--collect-only",
                f"--cairn-ci-lane={lane}",
                *nodes,
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
        )
        nodeids = result.stdout.splitlines()
        for node in nodes:
            if lane == "container":
                assert result.returncode == 0, result.stdout + result.stderr
                assert nodeids.count(node) == 1
                owners[node].append(lane)
            else:
                assert result.returncode == pytest.ExitCode.NO_TESTS_COLLECTED, result.stdout + result.stderr
                assert "deselected" in result.stdout
                assert node not in nodeids
    assert len(nodes) == 2
    assert all(lanes == ["container"] for lanes in owners.values())


def test_missing_docker_refuses_both_required_authority_nodes():
    env: dict[str, str] = {**os.environ, "CAIRN_CONTAINER_CONTEXT": f"cairn-unavailable-{uuid.uuid4().hex}"}
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            "--cairn-ci-lane=container",
            *CONTAINER_AUTHORITY_NODES,
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == pytest.ExitCode.TESTS_FAILED, result.stdout + result.stderr
    assert "2 failed" in result.stdout
    assert "DaemonUnavailable" in result.stdout
    assert "skipped" not in result.stdout
    for node in CONTAINER_AUTHORITY_NODES:
        assert f"FAILED {node}" in result.stdout
