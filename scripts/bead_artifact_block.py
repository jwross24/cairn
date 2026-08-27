"""Parse and validate the ARTIFACTS block a closing bead's body must carry.

    scripts/bead_artifact_block.py <bead-id> [<bead-id> ...]
    scripts/bead_artifact_block.py --body-file <path>
    scripts/bead_artifact_block.py --print-path-hint-re

The block is the deterministic half of a close. A close already produces its
contents in prose; the block is the machine-readable form of the same material,
and it is what the compliance audit's deterministic extractor reads.

    ARTIFACTS-BEGIN
    source: `src/cairn/doctor.py` lines 1-420
    test: `tests/unit/test_doctor_purity.py` lines 1-160
    commit: 879f4f6
    command: uv run pytest -q tests/unit/test_doctor_purity.py
    ARTIFACTS-END

Exit codes follow src/cairn/exits.py: 0 valid, 2 refused, 3 environment,
64 usage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

BEGIN = "ARTIFACTS-BEGIN"
END = "ARTIFACTS-END"
GIT_TIMEOUT_SECONDS = 30
BR_TIMEOUT_SECONDS = 60

# Mirrors PATH_HINT_RE in the compliance skill's scripts/extract-spec.py. A path
# the extractor cannot see contributes nothing to the implementation dimension,
# so the gate requires at least one that it can. --print-path-hint-re exposes
# this pattern so bead-artifact-block.sh can compare it against the vendored one.
PATH_HINT_RE = re.compile(r"`([\w./_\-]+\.\w+|[\w./_\-]+/)`")

ENTRY_RE = re.compile(r"^(source|test|commit|command)\s*:\s*(.+?)\s*$")
PATH_VALUE_RE = re.compile(r"^`([^`]+)`(?:\s+lines\s+(\d+)\s*-\s*(\d+))?$")

BODY_FIELDS = ("title", "description", "design", "acceptance_criteria", "notes", "close_reason")

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_ENVIRONMENT = 3
EXIT_USAGE = 64

HOW_TO_ADD = f"""            add one to the bead body (br update <id> --notes=... keeps it out of the description):

              {BEGIN}
              source: `path/to/file.py` lines 10-42
              test: `tests/unit/test_thing.py` lines 1-88
              commit: <sha of a commit in this bead's slice>
              command: <a command re-executed at close>
              {END}

            at least one `source:` and one `command:` are required; every path is
            checked for existence and every `lines A-B` range against the file's length."""


@dataclass
class Block:
    sources: list[tuple[str, int | None, int | None]] = field(default_factory=list)
    tests: list[tuple[str, int | None, int | None]] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)

    @property
    def paths(self) -> list[tuple[str, int | None, int | None]]:
        return self.sources + self.tests


def parse_block(body: str) -> tuple[Block | None, list[str]]:
    """Return the single block in body, or None plus the reasons it is unusable."""
    lines = body.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    if not starts:
        return None, [f"the body carries no {BEGIN} block"]
    if len(starts) > 1:
        return None, [f"the body carries {len(starts)} {BEGIN} markers; exactly one block is allowed"]
    if not ends:
        return None, [f"the block opens with {BEGIN} and never closes with {END}"]
    if len(ends) > 1:
        return None, [f"the body carries {len(ends)} {END} markers; exactly one block is allowed"]
    if ends[0] < starts[0]:
        return None, [f"{END} appears before {BEGIN}"]

    block = Block()
    errors: list[str] = []
    for offset, raw in enumerate(lines[starts[0] + 1 : ends[0]], start=starts[0] + 2):
        line = raw.strip()
        if not line:
            continue
        entry = ENTRY_RE.match(line)
        if not entry:
            errors.append(f"line {offset}: not a block entry: {line!r} (expected `source|test|commit|command: ...`)")
            continue
        kind, value = entry.group(1), entry.group(2)
        if kind in ("source", "test"):
            pv = PATH_VALUE_RE.match(value)
            if not pv:
                errors.append(f"line {offset}: {kind} needs a backticked path, optionally `lines A-B`: {value!r}")
                continue
            start = int(pv.group(2)) if pv.group(2) else None
            end = int(pv.group(3)) if pv.group(3) else None
            if start is not None and end is not None and end < start:
                errors.append(f"line {offset}: line range {start}-{end} ends before it starts")
                continue
            target = block.sources if kind == "source" else block.tests
            target.append((pv.group(1), start, end))
        elif kind == "commit":
            block.commits.append(value)
        else:
            block.commands.append(value)
    return block, errors


