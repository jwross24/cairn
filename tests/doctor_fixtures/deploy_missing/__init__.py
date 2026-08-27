FIXABLE = True
ONLY = None
FINDINGS = ("D-dirs/deploy-absent",)


def corrupt(shape):
    stash = shape.root / "deploy-stash"
    (shape.root / "deploy").rename(stash)
    shape.bundle = stash / shape.bundle.name
    shape.pin = stash / shape.pin.name
    shape.attest = stash / shape.attest.name
