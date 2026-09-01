"""A tier that runs the real git hooks against a throwaway repository.

`tests/conftest.py` allow-lists two argv0 values and fails any test that writes under
the repository root, which is what keeps the unit and integration tiers hermetic. A
hook contract is the opposite shape: the thing under test is `.githooks/pre-commit`
and `.githooks/post-commit` as bash, and the only way to reach that shell is to run
`git commit` for real. This tier therefore shadows `isolation_guard` by name from its
own conftest, and every path it writes lives under `tmp_path`.

The scratch repository carries the real hooks and the real scripts they call. What it
does not carry is a source tree, a bead database or a compliance skill, so the gates
that need those are taken through their own named, logged bypasses -- the same ones a
human uses -- rather than through an edit to the hook.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(os.environ.get("CAIRN_REPO_ROOT") or Path(__file__).resolve().parents[2])

HOOK_SCRIPTS = (
    "check.sh",
    "theater-patterns.sh",
    "theater_patterns.py",
    "closing_commit.py",
    "gate_marker.py",
    "bead-test-plan.sh",
    "bead-artifact-block.sh",
    "bead_artifact_block.py",
    "br_lookup.py",
    "beads_doctor_gate.py",
    "audit_attribution.py",
    "scorecard_coherence.py",
    "audit_missing_items.py",
)

SKILL_REL = ".claude/skills/beads-compliance-and-completion-verification"

# The pre-commit hook denies unless the compliance skill carries each of these, because
# an upstream update restores an audit that scores on defaults and says nothing. A
# stand-in that satisfies the markers keeps the hook on the path a real clone takes.
SKILL_FILES = {
    "scripts/sync-rubric-from-policy.py": "",
    "scripts/bootstrap-audit.sh": "sync-rubric-from-policy.py\ndef corrupting:\n",
    "scripts/inventory-beads.sh": "no readable check list\n",
    "scripts/score-bead.py": "NA_MEASURED_DIMENSIONS = ()\n",
    "assets/pre-commit-hook.sh": "#!/usr/bin/env bash\nexit ${FAKE_SKILL_AUDIT_RC:-0}\n",
}

BEAD_ROW = '{{"id": "cairn-zzz", "title": "scratch", "status": "{status}"}}\n'

BYPASSES = {
    "CAIRN_CHECK_SKIP": "hook-contract tier: the scratch repository carries no source tree to lint",
    "CAIRN_TEST_PLAN_SKIP": "hook-contract tier: the scratch repository carries no bead database",
    "CAIRN_ARTIFACT_BLOCK_SKIP": "hook-contract tier: the scratch repository carries no bead database",
    "CAIRN_DOCTOR_GATE_OK": "hook-contract tier: the scratch repository carries no bead database",
}


@dataclass
class ScratchRepo:
    path: Path
    origin: Path
    env: dict

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        proc = subprocess.run(
            ["git", "-C", str(self.path), *args],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=300,
        )
        if check and proc.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} exited {proc.returncode}\n{proc.stdout}\n{proc.stderr}")
        return proc

    def run_hook(self, name: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(self.path / ".githooks" / name)],
            cwd=str(self.path),
            capture_output=True,
            text=True,
            env={**self.env, **(extra_env or {})},
            timeout=600,
        )

    def commit(self, message: str, *flags: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.path), "commit", *flags, "-m", message],
            capture_output=True,
            text=True,
            env={**self.env, **(extra_env or {})},
            timeout=900,
        )

    def write(self, rel: str, text: str) -> Path:
        target = self.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return target

    def marker(self) -> Path:
        return self.path / ".git" / "cairn-gated-beads.json"

    def check_log(self) -> str:
        log = self.path / ".check.log"
        return log.read_text() if log.exists() else ""

    def hook_log(self) -> str:
        log = self.path / ".beads_hook.log"
        return log.read_text() if log.exists() else ""

    def origin_shas(self) -> list[str]:
        proc = subprocess.run(
            ["git", "-C", str(self.origin), "log", "--format=%H", "--all"],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=120,
        )
        return proc.stdout.split()


@pytest.fixture(autouse=True)
def isolation_guard():
    """Shadows the repository-wide guard for this tier only.

    The shared fixture forbids the two things a hook contract is made of: a subprocess
    that is not the interpreter, and a write inside a git worktree. Overriding it by
    name in this conftest leaves the shared one exactly as every other tier sees it.
    """


@pytest.fixture
def scratch(tmp_path: Path) -> ScratchRepo:
    repo = tmp_path / "repo"
    origin = tmp_path / "origin.git"
    home = tmp_path / "home"
    for directory in (repo, home):
        directory.mkdir(parents=True)

    env: dict[str, str] = {
        **os.environ,
        "HOME": str(home),
        "GIT_AUTHOR_NAME": "hook contract",
        "GIT_AUTHOR_EMAIL": "hook@example.invalid",
        "GIT_COMMITTER_NAME": "hook contract",
        "GIT_COMMITTER_EMAIL": "hook@example.invalid",
        **BYPASSES,
    }
    # uv keeps its cache and its managed interpreters under HOME, and moving HOME to
    # hide the machine's own compliance skill would otherwise send every `uv run` in
    # the hooks to a cold download.
    for key, default in (
        ("UV_CACHE_DIR", Path(os.environ["HOME"]) / ".cache" / "uv"),
        ("UV_PYTHON_INSTALL_DIR", Path(os.environ["HOME"]) / ".local" / "share" / "uv" / "python"),
    ):
        env.setdefault(key, str(default))
    env.pop("CAIRN_PUSH_SKIP", None)
    env.pop("GIT_DIR", None)
    env.pop("GIT_INDEX_FILE", None)

    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True, env=env)
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True, env=env)

    shutil.copytree(ROOT / ".githooks", repo / ".githooks")
    for entry in (repo / ".githooks").iterdir():
        entry.chmod(0o755)
    (repo / "scripts").mkdir()
    for name in HOOK_SCRIPTS:
        shutil.copy2(ROOT / "scripts" / name, repo / "scripts" / name)
        (repo / "scripts" / name).chmod(0o755)

    for rel, text in SKILL_FILES.items():
        target = repo / SKILL_REL / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        target.chmod(0o755)

    (repo / "audit-policy.yaml").write_text("threshold: 700\n")
    (repo / ".beads").mkdir()
    (repo / ".beads" / "issues.jsonl").write_text(BEAD_ROW.format(status="open"))
    (repo / "evidence.txt").write_text("A\n")

    scratch_repo = ScratchRepo(path=repo, origin=origin, env=env)
    scratch_repo.git("config", "core.hooksPath", ".githooks")
    scratch_repo.git("remote", "add", "origin", str(origin))
    scratch_repo.git("add", "-A")
    scratch_repo.commit("base", "--no-verify")
    scratch_repo.git("push", "-q", "origin", "main")
    return scratch_repo
