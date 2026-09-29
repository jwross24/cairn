import argparse
import json
import sys
from pathlib import Path

from cairn import cli, doctor_gc, exits, kat, log
from cairn.doctor import artifacts, detectors, fixers, mutate
from cairn.errors import CliError

lg = log.get("doctor")

DOCTOR_VERSION = "1.0.0"
DOCTOR_CONTRACT_VERSION = "1"
CAPABILITIES_COMMAND = "cairn doctor capabilities --json"
DEFAULT_ROOT = kat.REPO_ROOT
SUBCOMMANDS = (
    ("undo", "restore every file a run changed, in reverse order, from its verbatim backups"),
    ("capabilities", "print the doctor contract: detectors, fixers, exit codes, artifact layout"),
    ("health", "one line and an exit code; the cheap detectors only"),
    ("robot-docs", "print the doctor's agent handbook"),
    ("ls", "list recorded runs and show whether their artifacts are available"),
    ("gc", "list old run artifacts; --yes removes them and relinquishes their undo backups"),
    ("diff", "compare the current planned actions with a retained run; read-only"),
)
SEVERITY_ORDER = (detectors.ERROR, detectors.WARN, detectors.INFO)
FIXERS_DOC = fixers.FIXERS


class _DoctorParser(argparse.ArgumentParser):
    def error(self, message):
        raise CliError(
            exits.DOCTOR_USAGE,
            f"{self.prog}: {message}",
            next_command=f"{self.prog} --help",
        )


def configure(parser):
    parser.__class__ = _DoctorParser
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
        metavar="PATH",
        help="checkout root: locates .doctor/, .gitignore, pyproject.toml and .git/HEAD",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="with --fix, print the plan and write only the run artifact"
    )
    parser.add_argument("--quick", action="store_true", help="cheap detectors only: no gp spawn, no KAT")
    parser.add_argument(
        "--only",
        default=None,
        metavar="SUBSYSTEM,...",
        help=f"scope to a subset of subsystems: {', '.join(detectors.SUBSYSTEMS)}",
    )
    parser.add_argument("--online", action="store_true", help="enable network probes; refused at M0, nothing needs one")
    parser.add_argument("--explain", default=None, metavar="FINDING-ID", help="expand one finding with its evidence")
    parser.add_argument("--since", default=None, metavar="RUN-ID", help="compare findings with a retained run")
    parser.add_argument(
        "--robot-triage",
        action="store_true",
        help="one JSON document: summary, findings, actions_planned, recommended_command",
    )
    subs = parser.add_subparsers(dest="doctor_command", metavar="SUBCOMMAND")
    for name, summary in SUBCOMMANDS:
        sub = subs.add_parser(
            name, parents=[cli.json_parent()], help=summary, description=summary, epilog=cli.DISCOVERY_HINT
        )
        if name == "undo":
            sub.add_argument("run_id", metavar="RUN-ID", help="a run id under .doctor/runs/, or the word latest")
        elif name == "gc":
            sub.add_argument(
                "--before", required=True, metavar="DATE", help="UTC date or timezone-aware ISO-8601 instant"
            )
            sub.add_argument("--yes", action="store_true", help="remove every listed run artifact older than --before")
        elif name == "diff":
            sub.add_argument("run_id", nargs="?", metavar="RUN-ID", help="compare with a retained run report")


