import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from audit_missing_items import (
    REASON_NO_HINTS,
    classify,
    excluded_dimensions,
    main,
    spec_categories,
    unresolvable_reasons,
)

# Written out here rather than imported: the labels are the product. remediate.sh:111
# copies this section verbatim into the minted debt bead, so a swapped pair ships an
# inverted claim. An assertion sourced from the subject would agree with any wording.
HEADING = "## Missing items (verbatim)"
GAP_HEADING = "### Measured gaps — searched for, and not found"
UNMEASURED_HEADING = "### Not measured — no search ran for these"
GAP_NOTE = "Each line below rests on a search that ran and returned nothing."
UNMEASURED_NOTE = (
    "Each line below is the audit's silence. The gatherer performed no search for the item, "
    "so its absence from the evidence carries no information about the bead. A reader wanting "
    "a verdict on these has to run the phase that measures them."
)

GENUINE_LINE = "- spec item `code.primary` — No file matched any of: src/cairn/nowhere.py"
TESTS_LINE = "- spec item `tests.e2e.primary` — type=e2e desc=e2e test required by bead body"
TELEMETRY_LINE = "- spec item `telemetry.primary` — category=telemetry"
THEATER_LINE = "- theater [BLOCKING] `(bead cairn-x):?` — Closing commit added 1 line(s) to ignore lists"
DOC_LINE = "- spec item `documentation.primary` — category=documentation"
CI_LINE = "- spec item `ci_workflows.primary` — category=ci_workflows"
NAMED_TEST_LINE = "- spec item `tests.unit.test_the_thing` — type=unit desc=named unit test"

TABLE = """## Dimension scores

| Dimension | Score | Max | Why |
|-----------|------:|----:|-----|
| Implementation completeness vs. spec | 0 | 250 | code.primary MISSING |
| Required tests present and meaningfully passing | — | — | EXCLUDED from numerator and denominator — WAIVED — Phase 4 ran in stub mode |
| Anti-theater | 200 | 200 | BLOCKING=0 |
| Test depth | — | — | EXCLUDED from numerator and denominator — WAIVED — Phase 6 ran in stub mode |
| Docs / migrations / telemetry / flags | 0 | 25 | 0/1 non-code items found |
| Cross-bead integration | 25 | 25 | none |
| **TOTAL** | **450** | **1000** | 225 of 500 measured weight, rescaled to 1000 |
"""

PLAIN_TABLE = """## Dimension scores

| Dimension | Score | Max | Why |
|-----------|------:|----:|-----|
| Implementation completeness vs. spec | 0 | 250 | code.primary MISSING |
| Required tests present and meaningfully passing | 100 | 250 | scored |
| Docs / migrations / telemetry / flags | 0 | 25 | 0/2 non-code items found |
| **TOTAL** | **450** | **1000** |  |
"""


def scorecard(items, *, false_closed=False, table=TABLE):
    head = "# Scorecard — cairn-x\n\n**Score: 450 / 1000**\n"
    if false_closed:
        head += "**🚨 FALSE-CLOSED** (status=closed, score=450 < threshold 700)\n"
    return f"{head}\n{table}\n{HEADING}\n\n" + "\n".join(items) + "\n"


def spec(*, code_hints=("src/cairn/nowhere.py",)):
    return {
        "checklist": {
            "code_artifacts": [{"id": "code.primary", "expected_path_hints": list(code_hints)}],
            "tests": {"e2e": [{"id": "tests.e2e.primary"}], "unit": [{"id": "tests.unit.test_the_thing"}]},
            "telemetry": [{"id": "telemetry.primary"}],
            "documentation": [{"id": "documentation.primary"}],
            "ci_workflows": [{"id": "ci_workflows.primary"}],
        }
    }


def bead(tmp_path, items, *, false_closed=False, spec_doc=None, table=TABLE):
    directory = tmp_path / "pass" / "beads" / "cairn-x"
    directory.mkdir(parents=True)
    (directory / "scorecard.md").write_text(scorecard(items, false_closed=false_closed, table=table))
    (directory / "spec.json").write_text(json.dumps(spec_doc or spec()))
    return directory


def sections(text):
    body = text.split(HEADING, 1)[1]
    gap, unmeasured = body.split(UNMEASURED_HEADING, 1)
    return gap.split(GAP_HEADING, 1)[1], unmeasured


def test_the_rendered_section_carries_both_labels_and_both_notes_in_order(tmp_path):
    directory = bead(tmp_path, [GENUINE_LINE, TESTS_LINE])

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 0

    text = (directory / "scorecard.md").read_text()
    for literal in (HEADING, GAP_HEADING, GAP_NOTE, UNMEASURED_HEADING, UNMEASURED_NOTE):
        assert literal in text, literal
    positions = [text.index(x) for x in (HEADING, GAP_HEADING, GAP_NOTE, UNMEASURED_HEADING, UNMEASURED_NOTE)]
    assert positions == sorted(positions)
    assert text.index(GENUINE_LINE) < text.index(UNMEASURED_HEADING)
    assert text.index(TESTS_LINE) > text.index(UNMEASURED_HEADING)


