"""Decide which paths each fast gate checks for one commit.

`scripts/check.sh` runs the same five gates for the hook and for CI, and the hook's
run is over the whole tree, so one lane's unformatted or misspelled file refuses every
other lane's commit. The hook therefore names the paths its commit stages and CI keeps
the whole-tree form.

Which paths a gate takes is not uniform. `ruff` and `ty` are given `src tests scripts`
and `src tests` today, so a staged `research/grounding/probe.py` is outside both and
scoping must not pull it in. `codespell` walks the tree minus the skip list in
`pyproject.toml`, and that list is matched against a walk, so a vendored file named on
the command line is checked unless the skip is applied here. The theater gate resolves
its own policy globs and receives the whole list.

  usage: gate_scope.py staged [--root <path>]
         gate_scope.py plan [--root <path>] [--] <path> ...

`staged` prints the paths the pending commit stages, deletions excluded, one per line.
`plan` prints one `<gate>\t<path>` line per argument a gate takes; a gate with no line
has nothing staged in its scope and its caller skips it by name rather than running it
over an empty argument list, which is how `ruff` would silently widen back to the tree.

Exit 0 on an answer, 2 on a usage error or an empty path list, and 3 when git failed.
An empty list is a usage error because a caller that passed it would otherwise run no
gate at all and report a pass.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

GATES = ("format", "lint", "spelling", "types", "theater")
PYTHON_SCOPES = {
    "format": ("src", "tests", "scripts"),
    "lint": ("src", "tests", "scripts"),
    "types": ("src", "tests"),
}
GIT_TIMEOUT_SECONDS = 120
USAGE_EXIT = 2
GIT_FAILED_EXIT = 3


def staged(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "diff", "--cached", "--name-only", "--diff-filter=d", "-z"],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff --cached exited {proc.returncode}: {proc.stderr.strip()}")
    return [entry for entry in proc.stdout.split("\0") if entry]


def codespell_skips(root: Path) -> tuple[str, ...]:
    config = root / "pyproject.toml"
    if not config.is_file():
        return ()
    raw = tomllib.loads(config.read_text()).get("tool", {}).get("codespell", {}).get("skip", "")
    return tuple(entry.strip().removeprefix("./").rstrip("/") for entry in raw.split(",") if entry.strip())


def under(path: str, prefixes: tuple[str, ...]) -> bool:
    parts = PurePosixPath(path).parts
    return any(parts[: len(PurePosixPath(prefix).parts)] == PurePosixPath(prefix).parts for prefix in prefixes)


def for_gate(gate: str, paths: list[str], skips: tuple[str, ...]) -> list[str]:
    if gate in PYTHON_SCOPES:
        return [p for p in paths if p.endswith(".py") and under(p, PYTHON_SCOPES[gate])]
    if gate == "spelling":
        return [p for p in paths if not under(p, skips)]
    return list(paths)


def plan(paths: list[str], skips: tuple[str, ...]) -> list[tuple[str, str]]:
    return [(gate, path) for gate in GATES for path in for_gate(gate, paths, skips)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__)
    parser.add_argument("mode", choices=("staged", "plan"))
    parser.add_argument("--root", default=None)
    parser.add_argument("paths", nargs="*")
    ns = parser.parse_args(argv)
    root = Path(ns.root).resolve() if ns.root else Path(__file__).resolve().parents[1]

    if ns.mode == "staged":
        if ns.paths:
            print("staged takes no path arguments", file=sys.stderr)
            return USAGE_EXIT
        try:
            for path in staged(root):
                print(path)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            print(f"the staged path list is unknown: {exc}", file=sys.stderr)
            return GIT_FAILED_EXIT
        return 0

    if not ns.paths:
        print("plan needs at least one path; an empty scope checks nothing.", file=sys.stderr)
        return USAGE_EXIT
    for gate, path in plan(ns.paths, codespell_skips(root)):
        print(f"{gate}\t{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
