FIXABLE = False
ONLY = None
FINDINGS = ("D-uv-index/unpinned",)


def corrupt(shape):
    (shape.root / "pyproject.toml").write_text('[project]\nname = "cairn"\n')
