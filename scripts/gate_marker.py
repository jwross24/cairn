"""Record which beads the pre-commit gates ran for, so post-commit can refuse the rest.

`.githooks/pre-commit` learns which beads a commit closes from the staged diff, and
`git diff --cached` compares the index to HEAD. During `git commit --amend` that HEAD
already carries the close, so the staged diff shows no status flip and the test-plan
gate, the artifact-block gate and the attribution corrector all sit out. `git show HEAD`
after the amend still shows the flip, so `.githooks/post-commit` would push a close that
passed none of its gates.

Detecting an amend from inside pre-commit is not the rule here. Pre-commit instead
records the ids it actually gated, and post-commit refuses to push a closed bead that
record does not name.

The record is single-use: `check` deletes it whatever the verdict, so a run that leaves
one behind cannot vouch for the next commit. It also carries the sha the gated commit
was to sit on, and post-commit compares that against the new commit's first parent --
an amend replaces a commit rather than sitting on it, so the two disagree there.

  usage: gate_marker.py record --git-dir <dir> --parent <sha> [<bead-id> ...]
         gate_marker.py check  --git-dir <dir> --parent <sha> [<bead-id> ...]

`check` prints one line and exits 0 to allow the push, 1 to deny it. The record lives
inside the git directory, which is never part of the worktree and needs no ignore rule.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MARKER_NAME = "cairn-gated-beads.json"
OK = "OK"
DENY = "DENY"
EXIT_BY_VERDICT = {OK: 0, DENY: 1}


def marker_path(git_dir: str | Path) -> Path:
    return Path(git_dir) / MARKER_NAME


def record_text(parent: str, bead_ids) -> str:
    return json.dumps({"parent": parent, "gated": sorted(set(bead_ids))}, indent=2, sort_keys=True) + "\n"


def write_record(path: Path, parent: str, bead_ids) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record_text(parent, bead_ids))


def read_record(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except OSError, json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def describe(sha: str) -> str:
    return sha or "(no parent)"


def verdict(record: dict | None, closed_ids, parent: str) -> tuple[str, str]:
    closed = sorted(set(closed_ids))
    if not closed:
        return OK, "this commit closes no bead, so no gate was owed"
    named = ", ".join(closed)
    if record is None:
        return DENY, f"the pre-commit gates left no record, so {named} closed without them"
    recorded_parent = str(record.get("parent", ""))
    if recorded_parent != parent:
        return DENY, (
            f"the gate record was written for a commit sitting on {describe(recorded_parent)} "
            f"and this one sits on {describe(parent)}, so it says nothing about {named}"
        )
    gated = {str(bead) for bead in record.get("gated") or []}
    missing = [bead for bead in closed if bead not in gated]
    if missing:
        return DENY, f"the pre-commit gates never ran for {', '.join(missing)}"
    return OK, f"the pre-commit gates covered {named}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("record", "check"))
    parser.add_argument("bead_ids", nargs="*")
    parser.add_argument("--git-dir", required=True)
    parser.add_argument("--parent", default="")
    args = parser.parse_args(argv)

    path = marker_path(args.git_dir)
    if args.action == "record":
        try:
            write_record(path, args.parent, args.bead_ids)
        except OSError as failure:
            print(f"gate-marker: cannot write {path}: {failure}", file=sys.stderr)
            return 2
        print(f"gate-marker: recorded {len(set(args.bead_ids))} gated bead(s) on {describe(args.parent)}")
        return 0

    record = read_record(path)
    path.unlink(missing_ok=True)
    outcome, reason = verdict(record, args.bead_ids, args.parent)
    print(f"{outcome} {reason}")
    return EXIT_BY_VERDICT[outcome]


if __name__ == "__main__":
    sys.exit(main())
