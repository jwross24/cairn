import errno
import os
import resource
import subprocess
import sys

import pytest

from cairn import log

CHILD = [sys.executable, "-c", "import sys; sys.exit(3)"]


def test_communicate_reaps_so_wait4_raises_and_returncode_is_3():
    lg = log.get("grounding.subprocess")
    proc = subprocess.Popen(CHILD, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    with pytest.raises(ChildProcessError, match="No child processes") as excinfo:
        os.wait4(proc.pid, 0)
    lg.info(
        "reap_after_communicate",
        command=f"Popen({CHILD!r}, stdout=PIPE, stderr=PIPE); communicate(); os.wait4(pid, 0)",
        returncode=proc.returncode,
        stdout=out,
        stderr=err,
        wait4=f"{type(excinfo.value).__name__}: {excinfo.value}",
        python=sys.version.split()[0],
        subprocess_py=subprocess.__file__,
    )
    assert proc.returncode == 3
    assert (out, err) == (b"", b"")
    assert excinfo.value.errno == errno.ECHILD


def test_wait4_before_any_wait_returns_status_and_rusage_then_proc_wait_reports_0(tmp_path):
    lg = log.get("grounding.subprocess")
    with open(tmp_path / "out", "wb") as out, open(tmp_path / "err", "wb") as err:
        proc = subprocess.Popen(CHILD, stdout=out, stderr=err)
    returncode_before = proc.returncode
    pid, status, rusage = os.wait4(proc.pid, 0)
    exit_code = os.waitstatus_to_exitcode(status)
    later = proc.wait()
    lg.info(
        "wait4_then_proc_wait",
        command=f"Popen({CHILD!r}, stdout=file, stderr=file); os.wait4(pid, 0); proc.wait()",
        returncode_before=returncode_before,
        wait4_pid_matches=pid == proc.pid,
        status=status,
        exit_code=exit_code,
        rusage_type=type(rusage).__name__,
        proc_wait=later,
        returncode_after=proc.returncode,
        python=sys.version.split()[0],
        subprocess_py=subprocess.__file__,
    )
    assert returncode_before is None
    assert pid == proc.pid
    assert exit_code == 3
    assert isinstance(rusage, resource.struct_rusage)
    assert later == 0
    assert proc.returncode == 0
