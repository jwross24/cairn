from cairn import log
from cairn.claims_schema import CLAIM_STATEMENT as CLAIM_STATEMENT
from cairn.claims_schema import COST_MODEL as COST_MODEL
from cairn.claims_schema import EVIDENCE_KINDS as EVIDENCE_KINDS
from cairn.claims_schema import EVIDENCE_NODE as EVIDENCE_NODE
from cairn.claims_schema import EVIDENCE_VERDICTS as EVIDENCE_VERDICTS
from cairn.claims_schema import FORMALIZATION_GATES as FORMALIZATION_GATES
from cairn.claims_schema import GATE_RESULTS as GATE_RESULTS
from cairn.claims_schema import GATE_RUN as GATE_RUN
from cairn.claims_schema import GATES as GATES
from cairn.claims_schema import QUANTITIES as QUANTITIES
from cairn.claims_schema import REPRO_KINDS as REPRO_KINDS
from cairn.claims_schema import REPRO_RECORD as REPRO_RECORD
from cairn.claims_schema import REVIEW_VERDICT as REVIEW_VERDICT
from cairn.claims_schema import REVIEW_VERDICTS as REVIEW_VERDICTS
from cairn.claims_schema import SCOPE as SCOPE
from cairn.claims_schema import STATEMENT_STATUSES as STATEMENT_STATUSES
from cairn.claims_schema import TAGS as TAGS
from cairn.claims_schema import TERMINAL_STATEMENT_STATUSES as TERMINAL_STATEMENT_STATUSES
from cairn.claims_schema import TICKET as TICKET
from cairn.claims_schema import TIERS as TIERS
from cairn.claims_schema import ClaimStatement as ClaimStatement
from cairn.claims_schema import EvidenceNode as EvidenceNode
from cairn.claims_schema import GateRun as GateRun
from cairn.claims_schema import HypothesisObject as HypothesisObject
from cairn.claims_schema import ReproRecord as ReproRecord
from cairn.claims_schema import ReviewVerdict as ReviewVerdict
from cairn.claims_schema import Ticket as Ticket
from cairn.claims_schema import UnknownStatement as UnknownStatement
from cairn.claims_schema import claim_statement_canonical as claim_statement_canonical
from cairn.claims_schema import evidence_node_canonical as evidence_node_canonical
from cairn.claims_schema import gate_run_canonical as gate_run_canonical
from cairn.claims_schema import hypothesis_object_canonical as hypothesis_object_canonical
from cairn.claims_schema import jsonable as jsonable
from cairn.claims_schema import opt_json as opt_json
from cairn.claims_schema import repro_record_canonical as repro_record_canonical
from cairn.claims_schema import review_verdict_canonical as review_verdict_canonical
from cairn.claims_schema import review_verdict_digest as review_verdict_digest
from cairn.claims_schema import review_verdict_record as review_verdict_record
from cairn.claims_schema import ticket_canonical as ticket_canonical
from cairn.claims_schema import to_json as to_json
from cairn.substrate import HashCollision, _now

lg = log.get("claims")


def _insert_once(sub, table, pk_column, values, node_hash, *, write_time=("created_at",)):
    """A column outside the hash can differ under an identical key, and a silent keep would record the first write's value as if the second agreed."""
    row = sub.conn.execute(f"SELECT * FROM {table} WHERE {pk_column} = ?", (values[pk_column],)).fetchone()
    if row is not None:
        disagreed = sorted(k for k, v in values.items() if k not in write_time and row[k] != v)
        if disagreed:
            raise HashCollision(f"{table} row {values[pk_column]} exists with different {', '.join(disagreed)}")
        lg.info("write", table=table, hash=node_hash, status="exists")
        return False
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    sub.conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(values.values()))
    lg.info("write", table=table, hash=node_hash, status="inserted")
    return True


