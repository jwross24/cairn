import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import claims
from cairn.canon import length_prefix, u64le
from cairn.claims import HashCollision, UnknownStatement
from cairn.substrate import blob_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories  # noqa: E402
from _substrate_helpers import open_writer  # noqa: E402
from factories import CREATED_AT  # noqa: E402


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def populated(writer):
    stmt = factories.claim_statement(cost_model=True, seed=1)
    claims.write_claim_statement(writer, stmt)
    hyp = factories.hypothesis_object(claim_statement_hash=stmt.hash, seed=1)
    claims.write_hypothesis_object(writer, hyp)
    table, repro = factories.ladder_table_keep(stmt, stmt.scope, seed=1)
    claims.write_repro_record(writer, repro)
    claims.write_evidence_node(writer, table)
    verdict = factories.review_verdict(stmt.hash, seed=1)
    row_id = claims.write_review_verdict(writer, verdict)
    run = factories.gate_run(statement_hash=stmt.hash, seed=1)
    claims.write_gate_run(writer, run)
    tk = factories.ticket(hypothesis_key=hyp.hash, node_hash=hyp.hash, seed=1)
    claims.write_ticket(writer, tk)
    seq = claims.append_tag_history(writer, stmt.hash, None, "SPECULATION", None, "opened", "gate:justify", at=CREATED_AT)
    refusal_id = claims.add_tier_refusal(writer, hyp.hash, 2, 0, "tier-two-above", at=CREATED_AT)
    return {
        "writer": writer,
        "stmt": stmt,
        "hyp": hyp,
        "table": table,
        "repro": repro,
        "verdict": verdict,
        "row_id": row_id,
        "run": run,
        "ticket": tk,
        "seq": seq,
        "refusal_id": refusal_id,
    }


def test_write_one_of_each_reads_back_byte_equal(populated, db_snapshot):
    writer, stmt, hyp, table, repro = (populated[k] for k in ("writer", "stmt", "hyp", "table", "repro"))
    verdict, run, tk = (populated[k] for k in ("verdict", "run", "ticket"))
    db_snapshot(writer.conn, "one-of-each")
    assert claims.get_claim_statement(writer, stmt.hash) == {
        "hash": stmt.hash,
        "claim_id": stmt.claim_id,
        "version": 1,
        "informal": stmt.informal,
        "formal_source": None,
        "scope": claims.to_json(stmt.scope),
        "quantities": claims.to_json(stmt.quantities),
        "source_claim_hash": None,
        "supersedes": None,
        "status": "open",
        "created_at": CREATED_AT,
    }
    hyp_row = claims.get_hypothesis_object(writer, hyp.hash)
    assert hyp_row["claim_statement_hash"] == stmt.hash and hyp_row["supersedes"] is None and hyp_row["created_at"] == CREATED_AT
    assert bytes(hyp_row["canonical"]) == claims.hypothesis_object_canonical(hyp)
    assert claims.get_evidence_node(writer, table.hash) == {
        "hash": table.hash,
        "kind": "ladder_table",
        "target_statement_hash": stmt.hash,
        "population": claims.to_json(table.population),
        "assumptions": claims.to_json(table.assumptions),
        "producer_identity": table.producer_identity,
        "producer_tag": "skill",
        "verdict": "KEEP",
        "in_sample_sizes": claims.to_json(table.in_sample_sizes),
        "attempt_id": table.attempt_id,
        "repro_record_hash": repro.hash,
        "created_at": CREATED_AT,
    }
    assert claims.get_repro_record(writer, repro.hash) == {
        "hash": repro.hash,
        "attempt_id": repro.attempt_id,
        "kind": "second_attempt_agree",
        "passed": 1,
        "at": CREATED_AT,
    }
    assert claims.review_verdicts_for(writer, stmt.hash) == [
        {
            "row_id": populated["row_id"],
            "statement_hash": stmt.hash,
            "reviewer": verdict.reviewer,
            "verdict": "approve",
            "checklist_template_hash": verdict.checklist_template_hash,
            "gate_bundle_hash": verdict.gate_bundle_hash,
            "at": CREATED_AT,
            "supersedes": None,
            "record_digest": verdict.record_digest,
            "file_offset": 0,
        }
    ]
    assert claims.get_gate_run(writer, run.hash) == {
        "run_id": run.hash,
        "gate": "tier_gate",
        "bundle_hash": run.bundle_hash,
        "pin_hash": run.pin_hash,
        "plan_step": None,
        "instance_hash": None,
        "statement_hash": stmt.hash,
        "result": "admitted",
        "reasons": "[]",
        "at": CREATED_AT,
    }
    assert claims.get_ticket(writer, tk.hash) == {
        "ticket_hash": tk.hash,
        "hypothesis_key": hyp.hash,
        "method_identity": claims.to_json(tk.method_identity),
        "statement_hash": None,
        "tier": 0,
        "kind": "hypothesis_object",
        "node_hash": hyp.hash,
        "bundle_hash": tk.bundle_hash,
    }
    assert claims.tag_history_for(writer, stmt.hash) == [
        {
            "seq": populated["seq"],
            "statement_hash": stmt.hash,
            "from_tag": None,
            "to_tag": "SPECULATION",
            "evidence_hash": None,
            "justification": "opened",
            "actor": "gate:justify",
            "at": CREATED_AT,
        }
    ]
    assert claims.tier_refusals_for(writer, hyp.hash) == [
        {"id": populated["refusal_id"], "hypothesis_key": hyp.hash, "declared_tier": 2, "ticket_tier": 0, "reason": "tier-two-above", "at": CREATED_AT}
    ]


