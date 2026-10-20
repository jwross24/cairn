import hashlib
import json
from pathlib import Path

import pytest
from _migrate_helpers import make_store, sha256, shipped, stage_fingerprint, store_fp

from cairn import cli, exits, migrate_apply, migrate_catalog, migrate_plan
from cairn.migrate_fingerprint import fingerprint


def run_cli(capsys, *argv):
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_plan_apply_and_undo_round_trip_through_the_cli(tmp_path, capsys):
    path = make_store(tmp_path, "v1")
    code, out, _ = run_cli(capsys, "substrate", "migrate", "plan", "--db", str(path), "--json")
    plan = json.loads(out)
    assert code == exits.OK and plan["status"] == "planned" and plan["from_fingerprint"] == stage_fingerprint("v1")
    assert [s["id"] for s in plan["steps"]] == ["0001", "0002"]
    assert store_fp(path) == stage_fingerprint("v1")

    code, out, _ = run_cli(
        capsys, "substrate", "migrate", "apply", "--db", str(path), "--plan-token", plan["plan_token"], "--json"
    )
    applied = json.loads(out)
    assert code == exits.OK and Path(applied["backup_path"]).is_file()
    assert store_fp(path) == plan["to_fingerprint"]

    code, out, _ = run_cli(
        capsys, "substrate", "migrate", "undo", "--db", str(path), "--run", applied["run_id"], "--json"
    )
    undone = json.loads(out)
    assert code == exits.OK and Path(undone["quarantined"]).is_file()
    assert sha256(path) == sha256(applied["backup_path"])


def test_a_wrong_token_exits_gate_refused_and_names_the_plan_command(tmp_path, capsys):
    path = make_store(tmp_path, "v1")
    before = sha256(path)
    code, _, err = run_cli(capsys, "substrate", "migrate", "apply", "--db", str(path), "--plan-token", "00" * 32)
    assert code == exits.GATE_REFUSED and "cairn substrate migrate plan" in err
    assert sha256(path) == before


def test_a_command_that_opens_an_older_store_exits_needs_migration_and_names_the_verb(tmp_path, capsys):
    path = make_store(tmp_path, "v2")
    before = sha256(path)
    code, _, err = run_cli(capsys, "--db", str(path), "gc")
    assert code == exits.NEEDS_MIGRATION == 6
    assert "cairn substrate migrate plan --db" in err
    assert sha256(path) == before


def test_a_current_store_plans_to_nothing_and_exits_ok(tmp_path, capsys):
    path = make_store(tmp_path, "v1")
    token = json.loads(run_cli(capsys, "substrate", "migrate", "plan", "--db", str(path), "--json")[1])["plan_token"]
    run_cli(capsys, "substrate", "migrate", "apply", "--db", str(path), "--plan-token", token)
    code, out, _ = run_cli(capsys, "substrate", "migrate", "plan", "--db", str(path), "--json")
    assert code == exits.OK and json.loads(out)["status"] == "current"


def scratch_catalog(directory, sql):
    (directory / "0001_bad.sql").write_text(sql)
    entry = {
        "id": "0001",
        "file": "0001_bad.sql",
        "from": stage_fingerprint("v1"),
        "to": fingerprint(shipped()),
        "sql_sha256": hashlib.sha256(sql.encode()).hexdigest(),
    }
    (directory / "manifest.json").write_text(json.dumps({"migrations": [entry]}))
    return migrate_catalog.load_catalog(directory)


def test_a_migration_containing_update_is_refused_before_anything_is_written(tmp_path):
    store_dir = tmp_path / "store"
    store_dir.mkdir()
    path = make_store(store_dir, "v1")
    bad = scratch_catalog(tmp_path, "UPDATE nodes SET kind = 'x';\n")
    before = (sha256(path), sorted(p.name for p in store_dir.iterdir() if not p.name.endswith(("-wal", "-shm"))))
    with pytest.raises(migrate_catalog.MigrationRefused, match="not additive"):
        migrate_plan.plan_readonly(path, shipped(), bad)
    with pytest.raises(migrate_catalog.MigrationRefused, match="not additive"):
        migrate_apply.apply(path, "00" * 32, shipped(), bad)
    after = (sha256(path), sorted(p.name for p in store_dir.iterdir() if not p.name.endswith(("-wal", "-shm"))))
    assert after == before
