import argparse
import sys
from pathlib import Path

from cairn import cli, exits, kat, log
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
    ("ls", "list the runs recorded in .doctor/scorecard_history.jsonl"),
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
            "undo_latest_resolves_to": "the newest run whose actions.jsonl is not empty",
            "lock": mutate.LOCK_RELPATH,
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
        "Detect first, fix second. `cairn doctor` never writes outside .doctor/; `--fix` is the only mutating form",
        "and every write it makes is backed up verbatim first and replayable in reverse by `cairn doctor undo`.",
        "",
        "## The sequence when an M0 command refuses",
        "1. cairn doctor --robot-triage           one document: what is wrong and the exact next command",
        "2. cairn doctor --explain <finding-id>   the evidence behind one finding",
        "3. cairn doctor --dry-run --fix          the plan; writes nothing but the run artifact",
        "4. cairn doctor --fix                    apply the two repairs the doctor owns",
        "5. cairn doctor undo latest              restore every byte the newest run with actions changed",
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
        f"- {doc['run_artifacts']['lock']} is the flock a --fix holds; the kernel releases it when the holder dies",
        "- a backup carries the source file's flags, so a run that backed up a uappnd file leaves an",
        "  append-only tree: chflags -R nouappnd .doctor/runs/<run-id> before clearing that directory",
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
    rows = artifacts.history(root)
    if ns.json:
        cli.emit_json("doctor", {"mode": "ls", "runs": rows})
        return exits.DOCTOR_HEALTHY
    if not rows:
        print(f"no runs recorded under {artifacts.history_path(root)}")
        return exits.DOCTOR_HEALTHY
    for row in rows:
        print(
            f"{row['run_id']}  {row['mode']:<8} exit={row['exit_code']} "
            f"findings={row['findings']} actions={row['actions']}"
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
    run_dir = artifacts.resolve_undo_target(root, ns.run_id)
    if run_dir is None:
        raise CliError(
            exits.DOCTOR_USAGE,
            f"cairn doctor undo: no run {ns.run_id} under {artifacts.runs_dir(root)}",
            next_command="cairn doctor ls",
        )
    with mutate.acquire(root) as _lock:
        restored = mutate.undo(root, run_dir)
    payload = {
        "mode": "undo",
        "run_id": run_dir.name,
        "restored": [{"path": a["path"], "op": a["op"], "hash": a["before_hash"]} for a in restored],
        "exit_code": exits.DOCTOR_HEALTHY,
    }
    _emit(ns, payload, f"undid {len(restored)} actions from {run_dir.name}\n")
    return exits.DOCTOR_HEALTHY


def _report_text(report):
    lines = [f"cairn doctor {report['run_id']}: {report['summary']}"]
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
    fix = getattr(ns, "fix", False)
    mode = "fix" if fix and not ns.dry_run else "dry-run" if fix else "detect"
    lock = mutate.acquire(root) if mode == "fix" else None
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
        artifacts.finish(run, report)
    finally:
        artifacts.close(run)
        if lock is not None:
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
        sys.stderr.write(f"error: {exc}; run: cairn doctor (read-only) or wait\n")
        lg.info("refused", reason="concurrency", detail=str(exc))
        return exits.DOCTOR_CONCURRENCY
    except mutate.Refused as exc:
        sys.stderr.write(f"error: {exc}; nothing was changed; run: {CAPABILITIES_COMMAND}\n")
        lg.info("refused", reason="unsafe", detail=str(exc))
        return exits.DOCTOR_REFUSED
    except mutate.UndoFailed as exc:
        sys.stderr.write(f"error: {exc}; nothing was changed; run: cairn doctor ls\n")
        lg.info("refused", reason="undo_failed", detail=str(exc))
        return exits.DOCTOR_ROLLED_BACK
    except OSError as exc:
        sys.stderr.write(
            f"error: {exc}; the doctor could not read or write under --root; "
            f"nothing was changed; run: cairn doctor --root <a writable checkout>\n"
        )
        lg.info("refused", reason="io", detail=str(exc))
        return exits.DOCTOR_REFUSED


cli.register(
    "doctor",
    configure,
    _run,
    summary="diagnose the M0 deploy shape read-only, and repair the two failure modes it owns with --fix",
    read_only=False,
    json=True,
    dangerous=True,
    gating="--fix",
    dry_run_default=True,
)
