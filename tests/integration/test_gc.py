import json
import sqlite3

import pytest
from _substrate_helpers import (
    ENV_MANIFEST_HASH,
    IDENTITY_A,
    SELFTEST_SUMMARY,
    TRANSCRIPT_HASH,
    launch,
    open_writer,
    recipe,
)
from mutants import gc_mutants

from cairn import cli, exits, gc, substrate


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


def test_collect_removes_orphan_blob_and_keeps_the_rooted_one(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    launch(writer, key, "OK", {"a": b"payload"})
    b1 = substrate.blob_hash(b"payload")
    b2 = writer.put_blob(b"orphan")
    db_snapshot(writer.conn, "before")
    result = gc.collect(writer, dry_run=False)
    db_snapshot(writer.conn, "after")
    assert [c["hash"] for c in result["candidates"]] == [b2]
    assert result["deleted"] == 1
    assert result["bytes"] == len(b"orphan")
    assert writer.has_blob(b1) is True
    assert writer.has_blob(b2) is False


def test_serve_returns_none_while_a_manifest_blob_is_lost_and_again_once_it_is_restored(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    attempt, manifest = launch(writer, key, "OK", {"a": b"payload"})
    assert writer.serve(key) == substrate.Served(attempt, manifest)
    b1 = substrate.blob_hash(b"payload")
    writer.conn.execute("DELETE FROM blobs WHERE hash = ?", (b1,))
    db_snapshot(writer.conn, "blob-lost")
    assert writer.serve(key) is None
    writer.put_blob(b"payload")
    assert writer.serve(key) == substrate.Served(attempt, manifest)


def test_collect_on_an_empty_db_is_a_noop(writer, db_snapshot):
    db_snapshot(writer.conn, "empty")
    result = gc.collect(writer, dry_run=False)
    db_snapshot(writer.conn, "after")
    assert result["candidates"] == []
    assert result["deleted"] == 0
    assert result["bytes"] == 0
    assert writer.conn.execute("SELECT count(*) FROM gc_runs").fetchone()[0] == 1


def test_certificate_root_blob_survives(writer, db_snapshot):
    identity = writer.put_identity_bundle(IDENTITY_A)
    cert = writer.put_certificate(identity, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, SELFTEST_SUMMARY)
    assert writer.is_root("certificate", cert)
    blob = writer.put_blob(b"cert-artifact")
    writer.add_lineage(blob, cert, "member")
    db_snapshot(writer.conn, "before")
    result = gc.collect(writer, dry_run=False)
    db_snapshot(writer.conn, "after")
    assert result["deleted"] == 0
    assert writer.has_blob(blob) is True


def test_non_reproducible_divergence_attempts_both_survive(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    launch(writer, key, "OK", {"out": b"one"})
    launch(writer, key, "OK", {"out": b"two"})
    marked = writer.mark_non_reproducible(key)
    assert len(marked) == 2
    b1 = substrate.blob_hash(b"one")
    b2 = substrate.blob_hash(b"two")
    db_snapshot(writer.conn, "before")
    result = gc.collect(writer, dry_run=False)
    db_snapshot(writer.conn, "after")
    assert result["deleted"] == 0
    assert writer.has_blob(b1) is True
    assert writer.has_blob(b2) is True


def test_cli_without_yes_lists_exactly_the_orphan_and_deletes_nothing(tmp_path, capsys, db_snapshot):
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db) as sub:
        key = sub.put_recipe(recipe(1))
        launch(sub, key, "OK", {"a": b"payload"})
        orphan = sub.put_blob(b"orphan")
        db_snapshot(sub.conn, "before")
    code, out, err = _run(["gc", "--db", str(db), "--json"], capsys)
    assert code == exits.OK, err
    doc = json.loads(out)
    assert doc["dry_run"] is True
    assert [c["hash"] for c in doc["candidates"]] == [orphan]
    assert doc["deleted"] == 0
    with substrate.Substrate.open(db) as sub:
        db_snapshot(sub.conn, "after-listing")
        assert sub.has_blob(orphan) is True


def test_cli_explicit_dry_run_flag_behaves_the_same_as_the_default(tmp_path, capsys, db_snapshot):
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db) as sub:
        key = sub.put_recipe(recipe(1))
        launch(sub, key, "OK", {"a": b"payload"})
        orphan = sub.put_blob(b"orphan")
        db_snapshot(sub.conn, "before")
    code, out, err = _run(["gc", "--db", str(db), "--dry-run", "--json"], capsys)
    assert code == exits.OK, err
    doc = json.loads(out)
    assert doc["dry_run"] is True
    assert [c["hash"] for c in doc["candidates"]] == [orphan]
    with substrate.Substrate.open(db) as sub:
        db_snapshot(sub.conn, "after-listing")
        assert sub.has_blob(orphan) is True


def test_cli_refuses_dry_run_together_with_yes_and_changes_nothing(tmp_path, capsys, db_snapshot):
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db) as sub:
        key = sub.put_recipe(recipe(1))
        launch(sub, key, "OK", {"a": b"payload"})
        orphan = sub.put_blob(b"orphan")
        db_snapshot(sub.conn, "before")
    code, out, err = _run(["gc", "--db", str(db), "--dry-run", "--yes", "--json"], capsys)
    assert code == exits.USER_INPUT
    assert out == ""
    assert "--dry-run" in err and "--yes" in err
    assert f"cairn gc --db {db}   # list" in err and f"cairn gc --db {db} --yes   # delete" in err
    with substrate.Substrate.open(db) as sub:
        db_snapshot(sub.conn, "after-refusal")
        assert sub.has_blob(orphan) is True
        assert sub.conn.execute("SELECT count(*) FROM gc_runs").fetchone()[0] == 0


