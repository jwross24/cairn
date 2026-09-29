import sqlite3

FIXABLE = False
ONLY = "substrate"
FINDINGS = ("D-substrate/schema",)


def corrupt(shape):
    conn = sqlite3.connect(shape.db, autocommit=True)
    try:
        conn.execute("ALTER TABLE attempts ADD COLUMN planted_extra TEXT")
    finally:
        conn.close()
