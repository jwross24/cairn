import os

import pytest

from cairn import runner
from cairn.runner import ParsedOutput

EXITS = (0, 3, -9)
SKILL_STATUSES = ("OK", "FAIL", "DISAGREE", None)
UNDER, OVER = 0.5, 1.5
CEILING = 1.0

UNDER_CEILING = {
    (0, True, "OK"): "OK",
    (0, True, "FAIL"): "FAIL",
    (0, True, "DISAGREE"): "DISAGREE",
    (0, True, None): "FAIL",
    (0, False, "OK"): "FAIL",
    (0, False, "FAIL"): "FAIL",
    (0, False, "DISAGREE"): "FAIL",
    (0, False, None): "FAIL",
    (3, True, "OK"): "FAIL",
    (3, True, "FAIL"): "FAIL",
    (3, True, "DISAGREE"): "FAIL",
    (3, True, None): "FAIL",
    (3, False, "OK"): "FAIL",
    (3, False, "FAIL"): "FAIL",
    (3, False, "DISAGREE"): "FAIL",
    (3, False, None): "FAIL",
    (-9, True, "OK"): "FAIL",
    (-9, True, "FAIL"): "FAIL",
    (-9, True, "DISAGREE"): "FAIL",
    (-9, True, None): "FAIL",
    (-9, False, "OK"): "FAIL",
    (-9, False, "FAIL"): "FAIL",
    (-9, False, "DISAGREE"): "FAIL",
    (-9, False, None): "FAIL",
}


def _cell(exit_status, well_formed, skill_status, wall):
    where = "over" if wall > CEILING else "under"
    shape = "wellformed" if well_formed else "malformed"
    return f"exit{exit_status}-{shape}-{skill_status}-{where}"


def _parsed(well_formed, skill_status):
    if not well_formed:
        return ParsedOutput.malformed("planted")
    return ParsedOutput(True, skill_status, None, {"status": skill_status})


UNDER_CASES = [
    pytest.param(e, w, s, expected, id=_cell(e, w, s, UNDER))
    for (e, w, s), expected in UNDER_CEILING.items()
]
OVER_CASES = [
    pytest.param(e, w, s, id=_cell(e, w, s, OVER))
    for e in EXITS
    for w in (True, False)
    for s in SKILL_STATUSES
]


@pytest.mark.parametrize("exit_status,well_formed,skill_status,expected", UNDER_CASES)
def test_the_status_table_under_the_ceiling(
    exit_status, well_formed, skill_status, expected
):
    assert (
        runner.status_for(
            _parsed(well_formed, skill_status), exit_status, UNDER, CEILING
        )
        == expected
    )


@pytest.mark.parametrize("exit_status,well_formed,skill_status", OVER_CASES)
def test_every_cell_over_the_ceiling_is_budget_exceeded(
    exit_status, well_formed, skill_status
):
    assert (
        runner.status_for(
            _parsed(well_formed, skill_status), exit_status, OVER, CEILING
        )
        == "BUDGET_EXCEEDED"
    )


def test_the_table_covers_every_cell_exactly_once():
    assert len(UNDER_CASES) == len(OVER_CASES) == 24
    assert set(UNDER_CEILING) == {
        (e, w, s) for e in EXITS for w in (True, False) for s in SKILL_STATUSES
    }


def test_every_terminal_status_the_runner_can_emit_is_reachable():
    from cairn import substrate

    emitted = set(UNDER_CEILING.values()) | {"BUDGET_EXCEEDED"}
    assert emitted == {"OK", "FAIL", "DISAGREE", "BUDGET_EXCEEDED"}
    assert emitted <= set(substrate.TERMINAL_STATUSES)
    assert runner.STATUS_INTERRUPTED in substrate.TERMINAL_STATUSES


def test_a_wall_exactly_at_the_ceiling_is_not_over_budget():
    parsed = _parsed(True, "OK")
    assert runner.status_for(parsed, 0, CEILING, CEILING) == "OK"
    assert runner.status_for(parsed, 0, CEILING + 1e-9, CEILING) == "BUDGET_EXCEEDED"