def test_a_searched_for_item_stays_a_gap_and_the_unsearched_ones_move(tmp_path, capsys):
    directory = bead(tmp_path, [GENUINE_LINE, TESTS_LINE, TELEMETRY_LINE])

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 0

    gap, unmeasured = sections((directory / "scorecard.md").read_text())
    assert GENUINE_LINE in gap
    assert TESTS_LINE not in gap
    assert TELEMETRY_LINE not in gap
    assert TESTS_LINE in unmeasured
    assert TELEMETRY_LINE in unmeasured
    assert "REWRITTEN cairn-x" in capsys.readouterr().out


def test_every_original_line_survives_verbatim(tmp_path):
    lines = [GENUINE_LINE, TESTS_LINE, TELEMETRY_LINE, THEATER_LINE]
    directory = bead(tmp_path, lines)

    main([str(directory), "--log", str(tmp_path / "log")])

    rewritten = (directory / "scorecard.md").read_text()
    for line in lines:
        assert f"\n{line}\n" in rewritten


def test_each_unmeasured_item_names_the_reason_no_search_ran(tmp_path):
    directory = bead(tmp_path, [TESTS_LINE, TELEMETRY_LINE])

    main([str(directory), "--log", str(tmp_path / "log")])

    _, unmeasured = sections((directory / "scorecard.md").read_text())
    assert "the tests loop searches only when the item id's last segment differs from 'primary'" in unmeasured
    assert "carries no arm for category 'telemetry'" in unmeasured
    assert REASON_NO_HINTS not in unmeasured
    assert "EXCLUDED from numerator and denominator" in unmeasured


def test_a_false_closed_bead_whose_every_item_is_unresolvable_is_refused(tmp_path, capsys):
    directory = bead(tmp_path, [TESTS_LINE, TELEMETRY_LINE], false_closed=True)

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 1

    out = capsys.readouterr().out
    assert "DEBT-FROM-NOTHING cairn-x" in out
    log = (tmp_path / "log").read_text()
    assert "DENY missing-items debt-from-nothing: cairn-x" in log


def test_a_false_closed_bead_with_one_real_gap_is_allowed(tmp_path):
    directory = bead(tmp_path, [GENUINE_LINE, TESTS_LINE], false_closed=True)

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 0


def test_a_theater_finding_is_a_real_gap_and_holds_the_verdict_open(tmp_path):
    directory = bead(tmp_path, [TESTS_LINE, THEATER_LINE], false_closed=True)

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 0

    gap, _ = sections((directory / "scorecard.md").read_text())
    assert THEATER_LINE in gap


@pytest.mark.parametrize(
    ("label", "items"),
    [
        ("mixed", [GENUINE_LINE, TESTS_LINE, TELEMETRY_LINE]),
        ("all-gaps", [GENUINE_LINE, THEATER_LINE]),
        ("all-unmeasured", [TESTS_LINE, TELEMETRY_LINE]),
    ],
)
def test_a_second_run_changes_nothing(tmp_path, capsys, label, items):
    directory = bead(tmp_path, items)
    main([str(directory), "--log", str(tmp_path / "log")])
    first = (directory / "scorecard.md").read_text()
    capsys.readouterr()

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 0

    assert (directory / "scorecard.md").read_text() == first, label
    assert "UNCHANGED cairn-x" in capsys.readouterr().out
    for line in items:
        assert first.count(line) == 1, line


def test_a_pass_directory_reaches_every_bead_that_has_a_spec(tmp_path, capsys):
    directory = bead(tmp_path, [GENUINE_LINE, TESTS_LINE])
    orphan = directory.parent / "cairn-y"
    orphan.mkdir()
    (orphan / "scorecard.md").write_text(scorecard([TESTS_LINE]))

    assert main([str(directory.parent), "--log", str(tmp_path / "log")]) == 0

    out = capsys.readouterr().out
    assert "cairn-x" in out
    assert "cairn-y" not in out


