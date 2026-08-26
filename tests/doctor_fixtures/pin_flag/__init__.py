import os

FIXABLE = True
ONLY = None
FINDINGS = ("D-pin-mode/flag",)


def corrupt(shape):
    os.chflags(shape.pin, 0)
