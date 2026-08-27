FIXABLE = False
ONLY = None
FINDINGS = ("D-uv-index/absent",)


def corrupt(shape):
    (shape.root / "pyproject.toml").rename(shape.root / "pyproject-stash.toml")
