import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from audit_attribution import (
    ClosingDiff,
    correct,
    correct_pass,
    count_ignore_adds,
    passes_after,
    prior_pass,
    rederive,
)
from closing_commit import STAGED, UNKNOWN, history_closings

BEAD = "cairn-m0-e0s.16"
CLOSING_SHA = "04289d27eeb979a1ba3bcdf6f6083c6b5fcde9ce"
MENTIONING_SHA = "dcbe2080d0f7cbb3b8f0b7f1cf0b8a1ba6e5e5c1"
LATER_SHA = "0e560234b1c4a9e0f2d1a7c9b3e8d6f4a2c0b8e6"

MISATTRIBUTED = {
    "id": "anomaly.1",
    "severity": "BLOCKING",
    "category": "anomaly_ignore_list_growth",
    "path": f"(bead {BEAD})",
    "line": 0,
    "snippet": "(see show.json)",
    "description": "Closing commit added 1 line(s) to ignore lists — possible silencing instead of fixing",
}
UNRELATED = {
    "id": "theater.1",
    "severity": "MAJOR",
    "category": "assertion_free_test",
    "path": "tests/unit/test_thing.py",
    "line": 12,
    "snippet": "assert True",
    "description": "a test that asserts nothing",
}


def theater(*findings):
    summary = {"BLOCKING": 0, "MAJOR": 0, "MINOR": 0, "NOTE": 0}
    for finding in findings:
        summary[finding["severity"]] += 1
    return {"bead_id": BEAD, "scanned_files": [], "findings": list(findings), "summary": summary}


def bead_line(bead_id: str, status: str) -> str:
    return f'{{"id":"{bead_id}","title":"t","status":"{status}"}}'


def git_chunk(sha: str, lines: list[str]) -> str:
    return "\x00" + sha + "\n--- a/.beads/issues.jsonl\n+++ b/.beads/issues.jsonl\n" + "\n".join(lines) + "\n"


def closing_chunk(sha: str, bead_id: str) -> str:
    return git_chunk(sha, ["-" + bead_line(bead_id, "open"), "+" + bead_line(bead_id, "closed")])


def mentioning_chunk(sha: str, closes: str, mentions: str) -> str:
    """A later commit that closes some other bead and rewrites this one's row unchanged."""
    return git_chunk(
        sha,
        [
            "-" + bead_line(closes, "open"),
            "+" + bead_line(closes, "closed"),
            "-" + bead_line(mentions, "closed"),
            "+" + bead_line(mentions, "closed"),
        ],
    )


@pytest.mark.parametrize(
    ("diff", "categories"),
    [
        (ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=0), []),
        (ClosingDiff(CLOSING_SHA, files_changed=0, ignore_adds=0), ["anomaly_empty_diff"]),
        (ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=3), ["anomaly_ignore_list_growth"]),
        (
            ClosingDiff(CLOSING_SHA, files_changed=0, ignore_adds=1),
            ["anomaly_empty_diff", "anomaly_ignore_list_growth"],
        ),
        (None, []),
    ],
)
def test_each_attributed_pattern_is_rederived_from_the_closing_diff_alone(diff, categories):
    assert [f["category"] for f in rederive(diff)] == categories


def test_a_raised_finding_names_the_commit_it_was_judged_against():
    (finding,) = rederive(ClosingDiff(STAGED, files_changed=4, ignore_adds=2))
    assert STAGED in finding["description"]
    assert "2 line(s)" in finding["description"]


@pytest.mark.parametrize(
    ("diff_text", "count"),
    [
        ("+.beads_hook.log\n", 1),
        ("+++ b/.gitignore\n+one\n+two\n", 2),
        ("+\n", 0),
        ("-removed\n context\n", 0),
        ("", 0),
    ],
)
def test_added_lines_are_counted_the_way_the_scanner_counts_them(diff_text, count):
    assert count_ignore_adds(diff_text) == count


def test_a_finding_raised_against_another_beads_commit_is_dropped():
    corrected, notes = correct(
        theater(MISATTRIBUTED), BEAD, CLOSING_SHA, ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=0)
    )
    assert corrected["findings"] == []
    assert corrected["summary"]["BLOCKING"] == 0
    assert notes == ["dropped 1 finding(s) raised against a commit the bead did not close"]
    assert corrected["commit_attribution"]["closing_commit"] == CLOSING_SHA