def validate(block: Block, root: Path, *, resolve_commit=None) -> list[str]:
    """Every reason the block does not hold against the tree it claims."""
    errors: list[str] = []
    if not block.sources:
        errors.append("the block names no `source:` file; a close that changed no source is not a close")
    if not block.commands:
        errors.append("the block names no `command:`; a close re-executes at least one")

    for path, start, end in block.paths:
        target = root / path
        if not target.is_file():
            errors.append(f"named but absent: {path}")
            continue
        if end is None:
            continue
        length = len(target.read_text(errors="replace").splitlines())
        if end > length:
            errors.append(f"{path}: block claims lines {start}-{end}, the file has {length}")

    for sha in block.commits:
        if resolve_commit is None:
            continue
        if not resolve_commit(sha):
            errors.append(f"commit does not resolve in this repository: {sha}")

    if block.paths and not any(PATH_HINT_RE.search(f"`{p}`") for p, _, _ in block.paths):
        named = ", ".join(p for p, _, _ in block.paths)
        errors.append(
            "no path in the block is visible to the compliance extractor, so the audit would "
            f"measure nothing ({named}); name at least one path carrying a file extension"
        )
    return errors


def invisible_paths(block: Block) -> list[str]:
    return [p for p, _, _ in block.paths if not PATH_HINT_RE.search(f"`{p}`")]


def git_commit_resolver(root: Path):
    def resolve(sha: str) -> bool:
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "cat-file", "-e", f"{sha}^{{commit}}"],
                capture_output=True,
                timeout=GIT_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as expired:
            raise LookupError(
                f"git cat-file did not answer within {GIT_TIMEOUT_SECONDS}s for {sha}; "
                f"clear any stale index.lock and retry: git -C {root} status"
            ) from expired
        return proc.returncode == 0

    return resolve


