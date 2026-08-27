import os
import re
import subprocess
import sys
from pathlib import Path

import _session_deadline
import pytest
from _session_deadline import (
    BACKSTOP_EXIT_CODE,
    BACKSTOP_GRACE,
    DEFAULT_SECONDS,
    JOIN_TIMEOUT_S,
    SECONDS_VAR,
    SKIP_VAR,
    TIMEOUT_EXIT_CODE,
)

ROOT = Path(__file__).resolve().parent.parent.parent
TESTS = ROOT / "tests"

CHILD_TIMEOUT_S = 60

HANGS = """
import time


def test_child_blocks_past_the_session_deadline():
    time.sleep(3600)
"""

FAILS_THEN_HANGS = """
import time


def test_child_fails_before_anything_hangs():
    assert False, "the first reported failure of the child session"


def test_child_blocks_past_the_session_deadline():
    time.sleep(3600)
"""

RETURNS = """
def test_child_returns_well_inside_the_session_deadline():
    assert True
"""

SLEEPS_TWO_SECONDS = """
import time


def test_child_sleeps_past_a_one_second_deadline():
    time.sleep(2)
"""

HOLDS_THE_GIL = """
import re


def test_child_holds_the_gil_past_the_session_deadline():
    re.match(r"(a+)+$", "a" * 40 + "b")
"""

SCRIPT_ARMS_AND_HOLDS_THE_GIL = """
import re

import _session_deadline as deadline

deadline.BACKSTOP_GRACE = 2
deadline.pytest_configure(None)
re.match(r"(a+)+$", "a" * 40 + "b")
"""

SCRIPT_ARMS_THEN_DISARMS = """
import time

import _session_deadline as deadline

deadline.BACKSTOP_GRACE = 2
deadline.pytest_configure(None)
deadline.pytest_unconfigure(None)
time.sleep(5)
"""

MARKS_THAT_IT_RAN = """
from pathlib import Path


def test_child_records_that_it_ran():
    Path(__file__).with_name("ran.marker").write_text("ran")
"""


