import sys
from dataclasses import replace
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


def _honest(writer, attest_path, statement_hash, verdict="reject", seed=3, **kw):
    unplaced = factories.review_verdict(statement_hash, verdict=verdict, seed=seed, **kw)
    offset = attest.append_record(attest_path, claims.review_verdict_canonical(unplaced))
    placed = replace(unplaced, file_offset=offset)
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


def test_a_valid_record_elsewhere_does_not_authorize_a_mirror_at_another_frame(writer, attest_path):
    statement = _statement(writer)
    first = _honest(writer, attest_path, statement.hash, seed=3)
    second = factories.review_verdict(statement.hash, seed=4)
    own_offset = attest.append_record(attest_path, claims.review_verdict_canonical(second))
    misplaced = factories.review_verdict(statement.hash, seed=4, file_offset=first.file_offset)
    claims.write_review_verdict(writer, misplaced)
    assert attest.attestation_record_matches(attest_path, own_offset, misplaced.record_digest)
    assert not attest.attestation_record_matches(attest_path, misplaced.file_offset, misplaced.record_digest)
    assert [row["record_digest"] for row in claims.visible_review_verdicts(writer, statement.hash, attest_path)] == [
        first.record_digest
    ]


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


@pytest.mark.parametrize("decision", ["reject", "needs_revision", "approve"])
def test_an_authentic_successor_replaces_only_the_effective_verdict(writer, attest_path, decision):
    statement = _statement(writer)
    approval = _honest(writer, attest_path, statement.hash, verdict="approve")
    successor = _honest(writer, attest_path, statement.hash, verdict=decision, supersedes=approval.hash)
    history = claims.visible_review_verdicts(writer, statement.hash, attest_path)
    assert [claims._verdict_of(row).hash for row in history] == [approval.hash, successor.hash]
    effective = claims.effective_review_verdicts(writer, statement.hash, attest_path)
    assert [claims._verdict_of(row).hash for row in effective] == [successor.hash]


def test_an_explicit_chain_does_not_restore_an_earlier_approval(writer, attest_path):
    statement = _statement(writer)
    approval = _honest(writer, attest_path, statement.hash, verdict="approve")
    rejection = _honest(writer, attest_path, statement.hash, supersedes=approval.hash)
    replacement = _honest(writer, attest_path, statement.hash, verdict="approve", supersedes=rejection.hash)
    assert len(claims.visible_review_verdicts(writer, statement.hash, attest_path)) == 3
    effective = claims.effective_review_verdicts(writer, statement.hash, attest_path)
    assert [claims._verdict_of(row).hash for row in effective] == [replacement.hash]


@pytest.mark.parametrize("binding", ["statement", "bundle", "digest"])
def test_a_successor_with_an_unrelated_binding_cannot_revoke_an_approval(writer, attest_path, binding):
    statement = _statement(writer)
    approval = _honest(writer, attest_path, statement.hash, verdict="approve")
    other = factories.claim_statement(seed=2)
    claims.write_claim_statement(writer, other)
    _honest(
        writer,
        attest_path,
        other.hash if binding == "statement" else statement.hash,
        supersedes=approval.record_digest if binding == "digest" else approval.hash,
        gate_bundle_hash="0" * 64 if binding == "bundle" else approval.gate_bundle_hash,
    )
    effective = claims.effective_review_verdicts(writer, statement.hash, attest_path)
    assert approval.hash in [claims._verdict_of(row).hash for row in effective]


@pytest.mark.parametrize("forgery", ["fields", "digest", "offset"])
def test_an_unauthenticated_successor_cannot_revoke_an_approval(writer, attest_path, forgery):
    statement = _statement(writer)
    approval = _honest(writer, attest_path, statement.hash, verdict="approve")
    unplaced = factories.review_verdict(statement.hash, verdict="reject", seed=3, supersedes=approval.hash)
    offset = attest.append_record(attest_path, claims.review_verdict_canonical(unplaced))
    forged = replace(unplaced, file_offset=offset + 1 if forgery == "offset" else offset)
    _insert(
        writer,
        forged,
        verdict_text="needs_revision" if forgery == "fields" else "reject",
        record_digest="0" * 64 if forgery == "digest" else forged.record_digest,
    )
    assert len(claims.review_verdicts_for(writer, statement.hash)) == 2
    effective = claims.effective_review_verdicts(writer, statement.hash, attest_path)
    assert [claims._verdict_of(row).hash for row in effective] == [approval.hash]


@pytest.mark.parametrize("at", ["2026-01-01T00:00:00Z", "2027-01-01T00:00:00Z"])
def test_supersession_uses_the_explicit_edge_rather_than_timestamps(writer, attest_path, at):
    statement = _statement(writer)
    approval = _honest(writer, attest_path, statement.hash, verdict="approve")
    unrelated = _honest(writer, attest_path, statement.hash, at=at)
    effective = claims.effective_review_verdicts(writer, statement.hash, attest_path)
    assert [claims._verdict_of(row).hash for row in effective] == [approval.hash, unrelated.hash]
    successor = _honest(writer, attest_path, statement.hash, at=at, supersedes=approval.hash)
    effective = claims.effective_review_verdicts(writer, statement.hash, attest_path)
    assert [claims._verdict_of(row).hash for row in effective] == [unrelated.hash, successor.hash]
