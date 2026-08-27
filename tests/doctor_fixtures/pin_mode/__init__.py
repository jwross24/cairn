import os
import stat

FIXABLE = True
ONLY = None
FINDINGS = ("D-pin-mode/mode",)


def corrupt(shape):
    os.chflags(shape.pin, 0)
    shape.pin.chmod(0o644)
    os.chflags(shape.pin, stat.UF_APPEND)
