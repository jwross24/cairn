import sys
from pathlib import Path

import pytest

from cairn import attest, claims, human_queue
from cairn.human_queue import ClosingRuleViolation, Item

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _substrate_helpers import open_writer

T0 = "2026-09-02T00:00:00+00:00"
INSERT = (
    "INSERT INTO review_verdicts (statement_hash, reviewer, verdict, checklist_template_hash, gate_bundle_hash, "
    "at, supersedes, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


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


def _statement(writer):
    statement = factories.claim_statement(seed=1)
    claims.write_claim_statement(writer, statement)
    return statement


def _honest(writer, attest_path, statement_hash, verdict="reject", seed=3):
    unplaced = factories.review_verdict(statement_hash, verdict=verdict, seed=seed)
    offset = attest.append_record(attest_path, claims.review_verdict_canonical(unplaced))
    placed = factories.review_verdict(statement_hash, verdict=verdict, seed=seed, file_offset=offset)
    claims.write_review_verdict(writer, placed)
    return placed


def _insert(writer, verdict, *, verdict_text, record_digest):
    writer.conn.execute(
        INSERT,
        (
            verdict.statement_hash,
            verdict.reviewer,
            verdict_text,
            verdict.checklist_template_hash,
            verdict.gate_bundle_hash,
            verdict.at,
            verdict.supersedes,
            record_digest,
            verdict.file_offset,
        ),
    )
    writer.conn.commit()


def test_an_honest_row_is_visible_and_mirrored(writer, attest_path):
    statement = _statement(writer)
    placed = _honest(writer, attest_path, statement.hash)
    rows = claims.review_verdicts_for(writer, statement.hash)
    assert [r["record_digest"] for r in claims.visible_review_verdicts(writer, statement.hash, attest_path)] == [
        placed.record_digest
    ]
    assert claims._verdict_of(rows[0]).record_digest == placed.record_digest
    assert claims.verdict_mirrored(writer, statement.hash, placed.record_digest, placed.file_offset)


def test_a_row_whose_fields_differ_from_the_record_its_stored_digest_names_is_invisible(writer, attest_path):
    statement = _statement(writer)
    placed = _honest(writer, attest_path, statement.hash)
    _insert(writer, placed, verdict_text="approve", record_digest=placed.record_digest)
    rows = claims.review_verdicts_for(writer, statement.hash)
    assert [r["verdict"] for r in rows] == ["reject", "approve"]
    assert attest.attestation_record_matches(attest_path, rows[1]["file_offset"], rows[1]["record_digest"])
    assert claims._verdict_of(rows[1]).record_digest != rows[1]["record_digest"]
    assert [r["row_id"] for r in claims.visible_review_verdicts(writer, statement.hash, attest_path)] == [
        rows[0]["row_id"]
    ]
    assert not any(
        r["verdict"] == "approve" for r in claims.visible_review_verdicts(writer, statement.hash, attest_path)
    )


def test_a_row_whose_stored_digest_disagrees_with_its_fields_is_invisible_even_when_the_file_holds_them(
    writer, attest_path
):
    statement = _statement(writer)
    unplaced = factories.review_verdict(statement.hash, verdict="approve", seed=5)
    offset = attest.append_record(attest_path, claims.review_verdict_canonical(unplaced))
    corrupt = factories.review_verdict(statement.hash, verdict="approve", seed=5, file_offset=offset)
    _insert(writer, corrupt, verdict_text="approve", record_digest="0" * 64)
    rows = claims.review_verdicts_for(writer, statement.hash)
    assert attest.attestation_record_matches(attest_path, offset, claims._verdict_of(rows[0]).record_digest)
    assert claims.visible_review_verdicts(writer, statement.hash, attest_path) == []
    assert not claims.verdict_mirrored(writer, statement.hash, "0" * 64, offset)


def test_the_closure_binding_refuses_a_closure_against_a_forged_row(writer, attest_path):
    statement = _statement(writer)
    unplaced = factories.review_verdict(statement.hash, verdict="reject", seed=3)
    offset = attest.append_record(attest_path, claims.review_verdict_canonical(unplaced))
    honest = factories.review_verdict(statement.hash, verdict="reject", seed=3, file_offset=offset)
    _insert(writer, honest, verdict_text="approve", record_digest=honest.record_digest)
    item = human_queue.enqueue(
        writer,
        Item(
            human_queue.STATEMENT_REVIEW,
            human_queue.STATEMENT,
            statement.hash,
            T0,
            blocker=human_queue.STATEMENT_REVIEW,
        ),
    )
    assert attest.attestation_record_matches(attest_path, offset, honest.record_digest)
    assert [r["verdict"] for r in claims.review_verdicts_for(writer, statement.hash)] == ["approve"]
    with pytest.raises(ClosingRuleViolation, match="no review verdict on statement"):
        human_queue.close_by_attestation(
            writer, item, attest_path=attest_path, file_offset=offset, record_digest=honest.record_digest
        )
    assert human_queue.visible_closure(writer, item, attest_path) is None
