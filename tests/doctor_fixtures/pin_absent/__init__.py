import os

FIXABLE = False
ONLY = None
FINDINGS = ("D-bundle/absent",)


def corrupt(shape):
    os.chflags(shape.pin, 0)
    os.rename(shape.pin, shape.pin.with_name(shape.pin.name + ".stash"))
