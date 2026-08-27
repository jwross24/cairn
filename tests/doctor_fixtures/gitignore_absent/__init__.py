FIXABLE = True
ONLY = None
QUARANTINES_ON_UNDO = True
FINDINGS = ("D-dirs/gitignore",)


def corrupt(shape):
    (shape.root / ".gitignore").rename(shape.root / "gitignore-stash")
