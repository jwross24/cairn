from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import fd_ceiling_gate as gate


def test_the_exact_twenty_percent_boundary_is_clear():
    snapshot = gate.parse_snapshot(b"320\n400\n", b"")

    assert snapshot == gate.Snapshot(used=320, maximum=400)
    assert gate.has_minimum_free_capacity(snapshot) is True


@pytest.mark.parametrize(
    ("used", "maximum"),
    [(321, 400), (400, 400), (401, 400), (162749, 184320)],
)
def test_less_than_twenty_percent_free_refuses(used, maximum):
    assert gate.has_minimum_free_capacity(gate.Snapshot(used=used, maximum=maximum)) is False


@pytest.mark.parametrize(
    ("stdout", "stderr", "reason"),
    [
        (b"80\n", b"", "exactly two ASCII decimal integers"),
        (b"80\n400\nextra\n", b"", "exactly two ASCII decimal integers"),
        (b"80\n-400\n", b"", "exactly two ASCII decimal integers"),
        (b"80\n400\xff\n", b"", "not ASCII"),
        (b"80\n400\n", b"warning", "wrote to stderr"),
        (b"80\n0\n", b"", "greater than zero"),
    ],
)
def test_malformed_provider_output_is_rejected(stdout, stderr, reason):
    with pytest.raises(ValueError, match=reason):
        gate.parse_snapshot(stdout, stderr)


def test_provider_nonzero_is_rejected(monkeypatch):
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=7, stdout=b"", stderr=b"failed"),
    )

    with pytest.raises(RuntimeError, match="sysctl exited 7"):
        gate.read_snapshot()


def test_timeout_logs_infrastructure_denial(tmp_path, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(gate.subprocess, "run", timeout)
    monkeypatch.delenv(gate.SKIP_ENV, raising=False)
    log = tmp_path / "check.log"

    assert gate.run(log) == gate.EXIT_ENVIRONMENT
    assert "FD-INFRA-DENY sysctl timed out" in log.read_text()


def test_valid_bypass_is_logged(tmp_path, monkeypatch):
    monkeypatch.setenv(gate.SKIP_ENV, "maintenance window")
    log = tmp_path / "check.log"

    assert gate.run(log) == gate.EXIT_OK
    assert "FD-BYPASS CAIRN_FD_CEILING_SKIP reason=maintenance window" in log.read_text()


@pytest.mark.parametrize("reason", ["", "   ", "line one\nline two"])
def test_invalid_bypass_is_a_logged_denial(tmp_path, monkeypatch, reason):
    monkeypatch.setenv(gate.SKIP_ENV, reason)
    log = tmp_path / "check.log"

    assert gate.run(log) == gate.EXIT_ENVIRONMENT
    assert "FD-INFRA-DENY invalid CAIRN_FD_CEILING_SKIP reason" in log.read_text()


def test_check_skip_does_not_bypass_fd_capacity(tmp_path, monkeypatch):
    monkeypatch.delenv(gate.SKIP_ENV, raising=False)
    monkeypatch.setenv("CAIRN_CHECK_SKIP", "unrelated gate bypass")
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=b"321\n400\n", stderr=b""),
    )
    log = tmp_path / "check.log"

    assert gate.run(log) == gate.EXIT_REFUSED
    assert "FD-CEILING used=321 maximum=400 min_free=20%" in log.read_text()


def test_unwritable_log_denies_loudly(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(gate.SKIP_ENV, "maintenance")
    log = tmp_path / "missing" / "check.log"

    assert gate.run(log) == gate.EXIT_ENVIRONMENT
    assert "cannot write" in capsys.readouterr().err
