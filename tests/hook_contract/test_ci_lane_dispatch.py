import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from _ci_lanes import CI_LANES, SOLUTION_PLAN_LANES

ROOT = Path(__file__).resolve().parents[2]


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


@pytest.mark.parametrize("lane", [*CI_LANES, "solution-plan", "container-replay", "all"])
def test_lane_dispatch_preserves_pytest_arguments(dispatch, lane):
    args = [] if lane == "all" else ["--ci-lane", lane]
    result, calls = dispatch(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    assert [call for call in calls if "pytest" in call] == [
        ["run", "pytest", "-q", "--durations=25", f"--cairn-ci-lane={lane}"]
    ]


@pytest.mark.parametrize("lane", [*CI_LANES, "solution-plan", "container-replay"])
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
        ["--ci-lane", "python", "--fast"],
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
            for lane in SOLUTION_PLAN_LANES
            for flags in (["--fast"], ["--unit"], ["--paths", "src/cairn/lean.py"])
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
        ("lean", "test_lean_toolchain.py"),
        ("solution", "test_solution_build_compile.py"),
        ("solution-plan", "test_solution_build_compile.py"),
        *((lane, "test_solution_build_compile.py") for lane in SOLUTION_PLAN_LANES),
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
    assert f"tests/integration/{test_file}::" in result.stdout
    if lane.startswith("solution-plan-"):
        selected = [line for line in result.stdout.splitlines() if line.startswith("tests/") and "::" in line]
        cases = ("exact",) if lane == "solution-plan-exact" else ("sorry", "timeout")
        assert selected == [
            "tests/integration/test_solution_build_compile.py::"
            f"test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks[{case}]"
            for case in cases
        ]
