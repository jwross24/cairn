import json
import sys
from pathlib import Path

import pytest

from cairn import claims, gc, keys, ledger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _substrate_helpers import IDENTITY_A, open_writer

AT = "2026-09-02T00:00:00Z"
FIFTY_BITS = ({"numeric": {"bits": 50, "trials": 40}, "categorical": {"model": "c_sqrt_n"}},)
REJECT_RESULT = {
    "summary": "in-sample model miss: 1.31e9 ops at 50 bits against a sub-rho model",
    "value": "1310000000",
    "ci": ["1200000000", "1400000000"],
}
KILLED_RESULT = {"summary": "verified counterexample at 44 bits", "value": "1", "ci": ["1", "1"]}


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def branch(writer):
    statement = factories.claim_statement(cost_model=True, seed=5)
    claims.write_claim_statement(writer, statement)
    hypothesis = factories.hypothesis_object(claim_statement_hash=statement.hash, seed=5)
    claims.write_hypothesis_object(writer, hypothesis)
    return statement, hypothesis


def _node(writer, statement, kind, verdict, seed):
    node = factories.evidence_node(
        kind,
        statement.hash,
        statement.scope,
        statement.scope["assumption_set"],
        verdict=verdict,
        seed=seed,
        producer=(keys.identity_bundle_hash(IDENTITY_A), "skill"),
    )
    claims.write_evidence_node(writer, node)
    return node.hash


def test_a_reject_shaped_measured_entry_lands_with_its_kind(writer, branch, db_snapshot):
    statement, hypothesis = branch
    table = _node(writer, statement, "ladder_table", "REJECT", seed=1)
    before = db_snapshot(writer.conn, "before-reject")
    digest = ledger.write(
        writer,
        hypothesis_key=hypothesis.hash,
        decision=ledger.REFUTED,
        refutation_kind=ledger.MEASURED,
        evidence_node=table,
        method=hypothesis.method_identity,
        measured_points=FIFTY_BITS,
        result=REJECT_RESULT,
        caught_by="ladder:in_sample_model_miss",
        at=AT,
    )
    after = db_snapshot(writer.conn, "after-reject")
    row = ledger.get_entry(writer, digest)
    assert (row["decision"], row["refutation_kind"], row["caught_by"]) == (
        "REFUTED",
        "measured",
        "ladder:in_sample_model_miss",
    )
    assert json.loads(row["retry_predicate"]) == {"kind": "gate_owned_remeasurement", "target": hypothesis.hash}
    assert json.loads(row["measured_points"]) == [dict(p) for p in FIFTY_BITS]
    assert json.loads(row["result"])["ci"] == REJECT_RESULT["ci"]
    assert json.loads(row["method"]) == hypothesis.method_identity
    assert after["ledger_entries"] == before["ledger_entries"] + 1
    assert after["nodes"] == before["nodes"] + 1 and after["roots"] == before["roots"] + 1
    print(row)


def test_a_reject_shaped_implementation_entry_names_the_revision_it_disowns(writer, branch, db_snapshot):
    statement, hypothesis = branch
    table = _node(writer, statement, "ladder_table", "REJECT", seed=2)
    revision = keys.identity_bundle_hash(IDENTITY_A)
    digest = ledger.write(
        writer,
        hypothesis_key=hypothesis.hash,
        decision=ledger.REFUTED,
        refutation_kind=ledger.IMPLEMENTATION,
        evidence_node=table,
        method=hypothesis.method_identity,
        faulting_revision=revision,
        caught_by="ladder:xP_ne_Q",
        at=AT,
    )
    db_snapshot(writer.conn, "implementation")
    row = ledger.get_entry(writer, digest)
    assert (row["refutation_kind"], row["faulting_revision"]) == ("implementation", revision)
    assert json.loads(row["retry_predicate"]) == {"kind": "new_certified_revision", "target": revision}
    assert row["result"] is None and json.loads(row["measured_points"]) == []
    print(row)


def test_a_killed_shaped_entry_lands_as_measured_on_the_hunt_record(writer, branch, db_snapshot):
    statement, hypothesis = branch
    record = _node(writer, statement, "counterexample_hunt_record", "KILLED", seed=3)
    digest = ledger.write(
        writer,
        hypothesis_key=hypothesis.hash,
        decision=ledger.REFUTED,
        refutation_kind=ledger.MEASURED,
        evidence_node=record,
        method=hypothesis.method_identity,
        measured_points=({"numeric": {"bits": 44}, "categorical": {"family": "toy_curve"}},),
        result=KILLED_RESULT,
        caught_by="hunt:KILLED",
        at=AT,
    )
    db_snapshot(writer.conn, "killed")
    row = ledger.get_entry(writer, digest)
    assert (row["decision"], row["refutation_kind"], row["caught_by"], row["evidence_node"]) == (
        "REFUTED",
        "measured",
        "hunt:KILLED",
        record,
    )
    assert json.loads(row["retry_predicate"]) == {"kind": "gate_owned_remeasurement", "target": hypothesis.hash}
    print(row)


def test_both_shapes_go_through_the_one_api_and_neither_accepts_a_predicate(writer, branch):
    statement, hypothesis = branch
    table = _node(writer, statement, "ladder_table", "REJECT", seed=4)
    record = _node(writer, statement, "counterexample_hunt_record", "KILLED", seed=5)
    common = {
        "hypothesis_key": hypothesis.hash,
        "decision": ledger.REFUTED,
        "refutation_kind": ledger.MEASURED,
        "method": hypothesis.method_identity,
        "measured_points": FIFTY_BITS,
        "result": REJECT_RESULT,
        "at": AT,
    }
    for evidence_node, caught_by in ((table, "ladder:floor"), (record, "hunt:KILLED")):
        with pytest.raises(ledger.RetryPredicateNotYours):
            ledger.write(
                writer,
                evidence_node=evidence_node,
                caught_by=caught_by,
                retry_predicate={"kind": "gate_owned_remeasurement", "target": hypothesis.hash},
                **common,
            )
    assert ledger.entries_for(writer, hypothesis.hash) == []


def test_a_parked_entry_cites_the_refutation_it_waits_on(writer, branch, db_snapshot):
    statement, hypothesis = branch
    table = _node(writer, statement, "ladder_table", "REJECT", seed=6)
    digest = ledger.write(
        writer,
        hypothesis_key=hypothesis.hash,
        decision=ledger.PARKED,
        evidence_node=table,
        method=hypothesis.method_identity,
        blocker="null_control_pending",
        caught_by="preflight:RequiresNullControl",
        at=AT,
    )
    db_snapshot(writer.conn, "parked")
    row = ledger.get_entry(writer, digest)
    assert (row["decision"], row["blocker"], row["refutation_kind"], row["retry_predicate"]) == (
        "PARKED",
        "null_control_pending",
        None,
        None,
    )


def test_the_entry_keeps_its_evidence_reachable_from_the_roots(writer, branch):
    statement, hypothesis = branch
    table = _node(writer, statement, "ladder_table", "REJECT", seed=7)
    roots, edges, _ = gc._load(writer)
    assert table not in gc.reachable(roots, edges)
    digest = ledger.write(
        writer,
        hypothesis_key=hypothesis.hash,
        decision=ledger.REFUTED,
        refutation_kind=ledger.MEASURED,
        evidence_node=table,
        method=hypothesis.method_identity,
        measured_points=FIFTY_BITS,
        result=REJECT_RESULT,
        caught_by="ladder:floor",
        at=AT,
    )
    roots, edges, _ = gc._load(writer)
    assert digest in roots and table in gc.reachable(roots, edges)