def test_a_finding_true_of_the_beads_own_closing_commit_is_reraised():
    corrected, _ = correct(
        theater(MISATTRIBUTED), BEAD, CLOSING_SHA, ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=1)
    )
    (kept,) = corrected["findings"]
    assert kept["category"] == "anomaly_ignore_list_growth"
    assert kept["severity"] == "BLOCKING"
    assert CLOSING_SHA in kept["description"]
    assert corrected["summary"]["BLOCKING"] == 1


def test_a_pattern_the_scanner_missed_is_raised_against_the_right_commit():
    corrected, notes = correct(
        theater(UNRELATED), BEAD, CLOSING_SHA, ClosingDiff(CLOSING_SHA, files_changed=0, ignore_adds=0)
    )
    assert [f["category"] for f in corrected["findings"]] == ["assertion_free_test", "anomaly_empty_diff"]
    assert notes == [f"raised 1 finding(s) against {CLOSING_SHA}"]


def test_findings_the_patterns_do_not_own_survive_the_correction():
    corrected, _ = correct(theater(MISATTRIBUTED, UNRELATED), BEAD, CLOSING_SHA, ClosingDiff(CLOSING_SHA, 7, 0))
    assert corrected["findings"] == [UNRELATED]
    assert corrected["summary"] == {"BLOCKING": 0, "MAJOR": 1, "MINOR": 0, "NOTE": 0}


def test_a_bead_no_commit_closed_carries_neither_attributed_pattern():
    corrected, _ = correct(theater(MISATTRIBUTED), BEAD, UNKNOWN, None)
    assert corrected["findings"] == []
    assert corrected["commit_attribution"]["closing_commit"] == UNKNOWN


def test_anomaly_ids_are_renumbered_so_two_findings_never_share_one():
    second = dict(MISATTRIBUTED, id="anomaly.1", category="anomaly_empty_diff", severity="MAJOR")
    corrected, _ = correct(theater(second), BEAD, CLOSING_SHA, ClosingDiff(CLOSING_SHA, 0, 2))
    ids = [f["id"] for f in corrected["findings"]]
    assert ids == ["anomaly.1", "anomaly.2"]


@pytest.mark.parametrize(
    ("after", "expected"),
    [
        (None, ["a", "b", "c"]),
        ("a", ["b", "c"]),
        ("c", []),
    ],
)
def test_only_passes_opened_after_the_marker_are_corrected(after, expected):
    assert passes_after(["c", "a", "b"], after) == expected


def test_the_prior_pass_is_the_newest_one_that_is_not_this_one():
    assert prior_pass(["a", "b", "c"], "c") == "b"
    assert prior_pass(["a"], "a") is None


def test_the_commit_being_made_is_read_from_the_staged_diff_and_not_from_history(monkeypatch):
    import audit_attribution

    seen = []

    def fake_git(_root, args):
        seen.append(args[0])
        return "+one\n" if "--cached" in args and "--" in args else ".gitignore\nsrc/a.py\n"

    monkeypatch.setattr(audit_attribution, "_git", fake_git)
    diff = audit_attribution.git_closing_diff_reader(Path())(STAGED)
    assert seen == ["diff", "diff"]
    assert diff == ClosingDiff(label="(staged)", files_changed=2, ignore_adds=1)


def test_a_commit_already_in_history_is_read_with_show(monkeypatch):
    import audit_attribution

    seen = []

    def fake_git(_root, args):
        seen.append(args[0])
        return "" if "--" in args else "src/a.py\n"

    monkeypatch.setattr(audit_attribution, "_git", fake_git)
    diff = audit_attribution.git_closing_diff_reader(Path())(CLOSING_SHA)
    assert seen == ["show", "show"]
    assert diff == ClosingDiff(label=CLOSING_SHA, files_changed=1, ignore_adds=0)


def test_a_bead_no_commit_closed_asks_git_nothing(monkeypatch):
    import audit_attribution

    monkeypatch.setattr(audit_attribution, "_git", lambda *a: pytest.fail("git was consulted"))
    assert audit_attribution.git_closing_diff_reader(Path())(UNKNOWN) is None


