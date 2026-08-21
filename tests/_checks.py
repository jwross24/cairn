from pathlib import Path

MOCK_PATTERNS = ("unittest.mock", "MagicMock", "mocker.patch")
SCANNED_DIRS = ("tests/integration", "tests/e2e")


def scan_for_mocks(root):
    hits = []
    for name in SCANNED_DIRS:
        base = Path(root) / name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            text = path.read_text()
            hits.extend((str(path.relative_to(root)), pat) for pat in MOCK_PATTERNS if pat in text)
    return hits
