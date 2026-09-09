import ast
import hashlib
import importlib
import re
import runpy
import shlex
from decimal import Decimal
from pathlib import Path
from statistics import median

import pytest
from _unit_tier import (
    CALIBRATION,
    CALIBRATION_ROOT,
    SLOW_SECONDS,
    SLOW_UNIT_TESTS,
    duration_totals,
    unit_duration_samples,
    unmarked_slow_tests,
)

ROOT = Path(__file__).resolve().parents[2]


def test_bead_store_consumer_modules_match_every_direct_import():
    namespace = runpy.run_path(str(ROOT / "tests/conftest.py"))
    consumers = {
        path.name
        for path in (ROOT / "tests").rglob("*.py")
        if path.name != "conftest.py"
        and any(
            isinstance(node, ast.ImportFrom)
            and node.module == "_bead_store"
            and any(alias.name == "bead_store" for alias in node.names)
            for node in ast.walk(ast.parse(path.read_text()))
        )
    }
    assert consumers == namespace["BEAD_STORE_CONSUMER_MODULES"]


def _install_warm_hook(pytester):
    pytester.makeconftest(
        f"import runpy\npytest_collection_finish = runpy.run_path({str(ROOT / 'tests/conftest.py')!r})"
        '["pytest_collection_finish"]\n'
    )


def _consumer_module(pytester, source):
    directory = pytester.path / "warm_cases"
    directory.mkdir()
    (directory / "test_br_lookup.py").write_text(source)


def test_unrelated_selection_leaves_the_bead_store_cache_untouched(pytester):
    _install_warm_hook(pytester)
    store = importlib.import_module("_bead_store").bead_store
    before = store.cache_info()
    pytester.makepyfile(test_unrelated="def test_ok():\n    assert True\n")
    result = pytester.runpytest("-q", "--import-mode=importlib")
    result.assert_outcomes(passed=1)
    assert store.cache_info() == before
    assert "[unit-tier] bead-store warm" not in result.stdout.str()


def test_collect_only_leaves_the_bead_store_cache_untouched(pytester):
    _install_warm_hook(pytester)
    store = importlib.import_module("_bead_store").bead_store
    before = store.cache_info()
    _consumer_module(pytester, "def test_ok():\n    assert True\n")
    result = pytester.runpytest("-q", "--collect-only", "--import-mode=importlib")
    assert result.ret == 0
    assert store.cache_info() == before
    assert "[unit-tier] bead-store warm" not in result.stdout.str()


def test_consumer_selection_warms_the_real_store_before_the_test(pytester):
    importlib.import_module("test_br_lookup")
    _install_warm_hook(pytester)
    store = importlib.import_module("_bead_store").bead_store
    before = store.cache_info()
    _consumer_module(
        pytester,
        "import importlib\ndef test_ready():\n"
        '    assert importlib.import_module("_bead_store").bead_store.cache_info().currsize == 1\n',
    )
    result = pytester.runpytest("-q", "--import-mode=importlib")
    result.assert_outcomes(passed=1)
    after = store.cache_info()
    assert after.hits + after.misses == before.hits + before.misses + 1
    assert re.search(r"\[unit-tier\] bead-store warm \d+\.\d{6}s", result.stdout.str())


def test_bead_store_warm_failure_stops_the_session_loudly(pytester, monkeypatch):
    _install_warm_hook(pytester)

    def unavailable():
        raise RuntimeError("planted store import failure")

    monkeypatch.setattr(importlib.import_module("_bead_store"), "bead_store", unavailable)
    _consumer_module(pytester, "def test_must_not_run():\n    assert False\n")
    result = pytester.runpytest("-q", "--import-mode=importlib")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    assert "bead-store warm failed: planted store import failure" in result.stderr.str()


def test_unit_gate_selects_only_unmarked_units_with_a_duration_table():
    lines = (ROOT / "scripts" / "check.sh").read_text().splitlines()
    gate = next(line for line in lines if line.strip().startswith("gate unit-tests "))
    assert shlex.split(gate) == [
        "gate",
        "unit-tests",
        "uv",
        "run",
        "pytest",
        "tests/unit",
        "-q",
        "-m",
        "not slow",
        "--durations=10",
    ]


def test_marker_selection_keeps_the_measured_slow_test_in_the_full_run(pytester):
    importlib.import_module("test_formal_statement_hasher")
    pytester.makeconftest('pytest_plugins = ["_unit_tier"]')
    pytester.makeini("[pytest]\nmarkers = slow: measured unit duration above the calibrated tier threshold\n")
    directory = pytester.path / "tests" / "unit"
    directory.mkdir(parents=True)
    (directory / "test_formal_statement_hasher.py").write_text(
        "def test_lean_canonicalization_known_answer():\n    assert True\ndef test_quick():\n    assert True\n"
    )
    selected = pytester.runpytest("-q", "-m", "not slow", "-p", "no:cacheprovider", "--import-mode=importlib")
    selected.assert_outcomes(passed=1, deselected=1)
    complete = pytester.runpytest("-q", "-p", "no:cacheprovider", "--import-mode=importlib")
    complete.assert_outcomes(passed=2)


