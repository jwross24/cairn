import os
import signal
import socket
import struct
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from cairn import keys, rss, runner, substrate
from cairn.profile import Evaluation

CHILD = """
import os, signal, sys
memory = bytearray(32 * 1024**2)
if sys.argv[1] == 'ignore':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
print(os.getpid(), flush=True)
signal.pause()
"""


def _launch(tmp_path, code, *args, **kwargs):
    return runner.spawn_and_wait(
        [sys.executable, "-c", code, *args],
        tmp_path / "out",
        tmp_path / "err",
        wall_cap_s=kwargs.pop("wall_cap_s", 10),
        env=runner.child_env(),
        **kwargs,
    )


@pytest.mark.parametrize("code", ["pass", "raise SystemExit(127)"])
def test_short_lived_worker_reports_actual_exit(tmp_path, code):
    launch = _launch(tmp_path, code)
    assert launch.exit_status == (127 if "127" in code else 0)
    assert launch.peak_rss_bytes > 0
    assert launch.argv[:2] == (sys.executable, "-c")


def test_missing_executable_refuses_an_exec_measurement(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "executable", str(tmp_path / "missing"))
    with pytest.raises(FileNotFoundError):
        runner.spawn_and_wait(
            [sys.executable],
            tmp_path / "out",
            tmp_path / "err",
            wall_cap_s=2,
            env=runner.child_env(),
        )


@pytest.mark.parametrize(("behavior", "status"), [("term", -signal.SIGTERM), ("ignore", -signal.SIGKILL)])
def test_timeout_preserves_worker_memory_and_reaps_worker(tmp_path, behavior, status):
    launch = _launch(tmp_path, CHILD, behavior, wall_cap_s=0.4, grace=0.05)
    assert launch.exit_status == status
    assert launch.timed_out
    assert launch.peak_rss_bytes >= 32 * 1024**2
    assert launch.measurement_scope == runner.SCOPE_TRUNCATED
    pid = int((tmp_path / "out").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_yank_preserves_worker_usage_and_reaps_worker(tmp_path):
    began = time.monotonic()
    launch = _launch(tmp_path, CHILD, "term", is_yanked=lambda: time.monotonic() - began > 0.4)
    assert launch.skill_yanked and not launch.timed_out
    assert launch.exit_status == -signal.SIGTERM
    assert launch.peak_rss_bytes >= 32 * 1024**2
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "out").read_text()), 0)


@pytest.mark.parametrize("error", [KeyboardInterrupt, ValueError])
def test_callback_exception_cleans_up_worker(tmp_path, error):
    def refuse():
        if (tmp_path / "out").stat().st_size:
            raise error("planted callback")
        return False

    with pytest.raises(error, match="planted callback"):
        _launch(tmp_path, CHILD, "ignore", is_yanked=refuse)
    pid = int((tmp_path / "out").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_file_backed_output_avoids_pipe_backpressure(tmp_path):
    launch = _launch(tmp_path, "import os; os.write(1,b'x'*4_000_000); os.write(2,b'y'*4_000_000)")
    assert launch.exit_status == 0
    assert (tmp_path / "out").stat().st_size == (tmp_path / "err").stat().st_size == 4_000_000


def test_linux_worker_inherits_no_new_privileges(tmp_path):
    if sys.platform != "linux":
        with pytest.raises(rss.ReporterError, match="requires Linux"):
            rss.build_binary()
        return
    check = (
        "from pathlib import Path; "
        "assert next(x for x in Path('/proc/self/status').read_text().splitlines() "
        "if x.startswith('NoNewPrivs:')).split(':')[1].strip() == '1'"
    )
    launch = _launch(
        tmp_path, f"{check}; import subprocess,sys; subprocess.run([sys.executable,'-c',{check!r}],check=True)"
    )
    assert launch.exit_status == 0, (tmp_path / "err").read_text()


def test_linux_reporter_memfd_refuses_mutation():
    if sys.platform != "linux":
        with pytest.raises(rss.ReporterError, match="requires Linux"):
            rss.build_binary()
        return
    binary = rss.build_binary()
    rss.validate_binary(binary)
    with pytest.raises(PermissionError):
        os.pwrite(binary.fd, b"forged", 0)
    with pytest.raises(PermissionError):
        os.ftruncate(binary.fd, 0)
    assert rss.build_binary() is binary


def test_missing_execution_dependency_closes_the_attempt_without_a_receipt(tmp_path, monkeypatch):
    identity = {
        "interface_version": "1",
        "implementation_revision": "ab" * 32,
        "tool_digests": {},
        "container_digest": "cd" * 32,
        "numeric_profile": "fixture",
    }
    recipe = {
        "skill_identity_hash": keys.identity_bundle_hash(identity),
        "inputs": {},
        "seed": 1,
        "tool_versions": {},
        "container_digest": identity["container_digest"],
        "salt": "",
    }
    if sys.platform == "linux":
        monkeypatch.setattr(rss, "COMPILER", tmp_path / "missing-compiler")
    else:
        monkeypatch.setattr(sys, "executable", str(tmp_path / "missing-interpreter"))
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        with pytest.raises(FileNotFoundError):
            runner.launch(
                sub,
                "fixture",
                recipe,
                bundle_hash="ab" * 32,
                evaluation=Evaluation(1, 1, 1),
                ceiling_multiplier=4,
                tool_digests={},
                scratch_root=tmp_path / "runs",
            )
        attempts = sub.conn.execute("SELECT status, ended_at, receipt_hash FROM attempts").fetchall()
        assert len(attempts) == 1
        assert attempts[0]["status"] == runner.STATUS_FAIL
        assert attempts[0]["ended_at"] is not None
        assert attempts[0]["receipt_hash"] is None


def test_linux_same_uid_sender_cannot_supply_the_reporters_final_packet():
    if sys.platform != "linux":
        with pytest.raises(rss.ReporterError, match="requires Linux"):
            rss.build_binary()
        return
    receiver, sender = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    with receiver, sender:
        receiver.setsockopt(socket.SOL_SOCKET, rss.SO_PASSCRED, 1)
        receiver.settimeout(2)
        report = rss.Reports(os.getpid())
        credentials = [
            (socket.SOL_SOCKET, rss.SCM_CREDENTIALS, struct.pack("3i", os.getpid(), os.getuid(), os.getgid()))
        ]
        for frame in (b"START 654", b"EXEC 0 0", b"EXIT 654"):
            report.accept(frame, credentials, 0)
        child = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import socket,sys; socket.socket(fileno=int(sys.argv[1])).send(b'FINAL 654 0 200000 2000 3000')",
                str(sender.fileno()),
            ],
            pass_fds=(sender.fileno(),),
        )
        try:
            data, ancillary, flags, _ = receiver.recvmsg(256, socket.CMSG_SPACE(12))
            sender_pid, sender_uid, _ = struct.unpack("3i", ancillary[0][2])
            assert sender_pid == child.pid and sender_uid == os.getuid()
            assert data == b"FINAL 654 0 200000 2000 3000"
            with pytest.raises(rss.ReporterError, match="sender"):
                report.accept(data, ancillary, flags)
            assert report.final is None
        finally:
            child.wait(timeout=2)


