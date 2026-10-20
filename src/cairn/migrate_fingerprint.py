import hashlib
import json
import sqlite3

from cairn.substrate_schema_check import _schema_objects


def fingerprint(objects):
    rows = [
        [kind, name, tbl_name, sql, None if columns is None else [list(c) for c in columns]]
        for (kind, name), (tbl_name, sql, columns) in sorted(objects.items())
    ]
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def restrict(objects, universe):
    return {key: value for key, value in objects.items() if key in universe}


def store_fingerprint(conn, universe):
    return fingerprint(restrict(_schema_objects(conn), universe))


def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def user_tables(conn):
    return [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]


def table_columns(conn, table):
    return [row[1] for row in conn.execute("SELECT * FROM pragma_table_info(?)", (table,))]


def _row_order(conn, table):
    without_rowid = conn.execute("SELECT wr FROM pragma_table_list(?) WHERE schema = 'main'", (table,)).fetchone()
    if not without_rowid or not without_rowid[0]:
        return "rowid"
    keyed = sorted((row[5], row[1]) for row in conn.execute("SELECT * FROM pragma_table_info(?)", (table,)) if row[5])
    return ", ".join(quote(name) for _, name in keyed)


def table_digest(conn, table, columns):
    selected = ", ".join(quote(c) for c in columns)
    digest = hashlib.sha256()
    count = 0
    for row in conn.execute(f"SELECT {selected} FROM {quote(table)} ORDER BY {_row_order(conn, table)}"):
        digest.update(repr(tuple(row)).encode() + b"\n")
        count += 1
    return {"columns": list(columns), "rows": count, "sha256": digest.hexdigest()}


def row_digests(conn):
    return {table: table_digest(conn, table, table_columns(conn, table)) for table in user_tables(conn)}


def preserved_digests(conn, before):
    return {table: table_digest(conn, table, entry["columns"]) for table, entry in before.items()}


def digest_differences(before, after):
    return [table for table in sorted(before) if before[table] != after.get(table)]


def integrity(conn):
    try:
        rows = [row[0] for row in conn.execute("PRAGMA integrity_check")]
    except sqlite3.DatabaseError as exc:
        return f"error: {exc}"
    return "ok" if rows == ["ok"] else "; ".join(str(r) for r in rows[:5])


def store_witness(conn):
    sequences = []
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'sqlite_sequence'").fetchone():
        sequences = [list(r) for r in conn.execute("SELECT name, seq FROM sqlite_sequence ORDER BY name")]
    return {
        "full_schema": fingerprint(_schema_objects(conn)),
        "sequences": sequences,
        "user_version": conn.execute("PRAGMA user_version").fetchone()[0],
        "application_id": conn.execute("PRAGMA application_id").fetchone()[0],
    }
