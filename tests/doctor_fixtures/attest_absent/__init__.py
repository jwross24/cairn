import os

FIXABLE = False
ONLY = None
FINDINGS = ("D-attest-mode/absent",)


def corrupt(shape):
    os.chflags(shape.attest, 0)
    shape.attest.rename(shape.attest.with_name(shape.attest.name + ".stash"))
