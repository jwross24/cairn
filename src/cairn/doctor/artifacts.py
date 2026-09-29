import hashlib
import json
import logging
import os
import re
import stat
import time
from dataclasses import dataclass, field
from pathlib import Path

from cairn import cli, log

DOCTOR_DIRNAME = ".doctor"
RUNS_DIRNAME = "runs"
LATEST_NAME = "latest"
HISTORY_NAME = "scorecard_history.jsonl"
RUN_ID_STAMP = "%Y-%m-%dT%H-%M-%SZ"
RUN_ID_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z__[0-9a-f]{6}(?:-[1-9]\d{0,2})?")

lg = log.get("doctor.artifacts")


def git_head(root):
    head = Path(root) / ".git" / "HEAD"
    if not head.is_file():
        return "nogit"
    text = head.read_text().strip()
    if not text.startswith("ref:"):
        return text
    ref = text.split(":", 1)[1].strip()
    direct = Path(root) / ".git" / ref
    if direct.is_file():
        return direct.read_text().strip()
    packed = Path(root) / ".git" / "packed-refs"
    if packed.is_file():
        for line in packed.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
    return "nogit"


def make_run_id(root, *, at=None):
    seconds = int(at if at is not None else time.time())
    stamp = time.strftime(RUN_ID_STAMP, time.gmtime(seconds))
    digest = hashlib.sha256(f"{git_head(root)}{seconds}".encode()).hexdigest()[:6]
    return f"{stamp}__{digest}"


def runs_dir(root):
    return Path(root) / DOCTOR_DIRNAME / RUNS_DIRNAME


def history_path(root):
    return Path(root) / DOCTOR_DIRNAME / HISTORY_NAME


class UnsafeArtifactPath(ValueError):
    pass


def valid_run_id(run_id):
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        return False
    try:
        time.strptime(run_id[:20], RUN_ID_STAMP)
    except ValueError:
        return False
    return True


def _real_directory(path, label):
    try:
        st = Path(path).lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise UnsafeArtifactPath(f"unsafe {label}: {path} must be a real directory")
    return True


def _safe_runs_dir(root):
    doctor = Path(root) / DOCTOR_DIRNAME
    runs = doctor / RUNS_DIRNAME
    if not _real_directory(doctor, ".doctor directory"):
        return runs, False
    if not _real_directory(runs, ".doctor/runs directory"):
        return runs, False
    return runs, True


def resolve_run_dir(root, run_id):
    if run_id == LATEST_NAME:
        runs, present = _safe_runs_dir(root)
        link = Path(root) / DOCTOR_DIRNAME / LATEST_NAME
        try:
            st = link.lstat()
        except FileNotFoundError:
            return None
        if not stat.S_ISLNK(st.st_mode):
            raise UnsafeArtifactPath(f"unsafe latest path: {link} must be a symlink to one direct run")
        target = str(link.readlink())
        prefix = f"{RUNS_DIRNAME}/"
        if not target.startswith(prefix) or "/" in target[len(prefix) :] or not valid_run_id(target[len(prefix) :]):
            raise UnsafeArtifactPath(f"unsafe latest target: {link} -> {target}")
        if not present:
            raise UnsafeArtifactPath(f"unsafe latest target: {link} points into a missing runs directory")
        candidate = runs / target[len(prefix) :]
        try:
            candidate_stat = candidate.lstat()
        except FileNotFoundError:
            return None
        if stat.S_ISLNK(candidate_stat.st_mode) or not stat.S_ISDIR(candidate_stat.st_mode):
            raise UnsafeArtifactPath(f"unsafe latest target: {link} does not point to a direct run directory")
        return candidate
    if not valid_run_id(run_id):
        return None
    runs, present = _safe_runs_dir(root)
    if not present:
        return None
    candidate = runs_dir(root) / run_id
    try:
        candidate_stat = candidate.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(candidate_stat.st_mode) or not stat.S_ISDIR(candidate_stat.st_mode):
        raise UnsafeArtifactPath(f"unsafe run path: {candidate} must be a real directory")
    return candidate


def report(root, run_id):
    run_dir = resolve_run_dir(root, run_id)
    if run_dir is None:
        return None
    report_path = run_dir / "report.json"
    try:
        st = report_path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise UnsafeArtifactPath(f"unsafe report path: {report_path} must be a regular file")
    payload = json.loads(report_path.read_text())
    if not isinstance(payload, dict) or payload.get("run_id") != run_id:
        raise UnsafeArtifactPath(f"invalid report contents: {report_path}")
    return payload


def report_available(root, run_id):
    try:
        return report(root, run_id) is not None
    except OSError, ValueError:
        return False