def test_recorded_unit_durations_have_no_unmarked_slow_tests():
    reports = [CALIBRATION_ROOT / item["path"] for item in CALIBRATION["reports"]]
    for path, item in zip(reports, CALIBRATION["reports"], strict=True):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    samples = unit_duration_samples(reports)
    assert {node: len(values) for node, values in samples.items()} == CALIBRATION["sample_counts"]
    unmeasured = {node for node, values in samples.items() if len(values) < 2}
    assert unmeasured == set(CALIBRATION["unmeasured_nodeids"])
    assert not unmeasured & SLOW_UNIT_TESTS
    medians = {node: median(values) for node, values in samples.items() if len(values) >= 2}
    assert len(medians) == CALIBRATION["measured_count"]
    assert {node for node, seconds in medians.items() if seconds > SLOW_SECONDS} == SLOW_UNIT_TESTS
    retained = {node: seconds for node, seconds in medians.items() if seconds <= SLOW_SECONDS}
    total = sum(retained.values())
    assert len(retained) == CALIBRATION["retained_count"]
    assert total == Decimal(CALIBRATION["retained_median_sum_seconds"])
    budget = Decimal(CALIBRATION["budget_seconds"])
    assert total <= budget <= 55
    assert SLOW_SECONDS in medians.values()
    next_threshold = min(seconds for seconds in medians.values() if seconds > SLOW_SECONDS)
    assert sum(seconds for seconds in medians.values() if seconds <= next_threshold) > budget
    assert unmarked_slow_tests(reports, SLOW_UNIT_TESTS) == {}
    planted = max(medians, key=medians.__getitem__)
    assert unmarked_slow_tests(reports, SLOW_UNIT_TESTS - {planted}) == {planted: medians[planted]}


def _report(path, entries):
    lines = ["slowest durations"]
    for node, seconds in entries.items():
        lines.extend((f"0.00s setup {node}", f"{seconds}s call {node}", f"0.00s teardown {node}"))
    lines.append(f"{len(entries)} passed in 10.00s")
    path.write_text("\n".join(lines) + "\n")
    return path


def test_a_real_report_with_a_skipped_test_refuses(pytester):
    directory = pytester.path / "tests" / "unit"
    directory.mkdir(parents=True)
    (directory / "test_report.py").write_text(
        "import pytest\ndef test_pass():\n    assert True\n"
        'def test_skip():\n    pytest.skip("planted unavailable dependency")\n'
    )
    result = pytester.runpytest("tests/unit", "-q", "--durations=0", "--durations-min=0", "-p", "no:cacheprovider")
    result.assert_outcomes(passed=1, skipped=1)
    report = pytester.path / "durations.log"
    report.write_text(result.stdout.str())
    with pytest.raises(ValueError, match="expected a complete passing"):
        duration_totals(report)


def test_unmarked_slow_test_is_rejected_from_a_scratch_report(tmp_path):
    node = "tests/unit/test_planted.py::test_slow"
    seconds = SLOW_SECONDS + Decimal("0.01")
    reports = [_report(tmp_path / f"{index}.log", {node: seconds}) for index in range(2)]
    assert unmarked_slow_tests(reports, frozenset()) == {node: seconds}
    assert unmarked_slow_tests(reports, {node}) == {}


def test_slow_budget_uses_the_median_and_a_strict_threshold(tmp_path):
    node = "tests/unit/test_sample.py::test_case"
    reports = [
        _report(tmp_path / f"{index}.log", {node: seconds})
        for index, seconds in enumerate((SLOW_SECONDS * 2, SLOW_SECONDS, SLOW_SECONDS / 2))
    ]
    assert unmarked_slow_tests(reports, frozenset()) == {}


def test_parameter_ids_with_spaces_keep_every_duration_phase(tmp_path):
    node = "tests/unit/test_sample.py::test_case[has space]"
    report = _report(tmp_path / "report.log", {node: Decimal("0.10")})
    report.write_text(
        report.read_text().replace("0.00s setup", "0.02s setup").replace("0.00s teardown", "0.03s teardown")
    )
    assert duration_totals(report) == {node: Decimal("0.15")}


def test_single_observations_remain_unmeasured_and_duplicate_reports_refuse(tmp_path):
    node = "tests/unit/test_sample.py::test_case"
    report = _report(tmp_path / "report.log", {node: SLOW_SECONDS * 2})
    assert unit_duration_samples([report]) == {node: [SLOW_SECONDS * 2]}
    assert unmarked_slow_tests([report], frozenset()) == {}
    with pytest.raises(ValueError, match="distinct"):
        unmarked_slow_tests([report, report], frozenset())


@pytest.mark.parametrize("defect", ["count", "phase", "duplicate"])
def test_incomplete_or_duplicated_phase_populations_refuse(tmp_path, defect):
    node = "tests/unit/test_sample.py::test_case"
    report = _report(tmp_path / "report.log", {node: Decimal("0.10")})
    text = report.read_text()
    if defect == "count":
        text = text.replace("1 passed", "2 passed")
    elif defect == "phase":
        text = text.replace(f"0.00s teardown {node}\n", "")
    else:
        text = text.replace(f"0.00s setup {node}\n", f"0.00s setup {node}\n" * 2)
    report.write_text(text)
    with pytest.raises(ValueError, match=r"incomplete duration|duplicate duration"):
        duration_totals(report)


@pytest.mark.parametrize(
    "text",
    [
        "slowest durations\n6.00s call tests/unit/test_x.py::test_x\nTimeout (0:01:00)!\n",
        "slowest 25 durations\n6.00s call tests/unit/test_x.py::test_x\n1 passed in 6.00s\n",
        "slowest durations\n1 passed in 6.00s\n",
        "slowest durations\n1 passed in 6.00s\n1 failed, 1 passed in 7.00s\n",
    ],
)
def test_incomplete_or_empty_timing_reports_refuse(tmp_path, text):
    report = tmp_path / "durations.log"
    report.write_text(text)
    with pytest.raises(ValueError, match=r"expected a complete|no unit durations"):
        duration_totals(report)
