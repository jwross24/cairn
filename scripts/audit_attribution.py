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
import shlex
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from closing_commit import GIT_FAILED_EXIT, STAGED, UNKNOWN, GitError, resolve

IGNORE_LIST_PATHS = (".ubsignore", ".eslintignore", ".gitignore", ".flake8")
ATTRIBUTED_CATEGORIES = ("anomaly_empty_diff", "anomaly_ignore_list_growth")
SEVERITIES = ("BLOCKING", "MAJOR", "MINOR", "NOTE")
STAGED_LABEL = "(staged)"
FALSE_CLOSED = "false-closed"
UNVERIFIABLE = "unverifiable"
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


class IgnoreConfigError(ValueError):
    pass


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
                    f"Closing commit {diff.label} added {diff.ignore_adds} entry(s) to ignore "
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
    kept.extend(
        {
            "id": "anomaly.0",
            "severity": finding["severity"],
            "category": finding["category"],
            "path": f"(bead {bead_id})",
            "line": 0,
            "snippet": "(see show.json)",
            "description": finding["description"],
        }
        for finding in raised
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
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as failure:
        raise GitError(f"git {' '.join(args)} could not be read: {failure}") from failure
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} exited {proc.returncode}: {proc.stderr.strip()[-400:]}")
    return proc.stdout


def count_ignore_adds(diff_text: str) -> int:
    """Added lines in an ignore-list diff, counted the way `grep -cE '^\\+[^+]'` counts them."""
    return sum(1 for line in diff_text.splitlines() if len(line) > 1 and line[0] == "+" and line[1] != "+")


def _table(value: object, name: str) -> dict:
    if not isinstance(value, dict):
        raise IgnoreConfigError(f"{name} must be a table")
    return value


