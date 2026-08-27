import os
import sys

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
TABLE = {
    **{(e, w, s, "under"): expected for (e, w, s), expected in UNDER_CEILING.items()},
    **{(e, w, s, "over"): "BUDGET_EXCEEDED" for e in EXITS for w in (True, False) for s in SKILL_STATUSES},
}


def _cell(exit_status, well_formed, skill_status, where):
    shape = "wellformed" if well_formed else "malformed"
    return f"exit{exit_status}-{shape}-{skill_status}-{where}"


def _parsed(well_formed, skill_status):
    if not well_formed:
        return ParsedOutput.malformed("planted")
    return ParsedOutput(True, skill_status, None, {"status": skill_status})


CASES = [
    pytest.param(e, w, s, where, expected, id=_cell(e, w, s, where)) for (e, w, s, where), expected in TABLE.items()
]


@pytest.mark.parametrize(("exit_status", "well_formed", "skill_status", "where", "expected"), CASES)
def test_the_status_table(exit_status, well_formed, skill_status, where, expected):
    wall = UNDER if where == "under" else OVER
    assert runner.status_for(_parsed(well_formed, skill_status), exit_status, wall, CEILING) == expected


def test_the_table_covers_every_cell_exactly_once():
    assert len(TABLE) == 48
    assert set(TABLE) == {
        (e, w, s, where) for e in EXITS for w in (True, False) for s in SKILL_STATUSES for where in ("under", "over")
    }
    assert set(TABLE.values()) == {"OK", "FAIL", "DISAGREE", "BUDGET_EXCEEDED"}


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
    ("declared", "multiplier", "expected"),
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


def test_the_runner_never_emits_skill_yanked_though_the_schema_admits_it():
    from cairn import substrate

    assert runner.STATUS_SKILL_YANKED in substrate.STATUSES
    assert runner.STATUS_SKILL_YANKED not in set(UNDER_CEILING.values())
    assert runner.STATUS_SKILL_YANKED != "BUDGET_EXCEEDED"


@pytest.mark.parametrize(
    ("platform", "raw", "expected"),
    [("darwin", 16449536, 16449536), ("linux", 16064, 16449536)],
    ids=["macos-reports-bytes", "linux-reports-kilobytes"],
)
def test_peak_rss_normalizes_to_bytes_on_both_platforms(platform, raw, expected):
    assert runner.maxrss_bytes(raw, platform) == expected


@pytest.mark.parametrize("platform", ["win32", "cygwin", "aix", "emscripten", ""])
def test_an_unrecognized_platform_refuses_to_guess_the_maxrss_unit(platform):
    with pytest.raises(NotImplementedError, match="ru_maxrss units are unknown"):
        runner.maxrss_bytes(1024, platform)


@pytest.mark.parametrize("platform", ["linux", "freebsd14", "openbsd7", "netbsd9", "sunos5"])
def test_every_kilobyte_platform_is_scaled(platform):
    assert runner.maxrss_bytes(1024, platform) == 1024 * 1024


def test_skill_argv_is_the_interpreter_the_module_and_the_scratch_path(tmp_path):
    argv = runner.skill_argv("cairn.skills.toy_curve", tmp_path / "scratch")
    assert argv == [
        sys.executable,
        "-m",
        "cairn.skills.toy_curve",
        str(tmp_path / "scratch"),
    ]


def test_allocated_bytes_counts_blocks_not_apparent_size(tmp_path):
    root = tmp_path / "scratch"
    root.mkdir()
    assert runner.allocated_bytes(root) == 0
    (root / "dense.bin").write_bytes(b"d" * (1024 * 1024))
    dense = runner.allocated_bytes(root)
    assert dense >= 1024 * 1024

    sparse = root / "sparse.bin"
    with sparse.open("wb") as handle:
        handle.seek(100 * 1024 * 1024)
        handle.write(b"x")
    assert sparse.stat().st_size > 100 * 1024 * 1024
    assert runner.allocated_bytes(root) - dense < 1024 * 1024


def test_allocated_bytes_walks_nested_directories(tmp_path):
    root = tmp_path / "scratch"
    (root / "a" / "b").mkdir(parents=True)
    before = runner.allocated_bytes(root)
    (root / "a" / "b" / "deep.bin").write_bytes(b"z" * (512 * 1024))
    assert runner.allocated_bytes(root) - before >= 512 * 1024


def test_allocated_bytes_does_not_follow_a_symlink_out_of_the_tree(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "big.bin").write_bytes(b"o" * (4 * 1024 * 1024))
    root = tmp_path / "scratch"
    root.mkdir()
    before = runner.allocated_bytes(root)
    (root / "escape").symlink_to(outside)
    assert runner.allocated_bytes(root) - before < 1024 * 1024


@pytest.mark.parametrize("raised", [ProcessLookupError, PermissionError])
def test_the_group_signal_falls_back_to_the_pid(monkeypatch, raised):
    import os
    import signal

    killed = []
    monkeypatch.setattr(os, "killpg", lambda *a: (_ for _ in ()).throw(raised()))
    monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))
    runner._signal_group(4242, 99, signal.SIGKILL)
    assert killed == [(99, signal.SIGKILL)]


@pytest.mark.parametrize("raised", [ProcessLookupError, PermissionError])
def test_a_pid_that_is_gone_from_both_paths_is_swallowed(monkeypatch, raised):
    import os
    import signal

    monkeypatch.setattr(os, "killpg", lambda *a: (_ for _ in ()).throw(raised()))
    monkeypatch.setattr(os, "kill", lambda *a: (_ for _ in ()).throw(ProcessLookupError()))
    runner._signal_group(4242, 99, signal.SIGKILL)


def test_allocated_bytes_measures_what_is_already_there(tmp_path):
    root = tmp_path / "scratch"
    root.mkdir()
    (root / "seeded.bin").write_bytes(b"s" * (1024 * 1024))
    before = runner.allocated_bytes(root)
    assert before >= 1024 * 1024
    (root / "added.bin").write_bytes(b"a" * (512 * 1024))
    assert runner.allocated_bytes(root) - before >= 512 * 1024
