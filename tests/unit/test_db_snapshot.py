import logging
import sqlite3

import pytest


def _seed(path):
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE evidence (value INTEGER)")
        conn.executemany("INSERT INTO evidence VALUES (?)", [(7,), (11,)])
        conn.commit()
    finally:
        conn.close()


def _deny_evidence_read(action, arg1, arg2, database, trigger):
    if action == sqlite3.SQLITE_READ and arg1 == "evidence":
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _track_connections(monkeypatch):
    real_connect = sqlite3.connect
    opened = []

    def connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(sqlite3, "connect", connect)
    return opened


def _assert_closed(conn):
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        conn.execute("SELECT 1")


def test_path_snapshot_counts_logs_and_closes_owned_connection(tmp_path, db_snapshot, caplog, monkeypatch):
    path = tmp_path / "snapshot.sqlite"
    _seed(path)
    opened = _track_connections(monkeypatch)
    try:
        with caplog.at_level(logging.INFO, logger="cairn"):
            counts = db_snapshot(path, "owned-success")
        assert counts == {"evidence": 2}
        snapshot_logs = [record for record in caplog.records if record.getMessage() == "db_snapshot"]
        assert len(snapshot_logs) == 1
        assert snapshot_logs[0].step == "test"
        assert snapshot_logs[0].fields == {"label": "owned-success", "counts": counts}
        assert len(opened) == 1
        _assert_closed(opened[0])
    finally:
        for conn in opened:
            conn.close()


def test_borrowed_snapshot_preserves_uncommitted_transaction(tmp_path, db_snapshot):
    path = tmp_path / "borrowed-success.sqlite"
    _seed(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute("INSERT INTO evidence VALUES (13)")
        assert conn.in_transaction
        assert db_snapshot(conn, "borrowed-success") == {"evidence": 3}
        assert conn.in_transaction
        assert conn.execute("SELECT count(*) FROM evidence").fetchone() == (3,)
    finally:
        conn.close()


def test_path_snapshot_closes_owned_connection_after_query_error(tmp_path, db_snapshot, monkeypatch):
    path = tmp_path / "owned-error.sqlite"
    path.write_bytes(b"not a SQLite database")
    opened = _track_connections(monkeypatch)
    try:
        with pytest.raises(sqlite3.DatabaseError, match="not a database"):
            db_snapshot(path, "owned-error")
        assert len(opened) == 1
        _assert_closed(opened[0])
    finally:
        for conn in opened:
            conn.close()


def test_borrowed_snapshot_preserves_transaction_after_query_error(tmp_path, db_snapshot):
    path = tmp_path / "borrowed-error.sqlite"
    _seed(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute("INSERT INTO evidence VALUES (13)")
        conn.set_authorizer(_deny_evidence_read)
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            db_snapshot(conn, "borrowed-error")
        assert conn.in_transaction
        conn.set_authorizer(None)
        assert conn.execute("SELECT count(*) FROM evidence").fetchone() == (3,)
        assert conn.in_transaction
    finally:
        conn.set_authorizer(None)
        conn.close()


def test_path_snapshot_closes_owned_connection_when_logging_fails(tmp_path, db_snapshot, monkeypatch):
    path = tmp_path / "owned-log-error.sqlite"
    _seed(path)
    opened = _track_connections(monkeypatch)

    def fail_logging(*args, **kwargs):
        raise RuntimeError("snapshot logging failed")

    monkeypatch.setattr(logging.getLogger("cairn"), "info", fail_logging)
    try:
        with pytest.raises(RuntimeError, match="snapshot logging failed"):
            db_snapshot(path, "owned-log-error")
        assert len(opened) == 1
        _assert_closed(opened[0])
    finally:
        for conn in opened:
            conn.close()
