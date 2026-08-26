import os

FIXABLE = False
ONLY = None
FINDINGS = ("D-bundle/absent",)


def corrupt(shape):
    os.chflags(shape.bundle, 0)
    os.rename(shape.bundle, shape.bundle.with_name(shape.bundle.name + ".stash"))
