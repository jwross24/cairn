import os
import socket
import struct

import pytest

from cairn import rss

REPORTER_PID = 321
WORKER_PID = 654
FRAMES = (b"START 654", b"EXEC 0 0", b"EXIT 654", b"FINAL 654 0 200000 2000 3000")


def _credentials(pid=REPORTER_PID):
    return [(socket.SOL_SOCKET, rss.SCM_CREDENTIALS, struct.pack("3i", pid, os.getuid(), os.getgid()))]


def _report(frames=FRAMES):
    report = rss.Reports(REPORTER_PID)
    for frame in frames:
        report.accept(frame, _credentials(), 0)
    return report


def test_complete_authenticated_measurement_requires_eof_and_successful_reporter():
    report = _report()
    with pytest.raises(rss.ReporterError, match="complete measurement"):
        report.result(0)
    report.eof = True
    assert report.result(0) == (0, 200000, 2000, 3000)
    with pytest.raises(rss.ReporterError, match="complete measurement"):
        report.result(1)


@pytest.mark.parametrize("frames", [(), FRAMES[:1], FRAMES[:2], FRAMES[:3]])
def test_missing_report_refuses_measurement(frames):
    report = _report(frames)
    report.eof = True
    with pytest.raises(rss.ReporterError, match="complete measurement"):
        report.result(0)


@pytest.mark.parametrize(
    "bad_frame",
    [b"FINAL malformed", b"FINAL 654 0 -1 0 0", b"FINAL 655 0 1000 0 0", b"FINAL 654 65536 1000 0 0", b"\xff"],
)
def test_invalid_final_refuses_measurement(bad_frame):
    report = _report(FRAMES[:3])
    with pytest.raises(rss.ReporterError):
        report.accept(bad_frame, _credentials(), 0)
    assert report.final is None


@pytest.mark.parametrize("frame", FRAMES)
def test_duplicate_packet_refuses_measurement(frame):
    report = _report()
    with pytest.raises(rss.ReporterError, match=r"duplicate|out-of-order"):
        report.accept(frame, _credentials(), 0)


@pytest.mark.parametrize("credentials", [[], _credentials(WORKER_PID), _credentials() * 2])
def test_wrong_or_missing_sender_refuses_well_formed_payload(credentials):
    report = _report(FRAMES[:3])
    with pytest.raises(rss.ReporterError, match="sender"):
        report.accept(FRAMES[3], credentials, 0)
    assert report.final is None


@pytest.mark.parametrize("flags", [socket.MSG_TRUNC, socket.MSG_CTRUNC])
def test_truncated_packet_refuses_measurement(flags):
    report = _report(FRAMES[:3])
    with pytest.raises(rss.ReporterError, match="truncated"):
        report.accept(FRAMES[3], _credentials(), flags)


def test_reporter_exec_failure_is_distinct_from_worker_exit_127():
    report = _report((FRAMES[0], b"EXEC 2 2", FRAMES[2], b"FINAL 654 32512 1000 0 0"))
    report.eof = True
    with pytest.raises(FileNotFoundError, match="exec failed"):
        report.result(0)
    exited = _report((*FRAMES[:3], b"FINAL 654 32512 1000 0 0"))
    exited.eof = True
    assert os.waitstatus_to_exitcode(exited.result(0)[0]) == 127


def test_reporter_build_rejects_an_unprotected_compiler(tmp_path, monkeypatch):
    compiler = tmp_path / "compiler"
    compiler.write_bytes(b"fake")
    compiler.chmod(0o777)
    monkeypatch.setattr(rss, "COMPILER", compiler)
    with pytest.raises(rss.ReporterError, match="protected root-owned"):
        rss._compiler_digest()


def test_reporter_build_requires_linux():
    import sys

    if sys.platform != "linux":
        with pytest.raises(rss.ReporterError, match="requires Linux"):
            rss.build_binary()
    else:
        assert rss.F_ADD_SEALS == 1033 and rss.F_GET_SEALS == 1034