def write_hypothesis_object(sub, obj):
    canonical = hypothesis_object_canonical(obj)
    with sub.transaction():
        sub.put_node("hypothesis_object", canonical, hash=obj.hash)
        row = sub.conn.execute("SELECT * FROM hypothesis_objects WHERE hash = ?", (obj.hash,)).fetchone()
        if row is not None:
            if row["claim_statement_hash"] != obj.claim_statement_hash or row["supersedes"] != obj.supersedes:
                raise HashCollision(f"hypothesis object {obj.hash} exists with different companions")
            lg.info("write", table="hypothesis_objects", hash=obj.hash, status="exists")
            return obj.hash
        sub.conn.execute(
            "INSERT INTO hypothesis_objects (hash, canonical, claim_statement_hash, supersedes, created_at) VALUES (?, ?, ?, ?, ?)",
            (obj.hash, canonical, obj.claim_statement_hash, obj.supersedes, obj.created_at or _now()),
        )
    lg.info("write", table="hypothesis_objects", hash=obj.hash, status="inserted")
    return obj.hash


def write_claim_statement(sub, stmt):
    canonical = claim_statement_canonical(stmt)
    with sub.transaction():
        sub.put_node("claim_statement", canonical, hash=stmt.hash)
        _insert_once(
            sub,
            "claim_statements",
            "hash",
            {
                "hash": stmt.hash,
                "claim_id": stmt.claim_id,
                "version": stmt.version,
                "informal": stmt.informal,
                "formal_source": stmt.formal_source,
                "scope": to_json(stmt.scope),
                "quantities": to_json(stmt.quantities),
                "source_claim_hash": stmt.source_claim_hash,
                "supersedes": stmt.supersedes,
                "status": stmt.status,
                "created_at": stmt.created_at or _now(),
            },
            stmt.hash,
            write_time=("created_at", "status"),
        )
    return stmt.hash


def write_evidence_node(sub, node, *, replay_grade="Replayable"):
    canonical = evidence_node_canonical(node)
    with sub.transaction():
        sub.put_node(
            "evidence_node",
            canonical,
            replay_grade=replay_grade,
            producer_identity=node.producer_identity,
            hash=node.hash,
        )
        _insert_once(
            sub,
            "evidence_nodes",
            "hash",
            {
                "hash": node.hash,
                "kind": node.kind,
                "target_statement_hash": node.target_statement_hash,
                "population": to_json(node.population),
                "assumptions": to_json(node.assumptions),
                "producer_identity": node.producer_identity,
                "producer_tag": node.producer_tag,
                "verdict": node.verdict,
                "in_sample_sizes": opt_json(node.in_sample_sizes),
                "attempt_id": node.attempt_id,
                "repro_record_hash": node.repro_record_hash,
                "created_at": node.created_at or _now(),
            },
            node.hash,
        )
    return node.hash


def write_repro_record(sub, rec):
    canonical = repro_record_canonical(rec)
    with sub.transaction():
        sub.put_node("repro_record", canonical, hash=rec.hash)
        _insert_once(
            sub,
            "repro_records",
            "hash",
            {"hash": rec.hash, "attempt_id": rec.attempt_id, "kind": rec.kind, "passed": int(rec.passed), "at": rec.at},
            rec.hash,
        )
    return rec.hash


def write_review_verdict(sub, verdict):
    canonical = review_verdict_canonical(verdict)
    with sub.transaction():
        sub.put_node("review_verdict", canonical, producer_identity=verdict.reviewer, hash=verdict.hash)
        existing = sub.conn.execute(
            "SELECT row_id FROM review_verdicts WHERE record_digest = ? AND file_offset = ?",
            (verdict.record_digest, verdict.file_offset),
        ).fetchone()
        if existing is not None:
            lg.info("write", table="review_verdicts", hash=verdict.hash, status="exists", row_id=existing["row_id"])
            return existing["row_id"]
        cur = sub.conn.execute(
            "INSERT INTO review_verdicts (statement_hash, reviewer, verdict, checklist_template_hash, gate_bundle_hash, at, supersedes, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                verdict.statement_hash,
                verdict.reviewer,
                verdict.verdict,
                verdict.checklist_template_hash,
                verdict.gate_bundle_hash,
                verdict.at,
                verdict.supersedes,
                verdict.record_digest,
                verdict.file_offset,
            ),
        )
        row_id = cur.lastrowid
    lg.info("write", table="review_verdicts", hash=verdict.hash, status="inserted", row_id=row_id)
    return row_id


