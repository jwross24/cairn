FIXABLE = True
ONLY = None
FINDINGS = ("D-dirs/var-absent",)


def corrupt(shape):
    stash = shape.root / "var-stash"
    (shape.root / "var").rename(stash)
    shape.db = stash / shape.db.name
