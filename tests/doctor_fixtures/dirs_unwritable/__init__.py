import os

FIXABLE = False
ONLY = None
FINDINGS = ("D-dirs/var-unwritable",)


def corrupt(shape):
    os.chmod(shape.root / "var", 0o500)
