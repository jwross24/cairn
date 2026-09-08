import importlib
import shlex
from pathlib import Path

import pytest
from _unit_tier import SLOW_UNIT_TESTS, duration_totals, unmarked_slow_tests

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "research" / "grounding" / "ci-runtime-2026-09-08"


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
    pytester.makeini("[pytest]\nmarkers = slow: measured unit wall time above five seconds\n")
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
    reports = [EVIDENCE / name for name in ("unit-before.log.gz", "slow-repeat-2.log", "slow-repeat-3.log")]
    assert unmarked_slow_tests(reports, SLOW_UNIT_TESTS) == {}
    assert unmarked_slow_tests(reports, frozenset())


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
    report = tmp_path / "durations.log"
    report.write_text(
        "================ slowest durations ================\n"
        "4.90s call     tests/unit/test_planted.py::test_slow\n"
        "0.11s setup    tests/unit/test_planted.py::test_slow\n"
        "1 passed in 5.02s\n"
    )
    assert unmarked_slow_tests([report], frozenset()) == {"tests/unit/test_planted.py::test_slow": 5.01}
    assert unmarked_slow_tests([report], {"tests/unit/test_planted.py::test_slow"}) == {}


def test_slow_budget_uses_the_median_and_a_strict_five_second_boundary(tmp_path):
    reports = []
    for index, seconds in enumerate((9, 5, 1)):
        report = tmp_path / f"{index}.log"
        report.write_text(
            f"slowest durations\n{seconds:.2f}s call     tests/unit/test_sample.py::test_case\n1 passed in 10.00s\n"
        )
        reports.append(report)
    assert unmarked_slow_tests(reports, frozenset()) == {}


@pytest.mark.parametrize(
    "text",
    [
        "slowest durations\n6.00s call tests/unit/test_x.py::test_x\nTimeout (0:01:00)!\n",
        "slowest 25 durations\n6.00s call tests/unit/test_x.py::test_x\n1 passed in 6.00s\n",
        "slowest durations\n1 passed in 6.00s\n",
    ],
)
def test_incomplete_or_empty_timing_reports_refuse(tmp_path, text):
    report = tmp_path / "durations.log"
    report.write_text(text)
    with pytest.raises(ValueError, match=r"expected a complete|no unit durations"):
        duration_totals(report)
