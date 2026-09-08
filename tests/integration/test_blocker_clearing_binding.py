import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import attest, claims, disagreement, human_queue
from cairn.human_queue import ClosingRuleViolation, Item

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _substrate_helpers import open_writer

AT0 = "2026-09-02T00:00:00+00:00"
AT1 = "2026-09-02T00:01:00+00:00"
AT4 = "2026-09-02T00:04:00+00:00"
BRANCH = "b" * 64
LEFT = "11" * 32
RIGHT = "22" * 32


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def attest_path(tmp_path, clear_flags):
    path = tmp_path / "attestations.log"
    clear_flags(path)
    attest.init(path, "f" * 64)
    return path


def _attested_item(writer, attest_path, seed):
    statement = factories.claim_statement(seed=seed)
    claims.write_claim_statement(writer, statement)
    claims.append_tag_history(
        writer, statement.hash, None, "CONJECTURE", None, claims.to_json({"result": "fixture"}), "test", at=AT0
    )
    rec = disagreement.record(
        writer,
        statement_hash=statement.hash,
        left_hash=LEFT,
        right_hash=RIGHT,
        classification=disagreement.STATEMENT_ERROR,
        at=AT0,
    )
    return statement, rec


def _ruling(writer, attest_path, statement_hash, *, seed, at=AT4):
    unplaced = factories.review_verdict(statement_hash, verdict="approve", seed=seed, at=at)
    offset = attest.append_record(attest_path, claims.review_verdict_canonical(unplaced))
    placed = factories.review_verdict(statement_hash, verdict="approve", seed=seed, at=at, file_offset=offset)
    claims.write_review_verdict(writer, placed)
    return placed


def _gate_item(writer):
    return human_queue.enqueue(
        writer, Item("null_control_pending", "branch", BRANCH, AT0, blocker="null_control_pending")
    )


def test_an_attested_blocker_refuses_a_bare_string_and_the_freeze_stands(writer, attest_path):
    statement, rec = _attested_item(writer, attest_path, 1)
    before = disagreement.freeze_for(writer, statement.hash, attest_path)
    assert before is not None
    with pytest.raises(ClosingRuleViolation, match="carries an attestation record"):
        human_queue.close_by_blocker_clear(
            writer, rec.item_id, attest_path=attest_path, cleared_by="orchestrator:done", at=AT1
        )
    assert disagreement.freeze_for(writer, statement.hash, attest_path) == before
    assert human_queue.depth(writer, attest_path) == 1


def test_an_attested_blocker_clears_on_a_record_the_log_and_the_substrate_both_hold(writer, attest_path):
    statement, rec = _attested_item(writer, attest_path, 2)
    ruling = _ruling(writer, attest_path, statement.hash, seed=2)
    human_queue.close_by_blocker_clear(
        writer,
        rec.item_id,
        attest_path=attest_path,
        cleared_by="human:ruling",
        record_digest=ruling.record_digest,
        file_offset=ruling.file_offset,
        at=AT1,
    )
    closure = human_queue.visible_closure(writer, rec.item_id, attest_path)
    assert (closure["path"], closure["record_digest"], closure["file_offset"]) == (
        "blocker_cleared",
        ruling.record_digest,
        ruling.file_offset,
    )
    assert disagreement.freeze_for(writer, statement.hash, attest_path) is None
    assert human_queue.depth(writer, attest_path) == 0


def test_an_attested_blocker_refuses_a_record_the_substrate_does_not_mirror(writer, attest_path):
    statement, rec = _attested_item(writer, attest_path, 3)
    canonical = attest.waiver_canonical(attest.fixture_waiver("not-a-verdict"))
    offset = attest.append_record(attest_path, canonical)
    with pytest.raises(ClosingRuleViolation, match="no review verdict on statement"):
        human_queue.close_by_blocker_clear(
            writer,
            rec.item_id,
            attest_path=attest_path,
            cleared_by="human:ruling",
            record_digest=attest.blob_hash(canonical),
            file_offset=offset,
            at=AT1,
        )
    assert human_queue.depth(writer, attest_path) == 1


def test_an_attested_blocker_refuses_a_record_the_log_does_not_hold(writer, attest_path):
    statement, rec = _attested_item(writer, attest_path, 4)
    ruling = factories.review_verdict(statement.hash, verdict="approve", seed=4, at=AT4, file_offset=999_999)
    claims.write_review_verdict(writer, ruling)
    with pytest.raises(ClosingRuleViolation, match="holds no record at offset"):
        human_queue.close_by_blocker_clear(
            writer,
            rec.item_id,
            attest_path=attest_path,
            cleared_by="human:ruling",
            record_digest=ruling.record_digest,
            file_offset=ruling.file_offset,
            at=AT1,
        )
    assert human_queue.depth(writer, attest_path) == 1


def test_a_forged_attested_clearing_never_becomes_visible(writer, attest_path):
    statement, rec = _attested_item(writer, attest_path, 5)
    writer.conn.execute(
        "INSERT INTO human_queue_closures (item_id, path, ref, record_digest, file_offset, closed_at)"
        " VALUES (?, 'blocker_cleared', 'human:ruling', ?, 1, ?)",
        (rec.item_id, "ab" * 32, AT1),
    )
    writer.conn.commit()
    assert human_queue.visible_closure(writer, rec.item_id, attest_path) is None
    assert human_queue.depth(writer, attest_path) == 1
    assert disagreement.freeze_for(writer, statement.hash, attest_path) is not None


