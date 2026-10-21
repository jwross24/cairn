import os
import stat
from pathlib import Path

from cairn import escrow, log


def running_attempts(sub):
    rows = sub.conn.execute(
        "SELECT attempt_id FROM attempts WHERE status = 'RUNNING' AND ended_at IS NULL ORDER BY rowid"
    ).fetchall()
    return [row["attempt_id"] for row in rows]


def startup_scan(sub, *, at=None, dry_run=False):
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
