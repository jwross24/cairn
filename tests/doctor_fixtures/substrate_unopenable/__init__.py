FIXABLE = False
ONLY = None
FINDINGS = ("D-substrate/unopenable", "D-certificate/unreadable")


def corrupt(shape):
    shape.db = shape.root / "var" / "not-a-database.sqlite"
    shape.db.write_bytes(b"this file exists and is readable and is not a SQLite database")
