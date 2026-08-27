"""Resolve which commit closed a bead, from the bead store's own history.

A commit message that names a bead id is not evidence that the commit closed it.
`research/SESSION-PROMPTS.md` asks every session to cite the beads it worked on, so
the newest commit whose message mentions an id usually belongs to some other bead,
and a rule keyed on the message moves whenever an unrelated session commits.

The bead store cannot say that. A bead's status flips to `closed` in exactly one
commit: the one that closed it. That flip is what the git hooks already read to
decide which beads a commit closes, and it is the rule here.

  usage: closing_commit.py --staged
         closing_commit.py --commit <ref>
         closing_commit.py [--root <path>] <bead-id> ...

`--staged` and `--commit` print the ids that commit closes, one per line -- the form
the git hooks consume. With bead ids, prints `<bead-id> <sha>` for an id closed in
history, `<bead-id> STAGED` for one the pending commit closes, and
`<bead-id> UNKNOWN` for one no commit closed.

Exit 0 on an answer, 2 on a usage error, and 3 when git itself failed. The third is
its own code because an empty stdout otherwise reads as "this commit closes no bead",
and a caller that gates on that would skip every gate keyed to a close.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ID_RE = re.compile(r'"id"\s*:\s*"([a-z][a-z0-9_.-]*)"')
STATUS_RE = re.compile(r'"status"\s*:\s*"([a-z_]+)"')
FILE_RE = re.compile(r"^diff --git a/.* b/(.*)$")
BEAD_STORE_PATHSPEC = ":(glob).beads/*.jsonl"
STAGED = "STAGED"
UNKNOWN = "UNKNOWN"
GIT_TIMEOUT_SECONDS = 120
GIT_FAILED_EXIT = 3


def newly_closed(diff_text: str) -> list[str]:
    """Bead ids whose status flips to closed in one unified diff of the bead store.

    The pathspec is plural, so a bead's row can appear in more than one file of a
    single diff; the before and after status are held per file, or one file's
    unchanged copy of a row erases another file's flip.
    """
    old: dict[tuple[str | None, str], str] = {}
    new: dict[tuple[str | None, str], str] = {}
    path: str | None = None
    for line in diff_text.splitlines():
        match_file = FILE_RE.match(line)
        if match_file:
            path = match_file.group(1)
            continue
        if line.startswith(("+++", "---")) or not line.startswith(("+", "-")):
            continue
        match_id, match_status = ID_RE.search(line), STATUS_RE.search(line)
        if not (match_id and match_status):
            continue
        (new if line.startswith("+") else old)[(path, match_id.group(1))] = match_status.group(1)
    return sorted({key[1] for key, status in new.items() if status == "closed" and old.get(key) != "closed"})


def history_closings(log_text: str) -> dict[str, str]:
    """Map each bead id to the sha of the commit that closed it.

    `log_text` is `git log -p --format=%x00%H` over the bead store, newest first;
    the oldest close of a reopened bead therefore loses to its latest one.
    """
    closings: dict[str, str] = {}
    for chunk in reversed(log_text.split("\x00")[1:]):
        sha, _, body = chunk.partition("\n")
        sha = sha.strip()
        if not sha:
            continue
        for bid in newly_closed(body):
            closings[bid] = sha
    return closings


def closings(log_text: str, staged_diff_text: str = "") -> dict[str, str]:
    resolved = history_closings(log_text)
    for bid in newly_closed(staged_diff_text):
        resolved[bid] = STAGED
    return resolved


class GitError(RuntimeError):
    """git could not answer, so no bead may be called unclosed on its silence."""


def _git(root: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} exited {proc.returncode}: {proc.stderr.strip()[-400:]}")
    return proc.stdout


def git_history_reader(root: Path):
    def read() -> str:
        return _git(root, ["log", "--all", "-p", "--unified=0", "--format=%x00%H", "--", BEAD_STORE_PATHSPEC])

    return read


def git_staged_reader(root: Path):
    def read() -> str:
        return _git(root, ["diff", "--cached", "--unified=0", "--", BEAD_STORE_PATHSPEC])

    return read


def git_commit_reader(root: Path, ref: str):
    def read() -> str:
        return _git(root, ["show", ref, "--unified=0", "--format=", "--", BEAD_STORE_PATHSPEC])

    return read


def resolve(root: Path, *, history=None, staged=None) -> dict[str, str]:
    history = history or git_history_reader(root)
    staged = staged or git_staged_reader(root)
    return closings(history(), staged())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bead_ids", nargs="*")
    parser.add_argument("--root", default=".")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--commit")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not (args.staged or args.commit or args.bead_ids):
        parser.print_usage(sys.stderr)
        return 2
    try:
        if args.staged or args.commit:
            read = git_commit_reader(root, args.commit) if args.commit else git_staged_reader(root)
            for bid in newly_closed(read()):
                print(bid)
            return 0
        resolved = resolve(root)
    except GitError as failure:
        print(f"closing_commit: GIT-FAILED {failure}", file=sys.stderr)
        return GIT_FAILED_EXIT
    for bid in args.bead_ids:
        print(f"{bid} {resolved.get(bid, UNKNOWN)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
