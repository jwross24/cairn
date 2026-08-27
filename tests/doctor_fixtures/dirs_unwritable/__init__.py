FIXABLE = False
ONLY = None
FINDINGS = ("D-dirs/var-unwritable",)


def corrupt(shape):
    (shape.root / "var").chmod(0o500)
