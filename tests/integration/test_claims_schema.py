import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import claims
from cairn.canon import length_prefix, u64le
from cairn.claims import HashCollision, UnknownStatement
from cairn.substrate import blob_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _substrate_helpers import open_writer
from factories import CREATED_AT


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


TRANSITION_PINS = [
    ("hash", "hash = 'ff'"),
    ("claim_id", "claim_id = 'other'"),
    ("version", "version = version + 1"),
    ("informal", "informal = 'edited'"),
    ("formal_source", "formal_source = 'theorem edited'"),
    ("scope", "scope = '{}'"),
    ("quantities", "quantities = '{}'"),
    ("source_claim_hash", "source_claim_hash = 'ff'"),
    ("supersedes", "supersedes = 'ff'"),
    ("created_at", "created_at = 'edited'"),
]

IMMUTABLE_UPDATES = (
    [
        ("hypothesis_objects", "UPDATE hypothesis_objects SET supersedes = 'edited' WHERE hash = :hyp"),
        ("claim_statements", "UPDATE claim_statements SET informal = 'edited' WHERE hash = :stmt"),
        ("evidence_nodes", "UPDATE evidence_nodes SET verdict = 'REJECT' WHERE hash = :evidence"),
        ("repro_records", "UPDATE repro_records SET passed = 0 WHERE hash = :repro"),
        ("tag_history", "UPDATE tag_history SET to_tag = 'PROVEN' WHERE statement_hash = :stmt"),
        ("review_verdicts", "UPDATE review_verdicts SET verdict = 'reject' WHERE statement_hash = :stmt"),
        ("gate_runs", "UPDATE gate_runs SET result = 'pass' WHERE run_id = :run"),
        ("tickets", "UPDATE tickets SET tier = 3 WHERE ticket_hash = :ticket"),
        ("tier_refusals", "UPDATE tier_refusals SET reason = 'edited' WHERE hypothesis_key = :hyp"),
    ]
    + [(f"claim_statements-pin-{name}", f"UPDATE claim_statements SET status = 'refuted', {pin} WHERE hash = :stmt") for name, pin in TRANSITION_PINS]
    + [
        ("hypothesis_objects", "DELETE FROM hypothesis_objects WHERE hash = :hyp"),
        ("claim_statements", "DELETE FROM claim_statements WHERE hash = :stmt"),
        ("evidence_nodes", "DELETE FROM evidence_nodes WHERE hash = :evidence"),
        ("repro_records", "DELETE FROM repro_records WHERE hash = :repro"),
        ("tag_history", "DELETE FROM tag_history WHERE statement_hash = :stmt"),
        ("review_verdicts", "DELETE FROM review_verdicts WHERE statement_hash = :stmt"),
        ("gate_runs", "DELETE FROM gate_runs WHERE run_id = :run"),
        ("tickets", "DELETE FROM tickets WHERE ticket_hash = :ticket"),
        ("tier_refusals", "DELETE FROM tier_refusals WHERE hypothesis_key = :hyp"),
    ]
)


def _params(populated):
    return {
        "stmt": populated["stmt"].hash,
        "hyp": populated["hyp"].hash,
        "evidence": populated["table"].hash,
        "repro": populated["repro"].hash,
        "run": populated["run"].hash,
        "ticket": populated["ticket"].hash,
    }


@pytest.mark.parametrize(
    ("table", "statement"),
    IMMUTABLE_UPDATES,
    ids=[f"{t}-{'delete' if s.startswith('DELETE') else 'update'}-{i}" for i, (t, s) in enumerate(IMMUTABLE_UPDATES)],
)
def test_update_or_delete_on_any_immutable_row_is_refused(populated, db_snapshot, table, statement):
    writer = populated["writer"]
    counts = db_snapshot(writer.conn, f"immutable-{table}-before")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute(statement, _params(populated))
    assert db_snapshot(writer.conn, f"immutable-{table}-after") == counts


def test_the_permitted_transition_update_touching_no_pinned_column_is_admitted(populated):
    writer, stmt = populated["writer"], populated["stmt"]
    writer.conn.execute("UPDATE claim_statements SET status = 'refuted' WHERE hash = :stmt", _params(populated))
    assert claims.get_claim_statement(writer, stmt.hash)["status"] == "refuted"


