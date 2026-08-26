import os

FIXABLE = True
ONLY = None
FINDINGS = ("D-dirs/var-absent",)


def corrupt(shape):
    stash = shape.root / "var-stash"
    os.rename(shape.root / "var", stash)
    shape.db = stash / shape.db.name
