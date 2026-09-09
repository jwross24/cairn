from pathlib import Path

import pytest

from cairn import keys, runner, substrate
from cairn.profile import Evaluation
from cairn.skills import toy_curve

FIXTURES = str(Path(__file__).resolve().parent.parent / "fixtures")
BUNDLE_HASH = "cd" * 32
IDENTITY = toy_curve.identity_bundle()
TOOL_DIGESTS = IDENTITY["tool_digests"]

SLEEPS_TWO_SECONDS = "skills.sleep2"
BURNS_CPU = "skills.cpu_burner"

CHEAP_CPU_SLOW_WALL = Evaluation(0.25, 0.25, 0.0)
DECLARES_ALMOST_NO_CPU = Evaluation(0.005, 0.005, 0.0)


@pytest.fixture
def writer(tmp_path):
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        yield sub


def _recipe(seed):
    return {
        "skill_identity_hash": keys.identity_bundle_hash(IDENTITY),
        "inputs": {},
        "seed": seed,
        "tool_versions": {"cypari2": TOOL_DIGESTS["cypari2"]},
        "container_digest": IDENTITY["container_digest"],
        "salt": "",
    }


def _launch(sub, tmp_path, module, seed, evaluation, **overrides):
    kwargs = {
        "bundle_hash": BUNDLE_HASH,
        "evaluation": evaluation,
        "ceiling_multiplier": 4,
        "tool_digests": TOOL_DIGESTS,
        "scratch_root": tmp_path / "runs",
        "env_extra": {"PYTHONPATH": FIXTURES},
    }
    kwargs.update(overrides)
    return runner.launch(sub, module, _recipe(seed), stdin_document={"n": 1}, **kwargs)


def test_cheap_cpu_behind_a_slow_wall_is_not_a_budget_refusal(writer, tmp_path):
    attempt = _launch(writer, tmp_path, SLEEPS_TWO_SECONDS, 101, CHEAP_CPU_SLOW_WALL)
    ceiling_s = runner.ceiling_for(CHEAP_CPU_SLOW_WALL.expected_wall_s, 4)
    cpu_s = attempt.launch.cpu_user_s + attempt.launch.cpu_sys_s
    assert cpu_s < ceiling_s
    assert attempt.launch.wall_s > ceiling_s
    assert not attempt.launch.timed_out
    assert attempt.status == "OK"


def test_cpu_past_the_ceiling_is_still_refused(writer, tmp_path):
    attempt = _launch(writer, tmp_path, BURNS_CPU, 102, DECLARES_ALMOST_NO_CPU, subprocess_startup_ms=0)
    ceiling_s = runner.ceiling_for(DECLARES_ALMOST_NO_CPU.expected_wall_s, 4, subprocess_startup_ms=0)
    cpu_s = attempt.launch.cpu_user_s + attempt.launch.cpu_sys_s
    assert cpu_s > ceiling_s
    assert attempt.status == "BUDGET_EXCEEDED"


def test_a_child_that_burns_no_cpu_and_outlives_the_wall_cap_reads_as_blocked(writer, tmp_path):
    attempt = _launch(
        writer,
        tmp_path,
        SLEEPS_TWO_SECONDS,
        103,
        CHEAP_CPU_SLOW_WALL,
        wall_cap_multiplier=1.0,
        wall_cap_floor_s=0.0,
    )
    ceiling_s = runner.ceiling_for(CHEAP_CPU_SLOW_WALL.expected_wall_s, 4)
    cpu_s = attempt.launch.cpu_user_s + attempt.launch.cpu_sys_s
    assert attempt.launch.timed_out
    assert attempt.launch.exit_status < 0
    assert cpu_s < ceiling_s
    assert attempt.status == "BLOCKED"
    assert attempt.status != "BUDGET_EXCEEDED"


def test_the_two_refusals_never_share_a_status():
    parsed = runner.ParsedOutput.of({"status": "OK"}, "OK")
    too_expensive = runner.status_for(parsed, 0, 9.0, 1.0, wall_capped=False)
    stuck = runner.status_for(parsed, -15, 0.001, 1.0, wall_capped=True)
    assert too_expensive == "BUDGET_EXCEEDED"
    assert stuck == "BLOCKED"
    assert too_expensive != stuck
    assert {too_expensive, stuck} <= set(substrate.TERMINAL_STATUSES)
