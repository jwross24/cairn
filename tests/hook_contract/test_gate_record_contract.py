"""What the two hooks do, driven through real `git commit` in a throwaway repository."""

from __future__ import annotations

import json
import shutil

import pytest
from conftest import BEAD_ROW

BEAD = "cairn-zzz"


def stage_close(scratch, evidence: str = "A\n") -> None:
    scratch.write(".beads/issues.jsonl", BEAD_ROW.format(status="closed"))
    scratch.write("evidence.txt", evidence)
    scratch.git("add", "-A")


def test_a_gated_close_is_recorded_and_the_record_names_the_staged_tree(scratch):
    stage_close(scratch)
    result = scratch.run_hook("pre-commit")
    assert result.returncode == 0, result.stdout + result.stderr

    record = json.loads(scratch.marker().read_text())
    assert record["gated"] == [BEAD]
    assert record["parent"] == scratch.git("rev-parse", "HEAD").stdout.strip()
    assert record["tree"] == scratch.git("write-tree").stdout.strip()
    assert f"GATE-RECORD {BEAD}" in scratch.hook_log()


def test_post_commit_consumes_the_record_and_pushes_the_close(scratch):
    stage_close(scratch)
    committed = scratch.commit("close a bead")
    assert committed.returncode == 0, committed.stdout + committed.stderr

    assert not scratch.marker().exists()
    head = scratch.git("rev-parse", "HEAD").stdout.strip()
    assert head in scratch.origin_shas()
    assert "PUSHED post-commit" in scratch.check_log()


def test_an_abandoned_gate_run_does_not_vouch_for_a_later_no_verify_commit(scratch):
    """The hole the tree closes: the gates ran over one tree, that commit was never
    made, and a different tree is committed on the same parent closing the same bead."""
    stage_close(scratch, evidence="gated\n")
    gated = scratch.run_hook("pre-commit")
    assert gated.returncode == 0, gated.stdout + gated.stderr
    assert scratch.marker().exists()

    scratch.write("evidence.txt", "never gated\n")
    scratch.git("add", "-A")
    committed = scratch.commit("close a bead", "--no-verify")
    assert committed.returncode == 0, committed.stdout + committed.stderr

    assert scratch.origin_shas() == [scratch.git("rev-parse", "HEAD^").stdout.strip()]
    assert "DENY post-commit push" in scratch.check_log()
    assert "the gate record was written over the tree" in scratch.check_log()


def test_the_same_tree_gated_and_then_committed_unverified_is_still_vouched_for(scratch):
    """The tree is the claim, so a commit whose content the gates did see is allowed
    even though `--no-verify` skipped the second run."""
    stage_close(scratch)
    assert scratch.run_hook("pre-commit").returncode == 0
    committed = scratch.commit("close a bead", "--no-verify")
    assert committed.returncode == 0, committed.stdout + committed.stderr
    assert scratch.git("rev-parse", "HEAD").stdout.strip() in scratch.origin_shas()


def test_a_close_amended_onto_a_gated_commit_is_denied(scratch):
    stage_close(scratch)
    assert scratch.commit("close a bead").returncode == 0
    pushed = scratch.git("rev-parse", "HEAD").stdout.strip()

    scratch.write("evidence.txt", "amended\n")
    scratch.git("add", "-A")
    amended = scratch.commit("close a bead, amended", "--amend", "--no-verify")
    assert amended.returncode == 0, amended.stdout + amended.stderr

    assert scratch.git("rev-parse", "HEAD").stdout.strip() not in scratch.origin_shas()
    assert pushed in scratch.origin_shas()
    assert "DENY post-commit push" in scratch.check_log()


def test_a_commit_closing_no_bead_is_gated_but_never_pushed(scratch):
    scratch.write("evidence.txt", "a slice\n")
    scratch.git("add", "-A")
    committed = scratch.commit("a slice")
    assert committed.returncode == 0, committed.stdout + committed.stderr

    assert scratch.git("rev-parse", "HEAD").stdout.strip() not in scratch.origin_shas()
    assert "SKIP post-commit push" in scratch.check_log()


def test_a_resolver_that_cannot_read_git_denies_the_commit(scratch):
    """The empty-stdout hazard: a resolver that failed and a commit that closes nothing
    print the same thing, and the branch that separates them lives in the hook."""
    stage_close(scratch)
    scratch.write("scripts/closing_commit.py", "import sys\nsys.exit(3)\n")
    result = scratch.run_hook("pre-commit")

    assert result.returncode == 1
    assert "exited 3" in result.stderr
    assert "DENY closing-commit resolver rc=3" in scratch.hook_log()
    assert not scratch.marker().exists()


def test_an_attribution_corrector_that_cannot_read_git_denies_the_commit(scratch):
    stage_close(scratch)
    scratch.write("scripts/audit_attribution.py", "import sys\nsys.exit(3)\n")
    result = scratch.run_hook("pre-commit")

    assert result.returncode == 1
    assert "ATTRIBUTION-DENY git could not answer" in scratch.hook_log()
    assert "no score here is evidence" in result.stderr
    assert not scratch.marker().exists()


@pytest.mark.parametrize(
    ("rc", "expected"),
    [(1, "ATTRIBUTION rc=1"), (2, "ATTRIBUTION-NOTHING rc=2")],
)
def test_the_attribution_verdict_the_hook_acts_on_is_the_correctors(scratch, rc, expected):
    stage_close(scratch)
    scratch.write("scripts/audit_attribution.py", f"import sys\nsys.exit({rc})\n")
    result = scratch.run_hook("pre-commit")

    assert expected in scratch.hook_log()
    assert result.returncode == (1 if rc == 1 else 0)
    assert scratch.marker().exists() is (rc != 1)


def test_a_missing_compliance_skill_records_the_gate_and_says_so(scratch):
    stage_close(scratch)
    scratch.write("scripts/audit_attribution.py", "import sys\nsys.exit(0)\n")
    shutil.rmtree(scratch.path / ".claude")

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "NO-SKILL beads compliance gate did not run" in scratch.hook_log()
    assert json.loads(scratch.marker().read_text())["gated"] == [BEAD]


def test_a_reverted_fork_marker_denies_rather_than_scoring_on_defaults(scratch):
    stage_close(scratch)
    skill = scratch.path / ".claude" / "skills" / "beads-compliance-and-completion-verification"
    (skill / "scripts" / "score-bead.py").write_text("nothing the hook looks for\n")

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1
    assert "FORK-REVERTED the n/a-is-a-measurement split" in scratch.hook_log()
    assert not scratch.marker().exists()
