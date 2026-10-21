import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "scripts"))
sys.path.insert(0, str(ROOT_DIR / "tests"))

from _bead_store import bead_store, no_database  # noqa: E402
from test_theater_patterns import (  # noqa: E402
    MARK,
    ONE_LINE_SKIP,
    SKIP_BLOCK,
    document,
    exempt,
    open_bead,
    tree,
)
from theater_patterns import (  # noqa: E402
    EXPIRY_BEAD,
    evaluate,
    main,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "theater_patterns.py"
POLICY = ROOT / "audit-policy.yaml"
CHILD_TIMEOUT_S = 60

# --- the shell-facing contract ------------------------------------------------


def run_cli(*args, **kwargs):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT_S,
        **kwargs,
    )


def policy_file(tmp_path: Path, doc: dict) -> Path:
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(doc))
    return path


def test_cli_refuses_a_finding_and_logs_fail(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    log = tmp_path / "gate.log"
    proc = run_cli("--root", str(tmp_path), "--policy", str(policy_file(tmp_path, document())), "--log", str(log))
    assert proc.returncode == 2
    assert "MAJOR P-platform-skip-hides-a-gate  tests/unit/test_a.py:5" in proc.stderr
    assert log.read_text().split()[1:4] == ["FAIL", "theater-patterns:", "1"]


def test_cli_passes_the_real_tree_under_the_real_policy(tmp_path):
    log = tmp_path / "gate.log"
    proc = run_cli("--root", str(ROOT), "--policy", str(POLICY), "--log", str(log), cwd=bead_store())
    assert proc.returncode == 0, proc.stderr
    assert "PASS theater-patterns" in log.read_text()


def without_br(tmp_path: Path) -> dict[str, str]:
    """The CI runner's PATH: uv and git, no br."""
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    for tool in ("uv", "git", "python3"):
        found = shutil.which(tool)
        if found:
            (stub / tool).symlink_to(found)
    return {"PATH": f"{stub}:/usr/bin:/bin"}


def test_cli_passes_the_real_tree_with_br_off_path(tmp_path):
    log = tmp_path / "gate.log"
    proc = run_cli("--root", str(ROOT), "--policy", str(POLICY), "--log", str(log), env=without_br(tmp_path))
    assert proc.returncode == 0, proc.stderr
    text = log.read_text()
    assert "EXPIRY-UNKNOWN theater-patterns" in text
    assert "PASS theater-patterns" in text
    assert EXPIRY_BEAD in proc.stderr


def test_cli_with_br_off_path_still_refuses_a_planted_skip(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    log = tmp_path / "gate.log"
    policy = policy_file(tmp_path, document(exempt_paths=exempt("tests/unit/test_b.py"), exempt_until_bead="cairn-hcl"))
    tree(tmp_path, {"tests/unit/test_b.py": SKIP_BLOCK.format(mark=MARK, reason="known")})
    proc = run_cli("--root", str(tmp_path), "--policy", str(policy), "--log", str(log), env=without_br(tmp_path))
    assert proc.returncode == 2
    assert "tests/unit/test_a.py:5" in proc.stderr
    assert "EXPIRY-UNKNOWN theater-patterns" in log.read_text()


def test_cli_logs_off_when_the_section_is_deleted(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    log = tmp_path / "gate.log"
    proc = run_cli(
        "--root", str(tmp_path), "--policy", str(policy_file(tmp_path, {"threshold": 700})), "--log", str(log)
    )
    assert proc.returncode == 0
    assert "OFF theater-patterns" in log.read_text()


def test_cli_denies_a_missing_policy_rather_than_reporting_clean(tmp_path):
    log = tmp_path / "gate.log"
    proc = run_cli("--root", str(tmp_path), "--policy", str(tmp_path / "absent.yaml"), "--log", str(log))
    assert proc.returncode == 3
    assert "refusing to report a clean tree unscanned" in proc.stderr
    assert "DENY theater-patterns infra" in log.read_text()


def test_cli_denies_an_unparsable_policy(tmp_path):
    log = tmp_path / "gate.log"
    bad = tmp_path / "policy.yaml"
    bad.write_text("project_theater_patterns: [\n")
    proc = run_cli("--root", str(tmp_path), "--policy", str(bad), "--log", str(log))
    assert proc.returncode == 3
    assert "does not parse as YAML" in proc.stderr


def test_cli_bypass_is_named_and_logged(tmp_path, monkeypatch):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    log = tmp_path / "gate.log"
    monkeypatch.setenv("CAIRN_THEATER_PATTERNS_SKIP", "probing the bypass")
    assert main(["--root", str(tmp_path), "--policy", str(policy_file(tmp_path, document())), "--log", str(log)]) == 0
    assert "BYPASS theater-patterns: probing the bypass" in log.read_text()


def test_check_sh_runs_the_gate():
    assert "theater-patterns.sh" in (ROOT / "scripts" / "check.sh").read_text()


def test_a_br_that_never_answers_denies_the_scan_rather_than_skipping_the_expiry(monkeypatch):
    import br_lookup
    import theater_patterns

    def expire(argv, **kwargs):
        assert kwargs.get("timeout") == theater_patterns.BR_TIMEOUT_SECONDS, argv
        raise subprocess.TimeoutExpired(argv, theater_patterns.BR_TIMEOUT_SECONDS)

    monkeypatch.chdir(bead_store())
    monkeypatch.setattr(br_lookup.subprocess, "run", expire)
    with pytest.raises(LookupError) as raised:
        theater_patterns.bead_status_resolver()("cairn-fur")
    assert "did not answer within" in str(raised.value)
    assert "cairn-fur" in str(raised.value)


def test_cli_with_no_database_names_the_missing_store_rather_than_a_sync_conflict(tmp_path):
    log = tmp_path / "gate.log"
    proc = run_cli("--root", str(ROOT), "--policy", str(POLICY), "--log", str(log), cwd=no_database())
    assert proc.returncode == 0, proc.stderr
    text = log.read_text()
    assert "EXPIRY-UNKNOWN theater-patterns [no-database]" in text
    assert "PASS theater-patterns" in text
    assert "br sync --import-only" in proc.stderr
    assert "SYNC_CONFLICT" not in proc.stderr


def test_cli_with_br_off_path_is_not_reported_as_a_missing_database(tmp_path):
    log = tmp_path / "gate.log"
    proc = run_cli(
        "--root", str(ROOT), "--policy", str(POLICY), "--log", str(log), env=without_br(tmp_path), cwd=bead_store()
    )
    assert proc.returncode == 0, proc.stderr
    text = log.read_text()
    assert "EXPIRY-UNKNOWN theater-patterns [br-absent]" in text
    assert "no bead database" not in text


def test_cli_refuses_an_exemption_whose_bead_is_not_in_the_store(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    log = tmp_path / "gate.log"
    policy = policy_file(
        tmp_path, document(exempt_paths=exempt("tests/unit/test_a.py"), exempt_until_bead="cairn-zzz9")
    )
    proc = run_cli("--root", str(tmp_path), "--policy", str(policy), "--log", str(log), cwd=bead_store())
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "cairn-zzz9 is not in the bead store" in proc.stderr
    assert "br list --all" in proc.stderr
    assert "DENY theater-patterns policy" in log.read_text()


def test_a_scope_narrows_the_scan_to_the_files_it_names(tmp_path):
    tree(
        tmp_path,
        {
            "tests/unit/test_a.py": ONE_LINE_SKIP.format(mark=MARK),
            "tests/unit/test_b.py": ONE_LINE_SKIP.format(mark=MARK),
        },
    )
    outcome = evaluate(tmp_path, document(), scope={"tests/unit/test_a.py"})
    assert [f.path for f in outcome.findings] == ["tests/unit/test_a.py"]
    assert outcome.scanned == ["tests/unit/test_a.py"]


def test_a_scope_naming_no_reachable_file_scans_nothing_and_passes(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": ONE_LINE_SKIP.format(mark=MARK)})
    outcome = evaluate(tmp_path, document(), scope={"src/cairn/elsewhere.py"})
    assert outcome.kind == "PASS"
    assert outcome.scanned == []


def test_a_stale_exemption_is_refused_though_the_scope_hides_the_file_it_names(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": "x = 1\n", "tests/unit/test_b.py": "y = 2\n"})
    doc = document(exempt_paths=exempt("tests/unit/test_a.py"), exempt_until_bead="cairn-hcl")
    outcome = evaluate(tmp_path, doc, bead_status=open_bead, scope={"tests/unit/test_b.py"})
    assert outcome.kind == "DENY"
    assert any("no longer matches the signature" in problem for problem in outcome.problems)