def capabilities_document():
    return {
        "tool": "cairn doctor",
        "doctor_version": DOCTOR_VERSION,
        "doctor_contract_version": DOCTOR_CONTRACT_VERSION,
        "detectors": [
            {
                "id": d.id,
                "subsystem": d.subsystem,
                "summary": d.summary,
                "under_quick": detectors.under_quick(d.id),
            }
            for d in detectors.DETECTORS
        ],
        "fixers": [{"id": name, "summary": summary} for name, summary in FIXERS_DOC],
        "subsystems": list(detectors.SUBSYSTEMS),
        "exit_codes": {
            "cli": {str(k): v for k, v in exits.CLI.items()},
            "doctor": {str(k): v for k, v in exits.DOCTOR.items()},
        },
        "run_artifacts": {
            "directory": ".doctor/runs/<ISO8601Z>__<sha256(git_head+iso_seconds)[:6]>/",
            "files": ["report.json", "report.md", "actions.jsonl", "backups/", "staging/", "stderr.log", "undo.sh"],
            "index": ".doctor/scorecard_history.jsonl",
            "latest": ".doctor/latest",
            "undo_latest_resolves_to": "the newest retained run whose actions.jsonl is not empty",
            "lock": mutate.LOCK_RELPATH,
        },
        "retention": {
            "gc_cutoff": "run ID creation time strictly before --before; date-only cutoffs are UTC midnight",
            "gc_dry_run": "default; lists the exact batch without writes",
            "gc_yes": "removes the batch and relinquishes its undo backups",
            "gc_latest": "refuses the entire batch if it includes the target of .doctor/latest",
            "diff": "read-only comparison of planned actions with the current detector results",
            "since": "default-run comparison of findings with a retained report",
        },
        "writes_only_under": [".doctor/", "the paths named by a planned action"],
        "online": False,
        "capabilities_command": CAPABILITIES_COMMAND,
    }


def robot_docs_text():
    doc = capabilities_document()
    lines = [
        "# cairn doctor — agent handbook",
        "",
        "`cairn doctor` records reports under .doctor/. `--fix` backs up each changed path verbatim,",
        "and `cairn doctor undo` restores action runs whose artifacts remain retained.",
        "",
        "## The sequence when an M0 command refuses",
        "1. cairn doctor --robot-triage           one document: what is wrong and the exact next command",
        "2. cairn doctor --explain <finding-id>   the evidence behind one finding",
        "3. cairn doctor --dry-run --fix          the plan; writes only the run artifact",
        "4. cairn doctor --fix                    apply the two repairs the doctor owns",
        "5. cairn doctor undo latest              restore the newest retained action run",
        "",
        "## Detectors",
    ]
    lines += [
        f"- {d['id']} ({d['subsystem']}, under --quick: {d['under_quick']}): {d['summary']}" for d in doc["detectors"]
    ]
    lines += ["", "## Fixers (the only automated repairs; every other finding names an operator command)"]
    lines += [f"- {f['id']}: {f['summary']}" for f in doc["fixers"]]
    lines += ["", "## Exit codes (doctor)"]
    lines += [f"- {k}: {v}" for k, v in doc["exit_codes"]["doctor"].items()]
    lines += [
        "",
        "## Run artifacts",
        f"- {doc['run_artifacts']['directory']} holding {', '.join(doc['run_artifacts']['files'])}",
        f"- {doc['run_artifacts']['index']} is the index `cairn doctor ls` prints",
        f"- {doc['run_artifacts']['latest']} points at the newest run",
        f"- {doc['run_artifacts']['lock']} serializes report-producing runs, undo and collection",
        "- `cairn doctor gc --before YYYY-MM-DD` lists runs created strictly before UTC midnight",
        "  on that date; a date-time cutoff must include a timezone",
        "- gc lists candidates without writes; `gc --before DATE --yes` removes the listed artifacts",
        "  and permanently relinquishes their undo backups; it refuses the entire batch if it selects latest",
        "- gc clears file flags without following symlinks; do not clear flags manually",
        "- `cairn doctor diff [RUN-ID]` compares planned actions with current detector results without writes",
        "- `cairn doctor --since RUN-ID` adds a findings comparison to a new default-run report",
        "  diff and --since require the referenced report to remain available",
        "",
        "## Under --quick",
        "- full: the detector runs entire; skipped: it does not run; partial: it runs its cheap half only",
        "",
        "## Never",
        "- never read exit 0 from a detect run as proof a gate passes: the doctor checks shape, not verdicts",
        "- never hand-repair a pin or attestation file: cairn doctor --fix records the prior mode and flags",
        "- --online is refused at M0; nothing the doctor checks needs a network",
        "",
        f"Contract: {CAPABILITIES_COMMAND}",
    ]
    return "\n".join(lines) + "\n"


