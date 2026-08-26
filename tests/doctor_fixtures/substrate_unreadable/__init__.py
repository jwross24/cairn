import os

FIXABLE = False
ONLY = None
FINDINGS = ("D-substrate/unreadable",)


def corrupt(shape):
    os.chmod(shape.db, 0o000)
