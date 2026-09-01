"""Resolve a bead through `br`, and name the condition when that fails.

    from br_lookup import BeadLookupError, bead_row

Three different problems reach a gate as one nonzero exit from `br show`, and
they have three different fixes: `br` is not installed, the bead store has no
database, or the id names no bead. Under br 0.2.22 the middle one arrives as a
`SYNC_CONFLICT` whose message is "pending sync-merge state is unknown", which
reads as a conflict between two states rather than as an absent file, so a gate
that forwards the payload hands its reader the wrong problem.

Measured on br 0.2.22 in a workspace holding the tracked `.beads` files and no
database:

    br show <id> --json      exit 6  stdout error.code SYNC_CONFLICT
    br sync --import-only    exit 6  same refusal
    br init                  exit 6  same refusal

`br init` refuses while a `.beads` directory carrying no database is in place,
so the rebuild recipe moves that directory aside first. Every recognized code is
listed here; a code this module has never seen is UNREADABLE, which the callers
treat as blocking rather than as a bead that is merely absent.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

BR_TIMEOUT_SECONDS = 60

BR_ABSENT = "br-absent"
NO_DATABASE = "no-database"
UNKNOWN_BEAD = "unknown-bead"
UNREADABLE = "unreadable"

REBUILD_RECIPE = (
    "mv .beads .beads.tracked && br init && "
    "cp .beads.tracked/config.yaml .beads.tracked/metadata.json .beads/ && "
    "cp .beads.tracked/issues.jsonl .beads/issues.jsonl && br sync --import-only"
)

REMEDIATION = {
    BR_ABSENT: "install br, or run the gate against a body file instead of a bead id",
    NO_DATABASE: (
        "`.beads/beads.db` is derived state and is not committed; `.beads/issues.jsonl` is. "
        f"Rebuild the database from it: {REBUILD_RECIPE}"
    ),
    UNKNOWN_BEAD: "check the id against the store: br list --all",
    UNREADABLE: "br doctor --json names what the store is refusing",
}

# The error codes br 0.2.22 emits that carry a condition this module can name.
# Anything else keeps its own code and is reported as unreadable.
CODE_CONDITIONS = {
    "ISSUE_NOT_FOUND": UNKNOWN_BEAD,
    "SYNC_CONFLICT": NO_DATABASE,
}


class BeadLookupError(LookupError):
    def __init__(self, condition: str, detail: str) -> None:
        self.condition = condition
        self.detail = detail
        self.remediation = REMEDIATION.get(condition, REMEDIATION[UNREADABLE])
        super().__init__(f"{detail}; {self.remediation}")

    def headline(self, subject: str) -> str:
        """The condition in the words of whoever asked for `subject`."""
        if self.condition == UNKNOWN_BEAD:
            return f"{subject} is not in the bead store"
        if self.condition == NO_DATABASE:
            return "no bead database to resolve it against"
        if self.condition == BR_ABSENT:
            return "br is not installed"
        return f"the bead store would not answer for {subject}"


def as_lookup_error(exc: LookupError) -> BeadLookupError:
    """A resolver may raise a plain LookupError; it still has to name a condition."""
    return exc if isinstance(exc, BeadLookupError) else BeadLookupError(UNREADABLE, str(exc))


def describe(exc: LookupError, subject: str) -> str:
    named = as_lookup_error(exc)
    return f"{named.headline(subject)}: {named.detail}. {named.remediation}"


def beads_dir(start: Path | None = None) -> Path | None:
    """The `.beads` directory br would discover, by the same upward walk."""
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        found = candidate / ".beads"
        if found.is_dir():
            return found
    return None


def databases(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.db") if p.is_file())


def unavailable(start: Path | None = None) -> BeadLookupError | None:
    """The condition that stops any bead lookup here, before one is attempted."""
    if shutil.which("br") is None:
        return BeadLookupError(BR_ABSENT, "br is not on PATH")
    found = beads_dir(start)
    if found is None:
        return BeadLookupError(NO_DATABASE, f"no .beads directory above {(start or Path.cwd()).resolve()}")
    if not databases(found):
        return BeadLookupError(NO_DATABASE, f"no bead database in {found}")
    return None


def _error_payload(text: str) -> tuple[str, str]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return "", ""
    error = parsed.get("error") if isinstance(parsed, dict) else None
    if not isinstance(error, dict):
        return "", ""
    return str(error.get("code") or ""), str(error.get("message") or "")


def bead_row(bead_id: str, start: Path | None = None) -> dict:
    """The bead's fields, or a BeadLookupError naming which condition refused."""
    blocked = unavailable(start)
    if blocked is not None:
        raise blocked
    try:
        proc = subprocess.run(
            ["br", "show", bead_id, "--json"],
            capture_output=True,
            text=True,
            timeout=BR_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        raise BeadLookupError(UNREADABLE, f"br show {bead_id} did not answer within {BR_TIMEOUT_SECONDS}s") from expired
    except OSError as exc:
        raise BeadLookupError(UNREADABLE, f"br show {bead_id} could not be run: {exc}") from exc

    if proc.returncode != 0:
        code, message = _error_payload(proc.stdout)
        condition = CODE_CONDITIONS.get(code, UNREADABLE)
        named = f"br show {bead_id} exited {proc.returncode}"
        detail = f"{named} [{code}]: {message}" if code else f"{named}: {proc.stderr.strip()}"
        raise BeadLookupError(condition, detail)

    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise BeadLookupError(UNREADABLE, f"br show {bead_id} returned unreadable JSON: {exc}") from exc
    while isinstance(rows, list) and rows and isinstance(rows[0], list):
        rows = rows[0]
    row = rows[0] if isinstance(rows, list) and rows else rows
    if not isinstance(row, dict):
        raise BeadLookupError(UNKNOWN_BEAD, f"br show {bead_id} returned no bead")
    return row
