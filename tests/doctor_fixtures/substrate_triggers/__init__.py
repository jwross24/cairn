import sqlite3

FIXABLE = False
ONLY = None
FINDINGS = ("D-substrate/triggers",)


def corrupt(shape):
    conn = sqlite3.connect(shape.db)
    try:
        name = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name").fetchone()[0]
        conn.execute(f"DROP TRIGGER {name}")
        conn.commit()
    finally:
        conn.close()
