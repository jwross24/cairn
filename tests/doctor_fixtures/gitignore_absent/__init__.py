import os

FIXABLE = True
ONLY = None
QUARANTINES_ON_UNDO = True
FINDINGS = ("D-dirs/gitignore",)


def corrupt(shape):
    os.rename(shape.root / ".gitignore", shape.root / "gitignore-stash")
