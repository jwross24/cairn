#!/usr/bin/env python3
"""Check that a compliance scorecard's table, banner and denominator agree.

A gate whose output misrepresents its own arithmetic is worse than no gate: the
reader takes the dimension table at face value and concludes credit was awarded
that the scorer in fact excluded. This reads the rendered scorecard back and
refuses the disagreement.

  usage: scorecard_coherence.py <scorecard.md | directory> ...

Exactly one line per scorecard reaches stdout: COHERENT or INCOHERENT with the
problems named. Exit 0 when every scorecard checked is coherent, 1 when any is
not, and 2 when a path names nothing to check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCORE_RE = re.compile(r"^\*\*Score:\s*(\d+)\s*/\s*1000\*\*\s*$", re.MULTILINE)
DENOM_RE = re.compile(r"^\*\*Denominator:\*\*\s*(.+?)\s*$", re.MULTILINE)
BANNER_RE = re.compile(r"^\*\*⚠ DETERMINISTIC-ONLY PASS:\*\*\s*(.+?)\s*$", re.MULTILINE)
ROW_RE = re.compile(r"^\|(?!\s*\*\*TOTAL)\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)
TOTAL_RE = re.compile(r"^\|\s*\*\*TOTAL\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*1000\*\*\s*\|", re.MULTILINE)
RESCALED_RE = re.compile(r"scored over the (\d+) of 1000 weight measured \((\d+)/(\d+)\)")
UNVERIFIABLE_RE = re.compile(r"UNVERIFIABLE — only (\d+) of 1000 weight was measured")
FALSE_CLOSED_RE = re.compile(r"^\*\*🚨 FALSE-CLOSED\*\*", re.MULTILINE)
EXCLUDED_CELL = "—"
FULL_CREDIT_PHRASE = "WAIVED with full credit"


def _rows(text: str) -> list[tuple[str, str, str]]:
    out = []
    for name, score, maximum in ROW_RE.findall(text):
        if name.startswith("---") or score.startswith("---"):
            continue
        if name == "Dimension":
            continue
        out.append((name, score, maximum))
    return out


def check_scorecard(text: str) -> list[str]:
    problems: list[str] = []

    score_match = SCORE_RE.search(text)
    total_match = TOTAL_RE.search(text)
    if not score_match:
        problems.append("no **Score: N / 1000** line")
    if not total_match:
        problems.append("no **TOTAL** row")
    if score_match and total_match and score_match.group(1) != total_match.group(1):
        problems.append(f"banner score {score_match.group(1)} disagrees with the TOTAL row {total_match.group(1)}")

    rows = _rows(text)
    if not rows:
        problems.append("no dimension rows")

    measured_score = 0
    measured_weight = 0
    excluded: list[str] = []
    for name, score, maximum in rows:
        if score == EXCLUDED_CELL or maximum == EXCLUDED_CELL:
            if not (score == EXCLUDED_CELL and maximum == EXCLUDED_CELL):
                problems.append(f"row {name!r} is half-excluded: score={score!r} max={maximum!r}")
            excluded.append(name)
            continue
        if not (score.isdigit() and maximum.isdigit()):
            problems.append(f"row {name!r} has non-numeric cells: score={score!r} max={maximum!r}")
            continue
        if int(score) > int(maximum):
            problems.append(f"row {name!r} scores {score} out of {maximum}")
        measured_score += int(score)
        measured_weight += int(maximum)

    banner = BANNER_RE.search(text)
    if banner and FULL_CREDIT_PHRASE in banner.group(1) and excluded:
        problems.append(f"the banner claims {FULL_CREDIT_PHRASE!r} while {len(excluded)} row(s) are marked excluded")

    denominator = DENOM_RE.search(text)
    if excluded and not denominator:
        problems.append(f"{len(excluded)} row(s) excluded but no **Denominator:** line says so")
    if denominator and not excluded:
        problems.append("a **Denominator:** line is present but no row is marked excluded")

    if denominator:
        note = denominator.group(1)
        rescaled = RESCALED_RE.search(note)
        unverifiable = UNVERIFIABLE_RE.search(note)
        if rescaled:
            stated_weight, stated_score, stated_weight_again = (int(g) for g in rescaled.groups())
            if stated_weight != stated_weight_again:
                problems.append(f"denominator names two measured weights: {stated_weight} and {stated_weight_again}")
            if stated_weight != measured_weight:
                problems.append(
                    f"denominator says {stated_weight} of measured weight; the scored rows total {measured_weight}"
                )
            if stated_score != measured_score:
                problems.append(
                    f"denominator says {stated_score} measured points; the scored rows total {measured_score}"
                )
            if total_match and measured_weight:
                expected = round(measured_score * 1000 / measured_weight)
                if expected != int(total_match.group(1)):
                    problems.append(
                        f"{measured_score}/{measured_weight} rescales to {expected}, "
                        f"not the reported {total_match.group(1)}"
                    )
        elif unverifiable:
            if int(unverifiable.group(1)) != measured_weight:
                problems.append(
                    f"denominator says {unverifiable.group(1)} of measured weight; "
                    f"the scored rows total {measured_weight}"
                )
            if total_match and total_match.group(1) != "0":
                problems.append(f"denominator says UNVERIFIABLE but the TOTAL row reports {total_match.group(1)}")
            if FALSE_CLOSED_RE.search(text):
                problems.append(
                    "denominator says UNVERIFIABLE, so the total is a withheld placeholder; "
                    "a FALSE-CLOSED line convicts on it as though it were a score"
                )
        else:
            problems.append(f"unrecognized **Denominator:** note: {note!r}")

    return problems


def collect(paths: list[str]) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found.extend(sorted(path.rglob("scorecard.md")))
        elif path.is_file():
            found.append(path)
    return found


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: scorecard_coherence.py <scorecard.md | directory> ...", file=sys.stderr)
        return 2
    scorecards = collect(argv)
    if not scorecards:
        print(f"scorecard-coherence: NOTHING-TO-CHECK {' '.join(argv)}", file=sys.stderr)
        return 2
    bad = 0
    for path in scorecards:
        problems = check_scorecard(path.read_text())
        if problems:
            bad += 1
            print(f"INCOHERENT {path}: {'; '.join(problems)}")
        else:
            print(f"COHERENT {path}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
