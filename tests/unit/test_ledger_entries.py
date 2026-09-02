import json
import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import claims, gc, ledger
from cairn.ledger import LedgerError, RetryPredicateNotYours

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _substrate_helpers import open_writer

KEY = "1a" * 32
REVISION = "2b" * 32
METHOD = {"interface_version": "rho_dp/1", "params": {"r": "20"}}
POINTS = ({"numeric": {"bits": 50, "trials": 40}, "categorical": {"model": "c_sqrt_n"}},)
RESULT = {"summary": "in-sample model miss at 50 bits", "value": "1310000000", "ci": ["1200000000", "1400000000"]}
AT = "2026-09-02T00:00:00Z"


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def evidence(writer):
    statement = factories.claim_statement(seed=3)
    claims.write_claim_statement(writer, statement)
    nodes = {}
    for name, kind, verdict in (
        ("reject", "ladder_table", "REJECT"),
        ("keep", "ladder_table", "KEEP"),
        ("killed", "counterexample_hunt_record", "KILLED"),
        ("survived", "counterexample_hunt_record", "SURVIVED"),
        ("lean", "lean_artifact", None),
        ("lean_keep", "lean_artifact", "KEEP"),
    ):
        node = factories.evidence_node(
            kind,
            statement.hash,
            statement.scope,
            statement.scope["assumption_set"],
            verdict=verdict,
            seed=hash(name) % 1000,
        )
        claims.write_evidence_node(writer, node)
        nodes[name] = node.hash
    return nodes


def measured(evidence, **overrides):
    fields = {
        "hypothesis_key": KEY,
        "decision": ledger.REFUTED,
        "refutation_kind": ledger.MEASURED,
        "evidence_node": evidence["reject"],
        "method": METHOD,
        "measured_points": POINTS,
        "result": RESULT,
        "caught_by": "ladder:in_sample_model_miss",
        "at": AT,
    }
    fields.update(overrides)
    return fields


def implementation(evidence, **overrides):
    shape = {
        "refutation_kind": ledger.IMPLEMENTATION,
        "measured_points": (),
        "result": None,
        "faulting_revision": REVISION,
        "caught_by": "ladder:xP_ne_Q",
    }
    return measured(evidence, **{**shape, **overrides})


def formal(evidence, **overrides):
    shape = {
        "refutation_kind": ledger.FORMAL,
        "evidence_node": evidence["lean"],
        "measured_points": (),
        "result": None,
        "caught_by": "formal:lean_negation",
    }
    return measured(evidence, **{**shape, **overrides})


def parked(evidence, **overrides):
    shape = {
        "decision": ledger.PARKED,
        "refutation_kind": None,
        "blocker": "null_control_pending",
        "caught_by": "preflight:RequiresNullControl",
    }
    return measured(evidence, **{**shape, **overrides})


def test_a_measured_entry_carries_points_ci_and_a_gate_authored_retry_predicate(writer, evidence, db_snapshot):
    digest = ledger.write(writer, **measured(evidence))
    row = ledger.get_entry(writer, digest)
    db_snapshot(writer.conn, "measured")
    assert row["decision"] == "REFUTED" and row["refutation_kind"] == "measured"
    assert json.loads(row["measured_points"]) == [dict(p) for p in POINTS]
    assert json.loads(row["result"]) == RESULT
    assert json.loads(row["retry_predicate"]) == {"kind": "gate_owned_remeasurement", "target": KEY}
    assert json.loads(row["method"]) == METHOD
    assert (row["caught_by"], row["blocker"], row["faulting_revision"]) == ("ladder:in_sample_model_miss", None, None)
    assert row["evidence_node"] == evidence["reject"]


def test_an_implementation_entry_names_the_faulting_revision_and_retries_on_a_new_one(writer, evidence):
    digest = ledger.write(writer, **implementation(evidence))
    row = ledger.get_entry(writer, digest)
    assert row["refutation_kind"] == "implementation" and row["faulting_revision"] == REVISION
    assert json.loads(row["retry_predicate"]) == {"kind": "new_certified_revision", "target": REVISION}
    assert json.loads(row["measured_points"]) == [] and row["result"] is None


