import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from cairn.migrate_catalog import MigrationRefused, classify
from cairn.migrate_fingerprint import fingerprint, integrity, row_digests, store_witness, table_columns


class NothingToMigrate(MigrationRefused):
    pass


@dataclass(frozen=True)
class Plan:
    path: str
    from_fp: str
    to_fp: str
    steps: tuple
    digests: dict
    integrity: str
    token: str

    def run_id(self, utc):
        return f"{self.from_fp[:8]}-{self.to_fp[:8]}-{utc}"

    def document(self, utc):
        return {
            "path": self.path,
            "from_fingerprint": self.from_fp,
            "to_fingerprint": self.to_fp,
            "steps": [{"id": s.id, "file": s.file, "sql_sha256": s.sql_sha256} for s in self.steps],
            "backup_path": str(backup_path(self.path, self.run_id(utc))),
            "integrity_check": self.integrity,
            "row_counts": {table: entry["rows"] for table, entry in self.digests.items()},
            "plan_token": self.token,
        }


def utc_stamp(epoch=None):
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(time.time() if epoch is None else epoch))


def backup_path(path, run_id):
    return Path(f"{path}.pre-migrate-{run_id}.sqlite")


def sidecar_path(path, run_id):
    return Path(f"{backup_path(path, run_id)}.json")


def token_for(path, from_fp, to_fp, steps, digests, integrity_result, witness):
    material = {
        "path": path,
        "from": from_fp,
        "to": to_fp,
        "steps": [[s.id, s.file, s.sql_sha256] for s in steps],
        "digests": digests,
        "integrity": integrity_result,
        "witness": witness,
        "backup_pattern": f"{path}.pre-migrate-{from_fp[:8]}-{to_fp[:8]}-<utc>.sqlite",
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _applied_history_problems(conn, catalog):
    has_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
    ).fetchone()
    if not has_table:
        return []
    wanted = {"step_id", "sql_sha256"}
    if not wanted <= set(table_columns(conn, "schema_migrations")):
        return ["schema_migrations lacks step_id or sql_sha256"]
    problems = []
    for step_id, recorded in conn.execute("SELECT step_id, sql_sha256 FROM schema_migrations ORDER BY seq"):
        known = catalog.by_id(step_id)
        if known is None:
            problems.append(f"the store records applied step {step_id} that this checkout does not ship (newer store)")
        elif known.sql_sha256 != recorded:
            problems.append(
                f"step {step_id}: the store applied sha256 {recorded} but this checkout ships {known.sql_sha256}"
            )
    return problems


def build_plan(conn, path, shipped_objects, catalog):
    catalog.verify()
    state = classify(conn, shipped_objects, catalog)
    if state.kind == "empty":
        raise MigrationRefused(f"{path} holds no schema; nothing to migrate")
    if state.kind == "current":
        raise NothingToMigrate(f"{path} already has the shipped schema ({state.fingerprint[:12]}); nothing to migrate")
    if state.kind != "migratable":
        raise MigrationRefused(
            f"{path} holds {state.kind} schema fingerprint {state.fingerprint} with no migration path to the shipped "
            "schema; it is left unmodified (a non-additive change needs a new store)"
        )
    problems = _applied_history_problems(conn, catalog)
    if problems:
        raise MigrationRefused("; ".join(problems))
    result = integrity(conn)
    if result != "ok":
        raise MigrationRefused(f"{path} fails integrity_check ({result}); it is left unmodified")
    digests = row_digests(conn)
    target = fingerprint(shipped_objects)
    return Plan(
        path=str(path),
        from_fp=state.fingerprint,
        to_fp=target,
        steps=state.steps,
        digests=digests,
        integrity=result,
        token=token_for(str(path), state.fingerprint, target, state.steps, digests, result, store_witness(conn)),
    )


def plan_readonly(path, shipped_objects, catalog):
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{path} does not exist")
    conn = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True, timeout=5)
    try:
        return build_plan(conn, str(resolved), shipped_objects, catalog)
    finally:
        conn.close()
