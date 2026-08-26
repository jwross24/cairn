import os

FIXABLE = True
ONLY = None
FINDINGS = ("D-attest-mode/flag",)


def corrupt(shape):
    os.chflags(shape.attest, 0)
