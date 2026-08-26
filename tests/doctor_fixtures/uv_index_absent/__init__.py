import os

FIXABLE = False
ONLY = None
FINDINGS = ("D-uv-index/absent",)


def corrupt(shape):
    os.rename(shape.root / "pyproject.toml", shape.root / "pyproject-stash.toml")