def test_cli_exits_environment_when_the_substrate_file_is_absent(tmp_path, capsys):
    db = tmp_path / "absent.sqlite"
    code, out, err = _run(["gc", "--db", str(db), "--yes"], capsys)
    assert code == exits.ENVIRONMENT
    assert out == ""
    assert "does not exist" in err and str(db) in err
    assert not db.exists()


def test_cli_yes_removes_the_orphan_and_the_gc_runs_record_names_count_and_bytes(tmp_path, capsys, db_snapshot):
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db) as sub:
        key = sub.put_recipe(recipe(1))
        launch(sub, key, "OK", {"a": b"payload"})
        orphan = sub.put_blob(b"orphan")
        db_snapshot(sub.conn, "before")
    code, out, err = _run(["gc", "--db", str(db), "--yes", "--json"], capsys)
    assert code == exits.OK, err
    doc = json.loads(out)
    assert doc["dry_run"] is False
    assert doc["deleted"] == 1
    assert doc["bytes"] == len(b"orphan")
    with substrate.Substrate.open(db) as sub:
        db_snapshot(sub.conn, "after-collect")
        assert sub.has_blob(orphan) is False
        row = dict(sub.conn.execute("SELECT count, bytes, dry_run FROM gc_runs ORDER BY rowid DESC LIMIT 1").fetchone())
        assert row["count"] == 1
        assert row["bytes"] == len(b"orphan")
        assert row["dry_run"] == 0


def test_cli_yes_exits_conflict_when_a_second_connection_holds_a_write_transaction(tmp_path, capsys, db_snapshot):
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db) as sub:
        key = sub.put_recipe(recipe(1))
        launch(sub, key, "OK", {"a": b"payload"})
        sub.put_blob(b"orphan")
        db_snapshot(sub.conn, "before")
    blocker = sqlite3.connect(str(db))
    blocker.execute("BEGIN IMMEDIATE")
    try:
        code, out, err = _run(["gc", "--db", str(db), "--yes"], capsys)
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()
    assert code == exits.CONFLICT
    assert "locked" in err.lower(), err


