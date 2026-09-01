"""One test per refusal the two hooks can issue, driven through the real shell.

Each gate the scratch repository cannot satisfy honestly is driven by replacing the
script the hook calls with one that exits the code under test. The subject here is the
branch in bash that reads that code, and the Python behind each exit code has its own
coverage in `tests/unit`.
"""

from __future__ import annotations

import pytest
from conftest import BEAD_ROW

BEAD = "cairn-zzz"
PASS_NAME = "2026-01-01T000000Z"
EXITS = "import sys\nsys.exit({rc})\n"


def stage_close(scratch) -> None:
    scratch.write(".beads/issues.jsonl", BEAD_ROW.format(status="closed"))
    scratch.write("evidence.txt", "closing\n")
    scratch.git("add", "-A")


def with_pass_dir(scratch) -> None:
    (scratch.path / "beads_compliance_audit" / "passes" / PASS_NAME / "beads").mkdir(parents=True)


def test_a_failing_check_sh_blocks_and_records_no_gate(scratch):
    stage_close(scratch)
    scratch.write("scripts/check.sh", "#!/usr/bin/env bash\nexit 1\n")
    (scratch.path / "scripts" / "check.sh").chmod(0o755)

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1
    assert "BLOCKED by scripts/check.sh" in result.stderr
    assert not scratch.marker().exists()


def test_a_check_sh_that_is_not_executable_refuses_rather_than_committing_blind(scratch):
    stage_close(scratch)
    (scratch.path / "scripts" / "check.sh").chmod(0o644)

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1
    assert "refusing to commit blind" in result.stderr
    assert not scratch.marker().exists()


def test_a_failing_test_plan_gate_blocks_the_close(scratch):
    stage_close(scratch)
    scratch.write("scripts/bead-test-plan.sh", "#!/usr/bin/env bash\nexit 1\n")
    (scratch.path / "scripts" / "bead-test-plan.sh").chmod(0o755)

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1
    assert "names a test file that is absent or empty" in result.stderr
    assert not scratch.marker().exists()


def test_a_failing_artifact_block_gate_blocks_the_close(scratch):
    stage_close(scratch)
    scratch.write("scripts/bead-artifact-block.sh", "#!/usr/bin/env bash\nexit 1\n")
    (scratch.path / "scripts" / "bead-artifact-block.sh").chmod(0o755)

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1
    assert "carries no valid ARTIFACTS block" in result.stderr
    assert not scratch.marker().exists()


def test_a_blocking_doctor_gate_names_the_store_rather_than_a_low_score(scratch):
    stage_close(scratch)
    scratch.write("scripts/beads_doctor_gate.py", EXITS.format(rc=2))

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1
    assert "This is not a low score" in result.stderr
    assert not scratch.marker().exists()


@pytest.mark.parametrize(
    "marker",
    [
        "scripts/sync-rubric-from-policy.py",
        "scripts/bootstrap-audit.sh",
        "scripts/inventory-beads.sh",
    ],
)
def test_each_fork_marker_the_hook_names_denies_on_its_own(scratch, marker):
    stage_close(scratch)
    skill = scratch.path / ".claude" / "skills" / "beads-compliance-and-completion-verification"
    (skill / marker).unlink()

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1
    assert "FORK-REVERTED" in scratch.hook_log()
    assert not scratch.marker().exists()


def test_a_bootstrap_audit_that_keeps_the_sync_call_is_still_read_for_the_corruption_predicate(scratch):
    stage_close(scratch)
    skill = scratch.path / ".claude" / "skills" / "beads-compliance-and-completion-verification"
    (skill / "scripts" / "bootstrap-audit.sh").write_text("sync-rubric-from-policy.py\n")

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1
    assert "FORK-REVERTED the corruption predicate" in scratch.hook_log()


