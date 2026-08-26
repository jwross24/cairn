FIXABLE = False
ONLY = None
FINDINGS = ("D-attest-mode/framing",)


def corrupt(shape):
    with open(shape.attest, "ab") as fh:
        fh.write(b"\x99\x99")