def test_cli_yes_exits_conflict_when_a_writer_is_already_open_in_process(tmp_path, capsys, db_snapshot):
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db) as sub:
        key = sub.put_recipe(recipe(1))
        launch(sub, key, "OK", {"a": b"payload"})
        orphan = sub.put_blob(b"orphan")
        db_snapshot(sub.conn, "before")
        code, out, err = _run(["gc", "--db", str(db), "--yes"], capsys)
        assert code == exits.CONFLICT
        assert out == ""
        assert "another writer already holds" in err, err
        db_snapshot(sub.conn, "after-refusal")
        assert sub.has_blob(orphan) is True


def test_collect_is_idempotent_across_a_page_boundary_and_kills_the_one_page_mutant(writer, db_snapshot):
    for i in range(150):
        writer.put_blob(f"orphan-{i}".encode())
    db_snapshot(writer.conn, "before")
    first = gc.collect(writer, dry_run=False)
    db_snapshot(writer.conn, "after-first")
    second = gc.collect(writer, dry_run=False)
    db_snapshot(writer.conn, "after-second")
    assert first["deleted"] == 150
    assert second["deleted"] == 0

    for i in range(150):
        writer.put_blob(f"page-orphan-{i}".encode())
    db_snapshot(writer.conn, "before-mutant")
    with gc_mutants.collect_one_page_only():
        broken_first = gc.collect(writer, dry_run=False)
        db_snapshot(writer.conn, "after-mutant-first")
        broken_second = gc.collect(writer, dry_run=False)
    db_snapshot(writer.conn, "after-mutant-second")
    assert broken_first["deleted"] == gc.PAGE_SIZE
    assert broken_second["deleted"] == 50


def test_a_blob_rooted_by_a_second_connection_before_the_write_lock_is_not_collected(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    launch(writer, key, "OK", {"a": b"payload"})
    orphan = writer.put_blob(b"orphan")
    racer = sqlite3.connect(str(writer.path))
    fired = []

    def root_the_orphan(statement):
        if statement.strip().upper().startswith("BEGIN IMMEDIATE") and not fired:
            fired.append(statement)
            racer.execute(
                "INSERT INTO lineage (child_hash, parent_hash, edge_kind) VALUES (?, ?, ?)",
                (orphan, key, "input"),
            )
            racer.commit()

    db_snapshot(writer.conn, "before")
    writer.conn.set_trace_callback(root_the_orphan)
    try:
        result = gc.collect(writer, dry_run=False)
    finally:
        writer.conn.set_trace_callback(None)
        racer.close()
    db_snapshot(writer.conn, "after")
    assert len(fired) == 1
    assert writer.conn.execute("SELECT 1 FROM lineage WHERE child_hash = ?", (orphan,)).fetchone() is not None
    assert result["candidates"] == []
    assert result["deleted"] == 0
    assert writer.has_blob(orphan) is True


def test_candidates_are_listed_in_hash_order(writer, db_snapshot):
    orphans = [writer.put_blob(f"orphan-{i}".encode()) for i in range(8)]
    assert orphans != sorted(orphans)
    db_snapshot(writer.conn, "before")
    result = gc.collect(writer, dry_run=True)
    db_snapshot(writer.conn, "after")
    assert [c["hash"] for c in result["candidates"]] == sorted(orphans)


def test_the_collect_log_carries_the_run_summary_and_the_candidate_hashes(writer, db_snapshot, json_test_log):
    key = writer.put_recipe(recipe(1))
    launch(writer, key, "OK", {"a": b"payload"})
    orphan = writer.put_blob(b"orphan")
    db_snapshot(writer.conn, "before")
    result = gc.collect(writer, dry_run=False)
    db_snapshot(writer.conn, "after")
    records = [json.loads(line) for line in json_test_log.read_text().splitlines()]
    summaries = [r for r in records if r["step"] == "gc" and r["event"] == "collect"]
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["level"] == "INFO"
    assert summary["roots"] == result["roots"] == 1
    assert summary["reachable"] == result["reachable"] == 3
    assert summary["candidates"] == 1
    assert summary["bytes"] == len(b"orphan")
    assert summary["dry_run"] is False
    listings = [r for r in records if r["step"] == "gc" and r["event"] == "candidates"]
    assert len(listings) == 1
    assert listings[0]["level"] == "DEBUG"
    assert listings[0]["hashes"] == [orphan]
