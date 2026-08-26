from cairn import substrate

FIXABLE = False
ONLY = None
FINDINGS = ("D-certificate/uncertified",)


def corrupt(shape):
    shape.db = shape.root / "var" / "fresh.sqlite"
    with substrate.Substrate.open(shape.db):
        pass
