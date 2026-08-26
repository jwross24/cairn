import os
import stat

from cairn import attest, canon

FIXABLE = False
ONLY = None
FINDINGS = ("D-attest-mode/waiver",)


def corrupt(shape):
    other = attest.fixture_waiver("a" * 64)
    os.chflags(shape.attest, 0)
    with open(shape.attest, "wb") as fh:
        fh.write(canon.length_prefix(bytes(attest.waiver_canonical(other))))
    os.chflags(shape.attest, stat.UF_APPEND)