def resolve_undo_target(root, run_id):
    if run_id != LATEST_NAME:
        return resolve_run_dir(root, run_id)
    for row in reversed(history(root)):
        if row.get("actions"):
            run_dir = resolve_run_dir(root, row.get("run_id"))
            if run_dir is None:
                continue
            actions_path = run_dir / "actions.jsonl"
            try:
                st = actions_path.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode):
                return run_dir
    return None


@dataclass
class Run:
    root: Path
    run_id: str
    run_dir: Path
    backups_dir: Path
    staging_dir: Path
    actions_path: Path
    lock: object
    handler: object = field(default=None, repr=False)


class _NoLock:
    def held(self):
        return False


def _claim_run_dir(root, run_id):
    base = runs_dir(root)
    base.mkdir(parents=True, exist_ok=True)
    # two runs inside one wall-clock second derive the same id; the directory is still one per run
    for suffix in ("", *(f"-{n}" for n in range(1, 1000))):
        candidate = base / f"{run_id}{suffix}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(f"{base}: 1000 runs already claimed {run_id}")


def start(root, lock=None, *, at=None):
    root = Path(root)
    run_dir = _claim_run_dir(root, make_run_id(root, at=at))
    run_id = run_dir.name
    backups = run_dir / "backups"
    staging = run_dir / "staging"
    backups.mkdir(parents=True, exist_ok=True)
    staging.mkdir(parents=True, exist_ok=True)
    actions = run_dir / "actions.jsonl"
    actions.touch()
    handler = logging.FileHandler(run_dir / "stderr.log")
    handler.setFormatter(log.JsonFormatter())
    handler.setLevel(logging.DEBUG)
    logging.getLogger(log.LOGGER_NAME).addHandler(handler)
    lg.info("run_start", run_id=run_id, root=str(root))
    return Run(root, run_id, run_dir, backups, staging, actions, lock or _NoLock(), handler)


def _report_markdown(report):
    lines = [
        f"# cairn doctor — {report['run_id']}",
        "",
        f"- mode: {report['mode']}",
        f"- exit_code: {report['exit_code']} ({report['exit_meaning']})",
        f"- root: {report['root']}",
        f"- findings: {len(report['findings'])}",
        f"- actions: {len(report['actions'])}",
        "",
        "## Findings",
    ]
    if not report["findings"]:
        lines.append("none")
    for finding in report["findings"]:
        lines += [
            f"### {finding['id']} ({finding['severity']}, {finding['subsystem']})",
            finding["message"],
            f"- evidence: {finding['evidence']}",
            f"- fixable: {finding['fixable']}",
            f"- next: {finding['recommended_command']}",
        ]
    lines += ["", "## Actions"]
    if not report["actions"]:
        lines.append("none")
    for action in report["actions"]:
        lines.append(f"- {action['op']} {action['path']} ({action['before_hash']} -> {action['after_hash']})")
    lines += ["", f"Undo: cairn doctor undo {report['run_id']}", ""]
    return "\n".join(lines)


def _update_latest(root, run_id):
    doctor = Path(root) / DOCTOR_DIRNAME
    target = f"{RUNS_DIRNAME}/{run_id}"
    staging = doctor / f".{LATEST_NAME}.{os.getpid()}"
    if os.path.lexists(staging):
        os.chflags(staging, 0)
    staging.symlink_to(target)
    staging.replace(doctor / LATEST_NAME)


def finish(run, report):
    (run.run_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (run.run_dir / "report.md").write_text(_report_markdown(report))
    (run.run_dir / "undo.sh").write_text(f"#!/bin/sh\ncairn doctor undo {run.run_id}\n")
    _update_latest(run.root, run.run_id)
    with history_path(run.root).open("a") as fh:
        fh.write(
            json.dumps(
                {
                    "run_id": run.run_id,
                    "mode": report["mode"],
                    "exit_code": report["exit_code"],
                    "findings": len(report["findings"]),
                    "actions": len(report["actions"]),
                    "ts": cli.now_iso(),
                },
                sort_keys=True,
            )
            + "\n"
        )
    lg.info("run_finish", run_id=run.run_id, exit_code=report["exit_code"])


def close(run):
    if run.handler is not None:
        logging.getLogger(log.LOGGER_NAME).removeHandler(run.handler)
        run.handler.close()
        run.handler = None


def history(root):
    path = history_path(root)
    if not _real_directory(path.parent, ".doctor directory"):
        return []
    try:
        st = path.lstat()
    except FileNotFoundError:
        return []
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise UnsafeArtifactPath(f"unsafe history path: {path} must be a regular file")
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    except json.JSONDecodeError as exc:
        raise UnsafeArtifactPath(f"invalid history contents: {path}: {exc}") from exc
