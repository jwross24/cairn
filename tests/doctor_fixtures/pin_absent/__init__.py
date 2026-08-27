import os

FIXABLE = False
ONLY = None
FINDINGS = ("D-bundle/absent",)


def corrupt(shape):
    os.chflags(shape.pin, 0)
    shape.pin.rename(shape.pin.with_name(shape.pin.name + ".stash"))
