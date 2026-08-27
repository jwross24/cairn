import difflib
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
from _session_deadline import pytest_configure, pytest_unconfigure  # noqa: F401
from hypothesis import settings

pytest_plugins = ["pytester"]

ROOT = Path(os.environ.get("CAIRN_REPO_ROOT") or Path(__file__).resolve().parent.parent)
GUARDED_DIRS = (".doctor", "deploy", "var")
VECTORS = ROOT / "tests" / "vectors"
GOLDENS = ROOT / "tests" / "goldens"

settings.register_profile("ci", max_examples=500, deadline=None, print_blob=True)
settings.register_profile("dev", max_examples=50, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))


class IsolationViolation(AssertionError):
    pass


def _snapshot(root):
    seen = {}
    for name in GUARDED_DIRS:
        base = root / name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                st = path.stat()
                seen[str(path.relative_to(root))] = (st.st_size, st.st_mtime_ns)
    return seen


def _allowed_argv0():
    import cairn.pari

    return {sys.executable, os.path.realpath(sys.executable), cairn.pari.GP_BIN}


@pytest.fixture(autouse=True)
def isolation_guard(monkeypatch):
    before = _snapshot(ROOT)
    real_popen = subprocess.Popen

    class GuardedPopen(real_popen):
        def __init__(self, args, *a, **kw):
            argv0 = args[0] if isinstance(args, (list, tuple)) else str(args).split()[0]
            if str(argv0) not in _allowed_argv0():
                raise IsolationViolation(f"subprocess outside the allow-list: {argv0}")
            super().__init__(args, *a, **kw)

    monkeypatch.setattr(subprocess, "Popen", GuardedPopen)
    for key in list(os.environ):
        if key.startswith("CAIRN_DB"):
            monkeypatch.delenv(key)
    yield
    after = _snapshot(ROOT)
    if before != after:
        changed = sorted(set(before) ^ set(after) | {k for k in before if after.get(k) != before[k]})
        raise IsolationViolation(f"test touched guarded paths: {changed}")


class _JsonLineHandler(logging.Handler):
    def __init__(self, path):
        super().__init__(level=logging.DEBUG)
        self.path = path

    def emit(self, record):
        data = {
            "ts": record.created,
            "level": record.levelname,
            "step": getattr(record, "step", None),
            "event": record.getMessage(),
        }
        data.update(getattr(record, "fields", {}) or {})
        with open(self.path, "a") as fh:
            fh.write(json.dumps(data, sort_keys=True, default=str) + "\n")


@pytest.fixture(autouse=True)
def json_test_log(tmp_path, request):
    path = tmp_path / "test.log.jsonl"
    handler = _JsonLineHandler(path)
    logger = logging.getLogger("cairn")
    previous = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    start = time.monotonic()
    logger.debug("phase", extra={"step": "test", "fields": {"phase": "start", "test": request.node.nodeid}})
    yield path
    logger.debug(
        "phase",
        extra={
            "step": "test",
            "fields": {
                "phase": "end",
                "test": request.node.nodeid,
                "wall_ms": round((time.monotonic() - start) * 1000, 3),
            },
        },
    )
    logger.removeHandler(handler)
    logger.setLevel(previous)


@pytest.fixture
def popen_spy(monkeypatch):
    spawned = []
    base = subprocess.Popen

    class Spy(base):
        def __init__(self, args, *a, **kw):
            spawned.append(list(args) if isinstance(args, (list, tuple)) else [str(args)])
            super().__init__(args, *a, **kw)

    monkeypatch.setattr(subprocess, "Popen", Spy)
    return spawned


@pytest.fixture
def run_gp_spy(monkeypatch):
    import cairn.pari

    calls = []
    real = cairn.pari.run_gp

    def spy(args, stdin, **kw):
        record = {"args": list(args), "stdin": stdin, **kw}
        calls.append(record)
        rc, out, err = real(args, stdin, **kw)
        record.update(rc=rc, stdout=out, stderr=err)
        return rc, out, err

    monkeypatch.setattr(cairn.pari, "run_gp", spy)
    return calls


@pytest.fixture
def db_snapshot():
    def snap(conn_or_path, label):
        conn = (
            conn_or_path
            if isinstance(conn_or_path, sqlite3.Connection)
            else sqlite3.connect(f"file:{conn_or_path}?mode=ro", uri=True)
        )
        tables = [r[0] for r in conn.execute("select name from sqlite_master where type='table'")]
        counts = {t: conn.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tables}
        logging.getLogger("cairn").info(
            "db_snapshot", extra={"step": "test", "fields": {"label": label, "counts": counts}}
        )
        return counts

    return snap


def _golden_path(name):
    path = Path(name)
    if path.is_absolute():
        return path
    if str(name).endswith(".json"):
        return VECTORS / name
    return GOLDENS / f"{name}.golden"


SCRUB_RULES = (
    (re.compile(r"\b[0-9a-f]{64}\b"), "[HASH]"),
    (re.compile(r"\b[0-9a-f]{32}\b"), "[ID]"),
    (re.compile(r"(?<=wall_ms=)\d+"), "[MS]"),
    (re.compile(r"/[\w./-]*/(?:pytest-of-\w+|T)/[\w./-]+"), "[PATH]"),
)


def scrub(text, *, bundle_hash=None, pin_hash=None):
    if bundle_hash:
        text = text.replace(bundle_hash, "[BUNDLE]")
    if pin_hash:
        text = text.replace(pin_hash, "[PIN]")
    for pattern, replacement in SCRUB_RULES:
        text = pattern.sub(replacement, text)
    return text


@pytest.fixture(name="scrub")
def scrub_fixture():
    return scrub


@pytest.fixture
def assert_golden():
    def check(name, text):
        path = _golden_path(name)
        actual = path.with_name(path.name + ".actual")
        if os.environ.get("UPDATE_GOLDENS") == "1":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            actual.unlink(missing_ok=True)
            return
        expected = path.read_text() if path.exists() else ""
        if expected == text:
            # A leftover .actual from an earlier mismatch reads as pending work forever.
            actual.unlink(missing_ok=True)
        else:
            actual.write_text(text)
            diff = "".join(
                difflib.unified_diff(
                    expected.splitlines(True), text.splitlines(True), fromfile=str(path), tofile=str(actual)
                )
            )
            raise AssertionError(f"golden mismatch for {path.name}; rerun with UPDATE_GOLDENS=1 to accept\n{diff}")

    return check


@pytest.fixture
def load_vector():
    def load(name):
        return json.loads((VECTORS / name).read_text())

    return load


@pytest.fixture
def clear_flags():
    flagged = []
    yield flagged.append
    for path in flagged:
        if os.path.lexists(path):
            os.chflags(path, 0)
            os.chmod(path, 0o644)


@pytest.fixture
def pinned_bundle(tmp_path, clear_flags):
    from cairn import bundle as bundle_module

    def make(name="deploy", src=ROOT / "bundle"):
        directory = tmp_path / name
        directory.mkdir(parents=True, exist_ok=True)
        bundle_path, pin_path = directory / "gate-bundle.sqlite", directory / "gate-bundle.pin"
        bundle_module.build(src, bundle_path)
        bundle_module.write_pin(bundle_path, pin_path)
        clear_flags(pin_path)
        return bundle_path, pin_path

    return make
