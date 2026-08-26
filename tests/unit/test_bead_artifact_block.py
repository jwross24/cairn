import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "bead_artifact_block.py"
SHIM = ROOT / "scripts" / "bead-artifact-block.sh"

VALID = """ARTIFACTS-BEGIN
source: `pyproject.toml` lines 1-10
test: `tests/unit/test_bead_artifact_block.py` lines 1-5
commit: HEAD
command: uv run pytest -q
ARTIFACTS-END
"""


def run_validator(body_file, *args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--body-file", str(body_file), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def write_body(tmp_path, text):
    path = tmp_path / "body.txt"
    path.write_text(text)
    return path


def test_a_well_formed_block_over_real_files_is_accepted(tmp_path):
    proc = run_validator(write_body(tmp_path, VALID))
    assert proc.returncode == 0, proc.stderr
    assert "1 source, 1 test, 1 commit, 1 command" in proc.stdout


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Done.\n", "carries no ARTIFACTS-BEGIN block"),
        (VALID + VALID, "2 ARTIFACTS-BEGIN markers"),
        (VALID.replace("ARTIFACTS-END\n", ""), "never closes with ARTIFACTS-END"),
        (VALID.replace("source: `pyproject.toml` lines 1-10\n", ""), "names no `source:` file"),
        (VALID.replace("command: uv run pytest -q\n", ""), "names no `command:`"),
        (VALID.replace("pyproject.toml", "src/cairn/not_a_real_module.py"), "named but absent"),
        (VALID.replace("lines 1-10", "lines 1-99999"), "the file has"),
        (VALID.replace("lines 1-10", "lines 40-2"), "ends before it starts"),
        (VALID.replace("commit: HEAD", "commit: " + "d" * 40), "does not resolve"),
        (VALID.replace("source: `pyproject.toml`", "source: pyproject.toml"), "needs a backticked path"),
        (VALID.replace("command: uv run pytest -q", "just do the thing"), "not a block entry"),
    ],
)
def test_each_defect_is_refused_and_named(tmp_path, body, expected):
    proc = run_validator(write_body(tmp_path, body))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert expected in proc.stderr


def test_a_refusal_shows_how_to_add_the_block(tmp_path):
    proc = run_validator(write_body(tmp_path, "Done.\n"))
    assert "ARTIFACTS-BEGIN" in proc.stderr
    assert "source: `path/to/file.py` lines 10-42" in proc.stderr


def test_a_block_the_extractor_cannot_see_is_refused(tmp_path):
    body = VALID.replace("source: `pyproject.toml` lines 1-10", "source: `.githooks/pre-commit`").replace(
        "test: `tests/unit/test_bead_artifact_block.py` lines 1-5\n", ""
    )
    proc = run_validator(write_body(tmp_path, body))
    assert proc.returncode == 2, proc.stdout
    assert "visible to the compliance extractor" in proc.stderr


def test_an_invisible_path_beside_a_visible_one_passes_and_is_named(tmp_path):
    body = VALID.replace(
        "source: `pyproject.toml` lines 1-10",
        "source: `pyproject.toml` lines 1-10\nsource: `.githooks/pre-commit`",
    )
    proc = run_validator(write_body(tmp_path, body))
    assert proc.returncode == 0, proc.stderr
    assert "the extractor cannot see .githooks/pre-commit" in proc.stderr


def _stand_in_skill(tmp_path, pattern):
    scripts = tmp_path / "skill" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "extract-spec.py").write_text(f'PATH_HINT_RE = re.compile(r"{pattern}")\n')
    return scripts.parent


def _our_pattern():
    proc = subprocess.run([sys.executable, str(VALIDATOR), "--print-path-hint-re"], capture_output=True, text=True)
    return proc.stdout.strip()


def test_a_drifted_extractor_regex_denies(tmp_path):
    log = ROOT / ".check.log"
    before = log.stat().st_size if log.exists() else 0
    skill = _stand_in_skill(tmp_path, r"`([\w]+)`")
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "cairn-exi"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**_env(), "CAIRN_COMPLIANCE_SKILL": str(skill)},
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "no longer matches this gate's copy" in proc.stderr
    assert "DENY artifact-block parity" in _appended(log, before)


def test_a_matching_extractor_regex_does_not_deny(tmp_path):
    skill = _stand_in_skill(tmp_path, _our_pattern())
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "cairn-exi"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**_env(), "CAIRN_COMPLIANCE_SKILL": str(skill)},
    )
    assert proc.returncode != 3, proc.stdout + proc.stderr
    assert "no longer matches" not in proc.stderr


def _appended(log, offset):
    with log.open() as handle:
        handle.seek(offset)
        return handle.read()


def test_usage_without_arguments_is_refused():
    proc = subprocess.run([sys.executable, str(VALIDATOR)], capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 64
    assert "usage:" in proc.stderr


def test_bead_ids_and_body_file_are_alternatives(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "cairn-exi", "--body-file", str(write_body(tmp_path, VALID))],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 64
    assert "alternatives" in proc.stderr


def test_the_gate_logs_a_bypass_and_exits_zero(tmp_path):
    log = ROOT / ".check.log"
    before = log.stat().st_size if log.exists() else 0
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "cairn-exi"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**_env(), "CAIRN_ARTIFACT_BLOCK_SKIP": "proving the bypass is logged"},
    )
    assert proc.returncode == 0, proc.stderr
    assert "BYPASSED" in proc.stderr
    with log.open() as handle:
        handle.seek(before)
        appended = handle.read()
    assert "BYPASS artifact-block cairn-exi: proving the bypass is logged" in appended


def test_the_gate_denies_when_br_is_absent(tmp_path):
    log = ROOT / ".check.log"
    before = log.stat().st_size if log.exists() else 0
    # git and date stay reachable; a gate that cannot stamp its own log line would
    # be proving the wrong absence.
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "cairn-exi"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**_env(), "PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "is not installed" in proc.stderr
    assert "CAIRN_ARTIFACT_BLOCK_SKIP" in proc.stderr
    with log.open() as handle:
        handle.seek(before)
        appended = handle.read()
    assert "DENY artifact-block infra" in appended


def _env():
    return {k: v for k, v in os.environ.items() if k != "CAIRN_ARTIFACT_BLOCK_SKIP"}


def test_the_pre_commit_hook_runs_the_gate_for_every_closing_bead():
    hook = (ROOT / ".githooks" / "pre-commit").read_text()
    assert "scripts/bead-artifact-block.sh $NEWLY_CLOSED" in hook
    assert hook.index("bead-artifact-block.sh") > hook.index("NEWLY_CLOSED=")


def test_the_shell_entry_point_delegates_to_the_validator():
    assert f'exec uv run python "$(dirname "$0")/{VALIDATOR.name}" "$@"' in SHIM.read_text()
