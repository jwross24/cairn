import dataclasses
import json
import sqlite3
from pathlib import Path

import pytest
from _migrate_helpers import catalog, make_store, sha256, shipped, stage_fingerprint, store_fp

from cairn import migrate_apply, migrate_catalog, migrate_plan
from cairn.doctor import detectors
from cairn.migrate_fingerprint import row_digests
from cairn.substrate import Substrate
from cairn.substrate_errors import NeedsMigration, SchemaMismatch

EPOCH = 1_792_000_000
STAGE_STEPS = {"v1": ["0001", "0002"], "v2": ["0002"]}


def plan_for(path):
    return migrate_plan.plan_readonly(path, shipped(), catalog())


def apply_with(path, token, epoch=EPOCH):
    return migrate_apply.apply(path, token, shipped(), catalog(), epoch=epoch)


def digests_of(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        return row_digests(conn)
    finally:
        conn.close()


def listing(directory):
    return sorted(p.name for p in Path(directory).iterdir() if not p.name.endswith(("-wal", "-shm")))


def doctor_errors(path):
    ctx = detectors.Context(root=Path(), db=Path(path), bundle=Path(), pin=Path(), attest=Path(), quick=True)
    return [f for f in detectors.d_substrate(ctx) if f.severity == detectors.ERROR]


@pytest.fixture
def fresh_fingerprint(tmp_path):
    path = tmp_path / "fresh.sqlite"
    Substrate.open(path, role="writer").close()
    return store_fp(path)


@pytest.mark.parametrize("stage", ["v1", "v2"])
def test_a_store_from_each_historical_fingerprint_migrates_to_the_fresh_schema(stage, tmp_path, fresh_fingerprint):
    path = make_store(tmp_path, stage)
    assert store_fp(path) == stage_fingerprint(stage)
    before = digests_of(path)
    plan = plan_for(path)
    result = apply_with(path, plan.token)
    assert [s.id for s in plan.steps] == STAGE_STEPS[stage] == result["steps"]
    assert store_fp(path) == fresh_fingerprint == plan.to_fp
    after = digests_of(path)
    assert {t: after[t] for t in before} == before
    assert doctor_errors(path) == []
    Substrate.open(path, role="reader").close()
    conn = sqlite3.connect(path)
    recorded = conn.execute(
        "SELECT step_id, from_fingerprint, to_fingerprint, sql_sha256 FROM schema_migrations ORDER BY seq"
    ).fetchall()
    conn.close()
    assert [r[0] for r in recorded] == STAGE_STEPS[stage]
    assert recorded[0][1] == stage_fingerprint(stage) and recorded[-1][2] == fresh_fingerprint
    assert [r[3] for r in recorded] == [catalog().by_id(i).sql_sha256 for i in STAGE_STEPS[stage]]


def test_a_second_plan_on_a_migrated_store_says_there_is_nothing_to_do(tmp_path):
    path = make_store(tmp_path, "v1")
    apply_with(path, plan_for(path).token)
    with pytest.raises(migrate_plan.NothingToMigrate):
        plan_for(path)


@pytest.mark.parametrize("role", ["writer", "reader"])
def test_open_on_a_known_older_store_refuses_naming_the_command_and_leaves_it_untouched(role, tmp_path):
    path = make_store(tmp_path, "v1")
    before = (sha256(path), listing(tmp_path))
    with pytest.raises(NeedsMigration, match="cairn substrate migrate plan --db"):
        Substrate.open(path, role=role)
    assert (sha256(path), listing(tmp_path)) == before


def test_open_on_an_unknown_schema_is_refused_without_a_migration_hint_and_unmodified(tmp_path):
    path = make_store(tmp_path, "v1")
    conn = sqlite3.connect(path, autocommit=True)
    conn.execute("ALTER TABLE nodes ADD COLUMN stray TEXT")
    conn.close()
    before = (sha256(path), listing(tmp_path))
    with pytest.raises(SchemaMismatch) as caught:
        Substrate.open(path, role="writer")
    assert not isinstance(caught.value, NeedsMigration)
    with pytest.raises(migrate_catalog.MigrationRefused, match="no migration path"):
        plan_for(path)
    assert (sha256(path), listing(tmp_path)) == before


def test_the_doctor_reports_a_store_that_needs_migration(tmp_path):
    path = make_store(tmp_path, "v2")
    ctx = detectors.Context(root=Path(), db=path, bundle=Path(), pin=Path(), attest=Path(), quick=True)
    finding = next(f for f in detectors.d_substrate(ctx) if f.id == "D-substrate/schema")
    assert "needs migration" in finding.evidence and f"cairn substrate migrate plan --db {path}" in finding.evidence


def test_a_tampered_token_is_refused_and_nothing_is_written(tmp_path):
    path = make_store(tmp_path, "v1")
    token = plan_for(path).token
    forged = ("0" if token[0] != "0" else "1") + token[1:]
    before = (sha256(path), listing(tmp_path))
    with pytest.raises(migrate_catalog.MigrationRefused, match="plan token does not match"):
        apply_with(path, forged)
    assert (sha256(path), listing(tmp_path)) == before


def test_a_store_changed_between_plan_and_apply_is_refused(tmp_path):
    path = make_store(tmp_path, "v1")
    token = plan_for(path).token
    conn = sqlite3.connect(path, autocommit=True)
    conn.execute(
        "INSERT INTO gc_runs (run_id, dry_run, roots, reachable, candidates, count, bytes, at)"
        " VALUES ('late', 1, 0, 0, 0, 0, 0, '2026-10-20T00:00:00Z')"
    )
    conn.close()
    before = listing(tmp_path)
    with pytest.raises(migrate_catalog.MigrationRefused, match="plan token does not match"):
        apply_with(path, token)
    assert listing(tmp_path) == before
    assert store_fp(path) == stage_fingerprint("v1")


def test_a_crash_between_steps_rolls_back_and_leaves_a_verified_backup(tmp_path, monkeypatch):
    path = make_store(tmp_path, "v1")
    before = digests_of(path)
    plan = plan_for(path)
    real = migrate_apply.execute_step
    seen = []

    def crash_on_second(conn, step):
        real(conn, step)
        seen.append(step.id)
        if len(seen) == 2:
            raise RuntimeError("injected crash")

    monkeypatch.setattr(migrate_apply, "execute_step", crash_on_second)
    with pytest.raises(RuntimeError, match="injected crash"):
        apply_with(path, plan.token)
    assert seen == ["0001", "0002"]
    assert store_fp(path) == stage_fingerprint("v1")
    assert digests_of(path) == before
    backup = migrate_plan.backup_path(plan.path, plan.run_id(migrate_plan.utc_stamp(EPOCH)))
    record = json.loads(Path(f"{backup}.json").read_text())
    assert migrate_apply.file_sha256(backup) == record["backup_sha256"]
    assert migrate_apply.verify_copy(backup, set(shipped()), plan.from_fp, plan.digests) == []
    monkeypatch.setattr(migrate_apply, "execute_step", real)
    apply_with(path, plan_for(path).token, epoch=EPOCH + 60)
    assert store_fp(path) == plan.to_fp


def test_a_corrupted_migrated_file_fails_the_fresh_connection_gate_and_undo_restores_it(tmp_path, monkeypatch):
    path = make_store(tmp_path, "v1")
    original = digests_of(path)
    plan = plan_for(path)

    def corrupt(resolved):
        with Path(resolved).open("r+b") as handle:
            handle.seek(4096 * 4)
            handle.write(b"\xff" * 4096)

    monkeypatch.setattr(migrate_apply, "after_commit", corrupt)
    with pytest.raises(migrate_apply.PostCommitFailure, match=r"verification failed.*migrate undo") as caught:
        apply_with(path, plan.token)
    run_id = plan.run_id(migrate_plan.utc_stamp(EPOCH))
    assert run_id in str(caught.value)
    monkeypatch.undo()
    migrate_apply.undo(path, run_id, shipped(), epoch=EPOCH + 1)
    assert digests_of(path) == original
    assert store_fp(path) == stage_fingerprint("v1")


def test_a_store_with_uncheckpointed_wal_writes_keeps_them_through_backup_and_migration(tmp_path):
    source = make_store(tmp_path, "v1", "source.sqlite")
    live = sqlite3.connect(source, autocommit=True)
    live.execute("PRAGMA wal_autocheckpoint=0")
    live.execute(
        "INSERT INTO gc_runs (run_id, dry_run, roots, reachable, candidates, count, bytes, at)"
        " VALUES ('wal-only', 1, 0, 0, 0, 0, 0, '2026-10-20T00:00:00Z')"
    )
    copy_dir = tmp_path / "copy"
    copy_dir.mkdir()
    for suffix in ("", "-wal"):
        if Path(f"{source}{suffix}").exists():
            (copy_dir / f"copy.sqlite{suffix}").write_bytes(Path(f"{source}{suffix}").read_bytes())
    live.close()
    path = copy_dir / "copy.sqlite"
    assert (copy_dir / "copy.sqlite-wal").stat().st_size > 0
    result = apply_with(path, plan_for(path).token)
    for target in (path, Path(result["backup_path"])):
        conn = sqlite3.connect(f"file:{target}?mode=ro&immutable=1", uri=True)
        assert conn.execute("SELECT count(*) FROM gc_runs WHERE run_id = 'wal-only'").fetchone()[0] == 1
        conn.close()


def test_apply_refuses_while_another_connection_holds_the_store(tmp_path, monkeypatch):
    path = make_store(tmp_path, "v1")
    token = plan_for(path).token
    holder = sqlite3.connect(path, autocommit=True)
    holder.execute("BEGIN IMMEDIATE")
    monkeypatch.setattr(migrate_apply, "BUSY_S", 0.1)
    before = sha256(path)
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        apply_with(path, token)
    holder.execute("ROLLBACK")
    holder.close()
    assert sha256(path) == before


def test_undo_restores_the_backup_bytes_exactly_and_quarantines_without_deleting(tmp_path):
    path = make_store(tmp_path, "v1")
    plan = plan_for(path)
    result = apply_with(path, plan.token)
    migrated = sha256(path)
    names_before = set(listing(tmp_path))
    undone = migrate_apply.undo(path, result["run_id"], shipped(), epoch=EPOCH + 5)
    assert sha256(path) == undone["restored_sha256"] == sha256(result["backup_path"])
    quarantine = Path(undone["quarantined"])
    assert sha256(quarantine) == migrated
    assert names_before <= set(listing(tmp_path))
    assert quarantine.name in listing(tmp_path)
    assert store_fp(path) == stage_fingerprint("v1")


def test_undo_refuses_a_backup_whose_bytes_changed(tmp_path):
    path = make_store(tmp_path, "v1")
    result = apply_with(path, plan_for(path).token)
    backup = Path(result["backup_path"])
    backup.chmod(0o644)
    with backup.open("r+b") as handle:
        handle.seek(4096 * 6)
        handle.write(b"\x01")
    before = (sha256(path), listing(tmp_path))
    with pytest.raises(migrate_catalog.MigrationRefused, match="does not match the recorded sha256"):
        migrate_apply.undo(path, result["run_id"], shipped(), epoch=EPOCH + 5)
    assert (sha256(path), listing(tmp_path)) == before


def test_a_recorded_step_whose_sql_differs_from_the_shipped_manifest_is_a_drift_refusal(tmp_path):
    path = make_store(tmp_path, "v1")
    apply_with(path, plan_for(path).token)
    shipped_catalog = catalog()
    drifted = migrate_catalog.Catalog(
        (shipped_catalog.migrations[0], dataclasses.replace(shipped_catalog.migrations[1], sql_sha256="0" * 64))
    )
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        problems = migrate_plan._applied_history_problems(conn, drifted)
        unknown = migrate_plan._applied_history_problems(conn, migrate_catalog.Catalog(shipped_catalog.migrations[:1]))
    finally:
        conn.close()
    assert len(problems) == 1 and "step 0002" in problems[0] and "ships" in problems[0]
    assert len(unknown) == 1 and "step 0002" in unknown[0] and "newer store" in unknown[0]


def test_a_byte_level_change_that_leaves_every_row_alone_invalidates_the_plan_token(tmp_path):
    path = make_store(tmp_path, "v1")
    token = plan_for(path).token
    conn = sqlite3.connect(path, autocommit=True)
    conn.execute("CREATE INDEX stray_observer ON nodes (kind)")
    conn.close()
    before = listing(tmp_path)
    with pytest.raises(migrate_catalog.MigrationRefused, match="plan token does not match"):
        apply_with(path, token)
    assert listing(tmp_path) == before
