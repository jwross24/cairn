from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from conftest import ROOT

RECORDER = """#!/usr/bin/env bash
printf 'ran\\n' > "$(dirname "$0")/../fd-gate-ran.txt"
exit 0
"""


def test_head_hook_without_the_preflight_reaches_the_main_gate_under_low_capacity(scratch):
    check = scratch.write("scripts/check.sh", RECORDER)
    check.chmod(0o755)
    old_hook = subprocess.run(
        ["git", "show", "3801c15:.githooks/pre-commit"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    hook = scratch.write(".githooks/pre-commit", old_hook.stdout.decode("utf-8"))
    hook.chmod(0o755)
    sysctl = scratch.path / "bin" / "sysctl"
    sysctl.write_text("#!/usr/bin/env bash\nprintf '321\\n400\\n'\n")
    sysctl.chmod(0o755)

    result = scratch.run_hook("pre-commit")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (scratch.path / "fd-gate-ran.txt").exists()
    assert "FD-CEILING" not in scratch.check_log()


def test_low_capacity_refuses_before_the_main_gate_runs(scratch):
    check = scratch.write("scripts/check.sh", RECORDER)
    check.chmod(0o755)
    bin_dir = scratch.path / "bin"
    bin_dir.mkdir(exist_ok=True)
    sysctl = bin_dir / "sysctl"
    sysctl.write_text("#!/usr/bin/env bash\nprintf '321\\n400\\n'\n")
    sysctl.chmod(0o755)

    result = scratch.run_hook("pre-commit", extra_env={"PATH": f"{bin_dir}:{os.environ['PATH']}"})

    assert result.returncode == 1
    assert not (scratch.path / "fd-gate-ran.txt").exists()
    assert "FD-CEILING used=321 maximum=400 min_free=20%" in scratch.check_log()


def test_boundary_capacity_allows_the_main_gate_to_run(scratch):
    check = scratch.write("scripts/check.sh", RECORDER)
    check.chmod(0o755)

    result = scratch.run_hook("pre-commit")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (scratch.path / "fd-gate-ran.txt").exists()
    assert "FD-CLEAR used=320 maximum=400 min_free=20%" in scratch.check_log()


def test_provider_failure_refuses_before_the_main_gate_runs(scratch):
    check = scratch.write("scripts/check.sh", RECORDER)
    check.chmod(0o755)
    sysctl = scratch.path / "bin" / "sysctl"
    sysctl.write_text("#!/usr/bin/env bash\nprintf 'unavailable\\n' >&2\nexit 7\n")
    sysctl.chmod(0o755)

    result = scratch.run_hook("pre-commit")

    assert result.returncode == 1
    assert not (scratch.path / "fd-gate-ran.txt").exists()
    assert "FD-INFRA-DENY sysctl exited 7" in scratch.check_log()


def test_valid_fd_bypass_is_distinct_from_a_clear_snapshot(scratch):
    check = scratch.write("scripts/check.sh", RECORDER)
    check.chmod(0o755)
    sysctl = scratch.path / "bin" / "sysctl"
    sysctl.write_text("#!/usr/bin/env bash\nprintf '321\\n400\\n'\n")
    sysctl.chmod(0o755)

    result = scratch.run_hook("pre-commit", extra_env={"CAIRN_FD_CEILING_SKIP": "operator repair"})

    assert result.returncode == 0, result.stdout + result.stderr
    assert (scratch.path / "fd-gate-ran.txt").exists()
    assert "FD-BYPASS CAIRN_FD_CEILING_SKIP reason=operator repair" in scratch.check_log()


def test_check_skip_does_not_bypass_the_fd_preflight(scratch):
    check = scratch.write("scripts/check.sh", RECORDER)
    check.chmod(0o755)
    sysctl = scratch.path / "bin" / "sysctl"
    sysctl.write_text("#!/usr/bin/env bash\nprintf '321\\n400\\n'\n")
    sysctl.chmod(0o755)

    result = scratch.run_hook(
        "pre-commit",
        extra_env={
            "CAIRN_CHECK_SKIP": "not an fd bypass",
            "PATH": f"{scratch.path / 'bin'}:{scratch.env['PATH']}",
        },
    )

    assert result.returncode == 1
    assert not (scratch.path / "fd-gate-ran.txt").exists()
    assert "FD-CEILING used=321 maximum=400 min_free=20%" in scratch.check_log()


def test_missing_uv_is_a_logged_bootstrap_refusal(scratch):
    result = scratch.run_hook("pre-commit", extra_env={"PATH": "/usr/bin:/bin"})

    assert result.returncode == 1
    assert "FD-INFRA-DENY fd-ceiling bootstrap missing uv" in scratch.check_log()


def test_uv_that_cannot_launch_the_preflight_is_a_logged_refusal(scratch):
    check = scratch.write("scripts/check.sh", RECORDER)
    check.chmod(0o755)
    bin_dir = scratch.path / "failed-uv"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text("#!/usr/bin/env bash\nexit 7\n")
    uv.chmod(0o755)

    result = scratch.run_hook("pre-commit", extra_env={"PATH": f"{bin_dir}:/usr/bin:/bin"})

    assert result.returncode == 1
    assert not (scratch.path / "fd-gate-ran.txt").exists()
    assert "FD-PREFLIGHT-DENY uv run exited 7" in scratch.check_log()


def test_missing_sysctl_names_the_fd_bypass(scratch):
    check = scratch.write("scripts/check.sh", RECORDER)
    check.chmod(0o755)
    uv = shutil.which("uv")
    assert uv is not None

    result = scratch.run_hook("pre-commit", extra_env={"PATH": f"{Path(uv).parent}:/usr/bin:/bin"})

    assert result.returncode == 1
    assert not (scratch.path / "fd-gate-ran.txt").exists()
    assert "CAIRN_FD_CEILING_SKIP='<reason>'" in result.stderr