def test_a_reverted_fork_can_be_bypassed_by_name_and_the_bypass_is_logged(scratch):
    stage_close(scratch)
    skill = scratch.path / ".claude" / "skills" / "beads-compliance-and-completion-verification"
    (skill / "scripts" / "score-bead.py").write_text("nothing the hook looks for\n")

    result = scratch.run_hook("pre-commit", {"CAIRN_AUDIT_FORK_OK": "hook-contract tier"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "BYPASS fork check: hook-contract tier" in scratch.hook_log()
    assert scratch.marker().exists()


def test_a_policy_that_names_no_threshold_leaves_the_skill_default_and_says_so(scratch):
    stage_close(scratch)
    (scratch.path / "audit-policy.yaml").unlink()

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "THRESHOLD-UNREAD" in scratch.hook_log()
    assert "runs at the skill's default" in result.stderr


def test_the_threshold_the_audit_runs_at_comes_from_the_policy_file(scratch):
    stage_close(scratch)
    (scratch.path / "audit-policy.yaml").write_text("threshold: 815\n")

    assert scratch.run_hook("pre-commit").returncode == 0
    assert "THRESHOLD 815 from audit-policy.yaml" in scratch.hook_log()


def test_a_skill_audit_that_fails_denies_when_the_corrector_supplies_no_verdict(scratch):
    stage_close(scratch)
    result = scratch.run_hook("pre-commit", {"FAKE_SKILL_AUDIT_RC": "1"})

    assert result.returncode == 1
    assert "ATTRIBUTION-NOTHING" in scratch.hook_log()
    assert not scratch.marker().exists()


def test_a_corrector_verdict_of_zero_clears_a_failing_skill_audit(scratch):
    stage_close(scratch)
    scratch.write("scripts/audit_attribution.py", EXITS.format(rc=0))

    result = scratch.run_hook("pre-commit", {"FAKE_SKILL_AUDIT_RC": "1"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ATTRIBUTION rc=0 (skill audit rc=1)" in scratch.hook_log()
    assert scratch.marker().exists()


def test_a_coherent_scorecard_and_a_separated_missing_item_list_let_the_close_through(scratch):
    stage_close(scratch)
    with_pass_dir(scratch)
    scratch.write("scripts/scorecard_coherence.py", EXITS.format(rc=0))
    scratch.write("scripts/audit_missing_items.py", EXITS.format(rc=0))

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"SCORECARD-COHERENT beads_compliance_audit/passes/{PASS_NAME}/" in scratch.hook_log()
    assert "MISSING-ITEMS-SEPARATED" in scratch.hook_log()


def test_a_scorecard_that_disagrees_with_its_own_arithmetic_blocks(scratch):
    stage_close(scratch)
    with_pass_dir(scratch)
    scratch.write("scripts/scorecard_coherence.py", EXITS.format(rc=1))
    scratch.write("scripts/audit_missing_items.py", EXITS.format(rc=0))

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1
    assert "SCORECARD-INCOHERENT" in scratch.hook_log()
    assert "disagrees with its own arithmetic" in result.stderr


def test_an_incoherent_scorecard_can_be_bypassed_by_the_same_named_switch(scratch):
    stage_close(scratch)
    with_pass_dir(scratch)
    scratch.write("scripts/scorecard_coherence.py", EXITS.format(rc=1))
    scratch.write("scripts/audit_missing_items.py", EXITS.format(rc=0))

    result = scratch.run_hook("pre-commit", {"CAIRN_AUDIT_FORK_OK": "hook-contract tier"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "BYPASS scorecard coherence: hook-contract tier" in scratch.hook_log()


@pytest.mark.parametrize(
    ("rc", "expected"),
    [
        (1, "MISSING-ITEMS-DEBT-FROM-NOTHING"),
        (3, "MISSING-ITEMS-NO-SECTION"),
        (4, "MISSING-ITEMS-UNREADABLE-SPEC "),
        (5, "MISSING-ITEMS-UNREADABLE-SCORECARD"),
        (6, "MISSING-ITEMS-UNREADABLE-SPEC-FILE"),
        (7, "MISSING-ITEMS-SPEC-NOT-AN-OBJECT"),
        (9, "MISSING-ITEMS-DENY rc=9"),
    ],
)
def test_every_missing_items_outcome_reaches_the_log_under_its_own_name(scratch, rc, expected):
    stage_close(scratch)
    with_pass_dir(scratch)
    scratch.write("scripts/scorecard_coherence.py", EXITS.format(rc=0))
    scratch.write("scripts/audit_missing_items.py", EXITS.format(rc=rc))

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1
    assert expected in scratch.hook_log()
    assert not scratch.marker().exists()


def test_the_push_bypass_is_named_and_logged(scratch):
    stage_close(scratch)
    committed = scratch.commit("close a bead", extra_env={"CAIRN_PUSH_SKIP": "hook-contract tier"})
    assert committed.returncode == 0, committed.stdout + committed.stderr

    assert "BYPASS post-commit push: hook-contract tier" in scratch.check_log()
    assert scratch.git("rev-parse", "HEAD").stdout.strip() not in scratch.origin_shas()


def test_post_commit_separates_a_resolver_failure_from_a_commit_that_closes_nothing(scratch):
    stage_close(scratch)
    assert scratch.run_hook("pre-commit").returncode == 0
    scratch.write("scripts/closing_commit.py", EXITS.format(rc=3))
    committed = scratch.commit("close a bead", "--no-verify")
    assert committed.returncode == 0, committed.stdout + committed.stderr

    assert "DENY post-commit push: closing-commit resolver rc=3" in scratch.check_log()
    assert scratch.git("rev-parse", "HEAD").stdout.strip() not in scratch.origin_shas()


def test_a_close_with_no_remote_to_push_to_says_the_close_is_local(scratch):
    stage_close(scratch)
    scratch.git("remote", "remove", "origin")
    committed = scratch.commit("close a bead")
    assert committed.returncode == 0, committed.stdout + committed.stderr

    assert "DENY post-commit push: no origin remote" in scratch.check_log()


def test_a_push_that_fails_is_loud_and_leaves_the_commit_local(scratch):
    stage_close(scratch)
    scratch.git("remote", "set-url", "origin", str(scratch.origin.parent / "not-a-repository.git"))
    committed = scratch.commit("close a bead")
    assert committed.returncode == 0, committed.stdout + committed.stderr

    assert "DENY post-commit push: git push failed" in scratch.check_log()
    assert "PUSH FAILED" in committed.stderr
    assert scratch.origin_shas() != []
