import os
import stat

FIXABLE = False
ONLY = None
FINDINGS = ("D-attest-mode/empty",)


def corrupt(shape):
    os.chflags(shape.attest, 0)
    with shape.attest.open("wb"):
        pass
    os.chflags(shape.attest, stat.UF_APPEND)
