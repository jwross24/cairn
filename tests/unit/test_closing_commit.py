import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import closing_commit
from closing_commit import STAGED, UNKNOWN, GitError, closings, history_closings, newly_closed, resolve

BEAD = "cairn-m0-e0s.16"
CLOSING_SHA = "04289d27eeb979a1ba3bcdf6f6083c6b5fcde9ce"
MENTIONING_SHA = "dcbe2080d0f7cbb3b8f0b7f1cf0b8a1ba6e5e5c1"
LATER_SHA = "0e560234b1c4a9e0f2d1a7c9b3e8d6f4a2c0b8e6"


def bead_line(bead_id: str, status: str) -> str:
    return f'{{"id":"{bead_id}","title":"t","description":"d","status":"{status}"}}'


def chunk(sha: str, lines: list[str]) -> str:
    header = [
        "diff --git a/.beads/issues.jsonl b/.beads/issues.jsonl",
        "--- a/.beads/issues.jsonl",
        "+++ b/.beads/issues.jsonl",
    ]
    return "\x00" + sha + "\n" + "\n".join(header + lines) + "\n"


def log(*chunks: str) -> str:
    return "".join(chunks)


def closed_here(bead_id: str) -> list[str]:
    return ["@@ -1 +1 @@", "-" + bead_line(bead_id, "open"), "+" + bead_line(bead_id, "closed")]


def already_closed_here(bead_id: str) -> list[str]:
    """The shape a later `br` write leaves: the bead's row rewritten, its status unmoved."""
    return ["-" + bead_line(bead_id, "closed"), "+" + bead_line(bead_id, "closed")]


def touched_here(bead_id: str) -> list[str]:
    return ["@@ -1 +1 @@", "-" + bead_line(bead_id, "open"), "+" + bead_line(bead_id, "in_progress")]


def newest_mentioning(history: list[tuple[str, str]], bead_id: str) -> str:
    """The rule under correction: the newest commit whose message names the bead id."""
    for sha, message in history:
        if bead_id in message:
            return sha
    return UNKNOWN


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (closed_here(BEAD), [BEAD]),
        (touched_here(BEAD), []),
        (["+" + bead_line(BEAD, "closed")], [BEAD]),
        (["-" + bead_line(BEAD, "closed"), "+" + bead_line(BEAD, "open")], []),
        (["-" + bead_line(BEAD, "closed"), "+" + bead_line(BEAD, "closed")], []),
        ([" " + bead_line(BEAD, "closed")], []),
        (["+++ b/" + bead_line(BEAD, "closed")], []),
    ],
)
def test_only_a_status_flip_to_closed_counts_as_a_close(lines, expected):
    assert newly_closed("\n".join(lines)) == expected


def file_header(name: str) -> list[str]:
    return [f"diff --git a/.beads/{name} b/.beads/{name}", f"--- a/.beads/{name}", f"+++ b/.beads/{name}"]


def test_a_second_store_file_holding_the_row_unchanged_does_not_erase_the_close():
    diff = "\n".join(
        file_header("issues.jsonl") + closed_here(BEAD) + file_header("archive.jsonl") + already_closed_here(BEAD)
    )
    assert newly_closed(diff) == [BEAD]


@pytest.mark.parametrize("failing", ["log", "diff", "show"])
def test_a_git_that_fails_raises_rather_than_reporting_no_bead_closed(monkeypatch, failing):
    monkeypatch.setattr(
        closing_commit.subprocess,
        "run",
        lambda argv, **kw: subprocess.CompletedProcess(argv, 128, "", "fatal: bad object HEAD"),
    )
    readers = {
        "log": closing_commit.git_history_reader(Path(".")),
        "diff": closing_commit.git_staged_reader(Path(".")),
        "show": closing_commit.git_commit_reader(Path("."), "does-not-exist-ref"),
    }
    with pytest.raises(GitError, match="128"):
        readers[failing]()


def test_the_history_reader_looks_at_every_branch_not_only_the_current_one(monkeypatch):
    seen = []
    monkeypatch.setattr(
        closing_commit.subprocess,
        "run",
        lambda argv, **kw: seen.append(argv) or subprocess.CompletedProcess(argv, 0, "", ""),
    )
    closing_commit.git_history_reader(Path("."))()
    assert "--all" in seen[0]


def test_two_beads_closed_in_one_diff_both_come_back_sorted():
    diff = "\n".join(closed_here("cairn-b") + closed_here("cairn-a"))
    assert newly_closed(diff) == ["cairn-a", "cairn-b"]


def test_the_commit_that_closed_the_bead_is_the_one_whose_store_line_flipped():
    text = log(
        chunk(LATER_SHA, touched_here("cairn-other")),
        chunk(CLOSING_SHA, closed_here(BEAD)),
    )
    assert history_closings(text)[BEAD] == CLOSING_SHA


def test_a_reclose_wins_over_the_earlier_close_of_the_same_bead():
    text = log(
        chunk(LATER_SHA, closed_here(BEAD)),
        chunk(MENTIONING_SHA, touched_here(BEAD)),
        chunk(CLOSING_SHA, closed_here(BEAD)),
    )
    assert history_closings(text)[BEAD] == LATER_SHA


def test_a_bead_the_pending_commit_closes_resolves_to_staged_over_its_history():
    text = log(chunk(CLOSING_SHA, closed_here(BEAD)))
    assert closings(text, "\n".join(closed_here(BEAD)))[BEAD] == STAGED
    assert closings(text, "")[BEAD] == CLOSING_SHA


def test_a_bead_no_commit_ever_closed_resolves_to_nothing():
    assert history_closings(log(chunk(CLOSING_SHA, touched_here(BEAD)))) == {}


def test_a_commit_that_only_names_the_bead_is_not_its_closing_commit():
    """The bead's own reproduction, inverted: the message-grep pick is not the closer."""
    messages = [
        (MENTIONING_SHA, "give the audit a switch that can fail a false close\n\nSeen on " + BEAD),
        (CLOSING_SHA, "close " + BEAD),
    ]
    text = log(
        chunk(MENTIONING_SHA, closed_here("cairn-us2")),
        chunk(CLOSING_SHA, closed_here(BEAD)),
    )
    assert newest_mentioning(messages, BEAD) == MENTIONING_SHA
    assert history_closings(text)[BEAD] == CLOSING_SHA


def test_an_unrelated_later_commit_naming_the_bead_moves_the_grep_rule_and_not_this_one():
    before = log(chunk(CLOSING_SHA, closed_here(BEAD)))
    after = log(
        chunk(LATER_SHA, closed_here("cairn-cue") + already_closed_here(BEAD)),
        chunk(CLOSING_SHA, closed_here(BEAD)),
    )
    messages_before = [(CLOSING_SHA, "close " + BEAD)]
    messages_after = [(LATER_SHA, "close cairn-cue\n\nthe scorer it names is " + BEAD), *messages_before]

    assert newest_mentioning(messages_before, BEAD) != newest_mentioning(messages_after, BEAD)
    assert history_closings(before)[BEAD] == history_closings(after)[BEAD] == CLOSING_SHA


def test_resolve_reads_history_and_the_staged_diff_through_its_two_seams():
    resolved = resolve(
        Path("."),
        history=lambda: log(chunk(CLOSING_SHA, closed_here(BEAD))),
        staged=lambda: "\n".join(closed_here("cairn-pending")),
    )
    assert resolved == {BEAD: CLOSING_SHA, "cairn-pending": STAGED}
    assert resolved.get("cairn-absent", UNKNOWN) == UNKNOWN
