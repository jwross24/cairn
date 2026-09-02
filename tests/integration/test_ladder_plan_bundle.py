import json
import shutil
import sqlite3
from pathlib import Path

import blake3
import pytest

from cairn import bundle, cli, exits, ladderplan, substrate

ROOT = Path(__file__).resolve().parents[2]
SEEDED = "rungs.trials,design_radius,clock.rate_ratio"


def _pinned(tmp_path, name, src):
    directory = tmp_path / name
    directory.mkdir()
    bundle_path, pin_path = directory / "gate-bundle.sqlite", directory / "gate-bundle.pin"
    bundle.build(src, bundle_path)
    pin_path.write_text(bundle.bundle_hash(bundle.read_rows(bundle_path)) + "\n")
    return bundle_path, pin_path


def _source_copy(tmp_path, name, edit):
    directory = tmp_path / f"src-{name}"
    shutil.copytree(ROOT / "bundle", directory)
    edit(directory)
    return directory


def _plan_edit(mutate):
    def edit(directory):
        path = directory / "ladder_plan.json"
        obj = json.loads(path.read_text())
        mutate(obj)
        path.write_text(json.dumps(obj))

    return edit


def _drop_clock_tolerance(obj):
    del obj["tolerances"]["clock"]


def _widen_clock_tolerance(obj):
    obj["tolerances"]["clock"] = "0.30"


def _remove_plan(directory):
    (directory / "ladder_plan.json").unlink()


def _write_every_seed(obj):
    for key, marker in obj["provenance"].items():
        if marker.startswith("seeded:"):
            obj["provenance"][key] = "measured:test-fixture"


def _raise_tiers_ceiling(directory):
    path = directory / "tiers.json"
    obj = json.loads(path.read_text())
    obj["ceiling_multiplier"] = 8
    path.write_text(json.dumps(obj))


def _gate_runs(db_path, gate):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM gate_runs WHERE gate = ? ORDER BY at", (gate,))]
    finally:
        conn.close()


def _load(tmp_path, name, src):
    bundle_path, pin_path = _pinned(tmp_path, name, src)
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    db = tmp_path / f"{name}.sqlite"
    with substrate.Substrate.open(db) as sub:
        load = ladderplan.load_for_gate(sub, gate)
    return gate, load, _gate_runs(db, "ladder_plan")


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture
def plan_argv(tmp_path):
    def make(name="deploy", src=ROOT / "bundle"):
        bundle_path, pin_path = _pinned(tmp_path, name, src)
        return [
            "ladder",
            "plan",
            "--db",
            str(tmp_path / f"{name}.sqlite"),
            "--bundle",
            str(bundle_path),
            "--pin",
            str(pin_path),
        ]

    return make


def test_the_committed_plan_loads_from_a_pinned_bundle_and_the_load_row_carries_the_plan_hash(tmp_path):
    gate, load, rows = _load(tmp_path, "deploy", ROOT / "bundle")
    assert load.ok and load.reason is None
    assert load.plan_hash == gate.digest_of("ladder_plan") == blake3.blake3(gate.raw("ladder_plan")).hexdigest()
    assert (load.plan.hash, load.plan.bundle_hash) == (load.plan_hash, gate.hash)
    assert len(rows) == 1
    row = rows[0]
    assert (row["run_id"], row["plan_step"], row["result"]) == (load.run_id, "load", "pass")
    assert (row["bundle_hash"], row["pin_hash"]) == (gate.hash, gate.pin_hash)
    assert json.loads(row["reasons"]) == [f"ladder_plan:{load.plan_hash}"]


def test_a_plan_missing_a_tolerance_refuses_naming_the_field_and_records_the_refusal_under_its_own_hash(tmp_path):
    src = _source_copy(tmp_path, "no-clock", _plan_edit(_drop_clock_tolerance))
    gate, load, rows = _load(tmp_path, "no-clock", src)
    assert not load.ok and load.plan is None
    assert load.reason == "plan-missing-field:tolerances.clock"
    committed = blake3.blake3(
        bundle.canonical_bytes("ladder_plan", json.loads((ROOT / "bundle" / "ladder_plan.json").read_text()))
    ).hexdigest()
    assert load.plan_hash == gate.digest_of("ladder_plan") != committed
    assert [(r["result"], json.loads(r["reasons"])) for r in rows] == [
        ("refused", ["plan-missing-field:tolerances.clock", f"ladder_plan:{load.plan_hash}"])
    ]
    assert rows[0]["run_id"] == load.run_id


def test_a_clock_tolerance_the_band_cannot_cover_refuses_naming_the_bound(tmp_path):
    src = _source_copy(tmp_path, "wide-clock", _plan_edit(_widen_clock_tolerance))
    _, load, rows = _load(tmp_path, "wide-clock", src)
    assert load.reason == "clock-bound-violated:0.3*1=0.3>=0.2432"
    assert rows[0]["result"] == "refused" and json.loads(rows[0]["reasons"])[0] == load.reason


def test_a_bundle_without_the_plan_object_refuses_and_records_no_plan_hash(tmp_path):
    src = _source_copy(tmp_path, "absent", _remove_plan)
    _, load, rows = _load(tmp_path, "absent", src)
    assert (load.reason, load.plan_hash) == ("plan-object-absent", None)
    assert json.loads(rows[0]["reasons"]) == ["plan-object-absent"]


