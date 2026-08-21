import sys
from pathlib import Path

import pytest

from cairn import substrate

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _substrate_helpers import launch, open_writer, recipe  # noqa: E402

M1_STATUSES = ("SKILL_YANKED", "BUDGET_EXCEEDED", "INTERRUPTED")


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


def test_every_m1_column_of_escrow_yank_records_and_salts_round_trips_byte_equal(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    attempt = writer.start_attempt(key)
    escrow = {
        "attempt_id": attempt,
        "declared_production_cost": 0.25,
        "declared_verification_cost": 0.125,
        "reserved": 0.125,
        "spent_at": "2026-08-21T10:00:00.000001+00:00",
        "released_at": "2026-08-21T10:00:01.000001+00:00",
        "ceiling_multiplier": 4.0,
    }
    yank = {
        "yank_id": "yank-7",
        "skill_identity_hash": "aa" * 32,
        "reach_predicate": '{"bits":[0,50],"gp":"2.17.4"}',
        "ruling_ref": "ruling-3",
        "record_digest": "dd" * 32,
        "file_offset": 128,
        "created_at": "2026-08-21T10:00:02.000001+00:00",
    }
    salt = {"class_key": "toy_curve/1:gp=2.17.4", "salt": "salt-2", "record_digest": "ee" * 32, "file_offset": 256}
    writer.add_escrow(**escrow)
    writer.add_yank_record(**yank)
    writer.add_salt(**salt)
    db_snapshot(writer.conn, "m1-columns")
    for table, pk, expected in (("escrow", "attempt_id", escrow), ("yank_records", "yank_id", yank), ("salts", "class_key", salt)):
        row = dict(writer.conn.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (expected[pk],)).fetchone())
        assert row == expected
        assert {k: type(v) for k, v in row.items()} == {k: type(v) for k, v in expected.items()}
    assert writer.yanked("aa" * 32) is True


@pytest.mark.parametrize("status", M1_STATUSES)
def test_m1_statuses_are_admitted_and_never_served(writer, db_snapshot, status):
    key = writer.put_recipe(recipe(1))
    attempt, manifest = launch(writer, key, status, {"out": b"payload"})
    db_snapshot(writer.conn, status)
    row = writer.get_attempt(attempt)
    assert row["status"] == status and row["output_manifest_hash"] == manifest and row["ended_at"] is not None
    assert writer.serve(key) is None


def test_disowned_at_mark_excludes_its_attempt_from_serve(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    first, manifest_1 = launch(writer, key, "OK", {"out": b"one"})
    assert writer.serve(key) == substrate.Served(first, manifest_1)
    writer.disown(first, at="2026-08-21T10:00:03.000001+00:00")
    assert writer.serve(key) is None
    second, manifest_2 = launch(writer, key, "OK", {"out": b"two"})
    db_snapshot(writer.conn, "disowned-then-fresh")
    assert writer.get_attempt(first)["disowned_at"] == "2026-08-21T10:00:03.000001+00:00"
    assert writer.serve(key) == substrate.Served(second, manifest_2)
