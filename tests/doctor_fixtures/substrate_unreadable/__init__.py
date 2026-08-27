FIXABLE = False
ONLY = None
FINDINGS = ("D-substrate/unreadable",)


def corrupt(shape):
    shape.db.chmod(0o000)