def _strings(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise IgnoreConfigError(f"{name} must be an array of strings")
    return value


def _warning_filter(value: str, name: str) -> str:
    parts = [part.strip() for part in value.split(":")]
    if len(parts) > 5:
        raise IgnoreConfigError(f"{name}: warning filter has more than five fields")
    action = parts[0]
    actions = [item for item in ("default", "error", "ignore", "always", "module", "once") if item.startswith(action)]
    if not action:
        parts[0] = "default"
    elif action == "all":
        parts[0] = "always"
    elif len(actions) == 1:
        parts[0] = actions[0]
    else:
        raise IgnoreConfigError(f"{name}: invalid warning action {action!r}")
    parts.extend([""] * (5 - len(parts)))
    if not parts[2]:
        parts[2] = "Warning"
    try:
        line = int(parts[4] or "0")
    except ValueError as failure:
        raise IgnoreConfigError(f"{name}: invalid warning line {parts[4]!r}") from failure
    if line < 0:
        raise IgnoreConfigError(f"{name}: warning line must be nonnegative")
    parts[4] = str(line)
    return ":".join(parts)


def _pytest_ignores(config: dict, name: str) -> set[tuple[str, ...]]:
    entries = set()
    warnings = config.get("filterwarnings", [])
    if isinstance(warnings, str) and name.endswith("ini_options"):
        warnings = [line.strip() for line in warnings.splitlines() if line.strip()]
    filters = [
        ("config", _warning_filter(item, f"{name}.filterwarnings"))
        for item in _strings(warnings, f"{name}.filterwarnings")
    ]
    excluded = config.get("norecursedirs", [])
    if isinstance(excluded, str) and name.endswith("ini_options"):
        excluded = excluded.split()
    entries.update(("pytest", "norecursedirs", item) for item in _strings(excluded, f"{name}.norecursedirs"))
    args = config.get("addopts", [])
    if isinstance(args, str) and name.endswith("ini_options"):
        try:
            args = shlex.split(args)
        except ValueError as failure:
            raise IgnoreConfigError(f"{name}.addopts: {failure}") from failure
    iterator = iter(_strings(args, f"{name}.addopts"))
    for arg in iterator:
        flag, separator, value = arg.partition("=")
        if arg.startswith("-W"):
            flag, separator, value = "-W", arg[2:], arg[2:]
        if flag not in ("--ignore", "--ignore-glob", "-W", "--pythonwarnings"):
            continue
        if not separator:
            value = next(iterator, "")
        if not value or value.startswith("--"):
            raise IgnoreConfigError(f"{name}.addopts: {flag} requires a value")
        if flag in ("-W", "--pythonwarnings"):
            filters.append(("cli", _warning_filter(value, f"{name}.addopts")))
        else:
            entries.add(("pytest", flag, value))
    for index, (source, warning) in enumerate(filters):
        if warning.split(":", 1)[0] == "ignore":
            context = json.dumps(filters[index + 1 :])
            entries.add(("pytest", "filterwarnings", source, warning, context))
    return entries


def pyproject_ignores(text: str) -> set[tuple[str, ...]]:
    try:
        config = tomllib.loads(text)
    except tomllib.TOMLDecodeError as failure:
        raise IgnoreConfigError(f"invalid TOML: {failure}") from failure
    tool = _table(config.get("tool", {}), "tool")
    entries = set()
    ruff = _table(tool.get("ruff", {}), "tool.ruff")
    lint = _table(ruff.get("lint", {}), "tool.ruff.lint")
    for key in ("ignore", "extend-ignore", "per-file-ignores", "extend-per-file-ignores"):
        selected = set()
        for section, name in ((ruff, "tool.ruff"), (lint, "tool.ruff.lint")):
            if key in ("ignore", "extend-ignore"):
                parsed = {("ruff", "ignore", item) for item in _strings(section.get(key, []), f"{name}.{key}")}
            else:
                parsed = set()
                for pattern, codes in _table(section.get(key, {}), f"{name}.{key}").items():
                    parsed.update(
                        ("ruff", "per-file-ignores", pattern, code)
                        for code in _strings(codes, f"{name}.{key}.{pattern}")
                    )
            if key in section:
                selected = parsed
        entries.update(selected)
    for section, name, category, keys in (
        (ruff, "tool.ruff", "exclude", ("exclude", "extend-exclude")),
        (lint, "tool.ruff.lint", "lint.exclude", ("exclude",)),
        (_table(ruff.get("format", {}), "tool.ruff.format"), "tool.ruff.format", "format.exclude", ("exclude",)),
    ):
        for key in keys:
            entries.update(("ruff", category, item) for item in _strings(section.get(key, []), f"{name}.{key}"))
    ty = _table(tool.get("ty", {}), "tool.ty")
    overrides = ty.get("overrides", [])
    if not isinstance(overrides, list):
        raise IgnoreConfigError("tool.ty.overrides must be an array of tables")
    scopes = [(ty, "tool.ty", "global")]
    for index, value in enumerate(overrides):
        name = f"tool.ty.overrides[{index}]"
        override = _table(value, name)
        include = _strings(override.get("include", ["**"]), f"{name}.include")
        exclude = _strings(override.get("exclude", []), f"{name}.exclude")
        scopes.append((override, name, json.dumps([include, exclude])))
    for section, name, scope in scopes:
        for rule, severity in _table(section.get("rules", {}), f"{name}.rules").items():
            if severity not in ("ignore", "warn", "error"):
                raise IgnoreConfigError(f"{name}.rules.{rule} must be ignore, warn, or error")
            if severity == "ignore":
                entries.add(("ty", "rules", scope, rule))
    src = _table(ty.get("src", {}), "tool.ty.src")
    entries.update(("ty", "src.exclude", item) for item in _strings(src.get("exclude", []), "tool.ty.src.exclude"))
    pytest = _table(tool.get("pytest", {}), "tool.pytest")
    ini_options = _table(pytest.get("ini_options", {}), "tool.pytest.ini_options")
    if ini_options and any(key != "ini_options" for key in pytest):
        raise IgnoreConfigError("tool.pytest and tool.pytest.ini_options cannot both contain settings")
    entries.update(_pytest_ignores(pytest, "tool.pytest"))
    entries.update(_pytest_ignores(ini_options, "tool.pytest.ini_options"))
    codespell = _table(tool.get("codespell", {}), "tool.codespell")
    for key in ("ignore-words-list", "uri-ignore-words-list", "ignore-words", "skip", "exclude-file"):
        value = codespell.get(key, "")
        if isinstance(value, list):
            value = ",".join(_strings(value, f"tool.codespell.{key}"))
        if not isinstance(value, str):
            raise IgnoreConfigError(f"tool.codespell.{key} must be a string or array of strings")
        entries.update(("codespell", key, item.strip()) for item in value.split(",") if item.strip())
    for key in ("ignore-regex", "ignore-multiline-regex"):
        value = codespell.get(key, "")
        if not isinstance(value, str):
            raise IgnoreConfigError(f"tool.codespell.{key} must be a string")
        if value:
            entries.add(("codespell", key, value))
    return entries


def _pyproject_at(root: Path, revision: str | None) -> set[tuple[str, ...]]:
    if revision is None:
        return set()
    if revision == STAGED:
        listing = _git(root, ["ls-files", "--stage", "-z", "--", "pyproject.toml"])
    else:
        listing = _git(root, ["ls-tree", "-z", revision, "--", "pyproject.toml"])
    if not listing:
        return set()
    rows = listing.rstrip("\0").split("\0")
    fields = rows[0].split("\t", 1)[0].split()
    if len(rows) != 1 or len(fields) != 3 or fields[0] not in ("100644", "100755"):
        raise IgnoreConfigError(f"{revision}:pyproject.toml is not a regular, resolved file")
    if revision == STAGED and fields[2] != "0":
        raise IgnoreConfigError("staged pyproject.toml has an unresolved conflict")
    blob = fields[1] if revision == STAGED else fields[2]
    try:
        return pyproject_ignores(_git(root, ["cat-file", "blob", blob]))
    except IgnoreConfigError as failure:
        raise IgnoreConfigError(f"{revision}:pyproject.toml: {failure}") from failure


def git_closing_diff_reader(root: Path):
    def read(resolution: str) -> ClosingDiff | None:
        if resolution == UNKNOWN:
            return None
        if resolution == STAGED:
            names = _git(root, ["diff", "--cached", "--name-only"])
            adds = _git(root, ["diff", "--cached", "--", *IGNORE_LIST_PATHS])
            label = STAGED_LABEL
        else:
            names = _git(root, ["show", "--first-parent", "--pretty=format:", "--name-only", resolution])
            adds = _git(root, ["show", resolution, "--", *IGNORE_LIST_PATHS])
            label = resolution
        ignore_adds = count_ignore_adds(adds)
        if "pyproject.toml" in names.splitlines():
            if resolution == STAGED:
                status = _git(root, ["diff", "--cached", "--no-renames", "--name-status", "--", "pyproject.toml"])
                parent = None if status.startswith("A\t") else "HEAD"
            else:
                parents = _git(root, ["rev-list", "--parents", "-n", "1", resolution]).split()
                parent = parents[1] if len(parents) > 1 else None
            ignore_adds += len(_pyproject_at(root, resolution) - _pyproject_at(root, parent))
        return ClosingDiff(
            label=label,
            files_changed=len([line for line in names.splitlines() if line.strip()]),
            ignore_adds=ignore_adds,
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


def correct_pass(
    pass_dir: Path, *, resolutions, diff_for, score, prior: Path | None
) -> list[tuple[str, str, str | None]]:
    results = []
    for bead_dir in scored_bead_dirs(pass_dir):
        bead_id = bead_dir.name
        resolution = resolutions.get(bead_id, UNKNOWN)
        theater = json.loads((bead_dir / "theater.json").read_text())
        corrected, notes = correct(theater, bead_id, resolution, diff_for(resolution))
        (bead_dir / "theater.json").write_text(json.dumps(corrected, indent=2) + "\n")
        summary = score(bead_dir, pass_dir / "synthesis.md", prior)
        status = json.loads((bead_dir / "show.json").read_text()).get("status", "unknown")
        unverifiable = bool(summary.get("unverifiable"))
        failure = None
        if status == "closed":
            if unverifiable:
                failure = UNVERIFIABLE
            elif summary.get("false_closed"):
                failure = FALSE_CLOSED
        if resolution == UNKNOWN:
            verdict = "UNRESOLVED no commit closed this bead"
        elif notes:
            verdict = f"CORRECTED {resolution}: {'; '.join(notes)}"
        else:
            verdict = f"UNCHANGED {resolution}"
        if unverifiable:
            unmeasured = ", ".join(summary.get("unmeasured") or []) or "unnamed dimensions"
            verdict += (
                f" → the pass could not be verified; unmeasured: {unmeasured}"
                " (no score was computed and no threshold was compared)"
            )
        else:
            verdict += f" → score {summary.get('score')}"
        results.append((bead_id, verdict, failure))
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
        audit_dir = Path(args.pass_dirs[0]).parent.parent if args.pass_dirs else Path()
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
            for bead_id, verdict, bead_failure in correct_pass(
                pass_dir,
                resolutions=resolutions,
                diff_for=diff_for,
                score=score,
                prior=(audit_dir / "passes" / prior_pass(names, pass_dir.name))
                if prior_pass(names, pass_dir.name)
                else None,
            ):
                checked += 1
                failed += bool(bead_failure)
                print(f"{bead_failure.upper() if bead_failure else 'OK'} {bead_id} {verdict}")
    except IgnoreConfigError as failure:
        print(f"attribution: IGNORE-CONFIG-FAILED {failure}", file=sys.stderr)
        return GIT_FAILED_EXIT
    except GitError as failure:
        print(f"attribution: GIT-FAILED {failure}", file=sys.stderr)
        return GIT_FAILED_EXIT
    if not checked:
        print("attribution: NOTHING-TO-CHECK no pass holds a scored bead", file=sys.stderr)
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
