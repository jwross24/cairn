"""Bead workspaces a test can rely on, built rather than inherited.

`br` discovers its database by walking up from the working directory, and
`.beads/beads.db` is derived state no checkout carries. A test that runs a gate
from the repository root therefore reads whatever database the machine happens
to hold, which is green on a developer machine and red on a runner.

Both shapes here are constructed: `bead_store()` is a workspace with a database
imported from the repository's tracked `issues.jsonl`, and `no_database()` is a
workspace holding the same tracked files and no database at all.

conftest's isolation guard admits only the interpreter as a subprocess, so the
`br` calls run in a child launched from this file rather than from the test.
"""

from __future__ import annotations

import atexit
import functools
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKED = ("config.yaml", "metadata.json", "issues.jsonl")
BR_TIMEOUT_S = 180


def _workspace(prefix: str) -> Path:
    path = Path(os.path.realpath(tempfile.mkdtemp(prefix=prefix)))
    atexit.register(shutil.rmtree, path, ignore_errors=True)
    return path


def _copy_tracked(into: Path) -> None:
    into.mkdir(parents=True, exist_ok=True)
    for name in TRACKED:
        source = ROOT / ".beads" / name
        if source.is_file():
            shutil.copy2(source, into / name)


def no_database() -> Path:
    """A checkout as a runner sees it: the tracked bead files, no database."""
    workspace = _workspace("cairn-nodb-")
    _copy_tracked(workspace / ".beads")
    return workspace


def _build(workspace: Path) -> None:
    """`br init` refuses while a `.beads` directory carrying no database is in
    place, so the tracked files are laid down only after the store exists."""
    subprocess.run(["br", "init"], cwd=workspace, capture_output=True, text=True, timeout=BR_TIMEOUT_S, check=True)
    _copy_tracked(workspace / ".beads")
    subprocess.run(
        ["br", "sync", "--import-only"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=BR_TIMEOUT_S,
        check=True,
    )


@functools.lru_cache(maxsize=1)
def bead_store() -> Path:
    workspace = _workspace("cairn-beadstore-")
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), str(workspace)],
        capture_output=True,
        text=True,
        timeout=BR_TIMEOUT_S,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"building a bead store in {workspace} exited {proc.returncode}: {proc.stderr}")
    return workspace


if __name__ == "__main__":
    _build(Path(sys.argv[1]))