def run_child(tmp_path, body, *, extra_args=(), **env_overrides):
    child = tmp_path / "test_child.py"
    child.write_text(body)
    env = {k: v for k, v in os.environ.items() if k not in (SECONDS_VAR, SKIP_VAR)}
    env["PYTHONPATH"] = str(TESTS)
    env.update(env_overrides)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "_session_deadline",
            *extra_args,
            str(child),
        ],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    try:
        out, err = proc.communicate(timeout=CHILD_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        raise AssertionError(
            f"the child outlived {CHILD_TIMEOUT_S}s under {SECONDS_VAR}="
            f"{env_overrides.get(SECONDS_VAR)!r}: the session deadline never fired\n{out}\n{err}"
        ) from None
    return proc.returncode, out, err


def run_script(source, **env_overrides):
    env = {k: v for k, v in os.environ.items() if k not in (SECONDS_VAR, SKIP_VAR)}
    env["PYTHONPATH"] = str(TESTS)
    env.update(env_overrides)
    proc = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        env=env,
        text=True,
        timeout=CHILD_TIMEOUT_S,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_a_hanging_session_dies_at_the_deadline_with_a_thread_profile(tmp_path):
    returncode, out, err = run_child(tmp_path, HANGS, CAIRN_SESSION_DEADLINE="4")
    assert returncode == TIMEOUT_EXIT_CODE, (returncode, out, err)
    assert "Timeout (0:00:04)!" in err, err
    assert "Thread 0x" in err, err
    assert "test_child.py" in err, err
    assert "test_child_blocks_past_the_session_deadline" in err, err


def test_a2_a_reported_failure_does_not_disarm_the_deadline(tmp_path):
    returncode, out, err = run_child(tmp_path, FAILS_THEN_HANGS, CAIRN_SESSION_DEADLINE="4")
    assert returncode == TIMEOUT_EXIT_CODE, (returncode, out, err)
    assert "Timeout (0:00:04)!" in err, err
    assert "Thread 0x" in err, err
    assert "test_child_blocks_past_the_session_deadline" in err, err


def test_a3_a_gil_holding_call_that_starves_the_watchdog_is_killed_by_the_backstop(tmp_path):
    returncode, out, err = run_child(tmp_path, HOLDS_THE_GIL, CAIRN_SESSION_DEADLINE="4")
    assert returncode == BACKSTOP_EXIT_CODE, (returncode, out, err)
    assert "Timeout (" in err, err
    assert os.path.join("re", "__init__.py") in err, err
    assert "in match" in err, err


def test_a4_the_backstop_is_armed_by_configure():
    returncode, out, err = run_script(SCRIPT_ARMS_AND_HOLDS_THE_GIL, CAIRN_SESSION_DEADLINE="1")
    assert returncode == BACKSTOP_EXIT_CODE, (returncode, out, err)
    assert "Timeout (0:00:03)!" in err, err
    assert "in match" in err, err


def test_a5_the_backstop_is_cancelled_by_unconfigure():
    returncode, out, err = run_script(SCRIPT_ARMS_THEN_DISARMS, CAIRN_SESSION_DEADLINE="1")
    assert returncode == 0, (returncode, out, err)
    assert "Timeout" not in err, err


def test_b_a_session_that_finishes_leaves_no_dump_under_the_same_deadline(tmp_path):
    returncode, out, err = run_child(tmp_path, RETURNS, CAIRN_SESSION_DEADLINE="4")
    assert returncode == 0, (returncode, out, err)
    assert "1 passed" in out, out
    assert "Timeout" not in err, err
    assert "Thread 0x" not in err, err


@pytest.mark.parametrize(
    ("bad", "complaint"),
    [
        ("banana", "is not a number of seconds"),
        ("0", "is not a positive, finite number of seconds"),
        ("-5", "is not a positive, finite number of seconds"),
        ("nan", "is not a positive, finite number of seconds"),
        ("inf", "is not a positive, finite number of seconds"),
    ],
)
def test_c_a_malformed_deadline_denies_before_any_test_runs(tmp_path, bad, complaint):
    returncode, out, err = run_child(tmp_path, MARKS_THAT_IT_RAN, CAIRN_SESSION_DEADLINE=bad)
    assert returncode != 0, (returncode, out, err)
    assert SECONDS_VAR in out + err, (out, err)
    assert repr(bad) in out + err, (out, err)
    assert complaint in out + err, (out, err)
    assert not (tmp_path / "ran.marker").exists(), "the denied session still ran a test"
    assert "passed" not in out, out


def test_c2_the_same_child_under_a_valid_deadline_does_run_and_leave_its_marker(tmp_path):
    returncode, out, err = run_child(tmp_path, MARKS_THAT_IT_RAN, CAIRN_SESSION_DEADLINE="60")
    assert returncode == 0, (returncode, out, err)
    assert "1 passed" in out, out
    assert (tmp_path / "ran.marker").read_text() == "ran"


def test_d_the_named_bypass_disarms_the_deadline_and_says_so(tmp_path):
    reason = "measuring an unbounded run on purpose"
    returncode, out, err = run_child(
        tmp_path, SLEEPS_TWO_SECONDS, CAIRN_SESSION_DEADLINE="1", CAIRN_SESSION_DEADLINE_SKIP=reason
    )
    assert returncode == 0, (returncode, out, err)
    assert "1 passed" in out, out
    assert reason in err, err
    assert SKIP_VAR in err, err
    assert "Timeout" not in err, err


def test_e_the_durations_flag_prints_the_table_check_sh_asks_for(tmp_path):
    returncode, out, err = run_child(tmp_path, RETURNS, extra_args=("--durations=25",), CAIRN_SESSION_DEADLINE="60")
    assert returncode == 0, (returncode, out, err)
    assert "slowest 25 durations" in out, out


def test_f_the_running_session_is_armed_through_the_repository_conftest():
    bypass = os.environ.get(SKIP_VAR, "").strip()
    deadline = _session_deadline.active_deadline()
    assert bypass or deadline is not None, (
        "this session carries no deadline: tests/conftest.py does not wire _session_deadline in"
    )
    if deadline is not None:
        assert deadline.thread.is_alive()
        assert deadline.seconds > 0


def _ci_deadlines():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    ceiling = re.search(r"^\s*timeout-minutes:\s*(\d+)\s*$", ci, re.MULTILINE)
    session = re.search(r'^\s*CAIRN_SESSION_DEADLINE:\s*"(\d+)"\s*$', ci, re.MULTILINE)
    assert ceiling is not None, ci
    assert session is not None, ci
    return int(session.group(1)), int(ceiling.group(1)) * 60


def test_the_ci_session_deadline_fires_before_the_job_ceiling_cancels_the_run():
    session_s, ceiling_s = _ci_deadlines()
    # A job canceled by the ceiling uploads no transcript, so both watchdogs have to
    # land inside it for a wedge to leave a profile at all.
    assert session_s + BACKSTOP_GRACE < ceiling_s, (session_s, BACKSTOP_GRACE, ceiling_s)


def test_the_ci_session_deadline_clears_the_slowest_run_the_suite_has_taken():
    session_s, _ = _ci_deadlines()
    slowest_observed_s = 8.7 * 60
    assert session_s > slowest_observed_s, session_s


def test_the_local_default_clears_the_local_suite_and_needs_no_job_ceiling():
    assert DEFAULT_SECONDS > 4 * 230
    assert BACKSTOP_GRACE > JOIN_TIMEOUT_S
