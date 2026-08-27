import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from mutation_verdict import main, red_count, summary_line, verdict

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


@pytest.mark.parametrize(
    ("output", "returncode", "killed"),
    [
        (FAILING, 1, True),
        (COLLECTION_ERROR, 2, True),
        ("2 errors in 0.10s\n", 2, True),
        ("INTERNALERROR> RuntimeError\n", 3, True),
        ("", 4, True),
        (PASSING, 0, False),
        ("", 0, False),
    ],
)
def test_a_red_run_is_killed_and_only_an_all_green_one_survives(output, returncode, killed):
    got, message = verdict(output, returncode)
    assert got is killed, message
    assert message.startswith("KILLED" if killed else "SURVIVED"), message


def test_a_collection_error_names_its_count_rather_than_reading_as_undetected():
    killed, message = verdict(COLLECTION_ERROR, 2)
    assert killed
    assert "by 1 test(s)" in message
    assert "1 error in 0.04s" in message


def test_a_nonzero_exit_with_no_summary_says_which_code_it_saw():
    killed, message = verdict("", 3)
    assert killed
    assert "pytest exited 3" in message
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
