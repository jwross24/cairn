FIXABLE = False
ONLY = None
FINDINGS = ("D-substrate/absent",)


def corrupt(shape):
    shape.db = shape.root / "var" / "never-created.sqlite"
