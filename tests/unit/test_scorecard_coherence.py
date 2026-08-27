import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from scorecard_coherence import check_scorecard, main

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "scorecard_coherence.py"
CHILD_TIMEOUT_S = 60

HEADER = "| Dimension | Score | Max | Why |\n|-----------|------:|----:|-----|"


def card(score, rows, denominator=None, banner=None, total_why=""):
    out = ["# Scorecard — x\n", f"**Score: {score} / 1000**", "**Verdict: x**"]
    if denominator:
        out.append(f"**Denominator:** {denominator}")
    if banner:
        out.append(f"**⚠ DETERMINISTIC-ONLY PASS:** {banner}")
    out += ["\n## Dimension scores\n", HEADER]
    out += [f"| {name} | {s} | {m} | why |" for name, s, m in rows]
    out.append(f"| **TOTAL** | **{score}** | **1000** | {total_why} |")
    return "\n".join(out) + "\n"


RESCALED_ROWS: list[tuple[str, Any, Any]] = [
    ("Implementation completeness vs. spec", 175, 250),
    ("Required tests present and meaningfully passing", "—", "—"),
    ("Anti-theater", 200, 200),
    ("Test depth", "—", "—"),
    ("Docs / migrations / telemetry / flags", "—", "—"),
    ("Cross-bead integration", 25, 25),
]
RESCALED_NOTE = (
    "scored over the 475 of 1000 weight measured (400/475), rescaled; unmeasured: docs_etc, test_depth, tests"
)
EXCLUDED_BANNER = (
    "Phase 4 (Required tests) ran in stub mode. Under unmeasured_dimensions=excluded those dimensions carry no credit."
)


def coherent_rescaled():
    return card(842, RESCALED_ROWS, RESCALED_NOTE, EXCLUDED_BANNER, "400 of 475 measured weight, rescaled to 1000")


def test_rescaled_scorecard_is_coherent():
    assert check_scorecard(coherent_rescaled()) == []


def test_unverifiable_scorecard_is_coherent():
    rows = [
        ("Implementation completeness vs. spec", "—", "—"),
        ("Required tests present and meaningfully passing", "—", "—"),
        ("Anti-theater", 200, 200),
        ("Test depth", "—", "—"),
        ("Docs / migrations / telemetry / flags", "—", "—"),
        ("Cross-bead integration", 25, 25),
    ]
    note = (
        "UNVERIFIABLE — only 225 of 1000 weight was measured, below the 450 this "
        "project requires. Unmeasured: docs_etc, implementation, test_depth, tests."
    )
    text = card(
        0,
        rows,
        note,
        EXCLUDED_BANNER,
        "UNVERIFIABLE — 225 of 1000 weight measured, below the 450 floor; no score is issued",
    )
    assert check_scorecard(text) == []


def test_fully_measured_scorecard_needs_no_denominator():
    rows = [
        ("Implementation completeness vs. spec", 250, 250),
        ("Required tests present and meaningfully passing", 300, 300),
        ("Anti-theater", 200, 200),
        ("Test depth", 200, 200),
        ("Docs / migrations / telemetry / flags", 25, 25),
        ("Cross-bead integration", 25, 25),
    ]
    assert check_scorecard(card(1000, rows)) == []


def test_full_credit_table_over_an_excluded_denominator_is_refused():
    """The shape the gate was misreporting: rows awarded in full, weight excluded."""
    rows = [
        ("Implementation completeness vs. spec", 175, 250),
        ("Required tests present and meaningfully passing", 300, 300),
        ("Anti-theater", 200, 200),
        ("Test depth", 200, 200),
        ("Docs / migrations / telemetry / flags", 25, 25),
        ("Cross-bead integration", 0, 25),
    ]
    banner = (
        "Phase 4 (Required tests), Phase 6 (Test depth) ran in stub mode; those dimensions are WAIVED with full credit."
    )
    problems = check_scorecard(card(789, rows, RESCALED_NOTE, banner))
    assert any("no row is marked excluded" in p for p in problems)
    assert any("the scored rows total 1000" in p for p in problems)
    assert any("the scored rows total 900" in p for p in problems)


