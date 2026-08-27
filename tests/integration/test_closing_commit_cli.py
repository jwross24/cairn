import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CLOSING_COMMIT = REPO / "scripts" / "closing_commit.py"
ATTRIBUTION = REPO / "scripts" / "audit_attribution.py"
CHILD_TIMEOUT_S = 120

GIT_RUNNER = (
    "import subprocess, sys\n"
    "p = subprocess.run(['git', '-C', sys.argv[1], *sys.argv[2:]], capture_output=True, text=True)\n"
    "sys.stdout.write(p.stdout)\n"
    "sys.stderr.write(p.stderr)\n"
    "sys.exit(p.returncode)\n"
)

BEAD = "cairn-m0-e0s.16"
OTHER = "cairn-cue"

STUB_SCORER = """
import argparse, json, sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("bead_dir")
parser.add_argument("--threshold", type=int, default=700)
parser.add_argument("--rubric")
parser.add_argument("--synthesis")
parser.add_argument("--prior-pass-dir")
args = parser.parse_args()

summary = json.loads((Path(args.bead_dir) / "theater.json").read_text())["summary"]
score = 1000 - 350 * summary["BLOCKING"] - 15 * summary["MAJOR"]
print(json.dumps({"bead_id": Path(args.bead_dir).name, "score": score, "false_closed": score < args.threshold}))
"""

FAILING_SCORER = 'import sys\nsys.stderr.write("the rubric named no weights\\n")\nsys.exit(4)\n'


def git(repo, *args):
    proc = subprocess.run(
        [sys.executable, "-c", GIT_RUNNER, str(repo), *args],
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT_S,
    )
    assert proc.returncode == 0, f"git {args} failed: {proc.stderr}"
    return proc.stdout


def bead_row(bead_id, status):
    return json.dumps({"id": bead_id, "title": "t", "status": status})


def write_store(repo, rows):
    (repo / ".beads").mkdir(exist_ok=True)
    (repo / ".beads" / "issues.jsonl").write_text("".join(row + "\n" for row in rows))


@pytest.fixture
def store_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "nohooks").mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "commit.gpgsign", "false")
    # ~/.gitignore_global excludes .beads/, and this fixture is nothing but a bead store.
    git(repo, "config", "core.excludesFile", "/dev/null")
    git(repo, "config", "core.hooksPath", str(tmp_path / "nohooks"))
    write_store(repo, [bead_row(BEAD, "open"), bead_row(OTHER, "open")])
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "seed the bead store")
    return repo