def test_a_path_holding_no_scorecard_denies(tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()

    assert main([str(empty), "--log", str(tmp_path / "log")]) == 2

    assert "NOTHING-TO-CHECK" in capsys.readouterr().err
    assert "DENY missing-items infra" in (tmp_path / "log").read_text()


def test_no_path_at_all_denies(tmp_path, capsys):
    assert main(["--log", str(tmp_path / "log")]) == 2

    assert "DENY missing-items infra: no path given" in (tmp_path / "log").read_text()
    assert "usage:" in capsys.readouterr().err


def test_the_bypass_is_named_and_logged(tmp_path, monkeypatch, capsys):
    directory = bead(tmp_path, [TESTS_LINE], false_closed=True)
    monkeypatch.setenv("CAIRN_MISSING_ITEMS_SKIP", "proving the bypass is logged")

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 0

    assert "BYPASS missing-items" in (tmp_path / "log").read_text()
    assert "proving the bypass is logged" in capsys.readouterr().err
    assert HEADING + "\n\n- spec item" in (directory / "scorecard.md").read_text()


def test_an_item_with_hints_in_an_unsearched_category_is_still_unresolvable(tmp_path):
    doc = spec()
    doc["checklist"]["telemetry"] = [{"id": "telemetry.primary", "expected_path_hints": ["src/cairn/metrics.py"]}]
    directory = bead(tmp_path, [TELEMETRY_LINE], spec_doc=doc)

    main([str(directory), "--log", str(tmp_path / "log")])

    _, unmeasured = sections((directory / "scorecard.md").read_text())
    assert TELEMETRY_LINE in unmeasured
    assert REASON_NO_HINTS not in unmeasured


def test_a_searched_category_with_no_hints_stays_a_measured_gap(tmp_path):
    directory = bead(tmp_path, [DOC_LINE, CI_LINE], table=PLAIN_TABLE)

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 0

    gap, unmeasured = sections((directory / "scorecard.md").read_text())
    assert DOC_LINE in gap
    assert CI_LINE in gap
    assert DOC_LINE not in unmeasured
    assert CI_LINE not in unmeasured


def test_a_false_closed_bead_missing_only_a_searched_category_item_is_not_debt_from_nothing(tmp_path, capsys):
    directory = bead(tmp_path, [DOC_LINE], false_closed=True, table=PLAIN_TABLE)

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 0

    assert "DEBT-FROM-NOTHING" not in capsys.readouterr().out
    assert "DENY missing-items debt-from-nothing" not in (tmp_path / "log").read_text()


def test_a_test_item_the_ripgrep_guard_admits_stays_a_measured_gap(tmp_path):
    directory = bead(tmp_path, [NAMED_TEST_LINE], table=PLAIN_TABLE)

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 0

    gap, unmeasured = sections((directory / "scorecard.md").read_text())
    assert NAMED_TEST_LINE in gap
    assert NAMED_TEST_LINE not in unmeasured


def test_the_no_hints_reason_reaches_only_the_loop_that_reads_hints():
    for spec_item_id in ("documentation.primary", "ci_workflows.primary", "telemetry.primary", "tests.e2e.primary"):
        reasons = unresolvable_reasons(spec_item_id, spec_categories(spec()), set())
        assert not any("expected_path_hints" in reason for reason in reasons), spec_item_id
    code = unresolvable_reasons("code.primary", spec_categories(spec(code_hints=())), set())
    assert any("expected_path_hints" in reason for reason in code)


def test_a_code_item_with_no_hints_is_unresolvable_rather_than_missing(tmp_path):
    directory = bead(tmp_path, [GENUINE_LINE], spec_doc=spec(code_hints=()))

    main([str(directory), "--log", str(tmp_path / "log")])

    gap, unmeasured = sections((directory / "scorecard.md").read_text())
    assert GENUINE_LINE in unmeasured
    assert GENUINE_LINE not in gap


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ("| Test depth | — | — | EXCLUDED from numerator and denominator — WAIVED |", {"Test depth"}),
        ("| Test depth | 100 | 100 | scored |", set()),
        ("not a table row", set()),
    ],
)
def test_exclusions_come_from_the_table_the_scorecard_printed(row, expected):
    assert excluded_dimensions(row) == expected


def test_a_spec_item_the_checklist_does_not_name_is_left_as_a_gap(tmp_path):
    stray = "- spec item `ghost.primary` — invented"
    items = classify(scorecard([stray]), spec())
    assert [item.unresolvable for item in items] == [False]


@pytest.mark.parametrize(
    ("shape", "line"),
    [
        ("spec item", "- spec item `tests.e2e.primary` — type=e2e desc=e2e test required by bead body"),
        ("check", "- check `tests.e2e.primary` (FAIL) — no passing test found"),
    ],
)
def test_one_id_gets_one_verdict_whichever_producer_wrote_its_line(tmp_path, shape, line):
    directory = bead(tmp_path, [line], false_closed=True)

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 1, shape

    _, unmeasured = sections((directory / "scorecard.md").read_text())
    assert line in unmeasured


def test_a_scorecard_with_no_missing_items_heading_denies(tmp_path, capsys):
    directory = bead(tmp_path, [TESTS_LINE], false_closed=True)
    scorecard_path = directory / "scorecard.md"
    scorecard_path.write_text(scorecard_path.read_text().replace(HEADING, "## Missing items"))
    frozen = scorecard_path.read_text()

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 3

    assert "NO-SECTION cairn-x" in capsys.readouterr().out
    assert "DENY missing-items no-section" in (tmp_path / "log").read_text()
    assert scorecard_path.read_text() == frozen


def test_a_spec_that_does_not_parse_denies(tmp_path, capsys):
    directory = bead(tmp_path, [TESTS_LINE])
    (directory / "spec.json").write_text("{not json")

    assert main([str(directory), "--log", str(tmp_path / "log")]) == 4

    assert "UNREADABLE-SPEC cairn-x" in capsys.readouterr().out
    assert "DENY missing-items unreadable-spec" in (tmp_path / "log").read_text()
