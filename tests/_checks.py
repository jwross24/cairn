from pathlib import Path

MOCK_PATTERNS = ("unittest.mock", "MagicMock", "mocker.patch")
SCANNED_DIRS = ("tests/integration", "tests/e2e", "tests/conformance")


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


BENCH_BRIEF = "research/grounding/pari-sage-toy-curve-backend.md"
SEA_SEARCH_ABOVE_BITS = 50
CURVE_VECTOR_FIELDS = ("p", "a", "b", "n", "tries")


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []


def bench_tries(root):
    text = (Path(root) / BENCH_BRIEF).read_text()
    section = text[text.index("## 2. Measured") :]
    section = section[: section.index("\n## ", 1)]
    rows = {}
    for line in section.splitlines():
        cells = _cells(line)
        if len(cells) != 4 or not cells[0].isdigit():
            continue
        bits = int(cells[0])
        seeds = [int(s) for s in cells[1].split(",")]
        column = cells[2] if bits <= SEA_SEARCH_ABOVE_BITS else cells[3]
        counts = [int(part.split("/")[0].strip().strip("*")) for part in column.split(",")]
        rows.update(dict(zip(((bits, seed) for seed in seeds), counts, strict=True)))
    return rows


def curve_row(out):
    return (str(out.p), str(out.a), str(out.b), str(out.n), out.tries)


def matches_vector(out, vector):
    return curve_row(out) == tuple(vector[f] for f in CURVE_VECTOR_FIELDS) and [str(c) for c in out.P] == vector["P"]