def write_pass(tmp_path, findings):
    pass_dir = tmp_path / "passes" / "2026-08-26T16-29-01Z"
    bead_dir = pass_dir / "beads" / BEAD
    bead_dir.mkdir(parents=True)
    (bead_dir / "theater.json").write_text(json.dumps(theater(*findings), indent=2) + "\n")
    (bead_dir / "spec.json").write_text(json.dumps({"bead_id": BEAD, "items": []}))
    (bead_dir / "show.json").write_text(json.dumps({"id": BEAD, "status": "closed"}))
    return pass_dir, bead_dir


def anti_theater_score(bead_dir, _synthesis, _prior):
    """Stands in for score-bead.py, whose only input from the corrector is theater.json."""
    summary = json.loads((bead_dir / "theater.json").read_text())["summary"]
    total = 1000 - 350 * summary["BLOCKING"] - 15 * summary["MAJOR"]
    return {"bead_id": bead_dir.name, "score": total, "false_closed": total < 700}


# The two shas a mutated flip-vs-mention rule can pick between: the bead's own
# closing commit is clean, while the later commit that merely rewrites its row is an
# empty diff that grew an ignore list, and scores 635 against a threshold of 700.
DIFF_BY_SHA = {
    CLOSING_SHA: ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=0),
    LATER_SHA: ClosingDiff(LATER_SHA, files_changed=0, ignore_adds=5),
}


def run_correction(pass_dir, log_text):
    resolutions = history_closings(log_text)
    return correct_pass(
        pass_dir,
        resolutions=resolutions,
        diff_for=lambda resolution: DIFF_BY_SHA.get(resolution),
        score=anti_theater_score,
        prior=None,
    )


def test_the_corrected_verdict_does_not_move_when_an_unrelated_commit_lands(tmp_path):
    pass_dir, bead_dir = write_pass(tmp_path, [MISATTRIBUTED])
    uncorrected = (bead_dir / "theater.json").read_text()
    history = closing_chunk(CLOSING_SHA, BEAD)

    first = run_correction(pass_dir, history)
    theater_after_first = (bead_dir / "theater.json").read_text()

    (bead_dir / "theater.json").write_text(uncorrected)
    grown = (
        mentioning_chunk(LATER_SHA, closes="cairn-cue", mentions=BEAD)
        + mentioning_chunk(MENTIONING_SHA, closes="cairn-us2", mentions=BEAD)
        + history
    )
    second = run_correction(pass_dir, grown)

    assert [verdict.split(" → ")[-1] for _, verdict, _ in first] == ["score 1000"]
    assert [v.split(" → ")[-1] for _, v, _ in second] == ["score 1000"]
    assert (bead_dir / "theater.json").read_text() == theater_after_first


def test_a_bead_no_commit_closed_is_reported_unresolved_and_keeps_no_attributed_finding(tmp_path):
    pass_dir, bead_dir = write_pass(tmp_path, [MISATTRIBUTED])
    ((bead_id, verdict, _),) = run_correction(pass_dir, closing_chunk(CLOSING_SHA, "cairn-other"))
    written = json.loads((bead_dir / "theater.json").read_text())
    assert bead_id == BEAD
    assert verdict.startswith("UNRESOLVED")
    assert written["findings"] == []
    assert written["commit_attribution"]["closing_commit"] == UNKNOWN


def test_the_scorers_false_closed_flag_is_what_the_verdict_reports(tmp_path):
    pass_dir, _ = write_pass(tmp_path, [MISATTRIBUTED])
    results = correct_pass(
        pass_dir,
        resolutions={BEAD: CLOSING_SHA},
        diff_for=lambda _r: ClosingDiff(CLOSING_SHA, files_changed=0, ignore_adds=9),
        score=anti_theater_score,
        prior=None,
    )
    assert [failed for _, _, failed in results] == [True]


@pytest.mark.parametrize("absent", ["spec.json", "show.json", "theater.json"])
def test_a_bead_dir_the_pass_never_scored_is_left_alone(tmp_path, absent):
    pass_dir, bead_dir = write_pass(tmp_path, [MISATTRIBUTED])
    (bead_dir / absent).unlink()
    assert run_correction(pass_dir, closing_chunk(CLOSING_SHA, BEAD)) == []
