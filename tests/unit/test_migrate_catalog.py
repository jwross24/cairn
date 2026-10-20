import hashlib
import itertools
import json
import sqlite3

import pytest

from cairn import migrate_catalog, substrate
from cairn.migrate_fingerprint import fingerprint
from cairn.migrate_lint import lint
from cairn.substrate_schema_check import _schema_objects

ACCEPTED = [
    "CREATE TABLE IF NOT EXISTS t (a INTEGER PRIMARY KEY, b TEXT NOT NULL);",
    "CREATE UNIQUE INDEX IF NOT EXISTS t_by_b ON t (b);",
    "CREATE VIEW v AS SELECT a FROM t;",
    "ALTER TABLE t ADD COLUMN c INTEGER NOT NULL DEFAULT 0;",
    "ALTER TABLE t ADD COLUMN d TEXT DEFAULT 'x';",
    "ALTER TABLE t ADD COLUMN e TEXT;",
    "CREATE TRIGGER IF NOT EXISTS t_no_delete BEFORE DELETE ON t BEGIN SELECT RAISE(ABORT, 'append-only'); END;",
    "-- a note\nCREATE TABLE u (x);",
]
REFUSED = [
    "UPDATE t SET b = 'x';",
    "DELETE FROM t;",
    "DROP TABLE t;",
    "INSERT INTO t (b) VALUES ('x');",
    "ALTER TABLE t RENAME TO t2;",
    "ALTER TABLE t DROP COLUMN b;",
    "ALTER TABLE t ADD COLUMN c INTEGER NOT NULL;",
    "ALTER TABLE t ADD COLUMN c TEXT DEFAULT (datetime('now'));",
    "ALTER TABLE t ADD COLUMN c INTEGER UNIQUE;",
    "CREATE TABLE a (x); UPDATE t SET b = 'x';",
    "CREATE TABLE copy AS SELECT * FROM t;",
    "-- harmless\nUPDATE t SET b = 'x';",
    "CREATE TRIGGER g BEFORE INSERT ON t BEGIN UPDATE t SET b = 'x'; END;",
    "CREATE TRIGGER g BEFORE INSERT ON t BEGIN SELECT RAISE(ABORT, 'x'); DELETE FROM t; END;",
    "PRAGMA writable_schema = 1;",
    "",
]


@pytest.mark.parametrize("sql", ACCEPTED)
def test_the_lint_accepts_additive_statements(sql):
    assert lint(sql)[0] == []


@pytest.mark.parametrize("sql", REFUSED)
def test_the_lint_refuses_everything_that_is_not_additive(sql):
    assert lint(sql)[0] != []


def test_the_lint_flags_a_trigger_for_cross_family_review():
    assert lint(ACCEPTED[6])[1] is True
    assert lint(ACCEPTED[0])[1] is False


def write_catalog(directory, sql, *, review=True, recorded_sha=None):
    (directory / "0001_x.sql").write_text(sql)
    sha = recorded_sha or hashlib.sha256(sql.encode()).hexdigest()
    entry = {"id": "0001", "file": "0001_x.sql", "from": "a", "to": "b", "sql_sha256": sha}
    entry["trigger_review_required"] = review
    (directory / "manifest.json").write_text(json.dumps({"migrations": [entry]}))
    return migrate_catalog.load_catalog(directory)


def test_a_migration_that_updates_rows_is_refused_by_the_lint(tmp_path):
    cat = write_catalog(tmp_path, "UPDATE nodes SET kind = 'x';\n")
    with pytest.raises(migrate_catalog.MigrationRefused, match="not additive"):
        cat.verify()


def test_a_trigger_without_the_review_flag_is_refused(tmp_path):
    sql = "CREATE TRIGGER g BEFORE DELETE ON t BEGIN SELECT RAISE(ABORT, 'x'); END;\n"
    with pytest.raises(migrate_catalog.MigrationRefused, match="trigger_review_required"):
        write_catalog(tmp_path, sql, review=False).verify()
    write_catalog(tmp_path, sql, review=True).verify()


def test_an_applied_migration_whose_sql_changed_is_a_checksum_drift_refusal(tmp_path):
    cat = write_catalog(tmp_path, "CREATE TABLE a (x);\n", recorded_sha="0" * 64)
    with pytest.raises(migrate_catalog.MigrationRefused, match="changed after it was recorded"):
        cat.verify()


