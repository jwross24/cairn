import sqlite3

FIXABLE = False
ONLY = None
FINDINGS = ("D-substrate/integrity",)

SMEAR = b"\xa5" * 32


def _opens_but_fails_integrity(db):
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal" and (
            conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
        )
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def corrupt(shape):
    conn = sqlite3.connect(shape.db)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
    finally:
        conn.close()
    intact = bytes(shape.db.read_bytes())
    for page in range(1, page_count):
        data = bytearray(intact)
        start = page_size * page + 8
        data[start : start + len(SMEAR)] = SMEAR
        shape.db.write_bytes(bytes(data))
        if _opens_but_fails_integrity(shape.db):
            return
    shape.db.write_bytes(intact)
    raise AssertionError(f"no page of {shape.db} smears into an integrity_check failure that still opens")
