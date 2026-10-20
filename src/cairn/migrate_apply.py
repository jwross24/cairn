import contextlib
import hashlib
import hmac
import json
import os
import sqlite3
import subprocess
from pathlib import Path

from cairn.migrate_catalog import MigrationRefused
from cairn.migrate_fingerprint import (
    digest_differences,
    integrity,
    preserved_digests,
    store_fingerprint,
)
from cairn.migrate_plan import backup_path, build_plan, sidecar_path, utc_stamp

BUSY_S = 5
REPO = Path(__file__).resolve().parent


class PostCommitFailure(MigrationRefused):
    pass


def git_sha():
    head = subprocess.run(
        ["/usr/bin/git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30
    )
    return head.stdout.strip() if head.returncode == 0 and head.stdout.strip() else "unknown"


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lock_exclusive(path):
    conn = sqlite3.connect(f"file:{path}?mode=rw", uri=True, timeout=BUSY_S, autocommit=True)
    try:
        conn.execute("PRAGMA locking_mode=EXCLUSIVE")
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("COMMIT")
    except BaseException:
        conn.close()
        raise
    return conn


def checkpoint(conn):
    busy, _, _ = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise MigrationRefused("wal_checkpoint(TRUNCATE) could not complete; the store is left unmodified")


def verify_copy(path, universe, from_fp, digests):
    conn = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        problems = []
        result = integrity(conn)
        if result != "ok":
            problems.append(f"integrity_check: {result}")
        if store_fingerprint(conn, universe) != from_fp:
            problems.append("schema fingerprint differs from the source")
        changed = digest_differences(digests, preserved_digests(conn, digests))
        if changed:
            problems.append("row digests differ in " + ", ".join(changed))
        return problems
    finally:
        conn.close()


def write_backup(conn, plan, run_id, universe):
    destination, sidecar = backup_path(plan.path, run_id), sidecar_path(plan.path, run_id)
    if destination.exists() or sidecar.exists():
        raise MigrationRefused(f"{destination} already exists; it is never overwritten")
    target = sqlite3.connect(destination)
    try:
        conn.backup(target)
    finally:
        target.close()
    problems = verify_copy(destination, universe, plan.from_fp, plan.digests)
    if problems:
        raise MigrationRefused(f"the backup {destination} failed verification: " + "; ".join(problems))
    destination.chmod(0o444)
    record = {
        "run_id": run_id,
        "path": plan.path,
        "from_fingerprint": plan.from_fp,
        "to_fingerprint": plan.to_fp,
        "plan_token": plan.token,
        "backup_sha256": file_sha256(destination),
        "digests": plan.digests,
        "steps": [s.id for s in plan.steps],
        "cairn_git_sha": git_sha(),
    }
    with sidecar.open("x") as handle:
        handle.write(json.dumps(record, sort_keys=True, indent=1) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    sidecar.chmod(0o444)
    return destination, record


def execute_step(conn, step):
    for statement in step.statements():
        conn.execute(statement)


def run_steps(conn, plan, universe, run_id, applied_at, sha):
    conn.execute("BEGIN IMMEDIATE")
    try:
        for step in plan.steps:
            execute_step(conn, step)
            reached = store_fingerprint(conn, universe)
            if reached != step.to_fp:
                raise MigrationRefused(f"step {step.id} reached fingerprint {reached}, expected {step.to_fp}")
        changed = digest_differences(plan.digests, preserved_digests(conn, plan.digests))
        if changed:
            raise MigrationRefused("row-preservation digests changed in " + ", ".join(changed))
        for step in plan.steps:
            conn.execute(
                "INSERT INTO schema_migrations (run_id, step_id, from_fingerprint, to_fingerprint, sql_sha256,"
                " cairn_git_sha, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, step.id, step.from_fp, step.to_fp, step.sql_sha256, sha, applied_at),
            )
        conn.execute("COMMIT")
    except BaseException:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute("ROLLBACK")
        raise


def after_commit(_resolved):
    return None


def doctor_errors(path):
    from cairn.doctor import detectors

    ctx = detectors.Context(root=Path(), db=Path(path), bundle=Path(), pin=Path(), attest=Path(), quick=True)
    return [f"{f.id}: {f.evidence}" for f in detectors.d_substrate(ctx) if f.severity == detectors.ERROR]


def fresh_verification(path, plan, universe):
    from cairn.substrate import Substrate

    problems = []
    try:
        fresh = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=BUSY_S)
        try:
            result = integrity(fresh)
            if result != "ok":
                problems.append(f"fresh-connection integrity_check: {result}")
            elif store_fingerprint(fresh, universe) != plan.to_fp:
                problems.append("fresh-connection schema fingerprint is not the target")
            else:
                changed = digest_differences(plan.digests, preserved_digests(fresh, plan.digests))
                if changed:
                    problems.append("fresh-connection row digests differ in " + ", ".join(changed))
        finally:
            fresh.close()
        if not problems:
            Substrate.open(path, role="reader").close()
            problems += doctor_errors(path)
    except (sqlite3.DatabaseError, MigrationRefused) as exc:
        problems.append(f"{type(exc).__name__}: {exc}")
    return problems


def apply(path, token, shipped_objects, catalog, *, epoch=None):
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{path} does not exist")
    universe = set(shipped_objects)
    conn = lock_exclusive(resolved)
    try:
        plan = build_plan(conn, str(resolved), shipped_objects, catalog)
        if not hmac.compare_digest(plan.token.encode(), str(token).encode()):
            raise MigrationRefused(
                "the plan token does not match the store as it is now (stale, tampered, or the store changed "
                f"since the plan); nothing was changed; run: cairn substrate migrate plan --db {resolved}"
            )
        stamp = utc_stamp(epoch)
        run_id = plan.run_id(stamp)
        checkpoint(conn)
        backup, record = write_backup(conn, plan, run_id, universe)
        run_steps(conn, plan, universe, run_id, stamp, record["cairn_git_sha"])
        checkpoint(conn)
    finally:
        conn.close()
    after_commit(resolved)
    problems = fresh_verification(resolved, plan, universe)
    if problems:
        raise PostCommitFailure(
            f"the migration committed but verification failed: {'; '.join(problems)}; the pre-migration backup is "
            f"{backup}; run: cairn substrate migrate undo --db {resolved} --run {run_id}"
        )
    return {
        "run_id": run_id,
        "path": str(resolved),
        "backup_path": str(backup),
        "from_fingerprint": plan.from_fp,
        "to_fingerprint": plan.to_fp,
        "steps": [s.id for s in plan.steps],
        "row_digests": {t: e["sha256"] for t, e in plan.digests.items()},
    }


def _read_record(resolved, run_id):
    sidecar = sidecar_path(resolved, run_id)
    if not sidecar.is_file():
        raise MigrationRefused(f"no migration record {sidecar}")
    record = json.loads(sidecar.read_text())
    if record["run_id"] != run_id or record["path"] != str(resolved):
        raise MigrationRefused(f"{sidecar} belongs to a different run or store")
    backup = backup_path(resolved, run_id)
    if not backup.is_file() or file_sha256(backup) != record["backup_sha256"]:
        raise MigrationRefused(f"{backup} is missing or does not match the recorded sha256")
    return record, backup


def _quarantine(resolved, run_id, stamp):
    conn = lock_exclusive(resolved)
    try:
        checkpoint(conn)
        quarantine = Path(f"{resolved}.quarantine-{run_id}-{stamp}.sqlite")
        if quarantine.exists():
            raise MigrationRefused(f"{quarantine} already exists")
        resolved.rename(quarantine)
    finally:
        conn.close()
    for suffix in ("-wal", "-shm"):
        leftover = Path(f"{resolved}{suffix}")
        if leftover.exists():
            leftover.rename(Path(f"{quarantine}{suffix}"))
    return quarantine


def undo(path, run_id, shipped_objects, *, epoch=None):
    resolved = Path(path).resolve()
    record, backup = _read_record(resolved, run_id)
    universe = set(shipped_objects)
    problems = verify_copy(backup, universe, record["from_fingerprint"], record["digests"])
    if problems:
        raise MigrationRefused(f"the backup {backup} failed verification: " + "; ".join(problems))
    quarantine = _quarantine(resolved, run_id, utc_stamp(epoch)) if resolved.exists() else None
    staging = resolved.with_name(f"{resolved.name}.restore-{run_id}.partial")
    try:
        if resolved.exists() or staging.exists():
            raise MigrationRefused(f"{resolved} reappeared during the undo; the quarantined store is {quarantine}")
        with backup.open("rb") as source, staging.open("xb") as target:
            target.writelines(iter(lambda: source.read(1 << 20), b""))
            target.flush()
            os.fsync(target.fileno())
        staging.rename(resolved)
    except BaseException:
        if quarantine is not None and not resolved.exists():
            quarantine.rename(resolved)
        raise
    restored_problems = verify_copy(resolved, universe, record["from_fingerprint"], record["digests"])
    if file_sha256(resolved) != record["backup_sha256"]:
        restored_problems.append("restored bytes differ from the backup")
    if restored_problems:
        raise MigrationRefused(f"the restored store failed verification: {'; '.join(restored_problems)}")
    return {
        "run_id": run_id,
        "path": str(resolved),
        "restored_from": str(backup),
        "restored_sha256": record["backup_sha256"],
        "quarantined": None if quarantine is None else str(quarantine),
        "fingerprint": record["from_fingerprint"],
    }
