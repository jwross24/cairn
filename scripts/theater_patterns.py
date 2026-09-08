"""Scan the working tree for the theater patterns audit-policy.yaml declares.

    scripts/theater_patterns.py [--root DIR] [--policy FILE] [--log FILE] [PATH ...]

The vendored compliance skill reads `project_theater_patterns` only from its
`theater-detector.md` subagent, which the pre-commit path never runs;
`scripts/theater-scan.sh` carries a fixed catalog and opens no policy file. This
gate is cairn-owned, runs over the whole tree rather than one bead's cited files,
and keeps the skill unforked. Named paths narrow the scan to those files, which is
how `scripts/check.sh --paths` keeps a commit's gate off files the commit does not
touch; the exemption cross-check stays whole-tree, since a stale allowance is stale
wherever the file sits. Its findings gate the commit; they reach no
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
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import br_lookup

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_ENVIRONMENT = 3
EXIT_USAGE = 64

SECTION = "project_theater_patterns"
POLICY_NAMES = ("audit-policy.yaml", ".beads/audit-policy.yaml")
SEVERITIES = ("BLOCKING", "MAJOR", "MINOR", "NOTE")
TEST_MARKERS = ("test", "tests")
CLOSED = "closed"
EXPIRY_BEAD = "cairn-pwj"


class PolicyError(Exception):
    pass


@dataclass(frozen=True)
class Exemption:
    path: str
    matches: int


@dataclass(frozen=True)
class Pattern:
    id: str
    signature: re.Pattern[str]
    file_glob: tuple[str, ...]
    in_test_files: bool
    severity: str
    rationale: str
    exempt_paths: tuple[Exemption, ...]
    exempt_until_bead: str | None


@dataclass(frozen=True)
class Finding:
    pattern_id: str
    severity: str
    path: str
    line: int
    snippet: str
    rationale: str
    note: str = ""


@dataclass
class Outcome:
    kind: str
    patterns: int = 0
    scanned: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


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

    exempt = _exemptions(entry.get("exempt_paths", []), where)

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
        exempt_paths=exempt,
        exempt_until_bead=remover,
    )


def _exemptions(raw: object, where: str) -> tuple[Exemption, ...]:
    """An exempt path carries the count it is exempt for, so growth is a finding."""
    if not isinstance(raw, list):
        raise PolicyError(f"{where}: exempt_paths must be a list")
    out = []
    for item in raw:
        if isinstance(item, str):
            raise PolicyError(
                f"{where}: exempt_paths entry {item!r} is a bare path; "
                "each entry needs the count it is exempt for: `- path: <file>` / `  matches: <n>`"
            )
        if not isinstance(item, dict):
            raise PolicyError(f"{where}: exempt_paths entry is not a mapping: {item!r}")
        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            raise PolicyError(f"{where}: an exempt_paths entry has no path")
        count = item.get("matches")
        if isinstance(count, bool) or not isinstance(count, int):
            raise PolicyError(f"{where}: {path}: matches must be an integer")
        if count < 1:
            raise PolicyError(f"{where}: {path}: matches is {count}; drop the entry rather than exempting no match")
        unknown = set(item) - {"path", "matches"}
        if unknown:
            raise PolicyError(f"{where}: {path}: unknown exempt_paths key(s): {', '.join(sorted(unknown))}")
        out.append(Exemption(path=path, matches=count))
    seen = [e.path for e in out]
    duplicated = sorted({q for q in seen if seen.count(q) > 1})
    if duplicated:
        raise PolicyError(f"{where}: exempt_paths names {', '.join(duplicated)} more than once")
    return tuple(out)


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
    """Every reason an exemption no longer describes the tree it was written against.

    A count that has dropped is the stale half: the policy claims cover for matches
    that are not there, so the allowance would silently absorb a future one.
    """
    problems = []
    for exemption in pattern.exempt_paths:
        rel = exemption.path
        path = root / rel
        if not path.is_file():
            problems.append(f"{pattern.id}: exempt path is absent from the tree: {rel}")
            continue
        if rel not in reachable:
            problems.append(f"{pattern.id}: {rel} is exempt but no file_glob of this pattern reaches it")
            continue
        found = len(matches(path.read_text(errors="replace"), pattern))
        if found < exemption.matches:
            carries = f"carries {found}" if found else "no longer matches the signature and carries 0"
            problems.append(
                f"{pattern.id}: {rel} is exempt for {exemption.matches} match(es) but {carries}; "
                "lower matches to the real count so the allowance cannot absorb a new skip"
            )
    return problems


def evaluate(root: Path, document: object, *, bead_status=None, resolver_absence=None, scope=None) -> Outcome:
    try:
        patterns = load_patterns(document)
    except PolicyError as exc:
        return Outcome("DENY", problems=[str(exc)])
    if not patterns:
        return Outcome("OFF")

    problems: list[str] = []
    warnings: list[str] = []
    findings: list[Finding] = []
    scanned: set[str] = set()

    for pattern in patterns:
        reachable = targets(root, pattern)
        # The exemption cross-check reads the whole tree whatever the scan covers: an
        # allowance whose count has dropped is stale wherever the file sits, and a scope
        # that hid it would let the next skip in unseen.
        problems.extend(exemption_problems(root, pattern, reachable))
        if scope is not None:
            reachable = [rel for rel in reachable if rel in scope]
        scanned.update(reachable)

        # An unreadable expiry costs one auxiliary cross-check; the scan, the counts and
        # every finding are unaffected, so it warns. A resolver that IS available and
        # cannot find the bead is a misconfiguration, and that still refuses.
        if pattern.exempt_paths and pattern.exempt_until_bead:
            if bead_status is None:
                reason = (
                    resolver_absence.headline(pattern.exempt_until_bead)
                    if resolver_absence is not None
                    else "br is not on PATH"
                )
                warnings.append(
                    f"{pattern.id}: exempt_until_bead {pattern.exempt_until_bead} was not checked; "
                    f"{reason}, so whether the exemption has expired is unknown here"
                )
            else:
                try:
                    status = bead_status(pattern.exempt_until_bead)
                except LookupError as exc:
                    problems.append(
                        f"{pattern.id}: exempt_until_bead {pattern.exempt_until_bead}: "
                        f"{br_lookup.describe(exc, pattern.exempt_until_bead)}"
                    )
                    status = None
                if status == CLOSED:
                    problems.append(
                        f"{pattern.id}: exempt_until_bead {pattern.exempt_until_bead} is closed; "
                        f"drop the {len(pattern.exempt_paths)} exempt_paths entries, or name the bead that owns the gap now"
                    )

        allowance = {e.path: e.matches for e in pattern.exempt_paths}
        for rel in reachable:
            found = matches((root / rel).read_text(errors="replace"), pattern)
            covered = allowance.get(rel)
            if covered is None:
                for line, snippet in found:
                    findings.append(Finding(pattern.id, pattern.severity, rel, line, snippet, pattern.rationale))
            elif len(found) > covered:
                line, snippet = found[covered]
                findings.append(
                    Finding(
                        pattern.id,
                        pattern.severity,
                        rel,
                        line,
                        snippet,
                        pattern.rationale,
                        note=(
                            f"the exemption covers {covered} match(es) in this file; it carries {len(found)}. "
                            f"A skip added to an already-exempt file is invisible unless the count moves."
                        ),
                    )
                )

    if problems:
        return Outcome("DENY", patterns=len(patterns), scanned=sorted(scanned), problems=problems, warnings=warnings)
    if findings:
        return Outcome("FAIL", patterns=len(patterns), scanned=sorted(scanned), findings=findings, warnings=warnings)
    return Outcome("PASS", patterns=len(patterns), scanned=sorted(scanned), warnings=warnings)


BR_TIMEOUT_SECONDS = br_lookup.BR_TIMEOUT_SECONDS


def bead_status_resolver():
    def resolve(bead_id: str) -> str:
        return str(br_lookup.bead_row(bead_id).get("status") or "unknown")

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
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log.open("a") as handle:
        handle.write(f"{stamp} {text}\n")


def emit_findings(outcome: Outcome) -> None:
    print(f"[theater-patterns] REFUSED: {len(outcome.findings)} finding(s)", file=sys.stderr)
    for finding in outcome.findings:
        print(f"            {finding.severity} {finding.pattern_id}  {finding.path}:{finding.line}", file=sys.stderr)
        print(f"              {finding.snippet}", file=sys.stderr)
        if finding.note:
            print(f"              {finding.note}", file=sys.stderr)
        print(f"              {finding.rationale}", file=sys.stderr)
    print(
        "            pair the skip with an assertion naming the degraded behavior, or add the file to\n"
        f"            {SECTION}[].exempt_paths in audit-policy.yaml with the count it is exempt for,\n"
        "            beside the bead that removes it.",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__)
    parser.add_argument("--root", default=None)
    parser.add_argument("--policy", default=None)
    parser.add_argument("--log", default=None)
    parser.add_argument("paths", nargs="*")
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

    blocked = br_lookup.unavailable()
    outcome = evaluate(
        root,
        document,
        bead_status=None if blocked is not None else bead_status_resolver(),
        resolver_absence=blocked,
        scope=set(ns.paths) or None,
    )

    tag = f"[{blocked.condition}]" if blocked is not None else "[unavailable]"
    for warning in outcome.warnings:
        say(log, f"EXPIRY-UNKNOWN theater-patterns {tag}: {warning}")
        print(f"[theater-patterns] {warning}.", file=sys.stderr)
        if blocked is not None:
            print(f"                 {blocked.remediation}", file=sys.stderr)
        print(
            f"                 The expiry cross-check is {EXPIRY_BEAD}. The tree was scanned and the counts enforced.",
            file=sys.stderr,
        )

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