def test_the_shipped_migrations_verify():
    migrate_catalog.load_catalog().verify()


def test_the_manifest_chain_is_continuous_and_starts_from_recorded_history():
    cat = migrate_catalog.load_catalog()
    history = migrate_catalog.load_history()
    steps = cat.migrations
    assert [s.id for s in steps] == sorted(s.id for s in steps)
    assert all(a.to_fp == b.from_fp for a, b in itertools.pairwise(steps))
    assert all(s.from_fp in history for s in steps)
    assert len(set(history)) == len(history)


def test_the_newest_migration_ends_at_the_shipped_schema_fingerprint():
    cat = migrate_catalog.load_catalog()
    assert migrate_catalog.enforcement_problems(substrate.shipped_objects(), cat) == []


def objects_of(schema_text):
    conn = sqlite3.connect(":memory:")
    conn.executescript(schema_text)
    return _schema_objects(conn)


def test_a_schema_file_edit_without_a_migration_fails_the_enforcement_check(tmp_path):
    scratch = []
    for path in substrate.SCHEMA_PATHS:
        copy = tmp_path / path.name
        copy.write_text(path.read_text())
        scratch.append(copy)
    cat = migrate_catalog.load_catalog()
    assert migrate_catalog.enforcement_problems(objects_of("".join(p.read_text() for p in scratch)), cat) == []
    governance = scratch[2]
    governance.write_text(governance.read_text() + "\nCREATE TABLE IF NOT EXISTS stray_addition (x INTEGER);\n")
    problems = migrate_catalog.enforcement_problems(objects_of("".join(p.read_text() for p in scratch)), cat)
    assert any("a schema file changed without a migration" in p for p in problems)


def test_every_shipped_fingerprint_difference_changes_the_fingerprint():
    base = objects_of("CREATE TABLE t (a INTEGER);")
    assert fingerprint(base) == fingerprint(objects_of("CREATE TABLE  t (a   INTEGER);"))
    assert fingerprint(base) != fingerprint(objects_of("CREATE TABLE t (a INTEGER, b TEXT);"))


HIDING = ['"v\'"', "`v'`", "[v']", "'it''s'", "/* ' */ t", "t -- '\n"]
VERBS = ["DELETE FROM", "UPDATE", "DROP TABLE"]


@pytest.mark.parametrize("hide", HIDING)
@pytest.mark.parametrize("verb", VERBS)
def test_a_write_hidden_behind_any_quoting_form_inside_a_trigger_body_is_refused(hide, verb):
    sql = f"CREATE TRIGGER g AFTER INSERT ON t BEGIN\nSELECT RAISE(IGNORE) WHERE 0; SELECT {hide}; {verb} t;\nEND;"
    assert lint(sql)[0] != []
    sql = f"CREATE TRIGGER g AFTER INSERT ON t BEGIN\nSELECT {hide}; SELECT RAISE(IGNORE) WHERE 0; {verb} t;\nEND;"
    assert lint(sql)[0] != []


@pytest.mark.parametrize("hide", HIDING)
def test_a_second_statement_after_any_quoting_form_is_refused_at_top_level(hide):
    assert lint(f"CREATE TABLE a (x TEXT DEFAULT 'q'); CREATE TABLE b ({hide}); DELETE FROM a;")[0] != []


def test_the_lint_accepts_delimiters_inside_quotes_and_the_shipped_migrations():
    assert lint("CREATE TRIGGER g AFTER INSERT ON t BEGIN SELECT RAISE(ABORT, 'a; DELETE FROM t'); END;")[0] == []
    assert lint('CREATE TABLE "a;b" ("c d" TEXT CHECK ("c d" <> \'x; y\'));')[0] == []
    for migration in migrate_catalog.load_catalog().migrations:
        assert lint(migration.sql_bytes().decode())[0] == []


def test_a_check_literal_that_differs_only_in_inner_whitespace_changes_the_fingerprint():
    one = objects_of("CREATE TABLE t (x TEXT CHECK (x <> 'a b'));")
    two = objects_of("CREATE TABLE t (x TEXT CHECK (x <> 'a  b'));")
    spaced = objects_of("CREATE TABLE  t  (x TEXT   CHECK (x <>   'a b'));")
    assert fingerprint(one) != fingerprint(two)
    assert fingerprint(one) == fingerprint(spaced)
