import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import escrow, repro, runner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers

ATTEST = "unused-attestation-file"
AT = "2026-09-05T00:00:00.000000+00:00"
LATER = "2026-09-05T00:00:01.000000+00:00"
PAYLOAD = {"out.json": b'{"x": 1}'}


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


def reserve(sub, attempt_id, reserved=0.5):
    sub.add_escrow(
        attempt_id,
        declared_production_cost=1.0,
        declared_verification_cost=reserved,
        reserved=reserved,
        ceiling_multiplier=4.0,
    )
    return escrow.reservation(sub, attempt_id)


def ok_attempt(sub, seed=1, *, skip_cache_lookup=False):
    key = sub.put_recipe(helpers.recipe(seed=seed))
    attempt_id, _ = helpers.launch(sub, key, payloads=PAYLOAD, skip_cache_lookup=skip_cache_lookup)
    return key, attempt_id


def test_the_first_witness_check_spends_the_reservation_and_a_later_one_spends_nothing(writer, db_snapshot):
    _, attempt_id = ok_attempt(writer)
    assert escrow.unsettled(reserve(writer, attempt_id))
    first = repro.record_witness_check(writer, attempt_id, True, at=AT)
    row = escrow.reservation(writer, attempt_id)
    assert row["spent_at"] == AT and row["spent_by"] == f"witness_check:{first.hash}"
    assert row["released_at"] is None and row["released_by"] is None
    second = repro.record_witness_check(writer, attempt_id, True, at=LATER)
    db_snapshot(writer.conn, "two-checks")
    assert second.hash != first.hash
    assert escrow.reservation(writer, attempt_id) == row
    with pytest.raises(escrow.AlreadySettled, match="spent at"):
        escrow.spend(writer, attempt_id, check_event="again")


def test_a_witness_check_on_an_unknown_attempt_writes_nothing(writer):
    with pytest.raises(escrow.UnknownAttempt):
        repro.record_witness_check(writer, "no-such-attempt", True)
    assert writer.conn.execute("SELECT COUNT(*) FROM repro_records").fetchone()[0] == 0


def test_a_rerun_spends_the_first_attempts_reservation_and_the_rerun_holds_none(writer):
    key, first = ok_attempt(writer)
    reserve(writer, first)
    second, _ = helpers.launch(writer, key, payloads=PAYLOAD, skip_cache_lookup=True)
    record, marked = repro.record_rerun(writer, first, second, attest_path=ATTEST)
    assert record.passed and marked == ()
    row = escrow.reservation(writer, first)
    assert row["spent_by"] == f"second_attempt_agree:{record.hash}" and row["spent_at"] == record.at
    assert escrow.reservation(writer, second) is None
    assert escrow.first_check(writer, second, check_event="x") is None


def test_an_ok_owned_attempt_cannot_release(writer):
    _, attempt_id = ok_attempt(writer)
    reserve(writer, attempt_id)
    with pytest.raises(escrow.ReleaseRefused, match="releases only on status"):
        escrow.release(writer, attempt_id)
    assert escrow.settle_on_close(writer, attempt_id, "OK") is None
    assert escrow.standing(writer, attempt_id)


@pytest.mark.parametrize("status", ["FAIL", "DISAGREE", "BUDGET_EXCEEDED", "BLOCKED", "SKILL_YANKED", "INTERRUPTED"])
def test_a_close_with_status_other_than_ok_releases_the_unspent_reservation(writer, status):
    key = writer.put_recipe(helpers.recipe())
    attempt_id = writer.start_attempt(key)
    reserve(writer, attempt_id)
    writer.close_attempt(attempt_id, status)
    row = escrow.settle_on_close(writer, attempt_id, status, at=AT)
    assert row["released_at"] == AT and row["released_by"] == f"status:{status}"
    assert row["spent_at"] is None and row["spent_by"] is None
    assert escrow.settle_on_close(writer, attempt_id, status) is None
    with pytest.raises(escrow.AlreadySettled, match="released at"):
        escrow.spend(writer, attempt_id, check_event="late-check")


def test_a_deferred_reservation_survives_its_branchs_terminal_status_and_spends_on_the_late_check(writer):
    key, deferred = ok_attempt(writer)
    before = reserve(writer, deferred)
    sibling = writer.start_attempt(key)
    reserve(writer, sibling)
    writer.close_attempt(sibling, "BUDGET_EXCEEDED")
    assert escrow.settle_on_close(writer, sibling, "BUDGET_EXCEEDED", at=AT)["released_by"] == "status:BUDGET_EXCEEDED"
    assert escrow.reservation(writer, deferred) == before
    rerun, _ = helpers.launch(writer, key, payloads=PAYLOAD, skip_cache_lookup=True)
    record, _ = repro.record_rerun(writer, deferred, rerun, attest_path=ATTEST)
    after = escrow.reservation(writer, deferred)
    assert after["spent_by"] == f"second_attempt_agree:{record.hash}" and after["released_at"] is None


