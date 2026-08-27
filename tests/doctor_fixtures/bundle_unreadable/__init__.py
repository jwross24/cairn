import os

FIXABLE = False
ONLY = None
FINDINGS = ("D-bundle/unreadable",)


def corrupt(shape):
    os.chflags(shape.bundle, 0)
    shape.bundle.chmod(0o600)
    shape.bundle.write_bytes(b"SQLite format 3\x00 and then nothing that parses as one")