def write_gate_run(sub, run):
    canonical = gate_run_canonical(run)
    with sub.transaction():
        sub.put_node("gate_run", canonical, hash=run.hash)
        _insert_once(
            sub,
            "gate_runs",
            "run_id",
            {
                "run_id": run.hash,
                "gate": run.gate,
                "bundle_hash": run.bundle_hash,
                "pin_hash": run.pin_hash,
                "plan_step": run.plan_step,
                "instance_hash": run.instance_hash,
                "statement_hash": run.statement_hash,
                "formal_statement_hash": run.formal_statement_hash,
                "renderer_hash": run.renderer_hash,
                "prelude_hash": run.prelude_hash,
                "arm": run.arm,
                "result": run.result,
                "reasons": to_json(list(run.reasons)),
                "at": run.at,
            },
            run.hash,
        )
    return run.hash


def write_ticket(sub, ticket):
    canonical = ticket_canonical(ticket)
    with sub.transaction():
        sub.put_node("ticket", canonical, hash=ticket.hash)
        _insert_once(
            sub,
            "tickets",
            "ticket_hash",
            {
                "ticket_hash": ticket.hash,
                "hypothesis_key": ticket.hypothesis_key,
                "method_identity": to_json(ticket.method_identity),
                "statement_hash": ticket.statement_hash,
                "tier": ticket.tier,
                "kind": ticket.kind,
                "node_hash": ticket.node_hash,
                "bundle_hash": ticket.bundle_hash,
            },
            ticket.hash,
        )
    return ticket.hash


def append_tag_history(sub, statement_hash, from_tag, to_tag, evidence_hash, justification, actor, *, at=None):
    with sub.transaction():
        cur = sub.conn.execute(
            "INSERT INTO tag_history (statement_hash, from_tag, to_tag, evidence_hash, justification, actor, at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (statement_hash, from_tag, to_tag, evidence_hash, justification, actor, at or _now()),
        )
        seq = cur.lastrowid
    lg.info(
        "write", table="tag_history", hash=statement_hash, status="inserted", seq=seq, from_tag=from_tag, to_tag=to_tag
    )
    return seq


def add_tier_refusal(sub, hypothesis_key, declared_tier, ticket_tier, reason, *, at=None):
    with sub.transaction():
        cur = sub.conn.execute(
            "INSERT INTO tier_refusals (hypothesis_key, declared_tier, ticket_tier, reason, at) VALUES (?, ?, ?, ?, ?)",
            (hypothesis_key, declared_tier, ticket_tier, reason, at or _now()),
        )
        refusal_id = cur.lastrowid
    lg.info("write", table="tier_refusals", hash=hypothesis_key, status="inserted", id=refusal_id, reason=reason)
    return refusal_id


def transition_status(sub, statement_hash, to_status):
    if to_status not in TERMINAL_STATEMENT_STATUSES:
        raise ValueError(f"status must be one of {TERMINAL_STATEMENT_STATUSES}, got {to_status!r}")
    with sub.transaction():
        cur = sub.conn.execute("UPDATE claim_statements SET status = ? WHERE hash = ?", (to_status, statement_hash))
        if cur.rowcount == 0:
            raise UnknownStatement(f"no claim statement {statement_hash}")
    lg.info("write", table="claim_statements", hash=statement_hash, status=to_status)


def _one(sub, table, pk_column, value):
    row = sub.conn.execute(f"SELECT * FROM {table} WHERE {pk_column} = ?", (value,)).fetchone()
    return None if row is None else dict(row)


def get_hypothesis_object(sub, digest):
    return _one(sub, "hypothesis_objects", "hash", digest)


def get_claim_statement(sub, digest):
    return _one(sub, "claim_statements", "hash", digest)


def get_evidence_node(sub, digest):
    return _one(sub, "evidence_nodes", "hash", digest)


