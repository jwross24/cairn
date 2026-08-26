FIXABLE = True
ONLY = None
FINDINGS = ("D-dirs/gitignore",)


def corrupt(shape):
    (shape.root / ".gitignore").write_text("__pycache__/")
