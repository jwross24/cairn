"""Exit 0 while a file no commit touches can refuse that commit's gate.

The pre-commit hook and CI both call `scripts/check.sh`. Given no `--paths` the gates
read the whole tree, so a file another lane is mid-write on refuses a commit that does
not stage it: twice on 2026-09-08, on `lean/FormalConjecturesUtil/...` and then on
`src/cairn/ladder.py`.

The probe copies the trees the fast gates read into a sandbox, plants one unformatted
file there, and runs the gate twice over it: once as `HEAD` runs it, and once as this
change runs it with the scope a commit of clean paths would name. It exits 0 while the
first refuses and the second passes, and nonzero once either stops.

  usage: uv run python research/grounding/bie_repro.py [--keep <dir>]

Nothing is planted in the working tree, so a run cannot refuse another lane's commit.
The sandbox reuses this checkout's virtual environment read-only through
`UV_PROJECT_ENVIRONMENT` and `UV_NO_SYNC`, rather than resolving a second one.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COPIED = ("pyproject.toml", "audit-policy.yaml", "src", "scripts", "tests")
PLANT = Path("src") / "cairn" / "bie_probe_plant.py"
UNFORMATTED = "import os\nx  =   1\n"
CLEAN_SCOPE = ("scripts/gate_scope.py",)
GATE_TIMEOUT_SECONDS = 1800


def tool(name: str) -> str:
    found = shutil.which(name)
    if found is None:
        raise RuntimeError(f"{name} is not on PATH; the probe cannot run the gate it reports on")
    return found


def sandbox(at: Path) -> Path:
    at.mkdir(parents=True, exist_ok=True)
    for name in COPIED:
        source = ROOT / name
        target = at / name
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"), dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
    (at / PLANT).write_text(UNFORMATTED)
    return at


def run(at: Path, args: list[str]) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "UV_PROJECT_ENVIRONMENT": str(ROOT / ".venv"),
        "UV_NO_SYNC": "1",
        "CAIRN_THEATER_PATTERNS_SKIP": "probe sandbox: the theater policy names paths outside the copied trees",
    }
    return subprocess.run(
        [tool("bash"), "scripts/check.sh", *args],
        cwd=at,
        capture_output=True,
        text=True,
        timeout=GATE_TIMEOUT_SECONDS,
        env=env,
        check=False,
    )


def failed_gates(proc: subprocess.CompletedProcess) -> list[str]:
    return [line.split("FAIL ", 1)[1].strip() for line in proc.stderr.splitlines() if "[check] FAIL " in line]


def head_version(rel: str) -> str:
    proc = subprocess.run(
        [tool("git"), "-C", str(ROOT), "show", f"HEAD:{rel}"],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return proc.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__)
    parser.add_argument("--keep", default=None)
    ns = parser.parse_args(argv)
    at = sandbox(Path(ns.keep) if ns.keep else Path(tempfile.mkdtemp(prefix="bie-repro-")))

    scoped = run(at, ["--fast", "--paths", *CLEAN_SCOPE])
    (at / "scripts" / "check.sh").write_text(head_version("scripts/check.sh"))
    whole = run(at, ["--fast"])

    print(f"sandbox:         {at}")
    print(f"plant:           {PLANT.as_posix()} (unformatted, staged by nothing)")
    print(f"staged scope:    {' '.join(CLEAN_SCOPE)}")
    print(f"HEAD check.sh:   exit {whole.returncode}, failed gates {failed_gates(whole) or 'none'}")
    print(f"scoped check.sh: exit {scoped.returncode}, failed gates {failed_gates(scoped) or 'none'}")

    refuses_an_untouched_file = whole.returncode != 0 and "format" in failed_gates(whole)
    clean_scope_passes = scoped.returncode == 0
    print(f"\nVERDICT a file no commit touches refuses the gate HEAD runs: {refuses_an_untouched_file}")
    print(f"VERDICT the same tree passes the gate scoped to the staged paths: {clean_scope_passes}")
    return 0 if refuses_an_untouched_file and clean_scope_passes else 1


if __name__ == "__main__":
    sys.exit(main())
