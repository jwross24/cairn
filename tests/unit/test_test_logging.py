import json
import os
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from _test_logging import _release_append_flags

ROOT = Path(__file__).resolve().parents[2]


def _suite(pytester, monkeypatch, mode):
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "tests"))
    temporary = pytester.path / "temporary"
    temporary.mkdir()
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(temporary))
    pytester.makeini("[pytest]\ntmp_path_retention_policy = failed\naddopts = -p no:cacheprovider\n")
    pytester.makeconftest('pytest_plugins = ["_test_logging"]')
    pytester.makepyfile(
        f"""
import json
import logging
import os
import stat
from pathlib import Path
import pytest

MODE = {mode!r}

@pytest.fixture
def scenario(tmp_path, json_test_log):
    payload = tmp_path / "payload"
    payload.write_text("private scratch")
    payload.chmod(0o444)
    if hasattr(os, "chflags"):
        os.chflags(payload, stat.UF_APPEND)
        assert payload.stat().st_flags & stat.UF_APPEND
    Path("paths.json").write_text(json.dumps({{"scratch": str(tmp_path), "log": str(json_test_log)}}))
    logging.getLogger("cairn").warning("setup sentinel")
    if MODE == "setup":
        raise RuntimeError("planted setup failure")
    yield
    logging.getLogger("cairn").warning("teardown sentinel")
    if MODE == "teardown":
        raise RuntimeError("planted teardown failure")

@pytest.mark.parametrize("case", [0, 1])
def test_case(scenario, case):
    logging.getLogger("cairn").warning("call sentinel")
    if MODE == "interrupt":
        os._exit(7)
    assert MODE != "call"
"""
    )


def test_project_retains_only_failed_scratch():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert config["tool"]["pytest"]["ini_options"]["tmp_path_retention_policy"] == "failed"


def _run(pytester):
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=pytester.path, capture_output=True, text=True, timeout=30
    )


@pytest.mark.parametrize("mode", ["pass", "call", "setup", "teardown", "interrupt"])
def test_cleanup_preserves_logs_for_every_outcome(pytester, monkeypatch, mode):
    _suite(pytester, monkeypatch, mode)
    result = _run(pytester)
    expected = 7 if mode == "interrupt" else (0 if mode == "pass" else 1)
    assert result.returncode == expected, result.stdout + result.stderr
    paths = json.loads((pytester.path / "paths.json").read_text())
    scratch, log = Path(paths["scratch"]), Path(paths["log"])
    records = [json.loads(line) for line in log.read_text().splitlines()]
    logs = list(log.parent.parent.glob("*/test.log.jsonl"))
    assert len(logs) == (1 if mode == "interrupt" else 2)
    assert len({path.read_bytes() for path in logs}) == len(logs)
    assert any(record["event"] == "setup sentinel" for record in records)
    assert any(record.get("phase") == "start" for record in records)
    assert not log.is_relative_to(scratch.parent)
    if mode == "pass":
        assert not scratch.exists()
        assert not scratch.parent.exists()
    if mode in ("call", "interrupt"):
        assert (scratch / "payload").read_text() == "private scratch"
        if hasattr(os, "chflags"):
            assert (scratch / "payload").stat().st_flags & stat.UF_APPEND
    if mode != "interrupt":
        assert any(record.get("phase") == "end" for record in records)


def test_completed_sessions_do_not_overwrite_logs_or_touch_sibling_scratch(pytester, monkeypatch):
    _suite(pytester, monkeypatch, "pass")
    sibling = pytester.path / "active-sibling"
    sibling.mkdir()
    payload = sibling / "payload"
    payload.write_text("owned by another run")
    result = _run(pytester)
    assert result.returncode == 0, result.stdout + result.stderr
    first = json.loads((pytester.path / "paths.json").read_text())
    first_log = Path(first["log"])
    preserved = first_log.read_bytes()
    result = _run(pytester)
    assert result.returncode == 0, result.stdout + result.stderr
    second = json.loads((pytester.path / "paths.json").read_text())
    assert first["log"] != second["log"]
    assert first_log.read_bytes() == preserved
    assert Path(second["log"]).is_file()
    assert payload.read_text() == "owned by another run"


def test_append_flag_release_stays_inside_owned_tree(tmp_path):
    root = tmp_path / "owned"
    root.mkdir()
    payload = root / "attest.bin"
    payload.write_bytes(b"owned")
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    external = sibling / "attest.bin"
    external.write_bytes(b"external")
    (root / "linked-file").symlink_to(external)
    (root / "linked-directory").symlink_to(sibling, target_is_directory=True)
    if hasattr(os, "chflags"):
        os.chflags(payload, stat.UF_APPEND)
        os.chflags(external, stat.UF_APPEND)
        _release_append_flags(root)
        assert not payload.stat().st_flags & stat.UF_APPEND
        assert external.stat().st_flags & stat.UF_APPEND
    assert payload.read_bytes() == b"owned"
    assert external.read_bytes() == b"external"
