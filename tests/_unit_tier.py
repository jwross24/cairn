import gzip
import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median

import pytest

CALIBRATION_ROOT = Path(__file__).resolve().parents[1] / "research/grounding/unit-tier-calibration-2026-09-08"
CALIBRATION = json.loads((CALIBRATION_ROOT / "calibration.json").read_text())
SLOW_SECONDS = Decimal(CALIBRATION["threshold_seconds"])
SLOW_UNIT_TESTS = frozenset(CALIBRATION["slow_nodeids"])


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    for item in items:
        if item.nodeid in SLOW_UNIT_TESTS:
            item.add_marker(pytest.mark.slow)


def duration_totals(path):
    text = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text()
    passed = re.search(r"(?:^|\n)([1-9]\d*) passed(?:, \d+ warnings?)? in [\d.]+s(?: \([\d:]+\))?\s*\Z", text)
    if "slowest durations" not in text or passed is None:
        raise ValueError(f"{path}: expected a complete passing --durations=0 report")
    totals = defaultdict(Decimal)
    phases = defaultdict(set)
    for seconds, phase, nodeid in re.findall(
        r"^([\d.]+)s (setup|call|teardown)\s+(tests/unit/.+)$", text, re.MULTILINE
    ):
        if phase in phases[nodeid]:
            raise ValueError(f"{path}: duplicate duration phase for {nodeid}")
        totals[nodeid] += Decimal(seconds)
        phases[nodeid].add(phase)
    if not totals:
        raise ValueError(f"{path}: no unit durations recorded")
    if len(totals) != int(passed[1]) or any(value != {"setup", "call", "teardown"} for value in phases.values()):
        raise ValueError(f"{path}: incomplete duration population or phases; use --durations-min=0")
    return dict(totals)


def unit_duration_samples(paths):
    if len({path.resolve() for path in paths}) != len(paths):
        raise ValueError("expected distinct timing reports")
    samples = defaultdict(list)
    for path in paths:
        for nodeid, seconds in duration_totals(path).items():
            samples[nodeid].append(seconds)
    return dict(samples)


def unmarked_slow_tests(paths, marked):
    return {
        nodeid: median(seconds)
        for nodeid, seconds in unit_duration_samples(paths).items()
        if len(seconds) >= 2 and median(seconds) > SLOW_SECONDS and nodeid not in marked
    }