def test_every_typed_row_has_its_nodes_row_with_the_same_canonical(populated):
    writer = populated["writer"]
    expected = {
        populated["stmt"].hash: ("claim_statement", claims.claim_statement_canonical(populated["stmt"])),
        populated["hyp"].hash: ("hypothesis_object", claims.hypothesis_object_canonical(populated["hyp"])),
        populated["table"].hash: ("evidence_node", claims.evidence_node_canonical(populated["table"])),
        populated["repro"].hash: ("repro_record", claims.repro_record_canonical(populated["repro"])),
        populated["verdict"].hash: ("review_verdict", claims.review_verdict_canonical(populated["verdict"])),
        populated["run"].hash: ("gate_run", claims.gate_run_canonical(populated["run"])),
        populated["ticket"].hash: ("ticket", claims.ticket_canonical(populated["ticket"])),
    }
    for digest, (kind, canonical) in expected.items():
        node = writer.get_node(digest)
        assert node["kind"] == kind
        assert bytes(node["canonical"]) == canonical


def test_same_hash_insert_is_a_no_op_and_different_companions_collide(populated, db_snapshot):
    writer, hyp, stmt = populated["writer"], populated["hyp"], populated["stmt"]
    counts = db_snapshot(writer.conn, "before-reinsert")
    assert claims.write_hypothesis_object(writer, hyp) == hyp.hash
    assert claims.write_claim_statement(writer, stmt) == stmt.hash
    assert db_snapshot(writer.conn, "after-reinsert") == counts
    with pytest.raises(HashCollision, match="different companions"):
        claims.write_hypothesis_object(writer, factories.hypothesis_object(claim_statement_hash=None, seed=1))


IMMUTABLE_UPDATES = [
    ("hypothesis_objects", "UPDATE hypothesis_objects SET supersedes = 'edited'"),
    ("claim_statements", "UPDATE claim_statements SET informal = 'edited'"),
    ("evidence_nodes", "UPDATE evidence_nodes SET verdict = 'REJECT'"),
    ("repro_records", "UPDATE repro_records SET passed = 0"),
    ("tag_history", "UPDATE tag_history SET to_tag = 'PROVEN'"),
    ("review_verdicts", "UPDATE review_verdicts SET verdict = 'reject'"),
    ("gate_runs", "UPDATE gate_runs SET result = 'pass'"),
    ("tickets", "UPDATE tickets SET tier = 3"),
    ("tier_refusals", "UPDATE tier_refusals SET reason = 'edited'"),
]


@pytest.mark.parametrize(("table", "statement"), IMMUTABLE_UPDATES, ids=[t for t, _ in IMMUTABLE_UPDATES])
def test_update_on_any_immutable_row_is_refused(populated, db_snapshot, table, statement):
    writer = populated["writer"]
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute(statement)
    db_snapshot(writer.conn, f"immutable-{table}")


CHECK_CASES = [
    ("claim_statements", "status", "OPEN"),
    ("evidence_nodes", "kind", "waiver"),
    ("evidence_nodes", "verdict", "MAYBE"),
    ("repro_records", "kind", "third_attempt"),
    ("tag_history", "to_tag", "PROVED"),
    ("tag_history", "from_tag", "HUNCH"),
    ("review_verdicts", "verdict", "approved"),
    ("gate_runs", "gate", "vibes"),
    ("gate_runs", "result", "ok"),
]


@pytest.mark.parametrize(("table", "column", "bad_value"), CHECK_CASES, ids=[f"{t}.{c}={v}" for t, c, v in CHECK_CASES])
def test_undeclared_vocabulary_value_is_refused_by_the_check(populated, db_snapshot, table, column, bad_value):
    writer = populated["writer"]
    row = dict(writer.conn.execute(f"SELECT * FROM {table} LIMIT 1").fetchone())
    for auto in ("seq", "row_id", "id"):
        row.pop(auto, None)
    for pk in ("hash", "run_id", "ticket_hash"):
        if pk in row:
            row[pk] = "f0" * 32
    row[column] = bad_value
    columns = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    with pytest.raises(sqlite3.IntegrityError):
        writer.conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(row.values()))
    db_snapshot(writer.conn, f"check-{table}-{column}")


def test_superseding_statement_is_a_new_hash_and_evidence_does_not_transfer(populated, db_snapshot):
    writer, stmt = populated["writer"], populated["stmt"]
    v2 = factories.superseding_statement(stmt)
    assert v2.hash != stmt.hash
    claims.write_claim_statement(writer, v2)
    db_snapshot(writer.conn, "v2-written")
    assert v2.supersedes == stmt.hash
    assert [e["hash"] for e in claims.evidence_for(writer, stmt.hash)] == [populated["table"].hash]
    assert claims.evidence_for(writer, v2.hash) == []


