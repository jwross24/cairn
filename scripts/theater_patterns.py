"""Scan the working tree for the theater patterns audit-policy.yaml declares.

    scripts/theater_patterns.py [--root DIR] [--policy FILE] [--log FILE]

The vendored compliance skill reads `project_theater_patterns` only from its
`theater-detector.md` subagent, which the pre-commit path never runs;
`scripts/theater-scan.sh` carries a fixed catalog and opens no policy file. This
gate is cairn-owned, runs over the whole tree rather than one bead's cited files,
and keeps the skill unforked. Its findings gate the commit; they reach no
dimension of the audit's score.

The section is the switch: with no `project_theater_patterns` key the gate is off
and says so. A section that is present is binding, and every reason it cannot be
applied — an unparsable signature, an unknown severity, an exemption naming no
bead, an exemption whose bead is closed — refuses rather than scanning less.

Exit codes follow src/cairn/exits.py: 0 clean or off, 2 findings, 3 environment,
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
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_ENVIRONMENT = 3
EXIT_USAGE = 64

SECTION = "project_theater_patterns"
POLICY_NAMES = ("audit-policy.yaml", ".beads/audit-policy.yaml")
SEVERITIES = ("BLOCKING", "MAJOR", "MINOR", "NOTE")
TEST_MARKERS = ("test", "tests")
CLOSED = "closed"


class PolicyError(Exception):
    pass


@dataclass(frozen=True)
class Pattern:
    id: str
    signature: re.Pattern[str]
    file_glob: tuple[str, ...]
    in_test_files: bool
    severity: str
    rationale: str
    exempt_paths: tuple[str, ...]
    exempt_until_bead: str | None


@dataclass(frozen=True)
class Finding:
    pattern_id: str
    severity: str
    path: str
    line: int
    snippet: str
    rationale: str


@dataclass
class Outcome:
    kind: str
    patterns: int = 0
    scanned: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _text(entry: dict, key: str, where: str, *, required: bool = True) -> str:
    value = entry.get(key)
    if value is None and not required:
        return ""
    if not isinstance(value, str) or not value.strip():
        raise PolicyError(f"{where}: {key} must be a non-empty string")
    return value


def _pattern(entry: object, index: int) -> Pattern:
    where = f"{SECTION}[{index}]"
    if not isinstance(entry, dict):
        raise PolicyError(f"{where} is not a mapping")
    pattern_id = _text(entry, "id", where)
    where = f"{SECTION}[{index}] {pattern_id}"

    raw_signature = _text(entry, "signature", where)
    try:
        signature = re.compile(raw_signature)
    except re.error as exc:
        raise PolicyError(f"{where}: signature does not compile: {exc}") from exc

    globs = entry.get("file_glob")
    if isinstance(globs, str):
        globs = [globs]
    if not isinstance(globs, list) or not globs or not all(isinstance(g, str) and g.strip() for g in globs):
        raise PolicyError(f"{where}: file_glob must be a non-empty list of globs")

    in_test_files = entry.get("in_test_files", True)
    if not isinstance(in_test_files, bool):
        raise PolicyError(f"{where}: in_test_files must be a boolean")

    severity = _text(entry, "severity", where)
    if severity not in SEVERITIES:
        raise PolicyError(f"{where}: severity {severity!r} is not one of {', '.join(SEVERITIES)}")

    rationale = _text(entry, "rationale", where)

    exempt = entry.get("exempt_paths", [])
    if not isinstance(exempt, list) or not all(isinstance(p, str) and p.strip() for p in exempt):
        raise PolicyError(f"{where}: exempt_paths must be a list of paths")

    remover = entry.get("exempt_until_bead")
    if remover is not None and (not isinstance(remover, str) or not remover.strip()):
        raise PolicyError(f"{where}: exempt_until_bead must be a bead id")
    if exempt and not remover:
        raise PolicyError(
            f"{where}: {len(exempt)} exempt path(s) with no exempt_until_bead; "
            "an exemption that names no bead to remove it never expires"
        )

    return Pattern(
        id=pattern_id,
        signature=signature,
        file_glob=tuple(globs),
        in_test_files=in_test_files,
        severity=severity,
        rationale=rationale,
        exempt_paths=tuple(exempt),
        exempt_until_bead=remover,
    )


def load_patterns(document: object) -> list[Pattern]:
    if document is None or (isinstance(document, dict) and SECTION not in document):
        return []
    if not isinstance(document, dict):
        raise PolicyError("the policy file does not parse to a mapping")
    raw = document[SECTION]
    if not isinstance(raw, list) or not raw:
        raise PolicyError(f"{SECTION} is present but is not a non-empty list; delete the key to turn the gate off")
    return [_pattern(entry, index) for index, entry in enumerate(raw)]


def _is_test_path(rel: str) -> bool:
    return any(part in TEST_MARKERS or part.startswith("test_") for part in Path(rel).parts)


def targets(root: Path, pattern: Pattern) -> list[str]:
    seen: set[str] = set()
    for glob in pattern.file_glob:
        for path in root.glob(glob):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if not pattern.in_test_files and _is_test_path(rel):
                continue
            seen.add(rel)
    return sorted(seen)


def matches(text: str, pattern: Pattern) -> list[tuple[int, str]]:
    out = []
    for match in pattern.signature.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        out.append((line, " ".join(match.group(0).split())))
    return out


def exemption_problems(root: Path, pattern: Pattern, reachable: list[str]) -> list[str]:
    problems = []
    for rel in pattern.exempt_paths:
        path = root / rel
        if not path.is_file():
            problems.append(f"{pattern.id}: exempt path is absent from the tree: {rel}")
        elif rel not in reachable:
            problems.append(f"{pattern.id}: {rel} is exempt but no file_glob of this pattern reaches it")
        elif not pattern.signature.search(path.read_text(errors="replace")):
            problems.append(f"{pattern.id}: {rel} is exempt but no longer matches the signature")
    return problems


def evaluate(root: Path, document: object, *, bead_status=None) -> Outcome:
    try:
        patterns = load_patterns(document)
    except PolicyError as exc:
        return Outcome("DENY", problems=[str(exc)])
    if not patterns:
        return Outcome("OFF")

    problems: list[str] = []
    findings: list[Finding] = []
    scanned: set[str] = set()

    for pattern in patterns:
        reachable = targets(root, pattern)
        scanned.update(reachable)
        problems.extend(exemption_problems(root, pattern, reachable))

        if pattern.exempt_paths and pattern.exempt_until_bead:
            if bead_status is None:
                problems.append(
                    f"{pattern.id}: exempt_until_bead {pattern.exempt_until_bead} cannot be resolved; "
                    "an exemption whose expiry nobody can read never expires"
                )
            else:
                try:
                    status = bead_status(pattern.exempt_until_bead)
                except LookupError as exc:
                    problems.append(f"{pattern.id}: exempt_until_bead {pattern.exempt_until_bead}: {exc}")
                    status = None
                if status == CLOSED:
                    problems.append(
                        f"{pattern.id}: exempt_until_bead {pattern.exempt_until_bead} is closed; "
                        f"drop the {len(pattern.exempt_paths)} exempt_paths entries, or name the bead that owns the gap now"
                    )

        exempt = set(pattern.exempt_paths)
        for rel in reachable:
            if rel in exempt:
                continue
            for line, snippet in matches((root / rel).read_text(errors="replace"), pattern):
                findings.append(Finding(pattern.id, pattern.severity, rel, line, snippet, pattern.rationale))

    if problems:
        return Outcome("DENY", patterns=len(patterns), scanned=sorted(scanned), problems=problems)
    if findings:
        return Outcome("FAIL", patterns=len(patterns), scanned=sorted(scanned), findings=findings)
    return Outcome("PASS", patterns=len(patterns), scanned=sorted(scanned))


def bead_status_resolver():
    def resolve(bead_id: str) -> str:
        proc = subprocess.run(["br", "show", bead_id, "--json"], capture_output=True, text=True)
        if proc.returncode != 0:
            raise LookupError(f"br show exited {proc.returncode}: {proc.stderr.strip()}")
        try:
            rows = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise LookupError(f"br show returned unreadable JSON: {exc}") from exc
        while isinstance(rows, list) and rows and isinstance(rows[0], list):
            rows = rows[0]
        row = rows[0] if isinstance(rows, list) and rows else rows
        if not isinstance(row, dict):
            raise LookupError("br show returned no bead")
        return str(row.get("status") or "unknown")

    return resolve


def find_policy(root: Path, named: str | None) -> Path | None:
    if named:
        path = Path(named)
        return path if path.is_file() else None
    for name in POLICY_NAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def say(log: Path, text: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log.open("a") as handle:
        handle.write(f"{stamp} {text}\n")


def emit_findings(outcome: Outcome) -> None:
    print(f"[theater-patterns] REFUSED: {len(outcome.findings)} finding(s)", file=sys.stderr)
    for finding in outcome.findings:
        print(f"            {finding.severity} {finding.pattern_id}  {finding.path}:{finding.line}", file=sys.stderr)
        print(f"              {finding.snippet}", file=sys.stderr)
        print(f"              {finding.rationale}", file=sys.stderr)
    print(
        "            pair the skip with an assertion naming the degraded behavior, or add the file to\n"
        f"            {SECTION}[].exempt_paths in audit-policy.yaml beside the bead that removes it.",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__)
    parser.add_argument("--root", default=None)
    parser.add_argument("--policy", default=None)
    parser.add_argument("--log", default=None)
    ns = parser.parse_args(argv)

    root = Path(ns.root).resolve() if ns.root else Path(__file__).resolve().parents[1]
    log = Path(ns.log) if ns.log else root / ".check.log"

    skip = os.environ.get("CAIRN_THEATER_PATTERNS_SKIP")
    if skip:
        say(log, f"BYPASS theater-patterns: {skip}")
        print(f"[theater-patterns] BYPASSED: {skip} (logged to {log.name})", file=sys.stderr)
        return EXIT_OK

    policy = find_policy(root, ns.policy)
    if policy is None:
        named = ns.policy or " or ".join(POLICY_NAMES)
        say(log, f"DENY theater-patterns infra: no policy file at {named}")
        print(
            f"[theater-patterns] no policy file at {named}; refusing to report a clean tree unscanned.", file=sys.stderr
        )
        print("                 bypass (logged): CAIRN_THEATER_PATTERNS_SKIP='<reason>'", file=sys.stderr)
        return EXIT_ENVIRONMENT

    try:
        import yaml
    except ImportError:
        say(log, "DENY theater-patterns infra: PyYAML is not importable")
        print("[theater-patterns] PyYAML is not importable; the policy cannot be read.", file=sys.stderr)
        print("                 install: uv sync", file=sys.stderr)
        return EXIT_ENVIRONMENT

    try:
        document = yaml.safe_load(policy.read_text())
    except yaml.YAMLError as exc:
        say(log, f"DENY theater-patterns infra: {policy.name} does not parse: {exc}")
        print(f"[theater-patterns] {policy} does not parse as YAML: {exc}", file=sys.stderr)
        return EXIT_ENVIRONMENT

    outcome = evaluate(root, document, bead_status=bead_status_resolver() if shutil.which("br") else None)

    if outcome.kind == "OFF":
        say(log, f"OFF theater-patterns: {policy.name} declares no {SECTION}")
        print(f"[theater-patterns] off: {policy.name} declares no {SECTION}")
        return EXIT_OK
    if outcome.kind == "DENY":
        say(log, f"DENY theater-patterns policy: {len(outcome.problems)} problem(s)")
        print(f"[theater-patterns] the {SECTION} section cannot be applied as written:", file=sys.stderr)
        for problem in outcome.problems:
            print(f"            {problem}", file=sys.stderr)
        print("                 bypass (logged): CAIRN_THEATER_PATTERNS_SKIP='<reason>'", file=sys.stderr)
        return EXIT_ENVIRONMENT
    if outcome.kind == "FAIL":
        say(log, f"FAIL theater-patterns: {len(outcome.findings)} finding(s) over {len(outcome.scanned)} file(s)")
        emit_findings(outcome)
        print("                 bypass (logged): CAIRN_THEATER_PATTERNS_SKIP='<reason>'", file=sys.stderr)
        return EXIT_REFUSED

    say(log, f"PASS theater-patterns: {outcome.patterns} pattern(s) over {len(outcome.scanned)} file(s)")
    print(f"[theater-patterns] pass: {outcome.patterns} pattern(s) over {len(outcome.scanned)} file(s)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
