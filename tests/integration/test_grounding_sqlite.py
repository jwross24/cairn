import sqlite3
import sys
import threading
import time

import pytest

from cairn import log

BEGIN_KINDS = ("DEFERRED", "IMMEDIATE", "EXCLUSIVE")
READER_TIMEOUT_S = 0.5

READER_ROWS = [
    ("WAL", "DEFERRED", "reads"),
    ("WAL", "IMMEDIATE", "reads"),
    ("WAL", "EXCLUSIVE", "reads"),
    ("DELETE", "DEFERRED", "reads"),
    ("DELETE", "IMMEDIATE", "reads"),
    ("DELETE", "EXCLUSIVE", "locked"),
]

BUSY_ROWS = [
    (500, None, "locked", 450, 4000),
    (0, None, "locked", 0, 100),
    (500, 200, "ok", 150, 4000),
]


def _connect(path, timeout_s):
    return sqlite3.connect(path, autocommit=True, timeout=timeout_s)


def _fresh_db(tmp_path, journal_mode):
    path = tmp_path / f"{journal_mode.lower()}.sqlite"
    conn = _connect(path, 5.0)
    conn.execute("create table t (x integer)")
    observed_mode = conn.execute(f"pragma journal_mode={journal_mode}").fetchone()[0]
    assert observed_mode == journal_mode.lower()
    return path, conn


@pytest.mark.parametrize(
    ("journal_mode", "begin_kind", "expected"),
    READER_ROWS,
    ids=[f"{mode}-{kind}-{outcome}" for mode, kind, outcome in READER_ROWS],
)
def test_reader_against_uncommitted_writer_by_journal_mode_and_begin_kind(tmp_path, journal_mode, begin_kind, expected):
    lg = log.get("grounding.sqlite")
    path, writer = _fresh_db(tmp_path, journal_mode)
    writer.execute(f"BEGIN {begin_kind}")
    writer.execute("insert into t values (1)")
    reader = _connect(path, READER_TIMEOUT_S)
    start = time.monotonic()
    try:
        row = reader.execute("select count(*) from t").fetchone()
        observed, detail = "reads", row[0]
    except sqlite3.OperationalError as exc:
        observed, detail = "locked", str(exc)
    wait_ms = round((time.monotonic() - start) * 1000, 1)
    writer.execute("ROLLBACK")
    lg.info(
        "reader_vs_writer",
        command=f"writer: PRAGMA journal_mode={journal_mode}; BEGIN {begin_kind}; INSERT (uncommitted) | reader(timeout={READER_TIMEOUT_S}s): SELECT count(*)",
        journal_mode=journal_mode,
        begin_kind=begin_kind,
        observed=observed,
        detail=detail,
        wait_ms=wait_ms,
        python=sys.version.split()[0],
        sqlite=sqlite3.sqlite_version,
    )
    assert observed == expected
    if expected == "reads":
        assert detail == 0
        assert wait_ms < 100
    else:
        assert detail == "database is locked"
        assert wait_ms >= READER_TIMEOUT_S * 1000 * 0.9


@pytest.mark.parametrize(
    ("busy_timeout_ms", "commit_after_ms", "expected", "min_wait_ms", "max_wait_ms"),
    BUSY_ROWS,
    ids=[f"timeout{t}-commit{c}-{o}" for t, c, o, _lo, _hi in BUSY_ROWS],
)
def test_second_writer_busy_timeout_under_wal(tmp_path, busy_timeout_ms, commit_after_ms, expected, min_wait_ms, max_wait_ms):
    lg = log.get("grounding.sqlite")
    path, a = _fresh_db(tmp_path, "WAL")
    a.execute("BEGIN IMMEDIATE")
    a.execute("insert into t values (1)")
    result = {}

    def second_writer():
        b = _connect(path, busy_timeout_ms / 1000)
        start = time.monotonic()
        try:
            b.execute("insert into t values (2)")
            result["observed"], result["detail"] = "ok", "inserted"
        except sqlite3.OperationalError as exc:
            result["observed"], result["detail"] = "locked", str(exc)
        result["wait_ms"] = round((time.monotonic() - start) * 1000, 1)
        b.close()

    worker = threading.Thread(target=second_writer)
    worker.start()
    if commit_after_ms is not None:
        time.sleep(commit_after_ms / 1000)
        a.execute("COMMIT")
    worker.join()
    if commit_after_ms is None:
        a.execute("ROLLBACK")
    lg.info(
        "busy_timeout",
        command=f"A: BEGIN IMMEDIATE; INSERT; {'COMMIT after ' + str(commit_after_ms) + ' ms' if commit_after_ms is not None else 'never commits'} | B(busy_timeout={busy_timeout_ms} ms): INSERT",
        busy_timeout_ms=busy_timeout_ms,
        commit_after_ms=commit_after_ms,
        python=sys.version.split()[0],
        sqlite=sqlite3.sqlite_version,
        **result,
    )
    assert result["observed"] == expected
    assert min_wait_ms <= result["wait_ms"] <= max_wait_ms
    if expected == "locked":
        assert result["detail"] == "database is locked"
        assert a.execute("select count(*) from t").fetchone()[0] == 0
    else:
        assert a.execute("select count(*) from t").fetchone()[0] == 2