def test_the_patience_ceiling_is_checked_against_the_tiers_object_in_the_same_bundle(tmp_path):
    src = _source_copy(tmp_path, "tiers-8", _raise_tiers_ceiling)
    _, load, rows = _load(tmp_path, "tiers-8", src)
    assert load.reason == "patience-ceiling-ne-tiers:4!=8"
    assert rows[0]["result"] == "refused"


def test_the_cli_emits_one_json_document_naming_the_plan_hash_and_the_run_it_wrote(plan_argv, capsys, tmp_path):
    argv = plan_argv()
    code, out, err = _run([*argv, "--json"], capsys)
    assert code == exits.OK, err
    assert out.count("\n") == 1
    document = json.loads(out)
    assert document["schema_version"] == cli.SCHEMA_VERSION and document["command"] == "ladder"
    assert document["ok"] is True and document["sub"] == "plan"
    rows = _gate_runs(tmp_path / "deploy.sqlite", "ladder_plan")
    assert [r["run_id"] for r in rows] == [document["run_id"]]
    assert json.loads(rows[0]["reasons"]) == [f"ladder_plan:{document['plan_hash']}"]
    assert (
        document["plan"]["hash"] == document["plan_hash"] and document["plan"]["bundle_hash"] == document["bundle_hash"]
    )
    assert document["plan"]["seeded"] == SEEDED.split(",")
    assert document["plan"]["clock_bound"]["holds"] is True


def test_the_human_rendering_names_every_rung_the_bound_and_the_seeded_fields(plan_argv, capsys):
    code, out, err = _run(plan_argv(), capsys)
    assert code == exits.OK, err
    lines = out.strip().splitlines()
    assert lines[0].startswith("plan_hash ") and len(lines[0]) == len("plan_hash ") + 64
    assert lines[2].startswith("run_id ")
    assert lines[3:7] == [
        "rung 30 fit trials=130 floor_ops=41226 floor_bytes=497314 cap=none",
        "rung 40 fit trials=130 floor_ops=1171749 floor_bytes=15440525 cap=none",
        "rung 50 fit trials=130 floor_ops=44769554 floor_bytes=477370808 cap=477370808",
        "rung 60 hold_out trials=10 floor_ops=1840605416 floor_bytes=19625853059 cap=19625853059",
    ]
    assert lines[7:] == ["clock_bound 0.1*1=0.1<0.2432", f"seeded {SEEDED}"]


def test_the_cli_refuses_an_invalid_plan_with_exit_gate_refused_and_the_refusal_recorded(plan_argv, capsys, tmp_path):
    src = _source_copy(tmp_path, "no-clock", _plan_edit(_drop_clock_tolerance))
    argv = plan_argv(name="no-clock", src=src)
    code, out, err = _run([*argv, "--json"], capsys)
    assert code == exits.GATE_REFUSED
    assert out == ""
    assert "plan-missing-field:tolerances.clock" in err and "the refusal is gate run" in err
    rows = _gate_runs(tmp_path / "no-clock.sqlite", "ladder_plan")
    assert [r["result"] for r in rows] == ["refused"]
    assert rows[0]["run_id"] in err


def test_a_bundle_that_does_not_match_its_pin_fails_closed_before_the_plan_is_read(plan_argv, capsys, tmp_path):
    argv = plan_argv()
    stale = tmp_path / "stale.pin"
    stale.write_text("0" * 64 + "\n")
    argv[argv.index("--pin") + 1] = str(stale)
    code, out, err = _run(argv, capsys)
    assert code == exits.GATE_REFUSED
    assert out == "" and "differs from the pin" in err and "cairn bundle pin" in err
    db = tmp_path / "deploy.sqlite"
    assert _gate_runs(db, "ladder_plan") == []
    assert [json.loads(r["reasons"]) for r in _gate_runs(db, "bundle_open")] == [["bundle-hash-ne-pin"]]


def test_a_plan_with_no_seeded_field_renders_seeded_none(plan_argv, capsys, tmp_path):
    src = _source_copy(tmp_path, "written", _plan_edit(_write_every_seed))
    code, out, err = _run(plan_argv(name="written", src=src), capsys)
    assert code == exits.OK, err
    assert out.strip().splitlines()[-1] == "seeded none"


def test_a_second_writer_on_the_substrate_exits_conflict_before_the_plan_is_read(plan_argv, capsys, tmp_path):
    argv = plan_argv()
    with substrate.Substrate.open(tmp_path / "deploy.sqlite"):
        code, out, err = _run(argv, capsys)
    assert code == exits.CONFLICT
    assert out == "" and "another writer already holds" in err and "cairn ladder plan --db" in err
    assert _gate_runs(tmp_path / "deploy.sqlite", "ladder_plan") == []


@pytest.mark.parametrize("flag", ["--bundle", "--pin"])
def test_a_missing_bundle_or_pin_exits_environment_and_creates_no_substrate(plan_argv, capsys, tmp_path, flag):
    argv = plan_argv()
    argv[argv.index(flag) + 1] = str(tmp_path / "absent")
    code, out, err = _run(argv, capsys)
    assert code == exits.ENVIRONMENT
    assert "does not exist" in err and "cairn bundle build" in err
    assert not (tmp_path / "deploy.sqlite").exists()