def test_tag_history_downgrade_without_evidence_is_refused(populated, db_snapshot):
    writer, stmt = populated["writer"], populated["stmt"]
    with pytest.raises(sqlite3.IntegrityError, match="downgrade requires evidence"):
        claims.append_tag_history(writer, stmt.hash, "STRONG-EMPIRICAL", "CONJECTURE", None, "regressed", "gate:justify")
    claims.append_tag_history(writer, stmt.hash, "STRONG-EMPIRICAL", "CONJECTURE", populated["table"].hash, "regressed", "gate:justify")
    claims.append_tag_history(writer, stmt.hash, "SPECULATION", "CONJECTURE", None, "upgraded", "gate:justify")
    db_snapshot(writer.conn, "tag-history")
    assert [r["to_tag"] for r in claims.tag_history_for(writer, stmt.hash)] == ["SPECULATION", "CONJECTURE", "CONJECTURE"]


def test_status_moves_open_to_refuted_once_and_a_second_transition_is_refused(populated, db_snapshot):
    writer, stmt = populated["writer"], populated["stmt"]
    claims.transition_status(writer, stmt.hash, "refuted")
    assert claims.get_claim_statement(writer, stmt.hash)["status"] == "refuted"
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        claims.transition_status(writer, stmt.hash, "promoted")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute("UPDATE claim_statements SET status = 'open' WHERE hash = ?", (stmt.hash,))
    db_snapshot(writer.conn, "refuted")
    assert claims.get_claim_statement(writer, stmt.hash)["status"] == "refuted"
    with pytest.raises(ValueError, match="status must be one of"):
        claims.transition_status(writer, stmt.hash, "open")
    with pytest.raises(UnknownStatement):
        claims.transition_status(writer, "00" * 32, "refuted")


def test_evidence_node_reaches_its_repro_record_and_passed_is_one(populated, db_snapshot):
    writer = populated["writer"]
    row = writer.conn.execute(
        "SELECT r.passed FROM evidence_nodes e JOIN repro_records r ON r.hash = e.repro_record_hash WHERE e.hash = ?",
        (populated["table"].hash,),
    ).fetchone()
    db_snapshot(writer.conn, "repro-join")
    assert row["passed"] == 1


def test_cost_model_round_trips_and_is_null_when_absent(writer, db_snapshot):
    with_model = factories.claim_statement(cost_model={"exponent": "1/2", "constant": "0.886", "crossover": 44}, seed=2)
    without = factories.claim_statement(cost_model=None, seed=3)
    claims.write_claim_statement(writer, with_model)
    claims.write_claim_statement(writer, without)
    db_snapshot(writer.conn, "cost-model")
    assert claims.has_cost_model(writer, with_model.hash) is True
    assert claims.has_cost_model(writer, without.hash) is False
    extracted = writer.conn.execute("SELECT json_extract(quantities, '$.cost_model') FROM claim_statements WHERE hash = ?", (with_model.hash,)).fetchone()[0]
    assert extracted == claims.to_json({"exponent": "1/2", "constant": "0.886", "crossover": 44})
    assert writer.conn.execute("SELECT json_extract(quantities, '$.cost_model') FROM claim_statements WHERE hash = ?", (without.hash,)).fetchone()[0] is None


def test_in_sample_sizes_round_trips_and_is_null_off_the_ladder(populated, db_snapshot):
    writer, stmt = populated["writer"], populated["stmt"]
    stat = factories.evidence_node("statistical", stmt.hash, stmt.scope, frozenset({"A1"}), seed=5)
    claims.write_evidence_node(writer, stat)
    db_snapshot(writer.conn, "in-sample")
    assert claims.get_evidence_node(writer, populated["table"].hash)["in_sample_sizes"] == claims.to_json([30, 50])
    assert claims.get_evidence_node(writer, stat.hash)["in_sample_sizes"] is None


def test_review_verdict_digest_names_the_bytes_at_its_file_offset(populated, tmp_path, db_snapshot):
    writer, verdict = populated["writer"], populated["verdict"]
    attest = tmp_path / "attestations"
    attest.write_bytes(claims.review_verdict_record(verdict))
    row = claims.review_verdicts_for(writer, verdict.statement_hash)[0]
    data = attest.read_bytes()
    offset = row["file_offset"]
    length = int.from_bytes(data[offset : offset + 8], "little")
    record = data[offset + 8 : offset + 8 + length]
    db_snapshot(writer.conn, "attest")
    assert data[offset : offset + 8] == u64le(length)
    assert blob_hash(record) == row["record_digest"] == verdict.record_digest
    assert record == claims.review_verdict_canonical(verdict)
    forged = record[:-1] + bytes([record[-1] ^ 1])
    assert blob_hash(forged) != row["record_digest"]
    assert length_prefix(record) == data[offset : offset + 8 + length]
