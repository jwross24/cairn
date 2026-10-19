import sqlite3

import pytest
from _substrate_helpers import IDENTITY_A, certify, recipe

from cairn import substrate
from cairn.substrate import Substrate

RECEIPT = {name: ("aa" * 32 if name.endswith(("hash", "digest")) else 1) for name in substrate.RECEIPT_FIELDS}


@pytest.fixture
def populated(writer):
    key = writer.put_recipe(recipe(1))
    receipt = writer.put_receipt(RECEIPT)
    attempt = writer.start_attempt(key)
    artifacts = {"out": (writer.put_blob(b"x"), 1)}
    manifest = writer.put_output_manifest(artifacts, recipe_key=key)
    writer.close_attempt(
        attempt,
        "OK",
        output_manifest_hash=manifest,
        receipt_hash=receipt,
        verifier_result_hash="55" * 32,
        certificate_hash="66" * 32,
    )
    running = writer.start_attempt(key)
    identity, cert = certify(writer, IDENTITY_A)
    writer.weaken_grade(manifest, "Verifiable")
    writer.add_yank_record(
        "yank-1", identity, "{}", kind="human_path", ruling_ref="r-1", record_digest="dd" * 32, file_offset=0
    )
    writer.add_salt("class-1", "salt-1", kind="human_path", record_digest="dd" * 32, file_offset=1)
    return writer, {
        "key": key,
        "attempt": attempt,
        "running": running,
        "manifest": manifest,
        "identity": identity,
        "cert": cert,
        "receipt": receipt,
    }


