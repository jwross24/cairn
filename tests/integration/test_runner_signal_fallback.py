import os
import signal
import subprocess
import sys
import time

import pytest

from cairn import runner

SLEEPER = "import time; time.sleep(60)"

SPAWNS_A_GRANDCHILD_AND_EXITS = """
import subprocess, sys
grandchild = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(60)"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
print(grandchild.pid, flush=True)
"""

REAP_WAIT_S = 5.0


def _gone(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


def _wait_gone(pid):
    deadline = time.monotonic() + REAP_WAIT_S
    while time.monotonic() < deadline:
        if _gone(pid):
            return True
        time.sleep(0.01)
    return False


def _dead_pgid():
    done = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    done.wait()
    with pytest.raises(ProcessLookupError):
        os.killpg(done.pid, 0)
    return done.pid


@pytest.fixture
def stray():
    proc = subprocess.Popen([sys.executable, "-c", SLEEPER], stdin=subprocess.DEVNULL)
    try:
        yield proc
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGKILL])
def test_a_child_outside_the_recorded_group_is_signalled_by_pid(stray, sig):
    runner._signal_group(_dead_pgid(), stray.pid, sig)
    assert stray.wait(timeout=REAP_WAIT_S) == -sig


def test_the_pid_fallback_signals_only_the_named_pid(stray):
    bystander = subprocess.Popen([sys.executable, "-c", SLEEPER], stdin=subprocess.DEVNULL)
    try:
        assert os.getpgid(bystander.pid) == os.getpgid(stray.pid)
        runner._signal_group(_dead_pgid(), stray.pid, signal.SIGKILL)
        assert stray.wait(timeout=REAP_WAIT_S) == -signal.SIGKILL
        assert bystander.poll() is None
    finally:
        bystander.kill()
        bystander.wait()


def test_a_pid_already_gone_with_its_group_is_not_an_error():
    done = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    done.wait()
    runner._signal_group(done.pid, done.pid, signal.SIGKILL)


def test_the_final_sweep_reaches_a_grandchild_whose_group_leader_exited(tmp_path):
    launch = runner.spawn_and_wait(
        [sys.executable, "-c", SPAWNS_A_GRANDCHILD_AND_EXITS],
        tmp_path / "out",
        tmp_path / "err",
        wall_cap_s=30,
        env=runner.child_env(),
    )
    grandchild = int((tmp_path / "out").read_text())
    assert launch.exit_status == 0
    assert not launch.timed_out
    assert _wait_gone(grandchild)


def test_the_final_sweep_leaves_a_grandchild_in_another_group_alone(tmp_path):
    code = SPAWNS_A_GRANDCHILD_AND_EXITS.replace(
        "stderr=subprocess.DEVNULL,", "stderr=subprocess.DEVNULL,\n    start_new_session=True,"
    )
    launch = runner.spawn_and_wait(
        [sys.executable, "-c", code],
        tmp_path / "out",
        tmp_path / "err",
        wall_cap_s=30,
        env=runner.child_env(),
    )
    grandchild = int((tmp_path / "out").read_text())
    try:
        assert launch.exit_status == 0
        assert not _gone(grandchild)
    finally:
        os.kill(grandchild, signal.SIGKILL)