CHECK_CASES = [
    ("claim_statements", "status", "OPEN", "born open"),
    ("evidence_nodes", "kind", "waiver", "CHECK constraint failed"),
    ("evidence_nodes", "verdict", "MAYBE", "CHECK constraint failed"),
    ("repro_records", "kind", "third_attempt", "CHECK constraint failed"),
    ("tag_history", "to_tag", "PROVED", "CHECK constraint failed"),
    ("tag_history", "from_tag", "HUNCH", "CHECK constraint failed"),
    ("review_verdicts", "verdict", "approved", "CHECK constraint failed"),
    ("gate_runs", "gate", "vibes", "CHECK constraint failed"),
    ("gate_runs", "result", "ok", "CHECK constraint failed"),
]


@pytest.mark.parametrize(("table", "column", "bad_value", "match"), CHECK_CASES, ids=[f"{t}.{c}={v}" for t, c, v, _ in CHECK_CASES])
def test_undeclared_vocabulary_value_is_refused_by_the_check(populated, db_snapshot, table, column, bad_value, match):
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
    with pytest.raises(sqlite3.IntegrityError, match=match):
        writer.conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(row.values()))
    db_snapshot(writer.conn, f"check-{table}-{column}")


def test_superseding_statement_is_a_new_hash_and_evidence_does_not_transfer(populated, db_snapshot):
    writer, stmt = populated["writer"], populated["stmt"]
    v2 = factories.superseding_statement(stmt)
    claims.write_claim_statement(writer, v2)
    db_snapshot(writer.conn, "v2-written")
    assert [e["hash"] for e in claims.evidence_for(writer, stmt.hash)] == [populated["table"].hash]
    assert claims.evidence_for(writer, v2.hash) == []


ORDERED_PAIRS = [(a, b) for i, a in enumerate(claims.TAGS) for j, b in enumerate(claims.TAGS) if i > j]
PERMITTED_PAIRS = [(a, b) for i, a in enumerate(claims.TAGS) for j, b in enumerate(claims.TAGS) if i <= j]


@pytest.mark.parametrize(("from_tag", "to_tag"), ORDERED_PAIRS, ids=[f"{a}->{b}" for a, b in ORDERED_PAIRS])
def test_every_downgrade_needs_evidence_and_is_admitted_with_it(populated, db_snapshot, from_tag, to_tag):
    writer, stmt = populated["writer"], populated["stmt"]
    with pytest.raises(sqlite3.IntegrityError, match="downgrade requires evidence"):
        claims.append_tag_history(writer, stmt.hash, from_tag, to_tag, None, "regressed", "gate:justify")
    seq = claims.append_tag_history(writer, stmt.hash, from_tag, to_tag, populated["table"].hash, "regressed", "gate:justify")
    db_snapshot(writer.conn, f"downgrade-{from_tag}-{to_tag}")
    assert [(r["from_tag"], r["to_tag"], r["evidence_hash"]) for r in claims.tag_history_for(writer, stmt.hash) if r["seq"] == seq] == [
        (from_tag, to_tag, populated["table"].hash)
    ]


@pytest.mark.parametrize(("from_tag", "to_tag"), PERMITTED_PAIRS, ids=[f"{a}->{b}" for a, b in PERMITTED_PAIRS])
def test_upgrades_and_no_ops_need_no_evidence(populated, db_snapshot, from_tag, to_tag):
    writer, stmt = populated["writer"], populated["stmt"]
    seq = claims.append_tag_history(writer, stmt.hash, from_tag, to_tag, None, "derived", "gate:justify")
    db_snapshot(writer.conn, f"upgrade-{from_tag}-{to_tag}")
    assert [(r["from_tag"], r["to_tag"]) for r in claims.tag_history_for(writer, stmt.hash) if r["seq"] == seq] == [(from_tag, to_tag)]