def test_a_spent_reservation_stays_spent_when_the_attempt_is_disowned(writer):
    _, attempt_id = ok_attempt(writer)
    reserve(writer, attempt_id)
    repro.record_witness_check(writer, attempt_id, True, at=AT)
    writer.disown(attempt_id, at=LATER)
    assert escrow.settle_on_disown(writer, attempt_id) is None
    row = escrow.reservation(writer, attempt_id)
    assert row["spent_at"] == AT and row["released_at"] is None


def test_a_disown_releases_an_unspent_reservation(writer):
    _, attempt_id = ok_attempt(writer)
    reserve(writer, attempt_id)
    writer.disown(attempt_id, at=AT)
    row = escrow.settle_on_disown(writer, attempt_id, at=LATER)
    assert row["released_at"] == LATER and row["released_by"] == escrow.RELEASE_DISOWNED


def test_the_startup_scan_releases_the_reservation_of_every_interrupted_attempt(writer):
    key = writer.put_recipe(helpers.recipe())
    attempt_id = writer.start_attempt(key)
    reserve(writer, attempt_id)
    assert runner.startup_scan(writer, at=AT) == [attempt_id]
    row = escrow.reservation(writer, attempt_id)
    assert row["released_by"] == "status:INTERRUPTED" and row["released_at"] == AT


def test_the_runner_launch_path_releases_on_a_failed_launch(writer, tmp_path, monkeypatch):
    key = writer.put_recipe(helpers.recipe())
    attempt_id = writer.start_attempt(key)
    reserve(writer, attempt_id)
    writer.close_attempt(attempt_id, "FAIL")
    assert escrow.settle_on_close(writer, attempt_id, "FAIL")["released_by"] == "status:FAIL"


def test_a_release_without_an_attempt_is_refused(writer):
    writer.conn.execute("PRAGMA foreign_keys = OFF")
    with pytest.raises(escrow.NoReservation):
        escrow.release(writer, "ghost")
    with pytest.raises(escrow.NoReservation):
        escrow.spend(writer, "ghost", check_event="x")


def test_a_spend_names_its_check_event(writer):
    _, attempt_id = ok_attempt(writer)
    reserve(writer, attempt_id)
    with pytest.raises(escrow.EscrowError, match="names the check event"):
        escrow.spend(writer, attempt_id, check_event="")
    assert escrow.standing(writer, attempt_id)


@pytest.mark.parametrize(
    ("label", "sql"),
    [
        ("spend-twice", "UPDATE escrow SET spent_at = 'again', spent_by = 'x' WHERE attempt_id = ?"),
        ("release-after-spend", "UPDATE escrow SET released_at = 't', released_by = 'x' WHERE attempt_id = ?"),
        ("unspend", "UPDATE escrow SET spent_at = NULL, spent_by = NULL WHERE attempt_id = ?"),
        ("reprice", "UPDATE escrow SET reserved = 9.0 WHERE attempt_id = ?"),
        ("delete", "DELETE FROM escrow WHERE attempt_id = ?"),
    ],
)
def test_the_schema_refuses_every_write_other_than_the_one_settlement(writer, label, sql):
    _, attempt_id = ok_attempt(writer)
    reserve(writer, attempt_id)
    repro.record_witness_check(writer, attempt_id, True, at=AT)
    before = escrow.reservation(writer, attempt_id)
    with pytest.raises(sqlite3.IntegrityError, match=r"settles once|append-only"):
        writer.conn.execute(sql, (attempt_id,))
    assert escrow.reservation(writer, attempt_id) == before


@pytest.mark.parametrize(
    ("label", "sql"),
    [
        ("both-at-once", "UPDATE escrow SET spent_at = 't', spent_by = 'a', released_at = 't', released_by = 'b'"),
        ("stamp-without-actor", "UPDATE escrow SET spent_at = 't'"),
        ("actor-without-stamp", "UPDATE escrow SET released_by = 'b'"),
        ("reprice-unsettled", "UPDATE escrow SET reserved = 9.0"),
    ],
)
def test_an_unsettled_row_admits_only_a_whole_spend_or_a_whole_release(writer, label, sql):
    _, attempt_id = ok_attempt(writer)
    reserve(writer, attempt_id)
    with pytest.raises(sqlite3.IntegrityError, match=r"settles once|CHECK"):
        writer.conn.execute(sql)
    assert escrow.standing(writer, attempt_id)


def test_a_row_inserted_both_spent_and_released_is_refused(writer):
    _, attempt_id = ok_attempt(writer)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        writer.add_escrow(
            attempt_id,
            declared_production_cost=1.0,
            declared_verification_cost=0.5,
            reserved=0.5,
            ceiling_multiplier=4.0,
            spent_at="t",
            spent_by="a",
            released_at="t",
            released_by="b",
        )
    assert escrow.reservation(writer, attempt_id) is None
