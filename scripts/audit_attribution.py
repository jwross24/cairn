#!/usr/bin/env python3
"""Re-evaluate the audit's closing-commit anomalies against the commit that closed the bead.

Two patterns in the vendored compliance skill's `anomaly-scan.sh` judge a bead by
its "closing commit" and pick that commit with

    git log --all -F --grep="$ID" --format=%H | head -1

which is the newest commit whose *message* names the bead id. This repository asks
every session to cite its beads in commit messages, so the pick usually belongs to a
different bead, and it moves whenever an unrelated session commits. A score that
moves with other beads' commit messages measures the message stream, not the bead.

This is the cairn-owned correction. It runs after the vendored audit, resolves each
audited bead's closing commit through `closing_commit.py` -- the bead store's own
status flip, which cannot name a commit belonging to another bead -- re-derives the
two attributed patterns against that commit, and re-scores. The vendored skill is
left alone: a patch there is a sixth forked call site that an upstream update
reverts silently, and subtracting the pattern's weight would discard a real signal,
because a closing commit that genuinely silences a linter is worth flagging.

  usage: audit_attribution.py <pass-dir> ...
         audit_attribution.py --audit-dir <dir> [--after <pass-name>]

One line per bead reaches stdout: CORRECTED, UNCHANGED or UNRESOLVED, with the
commit each verdict rests on. Exit 0 when every closed bead scores at or above the
threshold, 1 when one does not, 2 when no scored bead was found to check, and 3 when
git itself failed, which is a silence no caller may read as a pass.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from closing_commit import GIT_FAILED_EXIT, STAGED, UNKNOWN, GitError, resolve

IGNORE_LIST_PATHS = (".ubsignore", ".eslintignore", ".gitignore", ".flake8", "pyproject.toml")
ATTRIBUTED_CATEGORIES = ("anomaly_empty_diff", "anomaly_ignore_list_growth")
SEVERITIES = ("BLOCKING", "MAJOR", "MINOR", "NOTE")
STAGED_LABEL = "(staged)"
GIT_TIMEOUT_SECONDS = 120
SCORE_TIMEOUT_SECONDS = 600
SKILL_CANDIDATES = (
    Path(".claude/skills/beads-compliance-and-completion-verification"),
    Path.home() / ".claude/skills/beads-compliance-and-completion-verification",
    Path.home() / ".codex/skills/beads-compliance-and-completion-verification",
)


@dataclass(frozen=True)
class ClosingDiff:
    label: str
    files_changed: int
    ignore_adds: int


def rederive(diff: ClosingDiff | None) -> list[dict]:
    if diff is None:
        return []
    findings = []
    if diff.files_changed == 0:
        findings.append(
            {
                "severity": "MAJOR",
                "category": "anomaly_empty_diff",
                "description": f"Closing commit {diff.label} touches zero files",
            }
        )
    if diff.ignore_adds > 0:
        findings.append(
            {
                "severity": "BLOCKING",
                "category": "anomaly_ignore_list_growth",
                "description": (
                    f"Closing commit {diff.label} added {diff.ignore_adds} line(s) to ignore "
                    "lists — possible silencing instead of fixing"
                ),
            }
        )
    return findings


def renumber(findings: list[dict]) -> list[dict]:
    out = []
    for index, finding in enumerate(findings, start=1):
        renumbered = dict(finding)
        if str(renumbered.get("id", "")).startswith("anomaly."):
            renumbered["id"] = f"anomaly.{index}"
        out.append(renumbered)
    return out


def correct(theater: dict, bead_id: str, resolution: str, diff: ClosingDiff | None) -> tuple[dict, list[str]]:
    kept = [f for f in theater.get("findings", []) if f.get("category") not in ATTRIBUTED_CATEGORIES]
    dropped = len(theater.get("findings", [])) - len(kept)
    raised = rederive(diff)
    for finding in raised:
        kept.append(
            {
                "id": "anomaly.0",
                "severity": finding["severity"],
                "category": finding["category"],
                "path": f"(bead {bead_id})",
                "line": 0,
                "snippet": "(see show.json)",
                "description": finding["description"],
            }
        )
    findings = renumber(kept)
    corrected = dict(theater)
    corrected["findings"] = findings
    summary = dict(theater.get("summary") or {})
    for severity in SEVERITIES:
        summary[severity] = sum(1 for f in findings if f.get("severity") == severity)
    corrected["summary"] = summary
    corrected["commit_attribution"] = {
        "resolver": "scripts/closing_commit.py",
        "closing_commit": resolution,
        "categories": list(ATTRIBUTED_CATEGORIES),
    }
    notes = []
    if dropped:
        notes.append(f"dropped {dropped} finding(s) raised against a commit the bead did not close")
    if raised:
        notes.append(f"raised {len(raised)} finding(s) against {resolution}")
    return corrected, notes


def passes_after(names: list[str], after: str | None) -> list[str]:
    ordered = sorted(names)
    if after is None:
        return ordered
    return [name for name in ordered if name > after]


def prior_pass(names: list[str], current: str) -> str | None:
    earlier = [name for name in sorted(names) if name != current]
    return earlier[-1] if earlier else None


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


def count_ignore_adds(diff_text: str) -> int:
    """Added lines in an ignore-list diff, counted the way `grep -cE '^\\+[^+]'` counts them."""
    return sum(1 for line in diff_text.splitlines() if len(line) > 1 and line[0] == "+" and line[1] != "+")


def git_closing_diff_reader(root: Path):
    def read(resolution: str) -> ClosingDiff | None:
        if resolution == UNKNOWN:
            return None
        if resolution == STAGED:
            names = _git(root, ["diff", "--cached", "--name-only"])
            adds = _git(root, ["diff", "--cached", "--", *IGNORE_LIST_PATHS])
            label = STAGED_LABEL
        else:
            names = _git(root, ["show", "--pretty=format:", "--name-only", resolution])
            adds = _git(root, ["show", resolution, "--", *IGNORE_LIST_PATHS])
            label = resolution
        return ClosingDiff(
            label=label,
            files_changed=len([line for line in names.splitlines() if line.strip()]),
            ignore_adds=count_ignore_adds(adds),
        )

    return read


def find_skill(named: str | None) -> Path | None:
    if named:
        path = Path(named)
        return path if path.is_dir() else None
    for candidate in SKILL_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return None


def score_runner(skill: Path, rubric: Path, threshold: int):
    def run(bead_dir: Path, synthesis: Path | None, prior: Path | None) -> dict:
        args = [
            "uv",
            "run",
            "--quiet",
            "--with",
            "pyyaml",
            "python",
            str(skill / "scripts" / "score-bead.py"),
            str(bead_dir),
            "--threshold",
            str(threshold),
            "--rubric",
            str(rubric),
        ]
        if synthesis and synthesis.is_file():
            args += ["--synthesis", str(synthesis)]
        if prior:
            args += ["--prior-pass-dir", str(prior)]
        proc = subprocess.run(args, capture_output=True, text=True, timeout=SCORE_TIMEOUT_SECONDS)
        if proc.returncode != 0:
            raise RuntimeError(f"score-bead.py exited {proc.returncode}: {proc.stderr.strip()[-400:]}")
        return json.loads(proc.stdout.strip().splitlines()[-1])

    return run


def scored_bead_dirs(pass_dir: Path) -> list[Path]:
    beads = pass_dir / "beads"
    if not beads.is_dir():
        return []
    required = ("theater.json", "spec.json", "show.json")
    return [d for d in sorted(beads.iterdir()) if all((d / name).is_file() for name in required)]


def correct_pass(pass_dir: Path, *, resolutions, diff_for, score, prior: Path | None) -> list[tuple[str, str, bool]]:
    results = []
    for bead_dir in scored_bead_dirs(pass_dir):
        bead_id = bead_dir.name
        resolution = resolutions.get(bead_id, UNKNOWN)
        theater = json.loads((bead_dir / "theater.json").read_text())
        corrected, notes = correct(theater, bead_id, resolution, diff_for(resolution))
        (bead_dir / "theater.json").write_text(json.dumps(corrected, indent=2) + "\n")
        summary = score(bead_dir, pass_dir / "synthesis.md", prior)
        status = json.loads((bead_dir / "show.json").read_text()).get("status", "unknown")
        failed = status == "closed" and bool(summary.get("false_closed"))
        if resolution == UNKNOWN:
            verdict = "UNRESOLVED no commit closed this bead"
        elif notes:
            verdict = f"CORRECTED {resolution}: {'; '.join(notes)}"
        else:
            verdict = f"UNCHANGED {resolution}"
        results.append((bead_id, f"{verdict} → score {summary.get('score')}", failed))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pass_dirs", nargs="*")
    parser.add_argument("--root", default=".")
    parser.add_argument("--audit-dir")
    parser.add_argument("--after")
    parser.add_argument("--rubric")
    parser.add_argument("--skill")
    parser.add_argument("--threshold", type=int, default=700)
    args = parser.parse_args(argv)

    root = Path(args.root)
    if args.audit_dir:
        audit_dir = Path(args.audit_dir)
        names = (
            [d.name for d in (audit_dir / "passes").iterdir() if d.is_dir()] if (audit_dir / "passes").is_dir() else []
        )
        selected = [audit_dir / "passes" / name for name in passes_after(names, args.after)]
    else:
        audit_dir = Path(args.pass_dirs[0]).parent.parent if args.pass_dirs else Path(".")
        names = (
            [d.name for d in (audit_dir / "passes").iterdir() if d.is_dir()] if (audit_dir / "passes").is_dir() else []
        )
        selected = [Path(p) for p in args.pass_dirs]

    skill = find_skill(args.skill)
    if skill is None:
        print("attribution: NO-SKILL the compliance skill is not installed", file=sys.stderr)
        return 2
    rubric = Path(args.rubric) if args.rubric else audit_dir / "rubric.md"
    if not rubric.is_file():
        print(f"attribution: NO-RUBRIC {rubric}", file=sys.stderr)
        return 2

    score = score_runner(skill, rubric, args.threshold)

    checked = 0
    failed = 0
    try:
        resolutions = resolve(root)
        diff_for = git_closing_diff_reader(root)
        for pass_dir in selected:
            for bead_id, verdict, bead_failed in correct_pass(
                pass_dir,
                resolutions=resolutions,
                diff_for=diff_for,
                score=score,
                prior=(audit_dir / "passes" / prior_pass(names, pass_dir.name))
                if prior_pass(names, pass_dir.name)
                else None,
            ):
                checked += 1
                failed += bool(bead_failed)
                print(f"{'FALSE-CLOSED' if bead_failed else 'OK'} {bead_id} {verdict}")
    except GitError as failure:
        print(f"attribution: GIT-FAILED {failure}", file=sys.stderr)
        return GIT_FAILED_EXIT
    if not checked:
        print("attribution: NOTHING-TO-CHECK no pass holds a scored bead", file=sys.stderr)
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
