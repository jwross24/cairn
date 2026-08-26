import os

FIXABLE = True
ONLY = "dirs"
FINDINGS = ("D-dirs/deploy-absent",)


def corrupt(shape):
    stash = shape.root / "deploy-stash"
    os.rename(shape.root / "deploy", stash)
    shape.bundle = stash / shape.bundle.name
    shape.pin = stash / shape.pin.name
    shape.attest = stash / shape.attest.name
