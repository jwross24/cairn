import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import claims, foundations, justify

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories

ATTEST = "unused-attestation-file"
PAYLOAD = {"out.json": b'{"x": 1}'}


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


def statement(writer, seed):
    stmt = factories.claim_statement(seed=seed)
    claims.write_claim_statement(writer, stmt)
    return stmt


def strong_evidence(writer, stmt, seed):
    key = writer.put_recipe(helpers.recipe(seed=seed))
    attempt, _ = helpers.launch(writer, key, payloads=PAYLOAD)
    record = factories.repro_record(attempt, passed=True)
    claims.write_repro_record(writer, record)
    node = factories.evidence_node(
        "ladder_table",
        stmt.hash,
        {**stmt.scope, "size_interval": [20, 60], "param_ranges": {"bits": [20, 60]}},
        frozenset(stmt.scope["assumption_set"]),
        verdict="KEEP",
        repro=record,
        attempt_id=attempt,
        in_sample_sizes=(20, 60),
        seed=seed,
    )
    claims.write_evidence_node(writer, node)
    return node, attempt


def test_the_query_finds_fixture_h_on_a_real_substrate_and_names_the_path(writer):
    root, a, b, c = (statement(writer, s) for s in (1, 2, 3, 4))
    for stmt, tag in ((root, justify.PROVEN), (a, justify.PROVEN), (b, justify.PROVEN), (c, justify.CONJECTURE)):
        claims.append_tag_history(writer, stmt.hash, None, tag, None, '{"planted": true}', "test")
    foundations.add_premise(writer, root.hash, a.hash)
    foundations.add_premise(writer, a.hash, b.hash)
    foundations.add_premise(writer, b.hash, c.hash)
    found = foundations.violations(writer, root.hash)
    assert len(found) == 1
    assert found[0].path == (root.hash, a.hash, b.hash, c.hash)
    assert (found[0].dependent_tag, found[0].premise_tag, found[0].depth) == (justify.PROVEN, justify.CONJECTURE, 3)
    assert foundations.closure(writer, root.hash) == [
        (root.hash, a.hash),
        (root.hash, a.hash, b.hash),
        (root.hash, a.hash, b.hash, c.hash),
    ]
    assert foundations.violations(writer, c.hash) == []


def test_a_premise_edge_refuses_self_reference_cycles_and_unknown_statements(writer):
    a, b = statement(writer, 5), statement(writer, 6)
    foundations.add_premise(writer, a.hash, b.hash)
    with pytest.raises(foundations.FoundationsError, match="cannot rest on itself"):
        foundations.add_premise(writer, a.hash, a.hash)
    with pytest.raises(foundations.FoundationsError, match="would close a cycle"):
        foundations.add_premise(writer, b.hash, a.hash)
    with pytest.raises(claims.UnknownStatement):
        foundations.add_premise(writer, a.hash, "0" * 64)
    assert foundations.premises_of(writer, a.hash) == [b.hash]
    assert foundations.dependents_of(writer, b.hash) == [a.hash]


def test_a_downgrade_re_derives_every_dependent_with_the_premise_s_evidence_pointer(writer):
    premise, mid, top = statement(writer, 7), statement(writer, 8), statement(writer, 9)
    premise_node, premise_attempt = strong_evidence(writer, premise, 7)
    strong_evidence(writer, mid, 8)
    strong_evidence(writer, top, 9)
    for stmt in (premise, mid, top):
        assert justify.derive_tag(writer, stmt.hash, ATTEST).tag == justify.STRONG_EMPIRICAL
    foundations.add_premise(writer, mid.hash, premise.hash)
    foundations.add_premise(writer, top.hash, mid.hash)
    assert foundations.violations(writer, top.hash) == []

    writer.disown(premise_attempt)
    dropped = justify.derive_tag(writer, premise.hash, ATTEST)
    assert (dropped.tag, dropped.justified_by) == (justify.SPECULATION, premise_node.hash)
    assert [(v.dependent, v.premise) for v in foundations.violations(writer, top.hash)] == [(mid.hash, premise.hash)]

    walked = foundations.rederive(writer, premise.hash, ATTEST)
    assert [d.statement_hash for d in walked] == [mid.hash, top.hash]
    assert [d.tag for d in walked] == [justify.SPECULATION, justify.SPECULATION]
    assert walked[0].premise_cap[:2] == (justify.SPECULATION, premise_node.hash)
    assert foundations.violations(writer, top.hash) == []
    for stmt in (mid, top):
        last = claims.tag_history_for(writer, stmt.hash)[-1]
        assert (last["from_tag"], last["to_tag"], last["evidence_hash"]) == (
            justify.STRONG_EMPIRICAL,
            justify.SPECULATION,
            premise_node.hash,
        )
        assert '"PremiseCeiling"' in last["justification"]


def test_a_re_derivation_that_would_move_a_tag_without_an_evidence_pointer_is_refused(writer):
    premise, dependent = statement(writer, 10), statement(writer, 11)
    claims.append_tag_history(writer, premise.hash, None, justify.CONJECTURE, None, '{"planted": true}', "test")
    strong_evidence(writer, dependent, 11)
    assert justify.derive_tag(writer, dependent.hash, ATTEST).tag == justify.STRONG_EMPIRICAL
    foundations.add_premise(writer, dependent.hash, premise.hash)
    assert foundations.ceiling_for(writer, dependent.hash) == (justify.CONJECTURE, None, premise.hash)
    with pytest.raises(sqlite3.IntegrityError, match="downgrade requires evidence"):
        justify.derive_tag(writer, dependent.hash, ATTEST)
    assert claims.tag_history_for(writer, dependent.hash)[-1]["to_tag"] == justify.STRONG_EMPIRICAL


def test_the_divergence_path_re_derives_the_claims_resting_on_the_marked_attempts(writer):
    premise, dependent = statement(writer, 12), statement(writer, 13)
    key = writer.put_recipe(helpers.recipe(seed=12))
    first, _ = helpers.launch(writer, key, payloads=PAYLOAD)
    node = factories.evidence_node(
        "ladder_table",
        premise.hash,
        {**premise.scope, "size_interval": [20, 60], "param_ranges": {"bits": [20, 60]}},
        frozenset(premise.scope["assumption_set"]),
        verdict="KEEP",
        attempt_id=first,
        in_sample_sizes=(20, 60),
        seed=12,
    )
    claims.write_evidence_node(writer, node)
    strong_evidence(writer, dependent, 13)
    assert justify.derive_tag(writer, premise.hash, ATTEST).tag == justify.CONJECTURE
    assert justify.derive_tag(writer, dependent.hash, ATTEST).tag == justify.STRONG_EMPIRICAL
    foundations.add_premise(writer, dependent.hash, premise.hash)
    second, _ = helpers.launch(writer, key, payloads={"out.json": b'{"x": 2}'}, skip_cache_lookup=True)
    from cairn import repro

    record, marked = repro.record_rerun(writer, first, second, attest_path=ATTEST)
    assert record.passed is False and set(marked) == {first, second}
    assert foundations.current_tag(writer, premise.hash) == justify.SPECULATION
    assert foundations.current_tag(writer, dependent.hash) == justify.SPECULATION
    assert claims.tag_history_for(writer, dependent.hash)[-1]["evidence_hash"] == node.hash