APPEND_ONLY_STATEMENTS = [
    ("nodes", "UPDATE nodes SET kind = 'other' WHERE hash = :manifest"),
    ("nodes", "DELETE FROM nodes WHERE hash = :manifest"),
    ("nodes", "UPDATE nodes SET replay_grade = 'AuditOnly' WHERE hash = :manifest"),
    ("recipes", "UPDATE recipes SET salt = 'x' WHERE recipe_key = :key"),
    ("recipes", "DELETE FROM recipes WHERE recipe_key = :key"),
    ("lineage", "UPDATE lineage SET edge_kind = 'x' WHERE child_hash = :manifest"),
    ("lineage", "DELETE FROM lineage WHERE child_hash = :manifest"),
    ("roots", "UPDATE roots SET root_kind = 'ledger_row' WHERE node_hash = :key"),
    ("roots", "DELETE FROM roots WHERE node_hash = :key"),
    ("skill_certificates", "UPDATE skill_certificates SET cert_hash = 'ff' WHERE identity_bundle_hash = :identity"),
    ("skill_certificates", "DELETE FROM skill_certificates WHERE identity_bundle_hash = :identity"),
    ("yank_records", "UPDATE yank_records SET reach_predicate = 'x' WHERE yank_id = 'yank-1'"),
    ("yank_records", "DELETE FROM yank_records WHERE yank_id = 'yank-1'"),
    ("salts", "UPDATE salts SET salt = 'x' WHERE class_key = 'class-1'"),
    ("salts", "DELETE FROM salts WHERE class_key = 'class-1'"),
    ("grade_history", "UPDATE grade_history SET to_grade = 'Replayable' WHERE node_hash = :manifest"),
    ("grade_history", "DELETE FROM grade_history WHERE node_hash = :manifest"),
    ("attempts", "UPDATE attempts SET status = 'FAIL' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET status = 'RUNNING', ended_at = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET output_manifest_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET recipe_key = 'other' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET skip_cache_lookup = 1 WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET started_at = 'x' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', inadmissible = 1 WHERE attempt_id = :attempt"),
    ("attempts", "DELETE FROM attempts WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET status = 'OK', ended_at = 'x', recipe_key = 'other' WHERE attempt_id = :running"),
    (
        "attempts",
        "UPDATE attempts SET status = 'OK', ended_at = 'x', replay_grade = 'AuditOnly' WHERE attempt_id = :running",
    ),
    (
        "attempts",
        "UPDATE attempts SET status = 'OK', ended_at = 'x', skip_cache_lookup = 1 WHERE attempt_id = :running",
    ),
    ("attempts", "UPDATE attempts SET status = 'OK', ended_at = 'x', started_at = 'x' WHERE attempt_id = :running"),
    ("attempts", "UPDATE attempts SET status = 'OK', ended_at = 'x', disowned_at = 'x' WHERE attempt_id = :running"),
    ("attempts", "UPDATE attempts SET status = 'OK', ended_at = 'x', inadmissible = 1 WHERE attempt_id = :running"),
    ("attempts", "UPDATE attempts SET status = 'OK', ended_at = NULL WHERE attempt_id = :running"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', receipt_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', verifier_result_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', certificate_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', output_manifest_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', replay_grade = 'AuditOnly' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', ended_at = 'x' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', recipe_key = 'other' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', status = 'FAIL' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', skip_cache_lookup = 1 WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', started_at = 'x' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, receipt_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, verifier_result_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, certificate_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, output_manifest_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, replay_grade = 'AuditOnly' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, ended_at = 'x' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, recipe_key = 'other' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, status = 'FAIL' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, skip_cache_lookup = 1 WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, started_at = 'x' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, disowned_at = 'x' WHERE attempt_id = :attempt"),
    ("receipts", "UPDATE receipts SET exit_status = 3 WHERE receipt_hash = :receipt"),
    ("receipts", "DELETE FROM receipts WHERE receipt_hash = :receipt"),
]


@pytest.mark.parametrize(
    ("table", "statement"),
    APPEND_ONLY_STATEMENTS,
    ids=[f"{t}:{s.split()[0]}:{i}" for i, (t, s) in enumerate(APPEND_ONLY_STATEMENTS)],
)
def test_append_only_triggers_refuse_update_and_delete(populated, db_snapshot, table, statement):
    sub, ids = populated
    before = db_snapshot(sub.conn, f"before:{table}")
    row_before = sub.get_attempt(ids["attempt"]), sub.get_attempt(ids["running"])
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sub.conn.execute(statement, ids)
    assert db_snapshot(sub.conn, f"after:{table}") == before
    assert (sub.get_attempt(ids["attempt"]), sub.get_attempt(ids["running"])) == row_before


def test_running_to_terminal_close_is_the_single_permitted_update(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    attempt = writer.start_attempt(key)
    writer.close_attempt(attempt, "INTERRUPTED")
    row = writer.get_attempt(attempt)
    assert row["status"] == "INTERRUPTED" and row["ended_at"] is not None
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.close_attempt(attempt, "OK")
    with pytest.raises(ValueError, match="status must be one of"):
        writer.close_attempt(attempt, "RUNNING")
    running = writer.start_attempt(key)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute("UPDATE attempts SET status = 'OK' WHERE attempt_id = ?", (running,))
    db_snapshot(writer.conn, "closes")
    assert writer.get_attempt(running)["status"] == "RUNNING"


def build_store(path, schema_text):
    conn = sqlite3.connect(str(path), autocommit=True)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(schema_text)
    conn.close()


def schema_without(trigger):
    shipped = substrate.schema_text()
    kept = [line for line in shipped.splitlines() if f"CREATE TRIGGER IF NOT EXISTS {trigger} " not in line]
    assert len(kept) == len(shipped.splitlines()) - 1
    return "\n".join(kept) + "\n"


def master_of(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return sorted(conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master"))
    finally:
        conn.close()


def test_a_store_from_an_older_schema_is_refused_before_a_trigger_reaches_it(tmp_path):
    db = tmp_path / "older.sqlite"
    build_store(db, schema_without("nodes_no_delete"))
    before = master_of(db)
    assert "nodes_no_delete" not in {name for _, name, _, _ in before}

    with pytest.raises(substrate.SchemaMismatch, match="trigger nodes_no_delete: absent from the store"):
        Substrate.open(db, role="writer")

    assert master_of(db) == before


def last_droppable_column(conn, table):
    """The shipped schema is read at runtime, so the planted store is one revision behind
    whatever it currently declares rather than behind a column name pinned here."""
    rows = list(conn.execute("SELECT * FROM pragma_table_info(?)", (table,)))
    droppable = [r[1] for r in rows if not r[3] and not r[5]]
    assert droppable
    return droppable[-1]


def test_a_store_missing_the_newest_shipped_column_is_refused_by_name(tmp_path):
    db = tmp_path / "narrow.sqlite"
    build_store(db, substrate.schema_text())
    conn = sqlite3.connect(str(db), autocommit=True)
    column = last_droppable_column(conn, "ladder_tables")
    conn.execute(f"ALTER TABLE ladder_tables DROP COLUMN {column}")
    conn.close()

    with pytest.raises(substrate.SchemaMismatch, match=f"table ladder_tables: missing {column}"):
        Substrate.open(db, role="writer")


def test_a_store_carrying_a_column_the_shipped_schema_lacks_is_refused_by_name(tmp_path):
    db = tmp_path / "wide.sqlite"
    build_store(db, substrate.schema_text())
    conn = sqlite3.connect(str(db), autocommit=True)
    conn.execute("ALTER TABLE ladder_tables ADD COLUMN unshipped_column TEXT")
    conn.close()

    with pytest.raises(substrate.SchemaMismatch, match="table ladder_tables: unknown unshipped_column"):
        Substrate.open(db, role="writer")


def test_a_store_carrying_a_table_and_trigger_the_shipped_schema_never_named_still_opens(tmp_path):
    db = tmp_path / "instrumented.sqlite"
    build_store(db, substrate.schema_text())
    conn = sqlite3.connect(str(db), autocommit=True)
    conn.executescript(
        "CREATE TABLE observer (seen TEXT);"
        "CREATE TRIGGER observe_salts AFTER INSERT ON salts BEGIN INSERT INTO observer (seen) VALUES ('salt'); END;"
    )
    conn.close()

    sub = Substrate.open(db, role="writer")
    sub.close()


def test_a_reader_refuses_a_store_from_an_older_schema(tmp_path):
    db = tmp_path / "older_reader.sqlite"
    build_store(db, schema_without("nodes_no_delete"))

    with pytest.raises(substrate.SchemaMismatch):
        Substrate.open(db, role="reader")


def test_a_reader_refuses_a_store_that_holds_no_schema_at_all(tmp_path):
    db = tmp_path / "hollow.sqlite"
    db.touch()

    with pytest.raises(substrate.SchemaMismatch, match="holds no schema at all"):
        Substrate.open(db, role="reader")


def test_a_store_built_from_the_shipped_schema_opens_and_reopens(tmp_path):
    db = tmp_path / "shipped.sqlite"
    build_store(db, substrate.schema_text())
    before = master_of(db)

    for role in ("writer", "reader", "writer"):
        sub = Substrate.open(db, role=role)
        sub.close()

    assert master_of(db) == before


def test_a_refused_open_leaves_the_stores_journal_mode_alone(tmp_path):
    db = tmp_path / "delete_mode.sqlite"
    conn = sqlite3.connect(str(db), autocommit=True)
    conn.execute("PRAGMA journal_mode=delete")
    conn.executescript(schema_without("nodes_no_delete"))
    conn.close()

    with pytest.raises(substrate.SchemaMismatch):
        Substrate.open(db, role="writer")

    conn = sqlite3.connect(str(db), autocommit=True)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    conn.close()


@pytest.mark.parametrize(
    ("drift", "statements", "expected"),
    [
        ("an_index", ["DROP INDEX attempts_by_recipe"], "index attempts_by_recipe: absent from the store"),
        (
            "a_trigger_body",
            [
                "DROP TRIGGER nodes_no_update",
                "CREATE TRIGGER nodes_no_update BEFORE UPDATE ON nodes BEGIN SELECT RAISE(ABORT, 'other'); END",
            ],
            "trigger nodes_no_update: definition differs from the shipped schema",
        ),
    ],
)
def test_a_shipped_object_that_drifted_is_refused_by_name(tmp_path, drift, statements, expected):
    db = tmp_path / f"{drift}.sqlite"
    build_store(db, substrate.schema_text())
    conn = sqlite3.connect(str(db), autocommit=True)
    for statement in statements:
        conn.execute(statement)
    conn.close()

    with pytest.raises(substrate.SchemaMismatch, match=expected):
        Substrate.open(db, role="writer")


def test_a_column_that_kept_its_name_but_changed_its_type_is_refused(tmp_path):
    db = tmp_path / "retyped.sqlite"
    shipped = substrate.schema_text()
    retyped = shipped.replace("    verdict_predicate TEXT NOT NULL,", "    verdict_predicate BLOB NOT NULL,")
    assert retyped != shipped
    build_store(db, retyped)

    with pytest.raises(substrate.SchemaMismatch, match="table ladder_tables: column definitions differ"):
        Substrate.open(db, role="writer")


def test_a_refused_open_leaves_no_writer_registered(tmp_path):
    build_store(tmp_path / "older_leak.sqlite", schema_without("nodes_no_delete"))

    with pytest.raises(substrate.SchemaMismatch):
        Substrate.open(tmp_path / "older_leak.sqlite", role="writer")

    sub = Substrate.open(tmp_path / "after.sqlite", role="writer")
    sub.close()
