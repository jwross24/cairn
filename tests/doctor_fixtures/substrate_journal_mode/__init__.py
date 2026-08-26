import sqlite3

FIXABLE = False
ONLY = None
FINDINGS = ("D-substrate/journal-mode",)


def corrupt(shape):
    conn = sqlite3.connect(shape.db)
    try:
        conn.execute("PRAGMA journal_mode=delete")
    finally:
        conn.close()