def bead_body(bead_id: str) -> tuple[str, str]:
    """The concatenated fields the compliance extractor reads, plus the status."""
    try:
        proc = subprocess.run(
            ["br", "show", bead_id, "--json"], capture_output=True, text=True, timeout=BR_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired as expired:
        raise LookupError(
            f"br show {bead_id} did not answer within {BR_TIMEOUT_SECONDS}s; retry after: br sync --flush-only"
        ) from expired
    if proc.returncode != 0:
        raise LookupError(f"br show {bead_id} exited {proc.returncode}: {proc.stderr.strip()}")
    rows = json.loads(proc.stdout)
    while isinstance(rows, list) and rows and isinstance(rows[0], list):
        rows = rows[0]
    row = rows[0] if isinstance(rows, list) else rows
    body = "\n".join(str(row.get(f) or "") for f in BODY_FIELDS)
    return body, str(row.get("status") or "unknown")


def report(label: str, body: str, root: Path, *, resolve_commit=None) -> tuple[bool, list[str]]:
    block, parse_errors = parse_block(body)
    if block is None:
        return False, parse_errors
    errors = parse_errors + validate(block, root, resolve_commit=resolve_commit)
    if errors:
        return False, errors
    unseen = invisible_paths(block)
    if unseen:
        print(
            f"[artifact-block] {label}: the extractor cannot see {', '.join(unseen)}; "
            "those paths gate here but score nothing in the audit.",
            file=sys.stderr,
        )
    print(
        f"[artifact-block] pass {label}: {len(block.sources)} source, {len(block.tests)} test, "
        f"{len(block.commits)} commit, {len(block.commands)} command"
    )
    return True, []


SKILL_LEAF = "beads-compliance-and-completion-verification"
SKILL_RE = re.compile(r'^PATH_HINT_RE = re\.compile\(r"(.*)"\)$', re.MULTILINE)


def skill_candidates() -> list[Path]:
    named = os.environ.get("CAIRN_COMPLIANCE_SKILL")
    roots = [Path(named)] if named else []
    roots += [
        Path.cwd() / ".claude" / "skills" / SKILL_LEAF,
        Path.home() / ".claude" / "skills" / SKILL_LEAF,
        Path.home() / ".codex" / "skills" / SKILL_LEAF,
    ]
    return [r / "scripts" / "extract-spec.py" for r in roots]


def extractor_pattern() -> str | None:
    for path in skill_candidates():
        if path.is_file():
            found = SKILL_RE.search(path.read_text())
            return found.group(1) if found else ""
    return None


class Gate:
    def __init__(self, log: Path) -> None:
        self.log = log

    def say(self, text: str) -> None:
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self.log.open("a") as handle:
            handle.write(f"{stamp} {text}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__)
    parser.add_argument("bead_ids", nargs="*")
    parser.add_argument("--body-file")
    parser.add_argument("--root", default=None)
    parser.add_argument("--log", default=None)
    parser.add_argument("--print-path-hint-re", action="store_true")
    ns = parser.parse_args(argv)

    if ns.print_path_hint_re:
        print(PATH_HINT_RE.pattern)
        return EXIT_OK

    root = Path(ns.root).resolve() if ns.root else Path(__file__).resolve().parents[1]
    gate = Gate(Path(ns.log) if ns.log else root / ".check.log")
    subjects = " ".join(ns.bead_ids) or (ns.body_file or "")

    skip = os.environ.get("CAIRN_ARTIFACT_BLOCK_SKIP")
    if skip:
        gate.say(f"BYPASS artifact-block {subjects}: {skip}")
        print(f"[artifact-block] BYPASSED: {skip} (logged to {gate.log.name})", file=sys.stderr)
        return EXIT_OK

    if ns.body_file and ns.bead_ids:
        print("bead ids and --body-file are alternatives, not a pair", file=sys.stderr)
        return EXIT_USAGE
    if not ns.body_file and not ns.bead_ids:
        print(
            "usage: bead_artifact_block.py <bead-id> [<bead-id> ...] | --body-file <path>",
            file=sys.stderr,
        )
        return EXIT_USAGE

    # The gate requires a path the compliance extractor can see, and decides that with
    # its own copy of the extractor's regex. A copy that drifts from the vendored one
    # would pass a block the audit cannot read, which is the appearance of a gate and
    # none of its effect. Compared when the skill is installed; reported when not.
    theirs = extractor_pattern()
    if theirs is None:
        gate.say(
            "PARITY-UNKNOWN artifact-block: the compliance skill is not installed; the extractor regex was not compared"
        )
        print(
            "[artifact-block] the compliance skill is absent; the extractor-visibility rule ran "
            "against this repo's copy of its regex, uncompared.",
            file=sys.stderr,
        )
    elif theirs != PATH_HINT_RE.pattern:
        gate.say(f"DENY artifact-block parity: ours={PATH_HINT_RE.pattern} theirs={theirs}")
        print(
            "[artifact-block] PATH_HINT_RE in the compliance skill no longer matches this gate's copy.", file=sys.stderr
        )
        print(f"                 skill:  {theirs}", file=sys.stderr)
        print(f"                 cairn:  {PATH_HINT_RE.pattern}", file=sys.stderr)
        print("                 a block this gate accepts may extract nothing. Update PATH_HINT_RE in", file=sys.stderr)
        print("                 scripts/bead_artifact_block.py, or bypass (logged):", file=sys.stderr)
        print("                 CAIRN_ARTIFACT_BLOCK_SKIP='<reason>'", file=sys.stderr)
        return EXIT_ENVIRONMENT

    resolve_commit = git_commit_resolver(root) if (root / ".git").exists() else None

    if ns.body_file:
        try:
            ok, errors = report(ns.body_file, Path(ns.body_file).read_text(), root, resolve_commit=resolve_commit)
        except LookupError as exc:
            gate.say(f"DENY artifact-block infra: {ns.body_file} unverifiable: {exc}")
            print(f"[artifact-block] cannot verify {ns.body_file}: {exc}", file=sys.stderr)
            return EXIT_ENVIRONMENT
        if ok:
            gate.say(f"PASS artifact-block {ns.body_file}")
            return EXIT_OK
        emit(ns.body_file, errors)
        gate.say(f"FAIL artifact-block {ns.body_file}: {len(errors)} finding(s)")
        return EXIT_REFUSED

    if shutil.which("br") is None:
        gate.say("DENY artifact-block infra: br not on PATH")
        print(
            "[artifact-block] br is not installed; refusing to report a block as valid without reading it.",
            file=sys.stderr,
        )
        print("                 bypass (logged): CAIRN_ARTIFACT_BLOCK_SKIP='<reason>'", file=sys.stderr)
        return EXIT_ENVIRONMENT

    status = EXIT_OK
    findings = 0
    for bead_id in ns.bead_ids:
        try:
            body, bead_status = bead_body(bead_id)
        except (LookupError, json.JSONDecodeError, OSError) as exc:
            gate.say(f"DENY artifact-block infra: {bead_id} unreadable: {exc}")
            print(f"[artifact-block] cannot read {bead_id}: {exc}", file=sys.stderr)
            print("                 check the id: br list --all", file=sys.stderr)
            return EXIT_ENVIRONMENT
        try:
            ok, errors = report(f"{bead_id} ({bead_status})", body, root, resolve_commit=resolve_commit)
        except LookupError as exc:
            gate.say(f"DENY artifact-block infra: {bead_id} unverifiable: {exc}")
            print(f"[artifact-block] cannot verify {bead_id}: {exc}", file=sys.stderr)
            return EXIT_ENVIRONMENT
        if not ok:
            emit(bead_id, errors)
            findings += len(errors)
            status = EXIT_REFUSED
    if status == EXIT_OK:
        gate.say(f"PASS artifact-block {subjects}")
    else:
        gate.say(f"FAIL artifact-block {subjects}: {findings} finding(s)")
        print("                 bypass (logged): CAIRN_ARTIFACT_BLOCK_SKIP='<reason>'", file=sys.stderr)
    return status


def emit(label: str, errors: list[str]) -> None:
    print(f"[artifact-block] REFUSED {label}", file=sys.stderr)
    for err in errors:
        print(f"            {err}", file=sys.stderr)
    print(HOW_TO_ADD, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
