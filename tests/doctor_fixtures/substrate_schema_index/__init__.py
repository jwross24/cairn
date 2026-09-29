import sqlite3

FIXABLE = False
ONLY = "substrate"
FINDINGS = ("D-substrate/schema",)


def corrupt(shape):
    conn = sqlite3.connect(shape.db, autocommit=True)
    try:
        conn.execute("DROP INDEX attempts_by_recipe")
    finally:
        conn.close()