def test_a_gate_blocker_clears_on_the_gate_outcome_and_carries_no_record(writer, attest_path):
    item_id = _gate_item(writer)
    human_queue.close_by_blocker_clear(writer, item_id, attest_path=attest_path, cleared_by="ladder:remeasured", at=AT1)
    closure = human_queue.visible_closure(writer, item_id, attest_path)
    assert (closure["path"], closure["ref"], closure["record_digest"]) == ("blocker_cleared", "ladder:remeasured", None)
    assert human_queue.depth(writer, attest_path) == 0


def test_a_gate_blocker_refuses_an_attestation_record(writer, attest_path):
    item_id = _gate_item(writer)
    canonical = attest.waiver_canonical(attest.fixture_waiver("gate"))
    offset = attest.append_record(attest_path, canonical)
    with pytest.raises(ClosingRuleViolation, match="clears on a gate outcome"):
        human_queue.close_by_blocker_clear(
            writer,
            item_id,
            attest_path=attest_path,
            cleared_by="ladder:remeasured",
            record_digest=attest.blob_hash(canonical),
            file_offset=offset,
            at=AT1,
        )
    assert human_queue.depth(writer, attest_path) == 1


def test_the_trigger_refuses_both_branches_written_the_wrong_way_round(writer, attest_path):
    _statement, rec = _attested_item(writer, attest_path, 6)
    gate = _gate_item(writer)
    for item_id, digest, offset in ((rec.item_id, None, None), (gate, "ab" * 32, 1)):
        with pytest.raises(sqlite3.IntegrityError, match="blocker clearing rule"):
            writer.conn.execute(
                "INSERT INTO human_queue_closures (item_id, path, ref, record_digest, file_offset, closed_at)"
                " VALUES (?, 'blocker_cleared', 'x', ?, ?, ?)",
                (item_id, digest, offset, AT1),
            )
    assert human_queue.depth(writer, attest_path) == 2


def test_a_ruling_issued_before_the_dispute_existed_does_not_settle_it(writer, attest_path):
    statement = factories.claim_statement(seed=7)
    claims.write_claim_statement(writer, statement)
    claims.append_tag_history(
        writer, statement.hash, None, "CONJECTURE", None, claims.to_json({"result": "fixture"}), "test", at=AT0
    )
    stale = _ruling(writer, attest_path, statement.hash, seed=7, at=AT0)
    rec = disagreement.record(
        writer,
        statement_hash=statement.hash,
        left_hash=LEFT,
        right_hash=RIGHT,
        classification=disagreement.STATEMENT_ERROR,
        at=AT1,
    )
    with pytest.raises(ClosingRuleViolation, match="ruled on nothing that existed yet"):
        human_queue.close_by_blocker_clear(
            writer,
            rec.item_id,
            attest_path=attest_path,
            cleared_by="human:ruling",
            record_digest=stale.record_digest,
            file_offset=stale.file_offset,
            at=AT1,
        )
    assert disagreement.freeze_for(writer, statement.hash, attest_path) is not None
    assert human_queue.depth(writer, attest_path) == 1


def test_one_ruling_settles_one_dispute_and_not_the_next(writer, attest_path):
    statement = factories.claim_statement(seed=8)
    claims.write_claim_statement(writer, statement)
    claims.append_tag_history(
        writer, statement.hash, None, "CONJECTURE", None, claims.to_json({"result": "fixture"}), "test", at=AT0
    )
    first = disagreement.record(
        writer,
        statement_hash=statement.hash,
        left_hash=LEFT,
        right_hash=RIGHT,
        classification=disagreement.STATEMENT_ERROR,
        at=AT0,
    )
    second = disagreement.record(
        writer,
        statement_hash=statement.hash,
        left_hash="33" * 32,
        right_hash="44" * 32,
        classification=disagreement.PROOF_GAP,
        at="2026-09-02T00:00:30+00:00",
    )
    assert first.item_id != second.item_id
    unplaced = factories.review_verdict(statement.hash, verdict="approve", seed=8, at=AT1)
    offset = attest.append_record(attest_path, claims.review_verdict_canonical(unplaced))
    ruling = factories.review_verdict(statement.hash, verdict="approve", seed=8, at=AT1, file_offset=offset)
    claims.write_review_verdict(writer, ruling)
    bound = {"record_digest": ruling.record_digest, "file_offset": ruling.file_offset}
    human_queue.close_by_blocker_clear(
        writer, first.item_id, attest_path=attest_path, cleared_by="human:first", at=AT1, **bound
    )
    with pytest.raises(ClosingRuleViolation, match="one ruling clears one item"):
        human_queue.close_by_blocker_clear(
            writer, second.item_id, attest_path=attest_path, cleared_by="human:second", at=AT1, **bound
        )
    assert human_queue.depth(writer, attest_path) == 1