def get_repro_record(sub, digest):
    return _one(sub, "repro_records", "hash", digest)


def get_gate_run(sub, run_id):
    return _one(sub, "gate_runs", "run_id", run_id)


def get_ticket(sub, ticket_hash):
    return _one(sub, "tickets", "ticket_hash", ticket_hash)


def evidence_for(sub, statement_hash):
    rows = sub.conn.execute(
        "SELECT * FROM evidence_nodes WHERE target_statement_hash = ? ORDER BY rowid", (statement_hash,)
    ).fetchall()
    return [dict(r) for r in rows]


def review_verdicts_for(sub, statement_hash):
    rows = sub.conn.execute(
        "SELECT * FROM review_verdicts WHERE statement_hash = ? ORDER BY row_id", (statement_hash,)
    ).fetchall()
    return [dict(r) for r in rows]


def tag_history_for(sub, statement_hash):
    rows = sub.conn.execute(
        "SELECT * FROM tag_history WHERE statement_hash = ? ORDER BY seq", (statement_hash,)
    ).fetchall()
    return [dict(r) for r in rows]


def repro_records_for_attempt(sub, attempt_id):
    rows = sub.conn.execute("SELECT * FROM repro_records WHERE attempt_id = ? ORDER BY rowid", (attempt_id,)).fetchall()
    return [dict(r) for r in rows]


def ticket_tier_for(sub, statement_hash):
    """The highest tier any recorded ticket grants the statement's branch; 0 with no ticket."""
    row = sub.conn.execute("SELECT MAX(tier) FROM tickets WHERE statement_hash = ?", (statement_hash,)).fetchone()
    return 0 if row is None or row[0] is None else int(row[0])


def tier_refusals_for(sub, hypothesis_key):
    rows = sub.conn.execute(
        "SELECT * FROM tier_refusals WHERE hypothesis_key = ? ORDER BY id", (hypothesis_key,)
    ).fetchall()
    return [dict(r) for r in rows]


def has_cost_model(sub, statement_hash):
    row = sub.conn.execute(
        "SELECT json_extract(quantities, '$.cost_model') FROM claim_statements WHERE hash = ?", (statement_hash,)
    ).fetchone()
    if row is None:
        raise UnknownStatement(f"no claim statement {statement_hash}")
    return row[0] is not None


def read_record(path, offset):
    from cairn import attest

    return attest.read_record(path, offset)


def _verdict_of(row):
    return ReviewVerdict(
        statement_hash=row["statement_hash"],
        reviewer=row["reviewer"],
        verdict=row["verdict"],
        checklist_template_hash=row["checklist_template_hash"],
        gate_bundle_hash=row["gate_bundle_hash"],
        at=row["at"],
        supersedes=row["supersedes"],
        file_offset=row["file_offset"],
    )


def verdict_matches_file(row, path):
    """A row counts only when the digest re-derived from its fields is the record at its offset."""
    from cairn import attest

    derived = _verdict_of(row).record_digest
    if derived != row["record_digest"]:
        return False
    return attest.attestation_record_matches(path, row["file_offset"], derived)


def visible_review_verdicts(sub, statement_hash, path):
    return [row for row in review_verdicts_for(sub, statement_hash) if verdict_matches_file(row, path)]


def mirrored_review_verdict(sub, statement_hash, record_digest, file_offset):
    for row in review_verdicts_for(sub, statement_hash):
        if (
            row["record_digest"] == record_digest
            and row["file_offset"] == file_offset
            and _verdict_of(row).record_digest == record_digest
        ):
            return row
    return None


def effective_review_verdicts(sub, statement_hash, path):
    rows = visible_review_verdicts(sub, statement_hash, path)
    superseded = {(row["supersedes"], row["gate_bundle_hash"]) for row in rows if row["supersedes"] is not None}
    return [row for row in rows if (_verdict_of(row).hash, row["gate_bundle_hash"]) not in superseded]


def verdict_mirrored(sub, statement_hash, record_digest, file_offset):
    return mirrored_review_verdict(sub, statement_hash, record_digest, file_offset) is not None