def test_an_opening_row_with_no_from_tag_needs_no_evidence(populated):
    writer, stmt = populated["writer"], populated["stmt"]
    claims.append_tag_history(writer, stmt.hash, None, "PROVEN", None, "opened", "gate:justify")
    assert [r["to_tag"] for r in claims.tag_history_for(writer, stmt.hash)] == ["SPECULATION", "PROVEN"]


@pytest.mark.parametrize("to_status", claims.TERMINAL_STATEMENT_STATUSES)
def test_status_moves_open_to_a_terminal_status_once_and_a_second_transition_is_refused(populated, db_snapshot, to_status):
    writer, stmt = populated["writer"], populated["stmt"]
    claims.transition_status(writer, stmt.hash, to_status)
    assert claims.get_claim_statement(writer, stmt.hash)["status"] == to_status
    for other in claims.TERMINAL_STATEMENT_STATUSES:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            claims.transition_status(writer, stmt.hash, other)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute("UPDATE claim_statements SET status = 'open' WHERE hash = ?", (stmt.hash,))
    db_snapshot(writer.conn, to_status)
    assert claims.get_claim_statement(writer, stmt.hash)["status"] == to_status
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


@pytest.fixture
def attested(populated, tmp_path):
    writer, first = populated["writer"], populated["verdict"]
    record_1 = claims.review_verdict_record(first)
    second = factories.review_verdict(first.statement_hash, verdict="needs_revision", seed=9, file_offset=len(record_1))
    claims.write_review_verdict(writer, second)
    path = tmp_path / "attestations"
    path.write_bytes(record_1 + claims.review_verdict_record(second))
    return {"path": path, "verdicts": {first.record_digest: first, second.record_digest: second}}


def test_each_verdict_digest_names_the_bytes_at_its_own_offset(populated, attested, db_snapshot):
    writer, path = populated["writer"], attested["path"]
    rows = claims.review_verdicts_for(writer, populated["stmt"].hash)
    data = path.read_bytes()
    db_snapshot(writer.conn, "attest")
    assert [row["file_offset"] for row in rows] == [0, len(claims.review_verdict_record(populated["verdict"]))]
    for row in rows:
        verdict = attested["verdicts"][row["record_digest"]]
        offset = row["file_offset"]
        length = int.from_bytes(data[offset : offset + 8], "little")
        record = data[offset + 8 : offset + 8 + length]
        assert data[offset : offset + 8] == u64le(length)
        assert length_prefix(record) == data[offset : offset + 8 + length]
        assert record == claims.review_verdict_canonical(verdict)
        assert blob_hash(record) == row["record_digest"] == verdict.record_digest
        assert claims.read_record(path, offset) == record
        assert claims.verdict_matches_file(row, path) is True
    assert claims.verdict_matches_file({**rows[0], "file_offset": rows[1]["file_offset"]}, path) is False
    assert claims.verdict_matches_file({**rows[1], "file_offset": rows[0]["file_offset"]}, path) is False
    assert claims.visible_review_verdicts(writer, populated["stmt"].hash, path) == rows


@pytest.mark.parametrize(
    ("mutate", "expected_visible"),
    [
        (lambda data: data[:-1] + bytes([data[-1] ^ 1]), 1),
        (lambda data: data[:-1], 1),
        (lambda data: b"\x00" + data, 0),
        (lambda data: b"", 0),
    ],
    ids=["flipped-byte", "truncated", "shifted", "empty"],
)
def test_a_verdict_is_absent_unless_its_digest_names_the_bytes_at_its_offset(populated, attested, db_snapshot, mutate, expected_visible):
    writer, path = populated["writer"], attested["path"]
    path.write_bytes(mutate(path.read_bytes()))
    db_snapshot(writer.conn, "forged-attest")
    assert len(claims.visible_review_verdicts(writer, populated["stmt"].hash, path)) == expected_visible


def test_the_same_verdict_written_twice_is_one_row(populated, db_snapshot):
    writer, verdict = populated["writer"], populated["verdict"]
    counts = db_snapshot(writer.conn, "before-rewrite")
    assert claims.write_review_verdict(writer, verdict) == populated["row_id"]
    assert db_snapshot(writer.conn, "after-rewrite") == counts
    moved = factories.review_verdict(verdict.statement_hash, seed=1, file_offset=512)
    assert moved.record_digest == verdict.record_digest
    assert claims.write_review_verdict(writer, moved) != populated["row_id"]
    assert [row["file_offset"] for row in claims.review_verdicts_for(writer, verdict.statement_hash)] == [0, 512]


