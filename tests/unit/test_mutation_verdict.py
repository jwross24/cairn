import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from mutation_verdict import INCONCLUSIVE, KILLED, SURVIVED, main, red_count, summary_line, verdict

COLLECTION_ERROR = """ERROR tests/unit/test_thing.py - StopIteration
!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!
1 error in 0.04s
"""

PASSING = """.............
13 passed in 4.21s
"""

FAILING = """F............
1 failed, 12 passed in 4.44s
"""

NO_TESTS_COLLECTED = """no tests ran in 0.01s
"""

USAGE_ERROR = """ERROR: file or directory not found: tests/unit/test_a.py tests/unit/test_b.py
"""


@pytest.mark.parametrize(
    ("output", "returncode", "expected"),
    [
        (FAILING, 1, KILLED),
        ("", 1, KILLED),
        (COLLECTION_ERROR, 2, KILLED),
        ("2 errors in 0.10s\n", 2, KILLED),
        ("INTERNALERROR> RuntimeError\n", 3, INCONCLUSIVE),
        (USAGE_ERROR, 4, INCONCLUSIVE),
        ("", 4, INCONCLUSIVE),
        (NO_TESTS_COLLECTED, 5, INCONCLUSIVE),
        (PASSING, 0, SURVIVED),
        ("", 0, SURVIVED),
    ],
)
def test_a_red_count_kills_a_run_that_never_happened_is_inconclusive_and_green_survives(output, returncode, expected):
    got, message = verdict(output, returncode)
    assert got == expected, message
    assert message.startswith(expected), message


def test_the_three_verdicts_are_three_different_process_exit_codes(monkeypatch):
    codes = {}
    for output, returncode in ((FAILING, 1), (USAGE_ERROR, 4), (PASSING, 0)):
        monkeypatch.setattr(sys, "stdin", io.StringIO(output))
        codes[verdict(output, returncode)[0]] = main([str(returncode)])
    assert len(set(codes.values())) == 3
    assert codes[KILLED] == 0


def test_a_run_that_collected_no_tests_is_never_reported_as_a_detection():
    outcome, message = verdict(NO_TESTS_COLLECTED, 5)
    assert outcome == INCONCLUSIVE
    assert "KILLED" not in message
    assert "without testing the mutation" in message


def test_a_collection_error_names_its_count_rather_than_reading_as_undetected():
    outcome, message = verdict(COLLECTION_ERROR, 2)
    assert outcome == KILLED
    assert "by 1 test(s)" in message
    assert "1 error in 0.04s" in message


def test_a_nonzero_exit_with_no_summary_says_which_code_it_saw():
    outcome, message = verdict("", 1)
    assert outcome == KILLED
    assert "pytest exited 1" in message
    assert "no recognized pytest summary line" in message


def test_the_summary_is_the_last_matching_line_not_an_earlier_echo():
    output = "captured stdout: 9 failed\n0 selected\n7 passed in 1.00s\n"
    assert summary_line(output) == "7 passed in 1.00s"
    assert red_count(summary_line(output)) == 0


def test_mixed_counts_sum_only_the_red_ones():
    assert red_count("2 failed, 1 error, 10 passed in 3.00s") == 3


def test_main_maps_the_verdict_onto_the_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(PASSING))
    assert main(["0"]) == 1
    assert "SURVIVED" in capsys.readouterr().out

    monkeypatch.setattr(sys, "stdin", io.StringIO(COLLECTION_ERROR))
    assert main(["2"]) == 0
    assert "KILLED" in capsys.readouterr().out


def test_main_refuses_a_missing_or_unparsable_return_code(capsys):
    assert main([]) == 2
    assert "usage:" in capsys.readouterr().err
    assert main(["banana"]) == 2
    assert "not a return code" in capsys.readouterr().err
