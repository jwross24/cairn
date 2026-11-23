import json
import logging
import os
import stat
import tempfile
import time
from pathlib import Path

import pytest

_CALL_PASSED = pytest.StashKey[bool]()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    if report.when == "call":
        item.stash[_CALL_PASSED] = report.passed
    return report


def _release_append_flags(root):
    pending = [root]
    while pending:
        path = pending.pop()
        metadata = os.lstat(path)
        if stat.S_ISLNK(metadata.st_mode):
            continue
        if metadata.st_flags & stat.UF_APPEND:
            os.chflags(path, metadata.st_flags & ~stat.UF_APPEND, follow_symlinks=False)
        if stat.S_ISDIR(metadata.st_mode):
            with os.scandir(path) as entries:
                pending.extend(entry.path for entry in entries)


def _expiring_scratch(user_root, keep):
    numbered = {}
    for entry in user_root.iterdir():
        suffix = entry.name.removeprefix("pytest-")
        if suffix != entry.name and suffix.isdigit():
            numbered[entry] = int(suffix)
        elif entry.name.startswith("garbage-"):
            yield entry
    newest = max(numbered.values(), default=-1)
    yield from (entry for entry, number in numbered.items() if number <= newest - keep)


def pytest_sessionstart(session):
    from _pytest.tmpdir import get_user

    config = session.config
    policy = config.getini("tmp_path_retention_policy")
    keep = 0 if policy == "none" else int(config.getini("tmp_path_retention_count"))
    if not hasattr(os, "chflags") or config.option.basetemp is not None:
        return
    temproot = Path(os.environ.get("PYTEST_DEBUG_TEMPROOT") or tempfile.gettempdir()).resolve()
    user_root = temproot / f"pytest-of-{get_user() or 'unknown'}"
    if not user_root.is_dir():
        return
    for scratch in _expiring_scratch(user_root, keep):
        try:
            _release_append_flags(scratch)
        except OSError:
            continue


@pytest.fixture
def tmp_path(tmp_path, request):
    yield tmp_path
    if hasattr(os, "chflags") and request.node.stash.get(_CALL_PASSED, False):
        _release_append_flags(tmp_path)


@pytest.fixture(scope="session")
def test_log_root(tmp_path_factory):
    base = tmp_path_factory.getbasetemp()
    root = base.parent / "cairn-test-logs"
    root.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{base.name}-", dir=root))


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
        with self.path.open("a") as fh:
            fh.write(json.dumps(data, sort_keys=True, default=str) + "\n")


@pytest.fixture(autouse=True)
def json_test_log(tmp_path, request, test_log_root):
    directory = Path(tempfile.mkdtemp(prefix=f"{tmp_path.name}-", dir=test_log_root))
    path = directory / "test.log.jsonl"
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