def test_banner_claiming_full_credit_beside_excluded_rows_is_refused():
    banner = "Phase 4 (Required tests) ran in stub mode; those dimensions are WAIVED with full credit."
    text = card(842, RESCALED_ROWS, RESCALED_NOTE, banner, "400 of 475 measured weight, rescaled to 1000")
    assert any("WAIVED with full credit" in p for p in check_scorecard(text))


def test_headline_score_must_match_the_total_row():
    text = coherent_rescaled().replace("**Score: 842 / 1000**", "**Score: 900 / 1000**")
    assert any("disagrees with the TOTAL row" in p for p in check_scorecard(text))


def test_rescaled_arithmetic_must_hold():
    text = (
        coherent_rescaled()
        .replace("**Score: 842 / 1000**", "**Score: 800 / 1000**")
        .replace("| **TOTAL** | **842** |", "| **TOTAL** | **800** |")
    )
    assert any("rescales to 842, not the reported 800" in p for p in check_scorecard(text))


def test_denominator_numerator_must_match_the_scored_rows():
    text = coherent_rescaled().replace("(400/475)", "(375/475)")
    assert any("says 375 measured points; the scored rows total 400" in p for p in check_scorecard(text))


def test_denominator_weight_must_match_the_scored_rows():
    text = coherent_rescaled().replace(
        "the 475 of 1000 weight measured (400/475)", "the 500 of 1000 weight measured (400/500)"
    )
    assert any("says 500 of measured weight; the scored rows total 475" in p for p in check_scorecard(text))


def test_unverifiable_denominator_forbids_a_nonzero_total():
    rows = [("Anti-theater", 200, 200), ("Cross-bead integration", 25, 25)]
    note = "UNVERIFIABLE — only 225 of 1000 weight was measured, below the 450 this project requires."
    assert any("but the TOTAL row reports 700" in p for p in check_scorecard(card(700, rows, note)))


def test_half_excluded_row_is_refused():
    rows = list(RESCALED_ROWS)
    rows[1] = ("Required tests present and meaningfully passing", 300, "—")
    text = card(842, rows, RESCALED_NOTE, EXCLUDED_BANNER)
    assert any("half-excluded" in p for p in check_scorecard(text))


def test_row_scoring_above_its_max_is_refused():
    rows = list(RESCALED_ROWS)
    rows[2] = ("Anti-theater", 300, 200)
    assert any("scores 300 out of 200" in p for p in check_scorecard(card(842, rows, RESCALED_NOTE, EXCLUDED_BANNER)))


def test_excluded_rows_without_a_denominator_are_refused():
    text = card(842, RESCALED_ROWS, None, EXCLUDED_BANNER)
    assert any("no **Denominator:** line says so" in p for p in check_scorecard(text))


def test_unrecognized_denominator_note_is_refused():
    text = card(842, RESCALED_ROWS, "scored somehow", EXCLUDED_BANNER)
    assert any("unrecognized" in p for p in check_scorecard(text))


def test_missing_total_row_is_refused():
    text = coherent_rescaled().replace("| **TOTAL** | **842** | **1000** |", "| TOTAL | 842 | 1000 |")
    assert any("no **TOTAL** row" in p for p in check_scorecard(text))


@pytest.mark.parametrize("argv", [[], ["/nonexistent/path/for/this/test"]])
def test_cli_refuses_when_there_is_nothing_to_check(argv):
    assert main(argv) == 2


def test_cli_exits_nonzero_on_an_incoherent_card(tmp_path):
    good, bad = tmp_path / "a", tmp_path / "b"
    good.mkdir()
    bad.mkdir()
    (good / "scorecard.md").write_text(coherent_rescaled())
    (bad / "scorecard.md").write_text(coherent_rescaled().replace("(400/475)", "(375/475)"))
    assert main([str(good)]) == 0
    assert main([str(tmp_path)]) == 1


def test_script_runs_as_a_subprocess(tmp_path):
    (tmp_path / "scorecard.md").write_text(coherent_rescaled())
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path)], capture_output=True, text=True, timeout=CHILD_TIMEOUT_S
    )
    assert done.returncode == 0
    assert "COHERENT" in done.stdout
