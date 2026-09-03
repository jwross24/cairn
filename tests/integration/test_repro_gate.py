import sys
from pathlib import Path

import pytest

from cairn import attest, claims, justify, repro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories

ATTEST = "unused-attestation-file"
PAYLOAD_A = {"out.json": b'{"x": 1}'}
PAYLOAD_B = {"out.json": b'{"x": 2}'}


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def statement(writer):
    stmt = factories.claim_statement(seed=11)
    claims.write_claim_statement(writer, stmt)
    return stmt


def population(stmt):
    return {**stmt.scope, "size_interval": [20, 60], "param_ranges": {"bits": [20, 60]}}


def recipe_key(writer, seed=1):
    return writer.put_recipe(helpers.recipe(seed=seed))


def ladder_evidence(writer, stmt, attempt_id, *, replay_grade="Replayable", repro_record=None, seed=0):
    node = factories.evidence_node(
        "ladder_table",
        stmt.hash,
        population(stmt),
        frozenset(stmt.scope["assumption_set"]),
        verdict="KEEP",
        repro=repro_record,
        attempt_id=attempt_id,
        in_sample_sizes=(20, 60),
        seed=seed,
    )
    claims.write_evidence_node(writer, node, replay_grade=replay_grade)
    return node


def ticket_at(writer, stmt, tier):
    ticket = factories.ticket(hypothesis_key="ab" * 32, tier=tier, statement_hash=stmt.hash, seed=tier)
    claims.write_ticket(writer, ticket)
    return ticket


def test_a_planted_divergence_marks_the_recipe_non_reproducible_with_both_attempts_rooted(writer, statement):
    key = recipe_key(writer)
    first, manifest_a = helpers.launch(writer, key, payloads=PAYLOAD_A)
    node = ladder_evidence(writer, statement, first)
    before = justify.derive_tag(writer, statement.hash, ATTEST)
    assert (before.tag, before.results[0][1].reason) == (justify.CONJECTURE, "ladder-keep-no-repro")
    second, manifest_b = helpers.launch(writer, key, payloads=PAYLOAD_B, skip_cache_lookup=True)
    assert manifest_a != manifest_b
    record, marked = repro.record_rerun(writer, first, second, attest_path=ATTEST)
    assert record.passed is False and record.kind == "second_attempt_agree"
    assert set(marked) == {first, second}
    assert writer.is_root("divergence", manifest_a) and writer.is_root("divergence", manifest_b)
    assert all(writer.get_attempt(a)["inadmissible"] for a in (first, second))
    assert claims.get_repro_record(writer, record.hash)["passed"] == 0
    after = justify.derive_tag(writer, statement.hash, ATTEST)
    result = after.results[0][1]
    assert isinstance(result, justify.Absent) and result.reason == justify.REASON_INADMISSIBLE
    history = claims.tag_history_for(writer, statement.hash)
    assert [(h["from_tag"], h["to_tag"], h["evidence_hash"]) for h in history] == [
        (None, justify.CONJECTURE, node.hash),
        (justify.CONJECTURE, justify.SPECULATION, node.hash),
    ]


def test_a_tier_two_replayable_derivation_waits_on_the_re_run_capped_at_conjecture(writer, statement):
    ticket_at(writer, statement, 2)
    key = recipe_key(writer)
    first, manifest = helpers.launch(writer, key, payloads=PAYLOAD_A)
    node = ladder_evidence(writer, statement, first)
    waiting = justify.derive_tag(writer, statement.hash, ATTEST)
    assert waiting.tag == justify.CONJECTURE
    assert waiting.results[0][1].reason == justify.REASON_REPRO_DEFERRED
    assert waiting.deferred == (node.hash,)
    second, again = helpers.launch(writer, key, payloads=PAYLOAD_A, skip_cache_lookup=True)
    assert again == manifest
    record, marked = repro.record_rerun(writer, first, second, attest_path=ATTEST)
    assert record.passed is True and marked == ()
    assert writer.get_attempt(second)["skip_cache_lookup"] == 1
    landed = justify.derive_tag(writer, statement.hash, ATTEST)
    assert (landed.tag, landed.justified_by, landed.deferred) == (justify.STRONG_EMPIRICAL, node.hash, ())
    assert landed.results[0][1].reason == "ladder-keep-repro"
    assert [h["to_tag"] for h in claims.tag_history_for(writer, statement.hash)] == [
        justify.CONJECTURE,
        justify.STRONG_EMPIRICAL,
    ]


@pytest.mark.parametrize("tier", [0, 1])
def test_a_tier_zero_or_one_replayable_without_a_record_is_capped_but_never_deferred(writer, statement, tier):
    if tier:
        ticket_at(writer, statement, tier)
    key = recipe_key(writer)
    first, _ = helpers.launch(writer, key, payloads=PAYLOAD_A)
    ladder_evidence(writer, statement, first)
    derived = justify.derive_tag(writer, statement.hash, ATTEST)
    assert derived.tag == justify.CONJECTURE
    assert derived.results[0][1].reason == "ladder-keep-no-repro"
    assert derived.deferred == ()


