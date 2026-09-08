"""Which paths the pre-commit gate is given, driven through the real hook."""

from __future__ import annotations

RECORDER = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$(dirname "$0")/../check-argv.txt"
exit ${FAKE_CHECK_RC:-0}
"""


def recording_check(scratch):
    path = scratch.write("scripts/check.sh", RECORDER)
    path.chmod(0o755)
    return path


def argv(scratch):
    recorded = scratch.path / "check-argv.txt"
    return recorded.read_text().split() if recorded.exists() else []


def test_the_gate_is_given_the_paths_the_commit_stages(scratch):
    recording_check(scratch)
    scratch.write("staged.py", "x = 1\n")
    scratch.git("add", "staged.py")

    result = scratch.run_hook("pre-commit")

    assert result.returncode == 0, result.stdout + result.stderr
    assert argv(scratch) == ["--fast", "--paths", "staged.py"]


def test_a_file_the_commit_does_not_touch_is_not_in_the_gate_s_scope(scratch):
    recording_check(scratch)
    scratch.write("staged.py", "x = 1\n")
    scratch.git("add", "staged.py")
    scratch.write("another_lane.py", "import os\n")

    result = scratch.run_hook("pre-commit")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "another_lane.py" not in argv(scratch)


def test_a_deleted_path_is_left_out_so_the_gate_is_not_handed_a_file_that_is_gone(scratch):
    recording_check(scratch)
    scratch.git("rm", "-q", "evidence.txt")

    result = scratch.run_hook("pre-commit")

    assert result.returncode == 0, result.stdout + result.stderr
    assert argv(scratch) == ["--fast"]


def test_an_index_that_stages_nothing_takes_the_tree_wide_form_rather_than_an_empty_scope(scratch):
    recording_check(scratch)

    result = scratch.run_hook("pre-commit")

    assert result.returncode == 0, result.stdout + result.stderr
    assert argv(scratch) == ["--fast"]


def test_a_refusal_from_the_scoped_gate_still_blocks_the_commit(scratch):
    recording_check(scratch)
    scratch.write("staged.py", "x = 1\n")
    scratch.git("add", "staged.py")

    result = scratch.run_hook("pre-commit", extra_env={"FAKE_CHECK_RC": "1"})

    assert result.returncode == 1
    assert "BLOCKED by scripts/check.sh" in result.stderr
    assert argv(scratch) == ["--fast", "--paths", "staged.py"]
