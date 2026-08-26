import fcntl
import json
import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path

import blake3

from cairn import cli, log

LOCK_RELPATH = ".doctor/lock"
QUARANTINE_SUFFIX = ".doctor-quarantine"
CRASH_ENV = "CAIRN_DOCTOR_CRASH_AFTER_BACKUP"

MODES = "modes"
WRITE = "write"
MKDIR = "mkdir"

lg = log.get("doctor.mutate")


class Refused(Exception):
    pass


class ConcurrencyLost(Exception):
    def __init__(self, path, holder):
        super().__init__(f"another cairn doctor --fix holds {path} (pid {holder})")
        self.path = str(path)
        self.holder = holder


class UndoFailed(Exception):
    pass


@dataclass(frozen=True)
class Op:
    kind: str
    mode: int | None = None
    flags: int | None = None
    data: bytes | None = None


class Lock:
    def __init__(self, root):
        self.path = Path(root) / LOCK_RELPATH
        self.fd = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            holder = os.read(fd, 64).decode("utf-8", "replace").strip() or "unknown"
            os.close(fd)
            lg.info("lock_held", path=str(self.path), holder=holder)
            raise ConcurrencyLost(self.path, holder) from None
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.fsync(fd)
        self.fd = fd
        lg.info("lock_taken", path=str(self.path), pid=os.getpid())
        return self

    def release(self):
        if self.fd is None:
            return
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None
        lg.info("lock_released", path=str(self.path))

    def held(self):
        return self.fd is not None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()


def acquire(root):
    return Lock(root).acquire()


def file_hash(path):
    return blake3.blake3(Path(path).read_bytes()).hexdigest()


def _state(path):
    if not os.path.lexists(path):
        return None, None, None
    st = os.stat(path)
    if stat.S_ISDIR(st.st_mode):
        return None, stat.S_IMODE(st.st_mode), st.st_flags
    return file_hash(path), stat.S_IMODE(st.st_mode), st.st_flags


def _relpath(root, path):
    return str(Path(path).resolve().relative_to(Path(root).resolve()))


def _backup(run, rel, path):
    target = Path(run.backups_dir) / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    os.chflags(target, os.stat(path).st_flags)
    return target


def _clear_flags(path):
    if os.stat(path).st_flags:
        os.chflags(path, 0)


def _apply(run, rel, path, op, before_mode):
    if op.kind == MODES:
        _clear_flags(path)
        os.chmod(path, op.mode)
        os.chflags(path, op.flags)
        return
    if op.kind == WRITE:
        staging = Path(run.staging_dir) / rel
        staging.parent.mkdir(parents=True, exist_ok=True)
        staging.write_bytes(op.data)
        os.chmod(staging, op.mode if op.mode is not None else (before_mode if before_mode is not None else 0o644))
        if os.path.lexists(path):
            _clear_flags(path)
        os.replace(staging, path)
        return
    if op.kind == MKDIR:
        os.mkdir(path, op.mode if op.mode is not None else 0o755)
        return
    raise Refused(f"unknown mutate op {op.kind!r}")


def mutate(run, path, op):
    if not run.lock.held():
        raise Refused(f"mutate({path}) without the {LOCK_RELPATH} lock")
    path = Path(path)
    rel = _relpath(run.root, path)
    exists = os.path.lexists(path)
    if op.kind == MODES and not exists:
        raise Refused(f"{rel} does not exist; creating it is an operator act, not a repair")
    if op.kind == MKDIR and exists:
        raise Refused(f"{rel} already exists")
    before_hash, before_mode, before_flags = _state(path)
    backup = None
    if exists and op.kind in (WRITE, MODES):
        backup = _relpath(run.root, _backup(run, rel, path))
    if os.environ.get(CRASH_ENV) == "1":
        lg.info("crash_hook", path=rel, op=op.kind)
        os.kill(os.getpid(), 9)
    _apply(run, rel, path, op, before_mode)
    after_hash, after_mode, after_flags = _state(path)
    action = {
        "path": rel,
        "op": op.kind,
        "before_hash": before_hash,
        "after_hash": after_hash,
        "before_mode": before_mode,
        "before_flags": before_flags,
        "after_mode": after_mode,
        "after_flags": after_flags,
        "backup": backup,
        "ts": cli.now_iso(),
    }
    with open(run.actions_path, "a") as fh:
        fh.write(json.dumps(action, sort_keys=True) + "\n")
    lg.info("mutate", **action)
    return action


def read_actions(run_dir):
    path = Path(run_dir) / "actions.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _restore_file(root, run_dir, action):
    target = Path(root) / action["path"]
    backup = Path(run_dir) / "backups" / action["path"]
    staging = Path(run_dir) / "undo-staging" / action["path"]
    staging.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, staging)
    os.chflags(staging, 0)
    os.chmod(staging, action["before_mode"])
    if os.path.lexists(target):
        _clear_flags(target)
    os.replace(staging, target)
    os.chflags(target, action["before_flags"] or 0)


def _undo_one(root, run_dir, action):
    target = Path(root) / action["path"]
    if action["op"] == MODES:
        if not os.path.lexists(target):
            raise UndoFailed(f"{action['path']} is gone; cannot restore its mode")
        _clear_flags(target)
        os.chmod(target, action["before_mode"])
        os.chflags(target, action["before_flags"] or 0)
    elif action["op"] == WRITE:
        if action["backup"] is None:
            quarantine = target.with_name(target.name + QUARANTINE_SUFFIX)
            _clear_flags(target)
            os.replace(target, quarantine)
            return
        _restore_file(root, run_dir, action)
    elif action["op"] == MKDIR:
        if any(Path(target).iterdir()):
            raise UndoFailed(f"{action['path']} is not empty; refusing to remove it")
        os.rmdir(target)
    else:
        raise UndoFailed(f"unknown op {action['op']!r}")
    after_hash, after_mode, after_flags = _state(target)
    if action["op"] != MKDIR and after_hash != action["before_hash"]:
        raise UndoFailed(f"{action['path']} restored to {after_hash}, expected {action['before_hash']}")
    lg.info("undo", path=action["path"], op=action["op"], mode=after_mode, flags=after_flags)


def undo(root, run_dir):
    actions = read_actions(run_dir)
    for action in actions:
        if action["backup"] is None:
            continue
        backup = Path(run_dir) / "backups" / action["path"]
        if not backup.is_file():
            raise UndoFailed(f"backup {backup} is missing; refusing to undo any action of this run")
    for action in reversed(actions):
        _undo_one(root, run_dir, action)
    lg.info("undo_done", run_dir=str(run_dir), actions=len(actions))
    return actions
