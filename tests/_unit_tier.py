import gzip
import re
from collections import defaultdict
from decimal import Decimal
from statistics import median

import pytest

SLOW_SECONDS = 5.0
SLOW_UNIT_TESTS = frozenset(
    {
        "tests/unit/test_formal_statement_hasher.py::test_lean_canonicalization_known_answer",
        "tests/unit/test_justify_properties.py::test_mr_w_then_mr_a_still_names_the_assumption",
    }
)


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    for item in items:
        if item.nodeid in SLOW_UNIT_TESTS:
            item.add_marker(pytest.mark.slow)


def duration_totals(path):
    text = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text()
    passed = re.search(r"^[1-9]\d* passed(?:, \d+ warnings?)? in [\d.]+s", text, re.MULTILINE)
    if "slowest durations" not in text or passed is None:
        raise ValueError(f"{path}: expected a complete passing --durations=0 report")
    totals = defaultdict(Decimal)
    for seconds, nodeid in re.findall(r"^([\d.]+)s (?:setup|call|teardown)\s+(tests/unit/\S+)$", text, re.MULTILINE):
        totals[nodeid] += Decimal(seconds)
    if not totals:
        raise ValueError(f"{path}: no unit durations recorded")
    return {nodeid: float(seconds) for nodeid, seconds in totals.items()}


def unmarked_slow_tests(paths, marked):
    samples = defaultdict(list)
    for path in paths:
        for nodeid, seconds in duration_totals(path).items():
            samples[nodeid].append(seconds)
    return {
        nodeid: median(seconds)
        for nodeid, seconds in samples.items()
        if median(seconds) > SLOW_SECONDS and nodeid not in marked
    }