def close_bead(repo, bead_id, message):
    rows = (repo / ".beads" / "issues.jsonl").read_text().splitlines()
    write_store(
        repo,
        [
            bead_row(json.loads(row)["id"], "closed" if json.loads(row)["id"] == bead_id else json.loads(row)["status"])
            for row in rows
        ],
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


def resolver(repo, *args):
    return subprocess.run(
        [sys.executable, str(CLOSING_COMMIT), "--root", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT_S,
        cwd=str(repo),
    )


def test_the_staged_form_names_the_bead_the_pending_commit_closes(store_repo):
    rows = (store_repo / ".beads" / "issues.jsonl").read_text().splitlines()
    write_store(store_repo, [bead_row(BEAD, "closed"), rows[1]])
    git(store_repo, "add", "-A")

    proc = resolver(store_repo, "--staged")
    assert proc.returncode == 0
    assert proc.stdout.split() == [BEAD]


def test_the_commit_form_names_the_bead_that_commit_closed(store_repo):
    close_bead(store_repo, BEAD, f"close {BEAD}")
    proc = resolver(store_repo, "--commit", "HEAD")
    assert proc.returncode == 0
    assert proc.stdout.split() == [BEAD]


def test_a_commit_that_closes_nothing_prints_nothing_and_still_exits_zero(store_repo):
    proc = resolver(store_repo, "--commit", "HEAD")
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_a_bead_id_resolves_to_its_sha_to_staged_or_to_unknown(store_repo):
    sha = close_bead(store_repo, BEAD, f"close {BEAD}")
    rows = (store_repo / ".beads" / "issues.jsonl").read_text().splitlines()
    write_store(store_repo, [rows[0], bead_row(OTHER, "closed")])
    git(store_repo, "add", "-A")

    proc = resolver(store_repo, BEAD, OTHER, "cairn-never")
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == [f"{BEAD} {sha}", f"{OTHER} STAGED", "cairn-never UNKNOWN"]


@pytest.mark.parametrize(
    "args",
    [
        ("--commit", "does-not-exist-ref"),
        ("--staged",),
        (BEAD,),
    ],
)
def test_a_git_that_cannot_answer_exits_three_rather_than_printing_no_bead(tmp_path, args):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    proc = subprocess.run(
        [sys.executable, str(CLOSING_COMMIT), "--root", str(outside), *args],
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT_S,
        cwd=str(outside),
    )
    assert proc.returncode == 3
    assert proc.stdout == ""
    assert "GIT-FAILED" in proc.stderr


def test_a_bad_ref_on_a_real_repository_exits_three(store_repo):
    proc = resolver(store_repo, "--commit", "does-not-exist-ref")
    assert proc.returncode == 3
    assert proc.stdout == ""
    assert "GIT-FAILED" in proc.stderr


def test_no_arguments_at_all_is_a_usage_error(store_repo):
    proc = resolver(store_repo)
    assert proc.returncode == 2
    assert "usage:" in proc.stderr


def test_an_amend_shows_the_close_to_the_commit_form_and_not_to_the_staged_one(store_repo):
    """Pins the observed split: `git diff --cached` compares the index to a HEAD that
    already carries the close, so an amend reaches post-commit and not pre-commit."""
    close_bead(store_repo, BEAD, f"close {BEAD}")
    (store_repo / "note.txt").write_text("an afterthought folded into the close\n")
    git(store_repo, "add", "-A")

    staged = resolver(store_repo, "--staged")
    head = resolver(store_repo, "--commit", "HEAD")
    assert staged.returncode == 0 and staged.stdout == ""
    assert head.returncode == 0 and head.stdout.split() == [BEAD]


def write_audit(tmp_path, *, findings, status="closed"):
    audit_dir = tmp_path / "beads_compliance_audit"
    bead_dir = audit_dir / "passes" / "2026-08-26T16-29-01Z" / "beads" / BEAD
    bead_dir.mkdir(parents=True)
    summary = {"BLOCKING": 0, "MAJOR": 0, "MINOR": 0, "NOTE": 0}
    for finding in findings:
        summary[finding["severity"]] += 1
    (bead_dir / "theater.json").write_text(
        json.dumps({"bead_id": BEAD, "scanned_files": [], "findings": findings, "summary": summary})
    )
    (bead_dir / "spec.json").write_text(json.dumps({"bead_id": BEAD, "items": []}))
    (bead_dir / "show.json").write_text(json.dumps({"id": BEAD, "status": status}))
    (audit_dir / "rubric.md").write_text("---\nweights_by_type: {}\n---\n")
    return audit_dir


def write_skill(tmp_path, name, body):
    skill = tmp_path / name
    (skill / "scripts").mkdir(parents=True)
    (skill / "scripts" / "score-bead.py").write_text(body)
    return skill


def attribution(repo, *args):
    return subprocess.run(
        [sys.executable, str(ATTRIBUTION), "--root", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT_S,
        cwd=str(repo),
    )


def test_a_bead_scoring_above_the_threshold_exits_zero(tmp_path, store_repo):
    close_bead(store_repo, BEAD, f"close {BEAD}")
    audit_dir = write_audit(tmp_path, findings=[])
    skill = write_skill(tmp_path, "skill", STUB_SCORER)

    proc = attribution(store_repo, "--audit-dir", str(audit_dir), "--skill", str(skill))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith(f"OK {BEAD} UNCHANGED ")
    assert "score 1000" in proc.stdout


def test_a_bead_the_corrected_scorecard_fails_exits_one(tmp_path, store_repo):
    close_bead(store_repo, BEAD, f"close {BEAD}")
    blocking = {
        "id": "theater.1",
        "severity": "BLOCKING",
        "category": "mock_only_test",
        "path": "tests/unit/test_thing.py",
        "line": 3,
        "snippet": "mock()",
        "description": "every boundary is mocked",
    }
    audit_dir = write_audit(tmp_path, findings=[blocking])
    skill = write_skill(tmp_path, "skill", STUB_SCORER)

    proc = attribution(store_repo, "--audit-dir", str(audit_dir), "--skill", str(skill))
    assert proc.returncode == 1, proc.stderr
    assert proc.stdout.startswith(f"FALSE-CLOSED {BEAD} ")
    assert "score 650" in proc.stdout


@pytest.mark.parametrize(
    ("marker", "extra"), [("NO-SKILL", ("--skill", "no-such-directory")), ("NOTHING-TO-CHECK", ())]
)
def test_a_run_with_nothing_it_can_score_exits_two(tmp_path, store_repo, marker, extra):
    audit_dir = write_audit(tmp_path, findings=[])
    skill = write_skill(tmp_path, "skill", STUB_SCORER)
    if marker == "NOTHING-TO-CHECK":
        (audit_dir / "passes" / "2026-08-26T16-29-01Z" / "beads" / BEAD / "spec.json").unlink()
        extra = ("--skill", str(skill))

    proc = attribution(store_repo, "--audit-dir", str(audit_dir), *extra)
    assert proc.returncode == 2
    assert marker in proc.stderr


def test_a_missing_rubric_exits_two(tmp_path, store_repo):
    audit_dir = write_audit(tmp_path, findings=[])
    (audit_dir / "rubric.md").unlink()
    skill = write_skill(tmp_path, "skill", STUB_SCORER)

    proc = attribution(store_repo, "--audit-dir", str(audit_dir), "--skill", str(skill))
    assert proc.returncode == 2
    assert "NO-RUBRIC" in proc.stderr


def test_a_git_that_cannot_answer_exits_three_without_scoring_anything(tmp_path):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    audit_dir = write_audit(tmp_path, findings=[])
    skill = write_skill(tmp_path, "skill", STUB_SCORER)

    proc = attribution(outside, "--audit-dir", str(audit_dir), "--skill", str(skill))
    assert proc.returncode == 3
    assert proc.stdout == ""
    assert "GIT-FAILED" in proc.stderr


def test_a_scorer_that_exits_nonzero_is_reported_rather_than_read_as_a_score(tmp_path, store_repo):
    close_bead(store_repo, BEAD, f"close {BEAD}")
    audit_dir = write_audit(tmp_path, findings=[])
    skill = write_skill(tmp_path, "broken", FAILING_SCORER)

    proc = attribution(store_repo, "--audit-dir", str(audit_dir), "--skill", str(skill))
    assert proc.returncode != 0
    assert "score-bead.py exited 4" in proc.stderr
    assert "the rubric named no weights" in proc.stderr


def test_an_unresolved_bead_is_reported_unresolved_and_keeps_no_attributed_finding(tmp_path, store_repo):
    audit_dir = write_audit(tmp_path, findings=[])
    skill = write_skill(tmp_path, "skill", STUB_SCORER)

    proc = attribution(store_repo, "--audit-dir", str(audit_dir), "--skill", str(skill))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith(f"OK {BEAD} UNRESOLVED ")
    theater = json.loads((audit_dir / "passes" / "2026-08-26T16-29-01Z" / "beads" / BEAD / "theater.json").read_text())
    assert theater["commit_attribution"]["closing_commit"] == "UNKNOWN"
