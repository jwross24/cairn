from __future__ import annotations

import pytest
from conftest import ROOT

FAILING_CHECK = "#!/usr/bin/env bash\nexit 1\n"


def diverge(scratch) -> str:
    scratch.git("checkout", "-q", "-b", "side")
    scratch.write("side.txt", "side\n")
    scratch.git("add", "side.txt")
    assert scratch.commit("side change", "--no-verify").returncode == 0
    scratch.git("checkout", "-q", "main")
    scratch.write("main.txt", "main\n")
    scratch.git("add", "main.txt")
    assert scratch.commit("main change", "--no-verify").returncode == 0
    return scratch.git("rev-parse", "HEAD").stdout.strip()


def merge(scratch):
    return scratch.git("merge", "--no-ff", "-m", "merge side", "side", check=False)


def test_a_merge_whose_result_fails_the_gate_is_refused(scratch):
    head = diverge(scratch)
    scratch.write("scripts/check.sh", FAILING_CHECK)
    (scratch.path / "scripts" / "check.sh").chmod(0o755)

    merged = merge(scratch)
    assert merged.returncode != 0, merged.stdout + merged.stderr
    assert scratch.git("rev-parse", "HEAD").stdout.strip() == head
    assert "BLOCKED by scripts/check.sh" in merged.stderr
    assert "DENY pre-merge-commit" in scratch.check_log()


def test_a_clean_merge_lands_and_leaves_a_trace(scratch):
    head = diverge(scratch)

    merged = merge(scratch)
    assert merged.returncode == 0, merged.stdout + merged.stderr
    assert scratch.git("rev-parse", "HEAD^1").stdout.strip() == head
    assert "ALLOW pre-merge-commit" in scratch.check_log()


def test_no_verify_bypasses_the_merge_gate(scratch):
    diverge(scratch)
    scratch.write("scripts/check.sh", FAILING_CHECK)
    (scratch.path / "scripts" / "check.sh").chmod(0o755)

    merged = scratch.git("merge", "--no-ff", "--no-verify", "-m", "merge side", "side", check=False)
    assert merged.returncode == 0, merged.stdout + merged.stderr


def test_a_missing_pre_commit_hook_denies_the_merge(scratch):
    head = diverge(scratch)
    (scratch.path / ".githooks" / "pre-commit").unlink()

    merged = merge(scratch)
    assert merged.returncode != 0, merged.stdout + merged.stderr
    assert scratch.git("rev-parse", "HEAD").stdout.strip() == head
    assert "DENY pre-merge-commit: .githooks/pre-commit is missing" in scratch.check_log()


@pytest.mark.parametrize("name", ["pre-commit", "pre-merge-commit"])
def test_both_hooks_ship_executable(name):
    hook = ROOT / ".githooks" / name
    assert hook.is_file()
    assert hook.stat().st_mode & 0o111