def test_linux_blocked_compiler_times_out_and_is_reaped(tmp_path, monkeypatch):
    if sys.platform != "linux":
        with pytest.raises(rss.ReporterError, match="requires Linux"):
            rss.build_binary()
        return
    fifo = tmp_path / "blocked-header"
    os.mkfifo(fifo)
    source = tmp_path / "reporter.c"
    source.write_text(f'#include "{fifo}"\nint main(void) {{ return 0; }}\n')
    monkeypatch.setattr(rss, "SOURCE", source)
    monkeypatch.setattr(rss, "_binary", None)
    monkeypatch.setattr(rss, "BUILD_TIMEOUT_S", 0.1)
    spawned = []
    base = subprocess.Popen

    class Recording(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            spawned.append(self.pid)

    monkeypatch.setattr(subprocess, "Popen", Recording)
    with pytest.raises(rss.ReporterError, match="compiler timed out"):
        _launch(tmp_path, "pass")
    assert len(spawned) == 1
    with pytest.raises(ProcessLookupError):
        os.kill(spawned[0], 0)


def test_linux_concurrent_first_build_uses_one_immutable_binary(monkeypatch):
    if sys.platform != "linux":
        with pytest.raises(rss.ReporterError, match="requires Linux"):
            rss.build_binary()
        return
    spawned = []
    base = subprocess.Popen

    class Recording(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            spawned.append(self.pid)

    with monkeypatch.context() as patch:
        patch.setattr(rss, "_binary", None)
        patch.setattr(subprocess, "Popen", Recording)
        with ThreadPoolExecutor(max_workers=4) as pool:
            binaries = list(pool.map(lambda _: rss.build_binary(), range(4)))
        assert len(spawned) == 1
        assert all(binary is binaries[0] for binary in binaries)
        rss.validate_binary(binaries[0])
    os.close(binaries[0].fd)


def test_linux_cached_binary_refuses_changed_source_inputs(tmp_path, monkeypatch):
    if sys.platform != "linux":
        with pytest.raises(rss.ReporterError, match="requires Linux"):
            rss.build_binary()
        return
    binary = rss.build_binary()
    source = tmp_path / "reporter.c"
    source.write_bytes(rss.SOURCE.read_bytes() + b"\n")
    monkeypatch.setattr(rss, "SOURCE", source)
    with pytest.raises(rss.ReporterError, match="inputs changed"):
        rss.build_binary()
    rss.validate_binary(binary)