def test_a_formal_entry_has_no_retry_predicate(writer, evidence):
    digest = ledger.write(writer, **formal(evidence))
    row = ledger.get_entry(writer, digest)
    assert row["refutation_kind"] == "formal" and row["retry_predicate"] is None


def test_a_parked_entry_carries_its_typed_blocker_and_no_kind(writer, evidence):
    digest = ledger.write(writer, **parked(evidence))
    row = ledger.get_entry(writer, digest)
    assert (row["decision"], row["refutation_kind"], row["blocker"]) == ("PARKED", None, "null_control_pending")
    assert row["retry_predicate"] is None


def test_a_caller_supplied_retry_predicate_is_refused_and_nothing_is_written(writer, evidence, db_snapshot):
    before = db_snapshot(writer.conn, "before")
    with pytest.raises(RetryPredicateNotYours, match="never supplied by its caller"):
        ledger.write(writer, retry_predicate={"kind": "gate_owned_remeasurement", "target": KEY}, **measured(evidence))
    assert db_snapshot(writer.conn, "after") == before


@pytest.mark.parametrize(
    ("build", "overrides", "message"),
    [
        (measured, {"measured_points": ()}, "carries the parameter points"),
        (measured, {"result": None}, "two-sided CI"),
        (measured, {"result": {**RESULT, "ci": None}}, "two-sided CI"),
        (measured, {"result": {**RESULT, "ci": ["1"]}}, "two-sided CI"),
        (measured, {"result": {**RESULT, "ci": ["1400000000", "1200000000"]}}, "CI low bound exceeds its high bound"),
        (measured, {"result": {**RESULT, "ci": ["low", "high"]}}, "CI bounds are decimal strings"),
        (measured, {"measured_points": ({"numeric": {}, "categorical": {}},)}, "at least one numeric or categorical"),
        (measured, {"faulting_revision": REVISION}, "only an implementation entry names a faulting revision"),
        (measured, {"blocker": "near_dup_review"}, "a REFUTED entry holds no blocker"),
        (measured, {"decision": "MAYBE"}, "decision must be one of"),
        (measured, {"refutation_kind": "vibes"}, "refutation_kind must be one of"),
        (measured, {"caught_by": "ladder"}, "must read <writer>:<predicate>"),
        (measured, {"caught_by": "oracle:said_so"}, "must read <writer>:<predicate>"),
        (measured, {"caught_by": "preflight:Blocked"}, "the preflight parks; it never refutes"),
        (
            measured,
            {"caught_by": "hunt:KILLED", "refutation_kind": ledger.IMPLEMENTATION, "faulting_revision": REVISION},
            "a hunt entry is one of",
        ),
        (
            measured,
            {"caught_by": "formal:lean", "refutation_kind": ledger.MEASURED},
            "a formal writer writes a formal entry",
        ),
        (implementation, {"faulting_revision": None}, "names the faulting revision"),
        (formal, {"faulting_revision": REVISION}, "only an implementation entry names a faulting revision"),
        (parked, {"refutation_kind": ledger.MEASURED}, "a PARKED entry carries no refutation kind"),
        (parked, {"blocker": "gut_feeling"}, "carries a typed blocker from"),
        (parked, {"caught_by": "ladder:parked"}, "is the preflight's write"),
        (measured, {"method": {"interface_version": "rho_dp/1"}}, "missing field"),
        (measured, {"measured_points": ({"numeric": {"bits": "50"}, "categorical": {}},)}, "expected int"),
        (measured, {"hypothesis_key": ""}, "must not be empty"),
    ],
)
def test_an_incomplete_entry_is_refused_before_any_write(writer, evidence, db_snapshot, build, overrides, message):
    before = db_snapshot(writer.conn, "before")
    with pytest.raises(LedgerError, match=message):
        ledger.write(writer, **build(evidence, **overrides))
    assert db_snapshot(writer.conn, "after") == before


def test_an_unknown_field_is_refused(writer, evidence):
    with pytest.raises(LedgerError, match="unexpected keyword argument 'severity'"):
        ledger.write(writer, severity="high", **measured(evidence))


