#!/usr/bin/env python3
"""Refuse a commit whose index changed after the gates read it.

  usage: index_tree_guard.py capture [--root <path>]
         index_tree_guard.py check --before <tree> [--root <path>] [--log <path>]

`capture` prints `git write-tree` for the index. `check` writes the tree again and
exits 0 when it equals `--before`, 1 when a later step changed it (the changed paths
go to stderr), and 3 when git could not answer. Every outcome appends one line to the
log (default `.check.log` under the root). `CAIRN_AUDIT_INDEX_OK='<reason>'` turns a
refusal into a logged bypass.
"""

from __future__ import annotations

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path

GIT_TIMEOUT_SECONDS = 120
GIT_FAILED_EXIT = 3
CHANGED_EXIT = 1
BYPASS_ENV = "CAIRN_AUDIT_INDEX_OK"


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )


def write_tree(root: Path) -> str | None:
    proc = git(root, "write-tree")
    tree = proc.stdout.strip()
    return tree if proc.returncode == 0 and tree else None


def log_line(log: Path, text: str) -> None:
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log.open("a") as handle:
        handle.write(f"{stamp} {text}\n")


def changed_paths(root: Path, before: str, after: str) -> str:
    proc = git(root, "diff-tree", "-r", "--name-status", before, after)
    return proc.stdout if proc.returncode == 0 else f"(git diff-tree exited {proc.returncode})\n"


def check(root: Path, before: str, log: Path) -> int:
    after = write_tree(root)
    if after is None:
        log_line(log, "DENY index-changed-by-audit: git write-tree failed; the index is unknown")
        print("[index-tree-guard] git write-tree failed; the index after the audit is unknown.", file=sys.stderr)
        return GIT_FAILED_EXIT
    if after == before:
        log_line(log, f"ALLOW index-unchanged-by-audit {after}")
        return 0
    paths = changed_paths(root, before, after)
    count = len(paths.splitlines())
    reason = os.environ.get(BYPASS_ENV, "")
    print(
        f"[index-tree-guard] the compliance audit changed the index ({count} paths):\n{paths}",
        file=sys.stderr,
        end="",
    )
    if reason:
        log_line(log, f"BYPASS index-changed-by-audit: {reason} ({count} paths, {before} -> {after})")
        return 0
    log_line(log, f"DENY index-changed-by-audit ({count} paths, {before} -> {after})")
    print(f"             Unstage them, or bypass: {BYPASS_ENV}='<reason>' git commit ...", file=sys.stderr)
    return CHANGED_EXIT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("capture", "check"):
        command = sub.add_parser(name)
        command.add_argument("--root", type=Path, default=Path.cwd())
        if name == "check":
            command.add_argument("--before", required=True)
            command.add_argument("--log", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.command == "capture":
        tree = write_tree(args.root)
        if tree is None:
            print("[index-tree-guard] git write-tree failed; nothing to compare against.", file=sys.stderr)
            return GIT_FAILED_EXIT
        print(tree)
        return 0
    return check(args.root, args.before, args.log or args.root / ".check.log")


if __name__ == "__main__":
    sys.exit(main())
