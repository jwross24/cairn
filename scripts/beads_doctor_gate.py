"""Classify `br doctor --json` into what may block the compliance audit.

    scripts/beads_doctor_gate.py [--db <path>] [--report-file <path>]

The compliance audit's precondition is a readable bead store, and `br doctor`
answers that question in a vocabulary the audit does not share. Under br 0.2.22
a satisfied dependency edge and a malformed SQLite page both leave exit 1 and
`ok: false`, so the exit code separates nothing; the difference is carried by
each check's `status` and by `workspace_health`.

Observed on br 0.2.22 in this repo:

    two dep WARNs      exit 1  ok=false  workspace_health=healthy
                               statuses {ok, warn}, anomaly_count=0
    malformed page     exit 1  ok=false  workspace_health=recoverable
                               statuses {ok, warn, error}, 3 anomalies
                               each with severity=recoverable

Corruption therefore arrives as `status: "error"` and `severity: "recoverable"`,
neither of which is the `"fail"` / `"error"` pair a reader would expect. A gate
that names the blocking values misses it, so this one names the benign values
and blocks on everything else, including any status it has never seen.

Exit codes follow src/cairn/exits.py: 0 the audit may run, 2 a doctor finding
blocks it, 3 doctor could not be run or its output did not parse, 64 usage.

Every invocation appends one line to .check.log: DOCTOR-CLEAR, DOCTOR-ADVISORY,
DOCTOR-BLOCKED, DOCTOR-INFRA or BYPASS.

Bypass, named and logged: CAIRN_DOCTOR_GATE_OK='<reason>'
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

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_ENVIRONMENT = 3
EXIT_USAGE = 64

BR_TIMEOUT_SECONDS = 120

# Established by observation, not by reading a schema: these are the only two
# check statuses br 0.2.22 emits on a store whose pages are intact. Anything
# else — "error", or a value a later br introduces — is outside what this gate
# has evidence for, and an unrecognized status is treated as a defect.
BENIGN_STATUSES = frozenset({"ok", "warn"})

# "recoverable" is the label a malformed page produces, so it is absent here.
BENIGN_HEALTH = frozenset({"healthy", "degraded"})

# No anomaly of any severity was observed on an intact store, so there is no
# severity this gate can call benign from evidence.
BENIGN_ANOMALY_SEVERITIES: frozenset[str] = frozenset()

# A WARN can still carry corruption: on the malformed copy,
# `audit.suspect_close_reasons` stayed at "warn" while its message read
# "database disk image is malformed". Status alone would clear it.
CORRUPTION_RE = re.compile(
    r"malformed|corrupt|disk image|btree|b-tree|page type|not a database|"
    r"file is encrypted|integrity",
    re.IGNORECASE,
)

# Names whose subject is the store's integrity rather than its contents. A
# non-ok result on any of these blocks whatever its message says.
INTEGRITY_NAME_RE = re.compile(r"integrity|schema|corrupt", re.IGNORECASE)


@dataclass
class Verdict:
    outcome: str
    blocking: list[str] = field(default_factory=list)
    advisory: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return {"clear": EXIT_OK, "advisory": EXIT_OK, "blocked": EXIT_REFUSED}[self.outcome]


def _describe(check: dict) -> str:
    name = check.get("name") or check.get("id") or "?"
    status = check.get("status", "<no status>")
    message = (check.get("message") or "").strip()
    line = f"{name} [{status}]"
    if message:
        line += f": {message}"
    remediation = (check.get("details") or {}).get("remediation")
    if remediation:
        line += f"\n      remediation: {remediation}"
    return line


def classify(report: object) -> Verdict:
    if not isinstance(report, dict):
        return Verdict("blocked", [f"doctor output is {type(report).__name__}, not an object"])

    if "error" in report and "checks" not in report:
        err = report["error"]
        message = err.get("message") if isinstance(err, dict) else str(err)
        return Verdict("blocked", [f"doctor refused to inspect the store: {message}"])

    checks = report.get("checks")
    if not isinstance(checks, list):
        return Verdict("blocked", ["doctor output carries no `checks` array, so nothing was inspected"])

    blocking: list[str] = []
    advisory: list[str] = []

    health = report.get("workspace_health")
    if not isinstance(health, str):
        blocking.append(f"workspace_health is {health!r}, so the rolled-up label is unreadable")
    elif health not in BENIGN_HEALTH:
        blocking.append(f"workspace_health is {health!r}, which is not a label this gate has cleared")

    for check in checks:
        if not isinstance(check, dict):
            blocking.append(f"a check entry is {type(check).__name__}, not an object")
            continue
        status = check.get("status")
        if status == "ok":
            continue
        name = str(check.get("name") or check.get("id") or "")
        message = str(check.get("message") or "")
        if not isinstance(status, str) or status not in BENIGN_STATUSES:
            blocking.append(f"unrecognized status — {_describe(check)}")
        elif INTEGRITY_NAME_RE.search(name):
            blocking.append(f"integrity check not ok — {_describe(check)}")
        elif CORRUPTION_RE.search(message):
            blocking.append(f"corruption named in the message — {_describe(check)}")
        else:
            advisory.append(_describe(check))

    audit = report.get("reliability_audit")
    if isinstance(audit, dict):
        anomalies = audit.get("anomalies")
        if isinstance(anomalies, list):
            for anomaly in anomalies:
                if not isinstance(anomaly, dict):
                    blocking.append(f"a reliability anomaly is {type(anomaly).__name__}, not an object")
                    continue
                severity = anomaly.get("severity")
                code = anomaly.get("code", "?")
                text = (anomaly.get("message") or "").strip()
                if severity not in BENIGN_ANOMALY_SEVERITIES:
                    blocking.append(f"reliability anomaly {code} [{severity}]: {text}")

    if blocking:
        return Verdict("blocked", blocking, advisory)
    if advisory:
        return Verdict("advisory", [], advisory)
    return Verdict("clear")


class Gate:
    def __init__(self, log: Path) -> None:
        self.log = log

    def say(self, text: str) -> None:
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self.log.open("a") as handle:
            handle.write(f"{stamp} {text}\n")


def resolve_db(root: Path, explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit)
    candidates = sorted((root / ".beads").glob("*.db"))
    return candidates[0] if candidates else None


def run_doctor(db: Path) -> tuple[object, str]:
    proc = subprocess.run(
        ["br", "--db", str(db), "doctor", "--json"],
        capture_output=True,
        text=True,
        timeout=BR_TIMEOUT_SECONDS,
        check=False,
    )
    raw = proc.stdout or proc.stderr
    return json.loads(raw), raw


def emit(verdict: Verdict) -> None:
    for line in verdict.blocking:
        print(f"    BLOCKS: {line}", file=sys.stderr)
    for line in verdict.advisory:
        print(f"    advisory: {line}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__)
    parser.add_argument("--db", default=None)
    parser.add_argument("--report-file", default=None)
    parser.add_argument("--root", default=None)
    parser.add_argument("--log", default=None)
    ns = parser.parse_args(argv)

    root = Path(ns.root).resolve() if ns.root else Path(__file__).resolve().parents[1]
    gate = Gate(Path(ns.log) if ns.log else root / ".check.log")

    skip = os.environ.get("CAIRN_DOCTOR_GATE_OK")
    if skip:
        gate.say(f"BYPASS beads-doctor-gate: {skip}")
        print(f"[doctor-gate] BYPASSED: {skip} (logged to {gate.log.name})", file=sys.stderr)
        return EXIT_OK

    if ns.report_file:
        try:
            report = json.loads(Path(ns.report_file).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            gate.say(f"DOCTOR-INFRA beads-doctor-gate: {ns.report_file} unreadable: {exc}")
            print(f"[doctor-gate] cannot read {ns.report_file}: {exc}", file=sys.stderr)
            return EXIT_ENVIRONMENT
    else:
        if shutil.which("br") is None:
            gate.say("DOCTOR-INFRA beads-doctor-gate: br not on PATH")
            print("[doctor-gate] br is not on PATH, so the audit's precondition is unknown.", file=sys.stderr)
            print("              bypass (logged): CAIRN_DOCTOR_GATE_OK='<reason>'", file=sys.stderr)
            return EXIT_ENVIRONMENT
        db = resolve_db(root, ns.db)
        if db is None or not db.is_file():
            gate.say(f"DOCTOR-INFRA beads-doctor-gate: no database at {db}")
            print(f"[doctor-gate] no bead database to inspect ({db}).", file=sys.stderr)
            return EXIT_ENVIRONMENT
        try:
            report, _raw = run_doctor(db)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            gate.say(f"DOCTOR-INFRA beads-doctor-gate: br doctor unusable: {exc}")
            print(f"[doctor-gate] br doctor produced nothing this gate can read: {exc}", file=sys.stderr)
            print("              bypass (logged): CAIRN_DOCTOR_GATE_OK='<reason>'", file=sys.stderr)
            return EXIT_ENVIRONMENT

    verdict = classify(report)
    if verdict.outcome == "clear":
        gate.say("DOCTOR-CLEAR beads-doctor-gate: every check ok")
        return EXIT_OK
    if verdict.outcome == "advisory":
        gate.say(f"DOCTOR-ADVISORY beads-doctor-gate: {len(verdict.advisory)} advisory finding(s)")
        print("[doctor-gate] br doctor reports findings that do not bear on the store's integrity.", file=sys.stderr)
        emit(verdict)
        print("              The compliance audit's precondition holds; proceeding.", file=sys.stderr)
        return EXIT_OK

    gate.say(f"DOCTOR-BLOCKED beads-doctor-gate: {len(verdict.blocking)} blocking finding(s)")
    print("[doctor-gate] REFUSED: br doctor reports the bead store may not be sound.", file=sys.stderr)
    print("              No bead was scored; this is the audit's precondition, not a score.", file=sys.stderr)
    emit(verdict)
    print("              Clear the finding above, or bypass (logged):", file=sys.stderr)
    print("              CAIRN_DOCTOR_GATE_OK='<reason>' git commit ...", file=sys.stderr)
    return verdict.exit_code


if __name__ == "__main__":
    sys.exit(main())
