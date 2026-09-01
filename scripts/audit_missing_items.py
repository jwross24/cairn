"""Separate a compliance scorecard's real gaps from the phases that never ran.

    scripts/audit_missing_items.py <pass-dir | bead-dir> ...

The vendored skill's `scripts/gather-evidence.sh` leaves a checklist item at
`MISSING` on paths where it performs no search at all:

  * the tests loop (line 148) searches only when the item id's last dot-segment
    differs from `primary`, and the spec extractor names every test item
    `tests.<type>.primary`, so the guard is false for the whole population;
  * the documentation / migrations / feature_flags / telemetry / ci_workflows
    loop (line 168) carries `case` arms for `documentation` and `ci_workflows`
    only, so an item in the other three categories reaches `emit_check` with
    the initial `MISSING` untouched;
  * a code artifact carrying no `expected_path_hints` drives the hint loop zero
    times, so nothing an author writes in a bead body can resolve it. Line 105 is
    that field's only reader in the whole gatherer: the tests loop resolves an
    item by ripgrepping its id (line 149) and the doc-family loop by existence
    checks (lines 170 and 175), so an empty hint list says nothing about either.

`score-bead.py` renders every such row under `## Missing items (verbatim)`, and
`remediate.sh` reads that section verbatim into a minted completion-debt bead's
description and acceptance criteria. A silence therefore travels as a finding,
and the debt bead demands an implementation and a passing test for an item no
command ever looked for. `~/.claude/rules/absence-is-not-evidence.md` names the
error: a missing row measures the artifact, not the system, and a predicate that
is structurally unreachable for a population carries no evidence about it.

This is the cairn-owned correction, in the shape of `audit_attribution.py` and
`scorecard_coherence.py`: it runs after the vendored audit and rewrites the
section into two labeled subsections, keeping every original line's text, so
whatever reads the section downstream states on its face which items were
measured and which were not. The vendored skill is left alone; a patch there is
a sixth forked call site that an upstream update reverts silently.

One line per bead reaches stdout: REWRITTEN, UNCHANGED, DEBT-FROM-NOTHING,
NO-SECTION, UNREADABLE-SPEC, UNREADABLE-SCORECARD, UNREADABLE-SPEC-FILE or
SPEC-NOT-AN-OBJECT. Exit 0 when no bead's false-closed verdict rests entirely on
unmeasured items, 1 when one does, 2 when a path names nothing to check, 3 when a
scorecard carries no `## Missing items (verbatim)` heading, 4 when a spec.json
does not parse, 5 when a scorecard.md cannot be read, 6 when a spec.json cannot
be read, and 7 when a spec.json parses to something other than an object.

Every code above 2 is structural: the section was never read, so the silence it
produces is not a pass. Each names its own verdict, exit code and .check.log
line, because an input this tool cannot read is a distinct fact from one it read
and disagreed with, and an agent confirming which path fired reads the log.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

HEADING = "## Missing items (verbatim)"
GAP_HEADING = "### Measured gaps — searched for, and not found"
UNMEASURED_HEADING = "### Not measured — no search ran for these"
GAP_NOTE = "Each line below rests on a search that ran and returned nothing."
UNMEASURED_NOTE = (
    "Each line below is the audit's silence. The gatherer performed no search for the item, "
    "so its absence from the evidence carries no information about the bead. A reader wanting "
    "a verdict on these has to run the phase that measures them."
)
NONE_LINE = "(none)"
ITEM_LINE_MARKERS = ("- spec item `", "- check `")
FALSE_CLOSED_MARKER = "**🚨 FALSE-CLOSED**"
# A scorecard whose denominator opens with this withheld no score, and its total is a
# placeholder zero. A verdict resting on that total rests on nothing the audit measured,
# so the debt check declines to speak for such a bead at all.
UNVERIFIABLE_MARKER = "**Denominator:** UNVERIFIABLE"
EXCLUDED_PHRASE = "EXCLUDED from numerator and denominator"

# gather-evidence.sh iterates these five categories and carries a `case` arm for
# two of them. An item in the other three reaches emit_check with the initial
# MISSING and no search behind it.
GATHERER_CATEGORIES = ("documentation", "migrations", "feature_flags", "telemetry", "ci_workflows")
GATHERER_SEARCHED_CATEGORIES = ("documentation", "ci_workflows")

# The tests loop guards its ripgrep with `[ "$NAME" != "primary" ]`, and the spec
# extractor names every test item `tests.<type>.primary`.
TESTS_GUARD_EXCLUDED_NAME = "primary"

# `expected_path_hints` reaches exactly one reader in gather-evidence.sh: line 105,
# inside the code_artifacts loop. The tests loop searches by ripgrep on the item id
# (line 149) and the doc-family loop by existence checks (lines 170 and 175), so a
# hint list carries no information about whether either of those searched.
HINT_DRIVEN_CATEGORIES = ("code_artifacts",)

DIMENSION_OF_CATEGORY = {
    "code_artifacts": "Implementation completeness vs. spec",
    "documentation": "Docs / migrations / telemetry / flags",
    "migrations": "Docs / migrations / telemetry / flags",
    "feature_flags": "Docs / migrations / telemetry / flags",
    "telemetry": "Docs / migrations / telemetry / flags",
    "ci_workflows": "Docs / migrations / telemetry / flags",
}
TESTS_DIMENSION = "Required tests present and meaningfully passing"

REASON_TESTS_GUARD = (
    "the tests loop searches only when the item id's last segment differs from "
    f"{TESTS_GUARD_EXCLUDED_NAME!r}; no ripgrep ran"
)
REASON_NO_CASE_ARM = "the gatherer's case statement carries no arm for category {category!r}; no search ran"
REASON_NO_HINTS = "the code_artifacts loop resolves only expected_path_hints, and spec.json carries none, so the hint loop drove zero iterations"
REASON_EXCLUDED = "the scorecard reports dimension {dimension!r} as {phrase}"

EXIT_OK = 0
EXIT_DEBT_FROM_NOTHING = 1
EXIT_NOTHING_TO_CHECK = 2
EXIT_NO_SECTION = 3
EXIT_UNREADABLE_SPEC = 4
EXIT_UNREADABLE_SCORECARD = 5
EXIT_UNREADABLE_SPEC_FILE = 6
EXIT_SPEC_NOT_AN_OBJECT = 7


class Gate:
    def __init__(self, log: Path) -> None:
        self.log = log

    def say(self, text: str) -> None:
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self.log.open("a") as handle:
            handle.write(f"{stamp} {text}\n")


@dataclass(frozen=True)
class Outcome:
    verdict: str
    detail: str
    problem: str | None = None


@dataclass(frozen=True)
class Item:
    line: str
    spec_item_id: str | None
    reasons: tuple[str, ...]

    @property
    def unresolvable(self) -> bool:
        return bool(self.reasons)


def spec_categories(spec: dict) -> dict[str, tuple[str, list]]:
    """Map each checklist item id to its category and its expected_path_hints."""
    out: dict[str, tuple[str, list]] = {}
    checklist = spec.get("checklist")
    if not isinstance(checklist, dict):
        return out
    for category, entries in checklist.items():
        if category == "tests" and isinstance(entries, dict):
            for test_type, items in entries.items():
                for item in items if isinstance(items, list) else []:
                    if isinstance(item, dict) and "id" in item:
                        out[item["id"]] = (f"tests.{test_type}", item.get("expected_path_hints") or [])
            continue
        for item in entries if isinstance(entries, list) else []:
            if isinstance(item, dict) and "id" in item:
                out[item["id"]] = (category, item.get("expected_path_hints") or [])
    return out


def excluded_dimensions(scorecard: str) -> set[str]:
    out: set[str] = set()
    for line in scorecard.splitlines():
        if not line.startswith("|") or EXCLUDED_PHRASE not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        out.add(cells[0].strip("* "))
    return out


def unresolvable_reasons(spec_item_id: str, categories: dict[str, tuple[str, list]], excluded: set[str]) -> list[str]:
    category, hints = categories.get(spec_item_id, (None, None))
    if category is None:
        return []
    reasons: list[str] = []
    if category.startswith("tests.") and spec_item_id.rsplit(".", 1)[-1] == TESTS_GUARD_EXCLUDED_NAME:
        reasons.append(REASON_TESTS_GUARD)
    bare = category.split(".", 1)[0]
    if category in GATHERER_CATEGORIES and category not in GATHERER_SEARCHED_CATEGORIES:
        reasons.append(REASON_NO_CASE_ARM.format(category=category))
    if category in HINT_DRIVEN_CATEGORIES and not hints:
        reasons.append(REASON_NO_HINTS)
    dimension = TESTS_DIMENSION if bare == "tests" else DIMENSION_OF_CATEGORY.get(bare)
    if dimension and dimension in excluded:
        reasons.append(REASON_EXCLUDED.format(dimension=dimension, phrase=EXCLUDED_PHRASE))
    return reasons


def section_bounds(scorecard: str) -> tuple[int, int] | None:
    lines = scorecard.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == HEADING)
    except StopIteration:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return start, end


def item_lines(scorecard: str) -> list[str]:
    bounds = section_bounds(scorecard)
    if bounds is None:
        return []
    start, end = bounds
    lines = scorecard.splitlines()[start + 1 : end]
    return [line for line in lines if line.startswith("- ") and line.strip() != f"- {NONE_LINE}"]


def spec_item_id_of(line: str) -> str | None:
    r"""The item id in a rendered line, whichever of score-bead.py's producers wrote it.

    Line 1240 emits `- spec item \`{id}\` — {notes}` from evidence.json and line 1241
    `- check \`{id}\` ({verdict}) — {reason}` from compliance.json. Both name a
    checklist item, so both have to reach the same verdict for the same id.
    """
    for marker in ITEM_LINE_MARKERS:
        if line.startswith(marker):
            rest = line[len(marker) :]
            end = rest.find("`")
            return rest[:end] if end > 0 else None
    return None


def classify(scorecard: str, spec: dict) -> list[Item]:
    categories = spec_categories(spec)
    excluded = excluded_dimensions(scorecard)
    out: list[Item] = []
    for line in item_lines(scorecard):
        spec_item_id = spec_item_id_of(line)
        reasons = unresolvable_reasons(spec_item_id, categories, excluded) if spec_item_id else []
        out.append(Item(line=line, spec_item_id=spec_item_id, reasons=tuple(reasons)))
    return out


def render_section(items: list[Item]) -> list[str]:
    gaps = [item for item in items if not item.unresolvable]
    unmeasured = [item for item in items if item.unresolvable]
    out = [HEADING, "", GAP_HEADING, "", GAP_NOTE, ""]
    if gaps:
        out.extend(item.line for item in gaps)
    else:
        out.append(f"- {NONE_LINE}")
    out += ["", UNMEASURED_HEADING, "", UNMEASURED_NOTE, ""]
    if not unmeasured:
        out.append(f"- {NONE_LINE}")
    for item in unmeasured:
        out.append(item.line)
        out.extend(f"  - unresolvable: {reason}" for reason in item.reasons)
    return out


def rewrite(scorecard: str, items: list[Item]) -> str:
    bounds = section_bounds(scorecard)
    if bounds is None:
        return scorecard
    start, end = bounds
    lines = scorecard.splitlines()
    rebuilt = lines[:start] + render_section(items) + ([""] if end < len(lines) else []) + lines[end:]
    return "\n".join(rebuilt) + "\n"


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def bead_dirs(paths: list[str]) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_dir():
            continue
        if (path / "spec.json").is_file() and (path / "scorecard.md").is_file():
            found.append(path)
            continue
        found.extend(
            sorted(child.parent for child in path.rglob("spec.json") if (child.parent / "scorecard.md").is_file())
        )
    return found


def process(bead: Path) -> Outcome:
    try:
        scorecard = (bead / "scorecard.md").read_text()
    except OSError as shut:
        return Outcome("UNREADABLE-SCORECARD", f"scorecard.md cannot be read: {shut}", "unreadable-scorecard")
    try:
        raw_spec = (bead / "spec.json").read_text()
    except OSError as shut:
        return Outcome("UNREADABLE-SPEC-FILE", f"spec.json cannot be read: {shut}", "unreadable-spec-file")
    try:
        spec = json.loads(raw_spec)
    except json.JSONDecodeError as broken:
        return Outcome("UNREADABLE-SPEC", f"spec.json does not parse: {broken}", "unreadable-spec")
    if not isinstance(spec, dict):
        return Outcome(
            "SPEC-NOT-AN-OBJECT",
            f"spec.json holds a {type(spec).__name__}, so it names no checklist to read",
            "spec-not-an-object",
        )
    if section_bounds(scorecard) is None:
        return Outcome(
            "NO-SECTION",
            f"the scorecard carries no {HEADING!r} heading, so no item was read and no verdict here is evidence",
            "no-section",
        )
    items = classify(scorecard, spec)
    false_closed = FALSE_CLOSED_MARKER in scorecard and UNVERIFIABLE_MARKER not in scorecard
    debt_from_nothing = false_closed and bool(items) and all(item.unresolvable for item in items)
    rebuilt = rewrite(scorecard, items)
    changed = rebuilt != scorecard
    if changed:
        atomic_write(bead / "scorecard.md", rebuilt)
    gaps = sum(1 for item in items if not item.unresolvable)
    unmeasured = len(items) - gaps
    verdict = "DEBT-FROM-NOTHING" if debt_from_nothing else ("REWRITTEN" if changed else "UNCHANGED")
    detail = f"{gaps} measured gap(s), {unmeasured} unmeasured"
    if debt_from_nothing:
        detail += "; every item behind the FALSE-CLOSED verdict is unresolvable"
    return Outcome(verdict, detail, "debt-from-nothing" if debt_from_nothing else None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--root", default=None)
    parser.add_argument("--log", default=None)
    ns = parser.parse_args(argv)

    root = Path(ns.root).resolve() if ns.root else Path(__file__).resolve().parents[1]
    gate = Gate(Path(ns.log) if ns.log else root / ".check.log")

    skip = os.environ.get("CAIRN_MISSING_ITEMS_SKIP")
    if skip:
        gate.say(f"BYPASS missing-items {' '.join(ns.paths)}: {skip}")
        print(f"[missing-items] BYPASSED: {skip} (logged to {gate.log.name})", file=sys.stderr)
        return EXIT_OK

    if not ns.paths:
        print("usage: audit_missing_items.py <pass-dir | bead-dir> ...", file=sys.stderr)
        gate.say("DENY missing-items infra: no path given")
        return EXIT_NOTHING_TO_CHECK

    beads = bead_dirs(ns.paths)
    if not beads:
        print(f"missing-items: NOTHING-TO-CHECK {' '.join(ns.paths)}", file=sys.stderr)
        gate.say(
            f"DENY missing-items infra: no bead directory holds both spec.json and scorecard.md under {' '.join(ns.paths)}"
        )
        return EXIT_NOTHING_TO_CHECK

    problems: dict[str, list[str]] = {}
    for bead in beads:
        outcome = process(bead)
        print(f"{outcome.verdict} {bead.name} — {outcome.detail}")
        if outcome.problem:
            problems.setdefault(outcome.problem, []).append(bead.name)

    # A structural failure outranks the verdict: it means the section was never read,
    # so `debt-from-nothing` could not have been decided for that bead either way.
    for problem, code, note in (
        ("unreadable-scorecard", EXIT_UNREADABLE_SCORECARD, "scorecard.md cannot be read"),
        ("unreadable-spec-file", EXIT_UNREADABLE_SPEC_FILE, "spec.json cannot be read"),
        ("unreadable-spec", EXIT_UNREADABLE_SPEC, "spec.json does not parse"),
        ("spec-not-an-object", EXIT_SPEC_NOT_AN_OBJECT, "spec.json parses to something other than an object"),
        ("no-section", EXIT_NO_SECTION, f"no {HEADING!r} heading; the upstream renderer has drifted"),
        ("debt-from-nothing", EXIT_DEBT_FROM_NOTHING, "every item behind the FALSE-CLOSED verdict is unmeasured"),
    ):
        named = problems.get(problem)
        if named:
            gate.say(f"DENY missing-items {problem}: {' '.join(named)} ({note})")
            return code

    gate.say(f"PASS missing-items {len(beads)} scorecard(s) separated into measured gaps and unmeasured items")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
