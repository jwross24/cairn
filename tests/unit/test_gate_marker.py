import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from gate_marker import DENY, OK, main, marker_path, read_record, verdict, write_record

BEAD = "cairn-m0-e0s.16"
OTHER = "cairn-cue"
PARENT = "04289d27eeb979a1ba3bcdf6f6083c6b5fcde9ce"
GRANDPARENT = "0e560234b1c4a9e0f2d1a7c9b3e8d6f4a2c0b8e6"
TREE = "5a0c1f2b8d4e6a7c9b3f1d2e4a6c8b0d2f4e6a80"
OTHER_TREE = "9f8e7d6c5b4a39281706f5e4d3c2b1a09f8e7d6c"


def record(parent=PARENT, gated=(BEAD,), tree=TREE):
    return {"parent": parent, "tree": tree, "gated": list(gated)}


def test_a_commit_that_closes_nothing_owes_no_gate():
    outcome, reason = verdict(None, [], PARENT)
    assert outcome == OK
    assert "no bead" in reason


def test_a_close_with_no_record_at_all_is_denied():
    outcome, reason = verdict(None, [BEAD], PARENT)
    assert outcome == DENY
    assert BEAD in reason


def test_a_close_the_record_names_on_the_matching_parent_is_allowed():
    outcome, reason = verdict(record(), [BEAD], PARENT, TREE)
    assert outcome == OK
    assert BEAD in reason


def test_a_record_written_against_a_different_parent_vouches_for_nothing():
    """The amend shape: pre-commit records the commit it replaces, and the amended
    commit sits on that commit's own parent instead."""
    outcome, reason = verdict(record(parent=PARENT), [BEAD], GRANDPARENT, TREE)
    assert outcome == DENY
    assert PARENT in reason and GRANDPARENT in reason


def test_a_record_written_over_a_different_tree_vouches_for_nothing():
    """The abandoned-run shape: the gates ran, the commit was never made, and a later
    commit on the same parent closing the same beads carries different content."""
    outcome, reason = verdict(record(tree=TREE), [BEAD], PARENT, OTHER_TREE)
    assert outcome == DENY
    assert TREE in reason and OTHER_TREE in reason


def test_a_record_carrying_no_tree_vouches_for_no_commit_that_has_one():
    outcome, reason = verdict({"parent": PARENT, "gated": [BEAD]}, [BEAD], PARENT, TREE)
    assert outcome == DENY
    assert "(none)" in reason


def test_the_tree_is_compared_after_the_parent_so_a_mismatch_names_the_parent():
    outcome, reason = verdict(record(parent=PARENT, tree=TREE), [BEAD], GRANDPARENT, OTHER_TREE)
    assert outcome == DENY
    assert "sitting on" in reason


def test_a_bead_the_record_does_not_name_is_denied_by_name():
    outcome, reason = verdict(record(gated=[OTHER]), [BEAD, OTHER], PARENT, TREE)
    assert outcome == DENY
    assert BEAD in reason and OTHER not in reason.split(BEAD)[-1]


def test_the_first_commit_in_a_repository_has_no_parent_on_either_side():
    outcome, _ = verdict(record(parent=""), [BEAD], "", TREE)
    assert outcome == OK


def test_a_record_written_and_read_back_carries_the_ids_sorted_and_unique(tmp_path):
    path = marker_path(tmp_path)
    write_record(path, PARENT, [OTHER, BEAD, BEAD], TREE)
    assert read_record(path) == {"parent": PARENT, "tree": TREE, "gated": sorted({BEAD, OTHER})}


@pytest.mark.parametrize("content", ["", "not json at all", '["a list, not a record"]'])
def test_an_unreadable_record_reads_as_no_record(tmp_path, content):
    path = marker_path(tmp_path)
    path.write_text(content)
    assert read_record(path) is None
    assert verdict(read_record(path), [BEAD], PARENT, TREE)[0] == DENY


def test_a_missing_record_file_reads_as_no_record(tmp_path):
    assert read_record(marker_path(tmp_path)) is None


def test_checking_consumes_the_record_so_it_cannot_vouch_for_a_second_commit(tmp_path, capsys):
    path = marker_path(tmp_path)
    write_record(path, PARENT, [BEAD], TREE)

    first = main(["check", "--git-dir", str(tmp_path), "--parent", PARENT, "--tree", TREE, BEAD])
    assert first == 0
    assert capsys.readouterr().out.startswith(OK)
    assert not path.exists()

    second = main(["check", "--git-dir", str(tmp_path), "--parent", PARENT, "--tree", TREE, BEAD])
    assert second == 1
    assert capsys.readouterr().out.startswith(DENY)


def test_the_record_subcommand_writes_what_check_reads(tmp_path, capsys):
    assert main(["record", "--git-dir", str(tmp_path), "--parent", PARENT, "--tree", TREE, BEAD, OTHER]) == 0
    capsys.readouterr()
    assert json.loads(marker_path(tmp_path).read_text())["gated"] == sorted([BEAD, OTHER])
    assert main(["check", "--git-dir", str(tmp_path), "--parent", PARENT, "--tree", TREE, BEAD, OTHER]) == 0


def test_a_record_that_cannot_be_written_is_reported_rather_than_assumed(tmp_path, capsys):
    blocked = tmp_path / "file-not-a-directory"
    blocked.write_text("")
    assert main(["record", "--git-dir", str(blocked), "--parent", PARENT, "--tree", TREE, BEAD]) == 2
    assert "cannot write" in capsys.readouterr().err
