FIXABLE = False
ONLY = None
FINDINGS = ("D-attest-mode/framing",)


def corrupt(shape):
    with shape.attest.open("ab") as fh:
        fh.write(b"\x99\x99")