def test_an_absent_ceiling_never_produces_budget_exceeded():
    parsed = _parsed(True, "OK")
    assert runner.status_for(parsed, 0, 1e9, None) == "OK"


@pytest.mark.parametrize(
    "declared,multiplier,expected",
    [(0.2, 4, 0.8), (0.1372, 4, 0.5488), (1.0, 1, 1.0), (0.0, 4, 0.0)],
    ids=["the-bead's-0.2s", "toy-curve-30-bit", "unit-multiplier", "zero-expectation"],
)
def test_ceiling_arithmetic(declared, multiplier, expected):
    assert runner.ceiling_for(declared, multiplier) == pytest.approx(expected)


LEAKY_ENV = {
    "CAIRN_DB": "/a/substrate.sqlite",
    "CAIRN_DB_PATH": "/b/substrate.sqlite",
    "CAIRN_DBASE": "/c",
    "PWD": "/repo/holding/the/substrate",
    "PYTHONPATH": "/repo/holding/the/substrate",
    "VIRTUAL_ENV": "/repo/.venv",
    "CAIRN_HOME": "/repo",
    "AWS_SECRET_ACCESS_KEY": "hunter2",
    "PATH": "/usr/bin",
    "HOME": "/home/x",
    "LANG": "en_US.UTF-8",
}


def test_the_child_environment_is_an_allowlist_not_a_cairn_db_denylist():
    env = runner.child_env(base=LEAKY_ENV)
    assert set(env) == {"PATH", "HOME", "LANG"}
    assert not any(k.startswith("CAIRN_DB") for k in env)


@pytest.mark.parametrize(
    "leaked",
    ["PWD", "PYTHONPATH", "VIRTUAL_ENV", "CAIRN_HOME", "AWS_SECRET_ACCESS_KEY"],
)
def test_no_path_bearing_variable_a_denylist_would_miss_reaches_the_child(leaked):
    assert leaked not in runner.child_env(base=LEAKY_ENV)


@pytest.mark.parametrize("key", ["CAIRN_DB", "CAIRN_DB_PATH", "CAIRN_DBASE"])
def test_a_substrate_path_cannot_be_smuggled_through_the_extra_mapping(key):
    with pytest.raises(ValueError, match=key):
        runner.child_env({key: "/a/substrate.sqlite"}, base={"PATH": "/usr/bin"})


def test_the_caller_may_name_what_crosses_the_boundary():
    env = runner.child_env({"PYTHONPATH": "/tests/fixtures"}, base=LEAKY_ENV)
    assert env["PYTHONPATH"] == "/tests/fixtures"
    assert set(env) == {"PATH", "HOME", "LANG", "PYTHONPATH"}


def test_the_child_environment_defaults_to_the_live_environment(monkeypatch):
    monkeypatch.setenv("CAIRN_DB", "/should/not/travel")
    monkeypatch.setenv("PATH", "/usr/bin")
    env = runner.child_env()
    assert "CAIRN_DB" not in env and env["PATH"] == "/usr/bin"
    assert os.environ["CAIRN_DB"] == "/should/not/travel"


def test_every_harness_terminated_status_is_terminal_and_never_ok():
    from cairn import substrate

    assert set(runner.HARNESS_TERMINATED) <= set(substrate.TERMINAL_STATUSES)
    assert runner.STATUS_OK not in runner.HARNESS_TERMINATED
    assert runner.STATUS_SKILL_YANKED in substrate.STATUSES


@pytest.mark.parametrize(
    "platform,raw,expected",
    [("darwin", 16449536, 16449536), ("linux", 16064, 16449536)],
    ids=["macos-reports-bytes", "linux-reports-kilobytes"],
)
def test_peak_rss_normalizes_to_bytes_on_both_platforms(platform, raw, expected):
    assert runner.maxrss_bytes(raw, platform) == expected


def test_the_two_platforms_agree_on_one_measurement():
    assert runner.maxrss_bytes(16449536, "darwin") == runner.maxrss_bytes(
        16064, "linux"
    )
