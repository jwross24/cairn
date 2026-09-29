import sqlite3

FIXABLE = False
ONLY = "substrate"
FINDINGS = ("D-substrate/schema",)


def corrupt(shape):
    conn = sqlite3.connect(shape.db, autocommit=True)
    try:
        conn.execute("DROP TRIGGER nodes_no_update")
        conn.execute("CREATE TRIGGER nodes_no_update BEFORE UPDATE ON nodes BEGIN SELECT RAISE(ABORT, 'other'); END")
    finally:
        conn.close()