def _context(ns, root):
    return detectors.Context(
        root=root,
        db=Path(ns.db),
        bundle=Path(ns.bundle),
        pin=Path(ns.pin),
        attest=Path(ns.attest),
        quick=ns.quick,
    )


def _only(ns):
    if not ns.only:
        return None
    wanted = [part.strip() for part in ns.only.split(",") if part.strip()]
    unknown = [w for w in wanted if w not in detectors.SUBSYSTEMS]
    if unknown:
        raise CliError(
            exits.DOCTOR_USAGE,
            f"cairn doctor --only: unknown subsystem {', '.join(unknown)}",
            next_command=CAPABILITIES_COMMAND,
        )
    return set(wanted)


def _summary(findings):
    counts = {level: sum(1 for f in findings if f.severity == level) for level in SEVERITY_ORDER}
    if not findings:
        return "healthy: no findings"
    parts = ", ".join(f"{counts[level]} {level}" for level in SEVERITY_ORDER if counts[level])
    return f"{len(findings)} findings ({parts})"


def _recommended(findings, mode):
    if not findings:
        return "cairn doctor"
    fixable = [f for f in findings if f.fixable]
    if fixable and mode != "fix":
        return "cairn doctor --fix"
    unfixable = [f for f in findings if not f.fixable]
    return unfixable[0].recommended_command if unfixable else "cairn doctor --fix"


def _emit(ns, payload, text):
    if ns.json:
        cli.emit_json("doctor", payload)
    else:
        sys.stdout.write(text)


def _run_capabilities(ns):
    doc = capabilities_document()
    if ns.json:
        cli.emit_json("doctor", {"mode": "capabilities", **doc})
        return exits.DOCTOR_HEALTHY
    print(f"cairn doctor {doc['doctor_version']} (contract {doc['doctor_contract_version']})")
    for detector in doc["detectors"]:
        print(f"  {detector['id']:<20} {detector['subsystem']:<10} {detector['summary']}")
    for fixer in doc["fixers"]:
        print(f"  {fixer['id']:<20} {'fixer':<10} {fixer['summary']}")
    print("exit codes (doctor): " + "; ".join(f"{k}={v}" for k, v in doc["exit_codes"]["doctor"].items()))
    print(f"full contract: {CAPABILITIES_COMMAND}")
    return exits.DOCTOR_HEALTHY


def _run_robot_docs(ns):  # noqa: ARG001
    sys.stdout.write(robot_docs_text())
    return exits.DOCTOR_HEALTHY


def _run_ls(ns, root):
    rows = [
        {**row, "artifact_state": "available" if artifacts.report_available(root, row.get("run_id")) else "unavailable"}
        for row in artifacts.history(root)
    ]
    if ns.json:
        cli.emit_json("doctor", {"mode": "ls", "runs": rows})
        return exits.DOCTOR_HEALTHY
    if not rows:
        print(f"no runs recorded under {artifacts.history_path(root)}")
        return exits.DOCTOR_HEALTHY
    for row in rows:
        print(
            f"{row['run_id']}  {row['mode']:<8} exit={row['exit_code']} "
            f"findings={row['findings']} actions={row['actions']} artifacts={row['artifact_state']}"
        )
    return exits.DOCTOR_HEALTHY


def _run_health(ns, root):
    ctx = detectors.Context(
        root=root, db=Path(ns.db), bundle=Path(ns.bundle), pin=Path(ns.pin), attest=Path(ns.attest), quick=True
    )
    findings = detectors.detect(ctx, only=_only(ns))
    code = exits.DOCTOR_FINDINGS if findings else exits.DOCTOR_HEALTHY
    named = "".join(f" {f.id}" for f in findings)
    line = f"cairn doctor: {_summary(findings)}{named}; run: {_recommended(findings, 'detect')}"
    if ns.json:
        cli.emit_json(
            "doctor",
            {"mode": "health", "summary": line, "findings": [f.id for f in findings], "exit_code": code},
        )
    else:
        print(line)
    return code


