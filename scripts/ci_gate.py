"""Record br's `check` gate for a bead from CI's run on the pushed HEAD commit.

The commit CI verified is the commit that closes. The gate passes only when HEAD
is on a remote branch, a completed push run of ci.yml for that exact commit
succeeded, and every lane the workflow's `lane:` matrix declares at that commit
has a successful `check (<lane>)` job. The matrix is read as data, never run;
`tests/unit/test_ci_gate.py` holds it equal to `tests/_ci_lanes.py` `CI_LANES`,
and that test is part of the run being read. Anything less records nothing.

  usage: ci_gate.py --bead <id>

Exit 0 when the gate is recorded, 1 when CI does not show the commit green, 2 on
a usage error, and 3 when git, gh or br could not answer.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = "ci.yml"
WORKFLOW_FILE = ".github/workflows/ci.yml"
TIMEOUT_SECONDS = 60

Run = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class Unanswered(Exception):
    """git, gh or br failed, so the commit's state is unknown."""


def default_run(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(cmd), cwd=ROOT, capture_output=True, text=True, check=False, timeout=TIMEOUT_SECONDS)


def ask(run: Run, cmd: Sequence[str]) -> str:
    try:
        done = run(cmd)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Unanswered(f"{cmd[0]}: {exc}") from exc
    if done.returncode != 0:
        raise Unanswered(f"{' '.join(cmd[:3])} exited {done.returncode}: {done.stderr.strip()}")
    return done.stdout


def green_run(runs: Sequence[dict]) -> int | None:
    for entry in runs:
        if entry.get("status") == "completed" and entry.get("conclusion") == "success":
            return int(entry["databaseId"])
    return None


def declared_lanes(workflow: str) -> tuple[str, ...]:
    lanes = tuple(
        lane.strip()
        for line in workflow.splitlines()
        if line.strip().startswith("lane: [")
        for lane in line.split("[", 1)[1].rsplit("]", 1)[0].split(",")
        if lane.strip()
    )
    if not lanes:
        raise Unanswered(f"{WORKFLOW_FILE} declares no lane matrix")
    return lanes


def missing_lanes(lanes: Sequence[str], jobs: Sequence[dict]) -> list[str]:
    passed = {job.get("name") for job in jobs if job.get("conclusion") == "success"}
    return [lane for lane in lanes if f"check ({lane})" not in passed]


def log_line(root: Path, text: str) -> None:
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with (root / ".check.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {text}\n")


def gate(bead: str, run: Run, root: Path, br: str) -> int:
    sha = ask(run, ["git", "rev-parse", "HEAD"]).strip()
    if not ask(run, ["git", "branch", "-r", "--contains", sha]).strip():
        log_line(root, f"DENY gate-report bead={bead} reason=ci-not-pushed sha={sha}")
        print(f"[check] HEAD {sha} is on no remote branch: push it and wait for CI", file=sys.stderr)
        return 1
    runs = json.loads(
        ask(
            run,
            [
                "gh",
                "run",
                "list",
                "--workflow",
                WORKFLOW,
                "--commit",
                sha,
                "--event",
                "push",
                "--json",
                "databaseId,status,conclusion",
            ],
        )
        or "[]"
    )
    run_id = green_run(runs)
    if run_id is None:
        states = ",".join(f"{r.get('status')}/{r.get('conclusion') or '-'}" for r in runs) or "none"
        log_line(root, f"DENY gate-report bead={bead} reason=ci-not-green sha={sha} runs={states}")
        print(f"[check] no green {WORKFLOW} push run for {sha} (runs: {states})", file=sys.stderr)
        return 1
    lanes = declared_lanes(ask(run, ["git", "show", f"{sha}:{WORKFLOW_FILE}"]))
    jobs = json.loads(ask(run, ["gh", "run", "view", str(run_id), "--json", "jobs"]) or "{}").get("jobs", [])
    missing = missing_lanes(lanes, jobs)
    if missing:
        log_line(root, f"DENY gate-report bead={bead} reason=ci-lane-missing run={run_id} lanes={','.join(missing)}")
        print(f"[check] run {run_id} has no successful job for lanes: {', '.join(missing)}", file=sys.stderr)
        return 1
    note = f"ci run {run_id} sha {sha} lanes {len(lanes)}"
    done = run(
        [
            br,
            "gate",
            "report",
            bead,
            "--gate",
            "check",
            "--provider",
            "ci",
            "--status",
            "pass",
            "--to",
            "closed",
            "--note",
            note,
        ]
    )
    log_line(
        root,
        f"GATE_REPORT bead={bead} gate=check status=pass exit={done.returncode} provider=ci run={run_id} sha={sha}",
    )
    if done.returncode != 0:
        print(f"[check] br gate report failed: {done.stderr.strip()}", file=sys.stderr)
        return 3
    print(f"[check] check gate recorded for {bead} from CI run {run_id} on {sha} ({len(lanes)} lanes)")
    return 0


def main(argv: Sequence[str] | None = None, run: Run = default_run, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(prog="ci_gate.py")
    parser.add_argument("--bead", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    br = os.environ.get("BR_BIN", str(Path.home() / ".local/bin/br"))
    try:
        return gate(args.bead, run, root, br)
    except (Unanswered, json.JSONDecodeError, KeyError) as exc:
        log_line(root, f"DENY gate-report bead={args.bead} reason=ci-unanswered detail={exc}")
        print(f"[check] cannot read the commit's CI state: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
