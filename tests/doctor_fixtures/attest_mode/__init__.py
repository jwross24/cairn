import os
import stat

FIXABLE = True
ONLY = None
FINDINGS = ("D-attest-mode/mode",)


def corrupt(shape):
    os.chflags(shape.attest, 0)
    os.chmod(shape.attest, 0o600)
    os.chflags(shape.attest, stat.UF_APPEND)