def test_a_statement_born_terminal_is_refused(writer, db_snapshot):
    born_refuted = factories.claim_statement(seed=11, status="refuted")
    with pytest.raises(sqlite3.IntegrityError, match="born open"):
        claims.write_claim_statement(writer, born_refuted)
    db_snapshot(writer.conn, "born-terminal")
    assert claims.get_claim_statement(writer, born_refuted.hash) is None


UNKNOWN_READERS = [
    claims.get_hypothesis_object,
    claims.get_claim_statement,
    claims.get_evidence_node,
    claims.get_repro_record,
    claims.get_gate_run,
    claims.get_ticket,
]


@pytest.mark.parametrize("reader", UNKNOWN_READERS, ids=[r.__name__ for r in UNKNOWN_READERS])
def test_every_reader_returns_none_for_an_unknown_digest(populated, reader):
    assert reader(populated["writer"], "00" * 32) is None


def test_has_cost_model_raises_for_an_unknown_statement(populated):
    with pytest.raises(UnknownStatement, match="00" * 32):
        claims.has_cost_model(populated["writer"], "00" * 32)


@pytest.mark.parametrize("replay_grade", ["Replayable", "Verifiable", "AuditOnly"])
def test_evidence_node_carries_its_replay_grade_and_producer_onto_the_nodes_row(writer, db_snapshot, replay_grade):
    stmt = factories.claim_statement(seed=12)
    claims.write_claim_statement(writer, stmt)
    node = factories.evidence_node("statistical", stmt.hash, stmt.scope, frozenset({"A1"}), seed=12)
    claims.write_evidence_node(writer, node, replay_grade=replay_grade)
    db_snapshot(writer.conn, f"grade-{replay_grade}")
    row = writer.get_node(node.hash)
    assert row["replay_grade"] == replay_grade
    assert row["producer_identity"] == node.producer_identity
    assert writer.effective_grade(node.hash) == replay_grade


REWRITES = [
    ("evidence_nodes", lambda p: claims.write_evidence_node(p["writer"], p["table"])),
    ("repro_records", lambda p: claims.write_repro_record(p["writer"], p["repro"])),
    ("gate_runs", lambda p: claims.write_gate_run(p["writer"], p["run"])),
    ("tickets", lambda p: claims.write_ticket(p["writer"], p["ticket"])),
]


@pytest.mark.parametrize(("table", "rewrite"), REWRITES, ids=[t for t, _ in REWRITES])
def test_rewriting_an_identical_typed_row_is_a_no_op(populated, db_snapshot, table, rewrite):
    counts = db_snapshot(populated["writer"].conn, f"before-{table}")
    rewrite(populated)
    assert db_snapshot(populated["writer"].conn, f"after-{table}") == counts


def test_a_tier_refusal_without_a_ticket_tier_and_a_superseding_verdict_round_trip(populated, db_snapshot):
    writer, stmt, hyp = populated["writer"], populated["stmt"], populated["hyp"]
    refusal_id = claims.add_tier_refusal(writer, hyp.hash, 1, None, "ticket-absent", at=CREATED_AT)
    superseding = factories.review_verdict(stmt.hash, verdict="reject", seed=13, supersedes=populated["verdict"].hash, file_offset=4096)
    row_id = claims.write_review_verdict(writer, superseding)
    db_snapshot(writer.conn, "optional-columns")
    assert [(r["id"], r["ticket_tier"], r["reason"]) for r in claims.tier_refusals_for(writer, hyp.hash)] == [
        (populated["refusal_id"], 0, "tier-two-above"),
        (refusal_id, None, "ticket-absent"),
    ]
    row = next(r for r in claims.review_verdicts_for(writer, stmt.hash) if r["row_id"] == row_id)
    assert row["supersedes"] == populated["verdict"].hash and row["file_offset"] == 4096 and row["record_digest"] == superseding.record_digest