def test_a_verifiable_witness_is_checked_and_never_deferred(writer, statement):
    ticket_at(writer, statement, 3)
    key = recipe_key(writer)
    first, _ = helpers.launch(writer, key, payloads=PAYLOAD_A, replay_grade="Verifiable")
    unchecked = ladder_evidence(writer, statement, first, replay_grade="Verifiable")
    derived = justify.derive_tag(writer, statement.hash, ATTEST)
    assert repro.policy("Verifiable", 3) == repro.CHECK_WITNESS
    assert (derived.tag, derived.deferred, derived.results[0][1].reason) == (
        justify.CONJECTURE,
        (),
        "ladder-keep-no-repro",
    )
    check = factories.repro_record(first, passed=True, kind="witness_check")
    claims.write_repro_record(writer, check)
    checked = justify.derive_tag(writer, statement.hash, ATTEST)
    assert checked.tag == justify.STRONG_EMPIRICAL and checked.justified_by == unchecked.hash


def test_a_re_run_served_from_cache_is_refused_and_records_nothing(writer, statement):
    key = recipe_key(writer)
    first, _ = helpers.launch(writer, key, payloads=PAYLOAD_A)
    ladder_evidence(writer, statement, first)
    served = writer.serve(key)
    assert served is not None and served.attempt_id == first
    with pytest.raises(repro.ReproError, match="cannot be its own re-run"):
        repro.record_rerun(writer, first, served.attempt_id, attest_path=ATTEST)
    cached, _ = helpers.launch(writer, key, payloads=PAYLOAD_A, skip_cache_lookup=False)
    with pytest.raises(repro.ReproError, match="launched with the cache open"):
        repro.record_rerun(writer, first, cached, attest_path=ATTEST)
    assert claims.repro_records_for_attempt(writer, first) == []
    other = writer.put_recipe(helpers.recipe(seed=2))
    elsewhere, _ = helpers.launch(writer, other, payloads=PAYLOAD_A, skip_cache_lookup=True)
    with pytest.raises(repro.ReproError, match="is on recipe"):
        repro.record_rerun(writer, first, elsewhere, attest_path=ATTEST)


def test_a_baseline_without_a_manifest_is_refused_before_any_record_is_written(writer, statement):
    key = recipe_key(writer)
    failed, _ = helpers.launch(writer, key, status="FAIL")
    fresh, _ = helpers.launch(writer, key, payloads=PAYLOAD_A, skip_cache_lookup=True)
    with pytest.raises(repro.ReproError, match=r"the attempt .* is FAIL with no manifest"):
        repro.record_rerun(writer, failed, fresh, attest_path=ATTEST)
    assert claims.repro_records_for_attempt(writer, failed) == []
    assert not writer.get_attempt(fresh)["inadmissible"]
    writer.disown(fresh)
    other, _ = helpers.launch(writer, key, payloads=PAYLOAD_A, skip_cache_lookup=True)
    with pytest.raises(repro.ReproError, match=r"the re-run .* is disowned"):
        repro.record_rerun(writer, other, fresh, attest_path=ATTEST)


def test_the_divergence_walk_reads_review_verdicts_through_the_attestation_file(writer, statement, tmp_path):
    path = tmp_path / "attest.bin"
    attest.init(str(path), "f" * 64)
    claims.write_review_verdict(writer, factories.review_verdict(statement.hash, seed=3))
    key = recipe_key(writer)
    first, _ = helpers.launch(writer, key, payloads=PAYLOAD_A)
    node = ladder_evidence(writer, statement, first)
    assert justify.derive_tag(writer, statement.hash, str(path)).tag == justify.CONJECTURE
    second, _ = helpers.launch(writer, key, payloads=PAYLOAD_B, skip_cache_lookup=True)
    record, marked = repro.record_rerun(writer, first, second, attest_path=str(path))
    assert record.passed is False and set(marked) == {first, second}
    history = claims.tag_history_for(writer, statement.hash)
    assert (history[-1]["from_tag"], history[-1]["to_tag"], history[-1]["evidence_hash"]) == (
        justify.CONJECTURE,
        justify.SPECULATION,
        node.hash,
    )
    again, marked_again = repro.record_rerun(writer, first, second, attest_path=str(path))
    assert again.passed is False and marked_again == ()
    assert claims.tag_history_for(writer, statement.hash)[-1]["to_tag"] == justify.SPECULATION


def test_an_audit_only_witness_justifies_nothing(writer, statement):
    key = recipe_key(writer)
    first, _ = helpers.launch(writer, key, payloads=PAYLOAD_A, replay_grade="AuditOnly")
    record = factories.repro_record(first, passed=True)
    claims.write_repro_record(writer, record)
    ladder_evidence(writer, statement, first, replay_grade="AuditOnly", repro_record=record)
    derived = justify.derive_tag(writer, statement.hash, ATTEST)
    result = derived.results[0][1]
    assert derived.tag == justify.SPECULATION
    assert isinstance(result, justify.Absent) and result.reason == justify.REASON_AUDIT_ONLY