def _run_undo(ns, root):
    with mutate.acquire(root) as _lock:
        run_dir = artifacts.resolve_undo_target(root, ns.run_id)
        if run_dir is None:
            raise CliError(
                exits.DOCTOR_USAGE,
                f"cairn doctor undo: no retained action run {ns.run_id} under {artifacts.runs_dir(root)}",
                next_command="cairn doctor ls",
            )
        restored = mutate.undo(root, run_dir)
    payload = {
        "mode": "undo",
        "run_id": run_dir.name,
        "restored": [{"path": a["path"], "op": a["op"], "hash": a["before_hash"]} for a in restored],
        "exit_code": exits.DOCTOR_HEALTHY,
    }
    _emit(ns, payload, f"undid {len(restored)} actions from {run_dir.name}\n")
    return exits.DOCTOR_HEALTHY


def _reference_report(root, run_id, command):
    if not artifacts.valid_run_id(run_id):
        raise CliError(
            exits.DOCTOR_USAGE,
            f"cairn doctor {command}: invalid run id {run_id!r}",
            next_command="cairn doctor ls",
        )
    try:
        report = artifacts.report(root, run_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise mutate.Refused(f"cairn doctor {command}: unsafe run artifact: {exc}") from exc
    if report is None:
        raise mutate.Refused(
            f"cairn doctor {command}: report for {run_id} is unavailable or collected; run: cairn doctor ls"
        )
    return report


def _action_delta(current, previous):
    current_by_key = {json_key(action): action for action in current}
    previous_by_key = {json_key(action): action for action in previous}
    return (
        [current_by_key[key] for key in sorted(current_by_key.keys() - previous_by_key.keys())],
        [previous_by_key[key] for key in sorted(previous_by_key.keys() - current_by_key.keys())],
    )


def json_key(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _run_diff(ns, root):
    reference = getattr(ns, "run_id", None)
    prior_actions = []
    if reference is not None:
        prior = _reference_report(root, reference, "diff")
        prior_actions = prior.get("actions_planned", [])
    ctx = _context(ns, root)
    actions = [action.as_dict() for action in fixers.plan(detectors.detect(ctx, only=_only(ns)))]
    added, removed = _action_delta(actions, prior_actions)
    payload = {
        "mode": "diff",
        "reference": reference,
        "actions_planned": actions,
        "added": added,
        "removed": removed,
    }
    lines = [f"cairn doctor diff: {len(actions)} planned action(s)"]
    lines.extend(f"+ {action['describe']} ({', '.join(action['because'])})" for action in added)
    lines.extend(f"- {action['describe']} ({', '.join(action['because'])})" for action in removed)
    if not added and not removed:
        lines.append("no planned-action changes")
    _emit(ns, payload, "\n".join(lines) + "\n")
    return exits.DOCTOR_HEALTHY


def _run_gc(ns, root):
    try:
        result = doctor_gc.collect(root, ns.before, yes=ns.yes)
    except doctor_gc.CollectionFailure as exc:
        payload = {
            "mode": "gc",
            "dry_run": False,
            "candidates": exc.candidates,
            "removed": exc.removed,
            "cleared_flags": exc.cleared_flags,
            "partial_state_possible": True,
            "failure_path": exc.path,
            "error": str(exc),
        }
        text = (
            f"cairn doctor gc: stopped; removed={len(exc.removed)} "
            f"cleared_flags={len(exc.cleared_flags)} partial_state_possible=true\n"
        )
        _emit(ns, payload, text)
        sys.stderr.write(
            f"error: {exc}; completed removals={len(exc.removed)}; "
            f"cleared flags={len(exc.cleared_flags)}; inspect `cairn doctor ls` before retrying\n"
        )
        lg.info(
            "gc_partial",
            detail=str(exc),
            removed=exc.removed,
            cleared_flags=exc.cleared_flags,
            failure_path=exc.path,
        )
        return exits.DOCTOR_REFUSED
    except ValueError as exc:
        raise CliError(
            exits.DOCTOR_USAGE,
            f"cairn doctor gc --before: {exc}",
            next_command="cairn doctor gc --before YYYY-MM-DD",
        ) from exc
    except doctor_gc.UnsafeCollection as exc:
        raise mutate.Refused(str(exc)) from exc
    payload = {"mode": "gc", **result}
    lines = [
        f"cairn doctor gc: candidates={len(result['candidates'])} dry_run={str(result['dry_run']).lower()} "
        f"removed={len(result['removed'])}"
    ]
    lines.extend(
        f"  {item['run_id']} started={item['created_at']} path={item['path']}" for item in result["candidates"]
    )
    lines.extend(f"  cleared flags={item['flags']:#x} path={item['path']}" for item in result["cleared_flags"])
    lines.extend(f"  removed {run_id}" for run_id in result["removed"])
    _emit(ns, payload, "\n".join(lines) + "\n")
    return exits.DOCTOR_HEALTHY


def _report_text(report):
    lines = [f"cairn doctor {report['run_id']}: {report['summary']}"]
    if report.get("since") is not None:
        delta = report["since"]
        lines.append(
            f"since {delta['run_id']}: {len(delta['added'])} findings added, {len(delta['resolved'])} resolved"
        )
    for finding in report["findings"]:
        lines.append(f"[{finding['severity']}] {finding['id']}: {finding['message']}")
        lines.append(f"    evidence: {finding['evidence']}")
        lines.append(f"    run: {finding['recommended_command']}")
    lines += [f"plan: {a['describe']}  ({', '.join(a['because'])})" for a in report["actions_planned"]]
    lines += [f"did: {a['op']} {a['path']}" for a in report["actions"]]
    lines.append(f"artifact: {report['run_dir']}")
    lines.append(f"run: {report['recommended_command']}")
    return "\n".join(lines) + "\n"


def _explain(ns, findings, root):
    match = next((f for f in findings if f.id == ns.explain), None)
    if match is None:
        raise CliError(
            exits.DOCTOR_USAGE,
            f"cairn doctor --explain: no finding {ns.explain} in this run",
            next_command="cairn doctor --json",
        )
    payload = {"mode": "explain", "finding": match.as_dict(), "root": str(root)}
    text = (
        f"{match.id} [{match.severity}] subsystem={match.subsystem}\n"
        f"{match.message}\n"
        f"evidence: {match.evidence}\n"
        f"fixable: {match.fixable}\n"
        f"run: {match.recommended_command}\n"
    )
    _emit(ns, payload, text)
    return exits.DOCTOR_FINDINGS


def _main_run(ns, root):
    only = _only(ns)
    ctx = _context(ns, root)
    since_report = _reference_report(root, ns.since, "--since") if ns.since else None
    fix = getattr(ns, "fix", False)
    mode = "fix" if fix and not ns.dry_run else "dry-run" if fix else "detect"
    lock = mutate.acquire(root)
    try:
        run = artifacts.start(root, lock)
        try:
            findings = detectors.detect(ctx, only=only)
            planned = fixers.plan(findings)
            actions = []
            if mode == "fix":
                actions = fixers.apply(run, planned)
                findings = detectors.detect(ctx, only=only)
                planned = fixers.plan(findings)
            if findings and mode == "fix":
                code = exits.DOCTOR_PARTIAL
            elif findings:
                code = exits.DOCTOR_FINDINGS
            else:
                code = exits.DOCTOR_HEALTHY
            report = {
                "mode": mode,
                "run_id": run.run_id,
                "run_dir": str(run.run_dir),
                "root": str(root),
                "exit_code": code,
                "exit_meaning": exits.DOCTOR[code],
                "summary": _summary(findings),
                "findings": [f.as_dict() for f in findings],
                "actions_planned": [a.as_dict() for a in planned],
                "actions": actions,
                "recommended_command": _recommended(findings, mode),
                "capabilities_command": CAPABILITIES_COMMAND,
                "ts": cli.now_iso(),
            }
            if since_report is not None:
                previous = {finding["id"]: finding for finding in since_report.get("findings", [])}
                current = {finding["id"]: finding for finding in report["findings"]}
                report["since"] = {
                    "run_id": ns.since,
                    "added": [current[key] for key in sorted(current.keys() - previous.keys())],
                    "resolved": [previous[key] for key in sorted(previous.keys() - current.keys())],
                }
            artifacts.finish(run, report)
        finally:
            artifacts.close(run)
    finally:
        lock.release()
    if ns.explain:
        return _explain(ns, findings, root)
    if ns.robot_triage:
        cli.emit_json(
            "doctor",
            {
                "summary": report["summary"],
                "findings": report["findings"],
                "actions_planned": report["actions_planned"],
                "recommended_command": report["recommended_command"],
                "capabilities_command": CAPABILITIES_COMMAND,
                "run_id": run.run_id,
                "exit_code": code,
            },
        )
        return code
    _emit(ns, report, _report_text(report))
    return code


def _dispatch(ns):
    root = Path(ns.root).resolve()
    command = getattr(ns, "doctor_command", None)
    if command is not None and ns.since:
        raise CliError(
            exits.DOCTOR_USAGE,
            "--since is available only on the default doctor run",
            next_command="cairn doctor --help",
        )
    if command == "gc":
        return _run_gc(ns, root)
    if command == "diff":
        return _run_diff(ns, root)
    if command == "capabilities":
        return _run_capabilities(ns)
    if command == "robot-docs":
        return _run_robot_docs(ns)
    if command == "ls":
        return _run_ls(ns, root)
    if command == "health":
        return _run_health(ns, root)
    if command == "undo":
        return _run_undo(ns, root)
    if ns.online:
        raise mutate.Refused("--online is refused at M0: no detector or fixer needs a network")
    return _main_run(ns, root)


def _run(ns):
    try:
        return _dispatch(ns)
    except mutate.ConcurrencyLost as exc:
        sys.stderr.write(f"error: {exc}; run: cairn doctor health or wait\n")
        lg.info("refused", reason="concurrency", detail=str(exc))
        return exits.DOCTOR_CONCURRENCY
    except mutate.Refused as exc:
        sys.stderr.write(f"error: {exc}; inspect `cairn doctor ls` before retrying; run: {CAPABILITIES_COMMAND}\n")
        lg.info("refused", reason="unsafe", detail=str(exc))
        return exits.DOCTOR_REFUSED
    except mutate.UndoFailed as exc:
        sys.stderr.write(f"error: {exc}; inspect `cairn doctor ls` before retrying\n")
        lg.info("refused", reason="undo_failed", detail=str(exc))
        return exits.DOCTOR_ROLLED_BACK
    except artifacts.UnsafeArtifactPath as exc:
        sys.stderr.write(f"error: {exc}; inspect `cairn doctor ls` before retrying\n")
        lg.info("refused", reason="unsafe_artifact", detail=str(exc))
        return exits.DOCTOR_REFUSED
    except OSError as exc:
        sys.stderr.write(
            f"error: {exc}; the doctor could not read or write under --root; "
            f"inspect `cairn doctor ls` before retrying; run: cairn doctor --root <a writable checkout>\n"
        )
        lg.info("refused", reason="io", detail=str(exc))
        return exits.DOCTOR_REFUSED


cli.register(
    "doctor",
    configure,
    _run,
    summary="diagnose and repair the M0 deploy shape; undo repairs or explicitly collect old doctor artifacts",
    read_only=False,
    json=True,
    dangerous=True,
    gating="--fix",
    dry_run_default=True,
)
