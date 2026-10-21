import fcntl
import os
import stat
from contextlib import contextmanager
from pathlib import Path

from cairn import escrow, log
from cairn.substrate_errors import WriterAlreadyOpen

HARNESS_LOCK_SUFFIX = ".harness-lock"


def running_attempts(sub):
    rows = sub.conn.execute(
        "SELECT attempt_id FROM attempts WHERE status = 'RUNNING' AND ended_at IS NULL ORDER BY rowid"
    ).fetchall()
    return [row["attempt_id"] for row in rows]


@contextmanager
def harness_lock(sub):
    real = Path(os.path.realpath(sub.path))
    fd = os.open(real.with_name(real.name + HARNESS_LOCK_SUFFIX), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        raise WriterAlreadyOpen(f"a live harness holds the attempts of {sub.path}") from None
    try:
        yield
    finally:
        os.close(fd)


def startup_scan(sub, *, at=None, dry_run=False, locked=False):
    if dry_run or locked:
        return _scan(sub, at, dry_run)
    with harness_lock(sub):
        return _scan(sub, at, dry_run)


def _scan(sub, at, dry_run):
    from cairn import runner

    interrupted = running_attempts(sub)
    if not dry_run:
        for attempt_id in interrupted:
            sub.close_attempt(attempt_id, runner.STATUS_INTERRUPTED, ended_at=at)
            escrow.settle_on_close(sub, attempt_id, runner.STATUS_INTERRUPTED, at=at)
    log.get(runner.LOG_STEP).info(
        "startup_scan",
        interrupted=interrupted,
        count=len(interrupted),
        dry_run=dry_run,
    )
    return interrupted


def artifacts(sub, stdout_bytes, scratch_dir):
    from cairn import runner

    lg = log.get(runner.LOG_STEP)
    found = {"output.json": (sub.put_blob(stdout_bytes), len(stdout_bytes))}
    root = Path(scratch_dir)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in sorted(dirnames + filenames):
            path = Path(dirpath) / name
            if not stat.S_ISREG(os.lstat(path).st_mode):
                lg.warning(
                    "artifact_skipped",
                    path=str(path.relative_to(root)),
                    reason="not a regular file",
                )
                continue
            artifact_name = str(path.relative_to(root))
            if artifact_name == "output.json":
                raise runner.RunnerError("scratch artifact output.json collides with captured stdout")
            data = path.read_bytes()
            found[artifact_name] = (sub.put_blob(data), len(data))
    return found


def diverged(sub, recipe_key):
    rows = sub.conn.execute(
        "SELECT output_manifest_hash FROM attempts WHERE recipe_key = ? AND status = 'OK' AND disowned_at IS NULL AND replay_grade = 'Replayable'",
        (recipe_key,),
    ).fetchall()
    manifests = {r["output_manifest_hash"] for r in rows if r["output_manifest_hash"]}
    if len(manifests) < 2:
        return ()
    return tuple(sub.mark_non_reproducible(recipe_key))