@pytest.mark.parametrize(
    ("build", "node", "message"),
    [
        (measured, "keep", "a ladder entry cites a ladder_table node with verdict REJECT"),
        (measured, "killed", "a ladder entry cites a ladder_table node with verdict REJECT"),
        (implementation, "keep", "a ladder entry cites a ladder_table node with verdict REJECT"),
        (formal, "reject", "a formal entry cites one of"),
        (formal, "lean_keep", "carrying no supporting verdict"),
        (parked, "lean", "a PARKED entry cites a measurement"),
        (measured, "missing", "is not in the substrate"),
    ],
)
def test_the_cited_evidence_must_carry_the_writer_s_verdict(writer, evidence, build, node, message):
    evidence = {**evidence, "missing": "ff" * 32}
    with pytest.raises(LedgerError, match=message):
        ledger.write(writer, **build(evidence, evidence_node=evidence[node]))


def test_a_hunt_entry_cites_a_killed_hunt_record(writer, evidence):
    fields = measured(evidence, evidence_node=evidence["killed"], caught_by="hunt:KILLED")
    digest = ledger.write(writer, **fields)
    assert ledger.get_entry(writer, digest)["caught_by"] == "hunt:KILLED"
    with pytest.raises(LedgerError, match="verdict KILLED"):
        ledger.write(writer, **measured(evidence, evidence_node=evidence["survived"], caught_by="hunt:KILLED"))


def test_the_entry_is_a_node_a_gc_root_and_linked_to_its_evidence(writer, evidence):
    before = gc.plan(writer)
    digest = ledger.write(writer, **measured(evidence))
    after = gc.plan(writer)
    assert writer.get_node(digest)["kind"] == "ledger_entry"
    assert writer.is_root("ledger_row", digest)
    assert [(r["parent_hash"], r["edge_kind"]) for r in writer.lineage_of(digest)] == [(evidence["reject"], "input")]
    assert after["roots"] == before["roots"] + 1


def test_the_same_entry_written_twice_is_one_row(writer, evidence, db_snapshot):
    first = ledger.write(writer, **measured(evidence))
    counts = db_snapshot(writer.conn, "once")
    assert ledger.write(writer, **measured(evidence)) == first
    assert db_snapshot(writer.conn, "twice") == counts
    assert [row["hash"] for row in ledger.entries_for(writer, KEY)] == [first]


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE ledger_entries SET retry_predicate = NULL WHERE hash = :digest",
        "UPDATE ledger_entries SET decision = 'PARKED', blocker = 'near_dup_review', refutation_kind = NULL WHERE hash = :digest",
        "UPDATE ledger_entries SET measured_points = '[]' WHERE hash = :digest",
        "DELETE FROM ledger_entries WHERE hash = :digest",
    ],
)
def test_a_written_entry_is_append_only(writer, evidence, statement):
    digest = ledger.write(writer, **measured(evidence))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute(statement, {"digest": digest})
    assert ledger.get_entry(writer, digest)["decision"] == "REFUTED"


@pytest.mark.parametrize(
    ("columns", "message"),
    [
        ({"decision": "REFUTED", "refutation_kind": None, "blocker": None}, "CHECK"),
        ({"decision": "PARKED", "refutation_kind": None, "blocker": None}, "CHECK"),
        ({"decision": "REFUTED", "refutation_kind": "measured", "blocker": "near_dup_review"}, "CHECK"),
        ({"decision": "REFUTED", "refutation_kind": "vibes", "blocker": None}, "CHECK"),
    ],
)
def test_the_schema_refuses_a_row_the_api_would_never_write(writer, columns, message):
    with pytest.raises(sqlite3.IntegrityError, match=message):
        writer.conn.execute(
            "INSERT INTO ledger_entries (hash, hypothesis_key, decision, refutation_kind, evidence_node, method, measured_points, result, retry_predicate, caught_by, blocker, faulting_revision, created_at) VALUES ('h', 'k', :decision, :refutation_kind, 'e', '{}', '[]', NULL, NULL, 'ladder:x', :blocker, NULL, 'now')",
            columns,
        )
