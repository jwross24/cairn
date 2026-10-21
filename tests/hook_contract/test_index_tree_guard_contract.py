from __future__ import annotations

import pytest
from conftest import SKILL_REL

STAGING_AUDIT = "#!/usr/bin/env bash\nprintf 'stray\\n' > stray.txt\ngit add stray.txt\nexit 0\n"
REWRITING_AUDIT = "#!/usr/bin/env bash\nprintf 'rewritten\\n' > evidence.txt\ngit add evidence.txt\nexit 0\n"
BYPASS = "CAIRN_AUDIT_INDEX_OK"


def stage_evidence(scratch) -> None:
    scratch.write("evidence.txt", "staged\n")
    scratch.git("add", "evidence.txt")


def install_audit(scratch, body: str) -> None:
    scratch.write(f"{SKILL_REL}/assets/pre-commit-hook.sh", body)


def test_an_audit_that_stages_a_file_is_denied_and_named(scratch):
    stage_evidence(scratch)
    install_audit(scratch, STAGING_AUDIT)
    before = scratch.git("write-tree").stdout.strip()

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "the compliance audit changed the index" in result.stderr
    assert "A\tstray.txt" in result.stderr
    assert "DENY index-changed-by-audit" in scratch.check_log()
    assert not scratch.marker().exists()
    assert before != scratch.git("write-tree").stdout.strip()


def test_a_commit_through_git_is_refused_when_the_audit_stages(scratch):
    stage_evidence(scratch)
    install_audit(scratch, STAGING_AUDIT)
    head = scratch.git("rev-parse", "HEAD").stdout.strip()

    committed = scratch.commit("slice")
    assert committed.returncode != 0
    assert scratch.git("rev-parse", "HEAD").stdout.strip() == head


def test_an_audit_that_rewrites_a_staged_path_is_denied(scratch):
    stage_evidence(scratch)
    install_audit(scratch, REWRITING_AUDIT)

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "M\tevidence.txt" in result.stderr


def test_an_audit_that_leaves_the_index_alone_is_allowed_and_logged(scratch):
    stage_evidence(scratch)

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ALLOW index-unchanged-by-audit" in scratch.check_log()
    assert scratch.marker().exists()


def test_the_named_bypass_allows_and_is_logged_with_its_reason(scratch):
    stage_evidence(scratch)
    install_audit(scratch, STAGING_AUDIT)

    result = scratch.run_hook("pre-commit", {BYPASS: "planted for the contract"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "BYPASS index-changed-by-audit: planted for the contract" in scratch.check_log()


def test_a_missing_guard_script_denies_rather_than_skipping(scratch):
    stage_evidence(scratch)
    (scratch.path / "scripts" / "index_tree_guard.py").unlink()

    result = scratch.run_hook("pre-commit")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "the index tree could not be recorded before the audit" in result.stderr


@pytest.mark.parametrize("marker", ["index_tree_guard.py capture", "index_tree_guard.py check --before"])
def test_the_hook_wires_both_halves(marker):
    from conftest import ROOT

    assert marker in (ROOT / ".githooks" / "pre-commit").read_text()
