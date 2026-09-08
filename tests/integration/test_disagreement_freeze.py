import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import attest, claims, disagreement, foundations, human_queue
from cairn.disagreement import (
    HARNESS_BUG,
    OUT_OF_SCOPE,
    OWNER_HUMAN,
    PROOF_GAP,
    STATEMENT_ERROR,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _substrate_helpers import open_writer

WAIVER_TARGET = "f" * 64
AT0 = "2026-09-02T00:00:00+00:00"
AT1 = "2026-09-02T00:01:00+00:00"
AT2 = "2026-09-02T00:02:00+00:00"
AT3 = "2026-09-02T00:03:00+00:00"
AT4 = "2026-09-02T00:04:00+00:00"
LEFT = "11" * 32
RIGHT = "22" * 32
LEFT2 = "33" * 32
RIGHT2 = "44" * 32


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def attest_path(tmp_path, clear_flags):
    path = tmp_path / "attestations.log"
    clear_flags(path)
    attest.init(path, WAIVER_TARGET)
    return path


def _statement(writer, seed):
    statement = factories.claim_statement(seed=seed)
    claims.write_claim_statement(writer, statement)
    return statement


def _ruling(writer, attest_path, statement_hash, *, seed, at=AT4):
    unplaced = factories.review_verdict(statement_hash, verdict="approve", seed=seed, at=at)
    offset = attest.append_record(attest_path, claims.review_verdict_canonical(unplaced))
    placed = factories.review_verdict(statement_hash, verdict="approve", seed=seed, at=at, file_offset=offset)
    claims.write_review_verdict(writer, placed)
    return {"record_digest": placed.record_digest, "file_offset": placed.file_offset}


def _set_tag(writer, statement_hash, tag, *, at=AT0):
    claims.append_tag_history(
        writer, statement_hash, None, tag, None, claims.to_json({"result": "test-fixture"}), "test", at=at
    )


def test_a_disagreement_freezes_a_standing_statement_at_its_current_tag(writer, attest_path):
    statement = _statement(writer, 1)
    _set_tag(writer, statement.hash, "STRONG-EMPIRICAL")
    rec = disagreement.record(
        writer, statement_hash=statement.hash, left_hash=LEFT, right_hash=RIGHT, classification=STATEMENT_ERROR, at=AT1
    )
    row = dict(writer.conn.execute("SELECT * FROM disagreements WHERE disagreement_id = ?", (rec.hash,)).fetchone())
    assert row == {
        "disagreement_id": rec.hash,
        "statement_hash": statement.hash,
        "left_hash": LEFT,
        "right_hash": RIGHT,
        "classification": STATEMENT_ERROR,
        "owner": OWNER_HUMAN,
        "frozen_tag": "STRONG-EMPIRICAL",
        "item_id": rec.item_id,
        "raised_at": AT1,
    }
    item = human_queue.get_item(writer, rec.item_id)
    assert item["class"] == "disagreement"
    assert item["blocker"] == "disagreement"
    assert item["target"] == statement.hash


def test_freeze_for_returns_the_frozen_tag_while_the_item_is_open(writer, attest_path):
    statement = _statement(writer, 2)
    _set_tag(writer, statement.hash, "STRONG-EMPIRICAL")
    rec = disagreement.record(
        writer, statement_hash=statement.hash, left_hash=LEFT, right_hash=RIGHT, classification=STATEMENT_ERROR, at=AT1
    )
    assert disagreement.freeze_for(writer, statement.hash, attest_path) == ("STRONG-EMPIRICAL", LEFT, rec.hash)


def test_the_freeze_caps_an_upgrade_and_lifts_on_lawful_closure(writer, attest_path):
    statement = _statement(writer, 3)
    _set_tag(writer, statement.hash, "STRONG-EMPIRICAL")
    rec = disagreement.record(
        writer, statement_hash=statement.hash, left_hash=LEFT, right_hash=RIGHT, classification=STATEMENT_ERROR, at=AT1
    )
    freeze = disagreement.freeze_for(writer, statement.hash, attest_path)
    assert freeze is not None
    assert foundations.rank("PROVEN") > foundations.rank(freeze[0])
    tag = "PROVEN"
    if foundations.rank(tag) > foundations.rank(freeze[0]):
        tag = freeze[0]
    assert tag == freeze[0]
    ruling = _ruling(writer, attest_path, statement.hash, seed=101)
    human_queue.close_by_blocker_clear(
        writer, rec.item_id, attest_path=attest_path, cleared_by="human:ruling", at=AT2, **ruling
    )
    assert disagreement.freeze_for(writer, statement.hash, attest_path) is None


def test_a_closure_on_a_different_statements_disagreement_does_not_release_this_one(writer, attest_path):
    s1 = _statement(writer, 4)
    s2 = _statement(writer, 5)
    _set_tag(writer, s1.hash, "CONJECTURE")
    _set_tag(writer, s2.hash, "CONJECTURE")
    rec1 = disagreement.record(
        writer, statement_hash=s1.hash, left_hash=LEFT, right_hash=RIGHT, classification=STATEMENT_ERROR, at=AT1
    )
    rec2 = disagreement.record(
        writer, statement_hash=s2.hash, left_hash=LEFT2, right_hash=RIGHT2, classification=STATEMENT_ERROR, at=AT1
    )
    ruling = _ruling(writer, attest_path, s1.hash, seed=102)
    human_queue.close_by_blocker_clear(
        writer, rec1.item_id, attest_path=attest_path, cleared_by="human:x", at=AT1, **ruling
    )
    assert disagreement.freeze_for(writer, s2.hash, attest_path) == ("CONJECTURE", LEFT2, rec2.hash)
    assert disagreement.freeze_for(writer, s1.hash, attest_path) is None


def test_only_the_blocker_clearing_can_close_a_disagreement_item_so_the_freeze_stands_otherwise(writer, attest_path):
    statement = _statement(writer, 6)
    _set_tag(writer, statement.hash, "CONJECTURE")
    rec = disagreement.record(
        writer, statement_hash=statement.hash, left_hash=LEFT, right_hash=RIGHT, classification=HARNESS_BUG, at=AT1
    )
    ack = human_queue.acknowledgment_from(
        {"item_id": rec.item_id, "issued_by": "operator", "at": AT1, "note": "unfiled"}
    )
    with pytest.raises(human_queue.ClosingRuleViolation, match="holds blocker"):
        human_queue.write_acknowledgment(writer, ack, attest_path=attest_path, file_offset=4096)
    with pytest.raises(human_queue.ClosingRuleViolation, match="holds blocker"):
        human_queue.close_by_terminal_status(writer, rec.item_id, attest_path=attest_path, status="x", ref="test")
    assert disagreement.freeze_for(writer, statement.hash, attest_path) == ("CONJECTURE", LEFT, rec.hash)


def test_several_standing_disagreements_the_weakest_tag_wins(writer, attest_path):
    statement = _statement(writer, 7)
    _set_tag(writer, statement.hash, "PROVEN", at=AT0)
    rec_a = disagreement.record(
        writer, statement_hash=statement.hash, left_hash=LEFT, right_hash=RIGHT, classification=STATEMENT_ERROR, at=AT1
    )
    assert rec_a.frozen_tag == "PROVEN"
    claims.append_tag_history(
        writer, statement.hash, "PROVEN", "CONJECTURE", "ev", claims.to_json({"result": "downgrade"}), "test", at=AT2
    )
    rec_b = disagreement.record(
        writer, statement_hash=statement.hash, left_hash=LEFT2, right_hash=RIGHT2, classification=PROOF_GAP, at=AT3
    )
    assert rec_b.frozen_tag == "CONJECTURE"
    assert disagreement.freeze_for(writer, statement.hash, attest_path) == ("CONJECTURE", LEFT2, rec_b.hash)


def test_released_names_the_closure_that_lifted_the_freeze(writer, attest_path):
    statement = _statement(writer, 8)
    _set_tag(writer, statement.hash, "CONJECTURE")
    rec = disagreement.record(
        writer, statement_hash=statement.hash, left_hash=LEFT, right_hash=RIGHT, classification=OUT_OF_SCOPE, at=AT1
    )
    assert disagreement.released(writer, rec.hash, attest_path) is None
    with pytest.raises(human_queue.ClosingRuleViolation, match="carries an attestation record"):
        human_queue.close_by_blocker_clear(
            writer, rec.item_id, attest_path=attest_path, cleared_by="orchestrator:done", at=AT2
        )
    assert disagreement.released(writer, rec.hash, attest_path) is None
    ruling = _ruling(writer, attest_path, statement.hash, seed=103)
    human_queue.close_by_blocker_clear(
        writer, rec.item_id, attest_path=attest_path, cleared_by="orchestrator:done", at=AT2, **ruling
    )
    closure = disagreement.released(writer, rec.hash, attest_path)
    assert closure is not None
    assert closure["path"] == "blocker_cleared"
    assert closure["ref"] == "orchestrator:done"


def test_tag_history_reflects_the_freeze_and_the_release_while_the_disagreement_row_stays_unchanged(
    writer, attest_path
):
    statement = _statement(writer, 9)
    _set_tag(writer, statement.hash, "CONJECTURE", at=AT0)
    rec = disagreement.record(
        writer, statement_hash=statement.hash, left_hash=LEFT, right_hash=RIGHT, classification=PROOF_GAP, at=AT1
    )
    freeze = disagreement.freeze_for(writer, statement.hash, attest_path)
    assert freeze == ("CONJECTURE", LEFT, rec.hash)
    claims.append_tag_history(
        writer,
        statement.hash,
        "CONJECTURE",
        "CONJECTURE",
        freeze[1],
        claims.to_json({"result": "PremiseCeiling", "cls": "CONJECTURE"}),
        "gate:justify",
        at=AT2,
    )
    with pytest.raises(human_queue.ClosingRuleViolation, match="carries an attestation record"):
        human_queue.close_by_blocker_clear(
            writer, rec.item_id, attest_path=attest_path, cleared_by="prover:fixed", at=AT3
        )
    assert disagreement.freeze_for(writer, statement.hash, attest_path) == freeze
    ruling = _ruling(writer, attest_path, statement.hash, seed=104)
    human_queue.close_by_blocker_clear(
        writer, rec.item_id, attest_path=attest_path, cleared_by="prover:fixed", at=AT3, **ruling
    )
    assert disagreement.freeze_for(writer, statement.hash, attest_path) is None
    claims.append_tag_history(
        writer,
        statement.hash,
        "CONJECTURE",
        "PROVEN",
        "ev-final",
        claims.to_json({"result": "released"}),
        "gate:justify",
        at=AT4,
    )
    history = claims.tag_history_for(writer, statement.hash)
    assert [row["to_tag"] for row in history] == ["CONJECTURE", "CONJECTURE", "PROVEN"]
    row = dict(writer.conn.execute("SELECT * FROM disagreements WHERE disagreement_id = ?", (rec.hash,)).fetchone())
    assert row["frozen_tag"] == "CONJECTURE"
    assert row["item_id"] == rec.item_id
    assert row["disagreement_id"] == rec.hash


def test_the_disagreements_table_refuses_update_and_delete(writer, attest_path):
    statement = _statement(writer, 10)
    _set_tag(writer, statement.hash, "CONJECTURE")
    rec = disagreement.record(
        writer, statement_hash=statement.hash, left_hash=LEFT, right_hash=RIGHT, classification="inconclusive", at=AT1
    )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute("UPDATE disagreements SET frozen_tag = 'PROVEN' WHERE disagreement_id = ?", (rec.hash,))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute("DELETE FROM disagreements WHERE disagreement_id = ?", (rec.hash,))


@pytest.mark.parametrize(
    ("left", "right"),
    [(LEFT, LEFT), ("", RIGHT), (LEFT, "   ")],
)
def test_a_refused_record_enqueues_no_item_and_writes_no_row(writer, left, right):
    statement = _statement(writer, 7)
    with pytest.raises(disagreement.DisagreementError):
        disagreement.record(
            writer,
            statement_hash=statement.hash,
            left_hash=left,
            right_hash=right,
            classification=PROOF_GAP,
            at=AT1,
        )
    assert writer.conn.execute("SELECT COUNT(*) FROM disagreements").fetchone()[0] == 0
    assert (
        writer.conn.execute("SELECT COUNT(*) FROM human_queue_items WHERE target = ?", (statement.hash,)).fetchone()[0]
        == 0
    )
