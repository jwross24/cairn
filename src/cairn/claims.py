import json
from dataclasses import dataclass, field

from cairn import canon, keys, log
from cairn.canon import BOOL, INT, NON_EMPTY_STR, STR, Field, List, Map, Optional, Set, Struct
from cairn.substrate import HashCollision, SubstrateError, _now, blob_hash

lg = log.get("claims")

TAGS = ("SPECULATION", "CONJECTURE", "STRONG-EMPIRICAL", "PROVEN")
STATEMENT_STATUSES = ("open", "refuted", "promoted", "withdrawn")
TERMINAL_STATEMENT_STATUSES = STATEMENT_STATUSES[1:]
EVIDENCE_KINDS = (
    "lean_artifact",
    "ladder_table",
    "repro_node",
    "counterexample_hunt_record",
    "statistical",
    "model_proof",
)
EVIDENCE_VERDICTS = ("KEEP", "KEEP_IN_SAMPLE", "REJECT", "INCONCLUSIVE", "SURVIVED", "KILLED", "INCOMPLETE")
REPRO_KINDS = ("second_attempt_agree", "witness_check")
REVIEW_VERDICTS = ("approve", "reject", "needs_revision")
GATES = (
    "canon_kat",
    "verifier",
    "tier_gate",
    "self_test",
    "gate_plan",
    "bundle_open",
    "ladder_plan",
    "challenge_render",
)
GATE_RESULTS = ("pass", "fail", "refused", "blocked", "admitted")
TIERS = (0, 1, 2, 3)

SCOPE = Struct(
    "scope",
    [
        Field("target_family", NON_EMPTY_STR),
        Field("size_interval", List(INT)),
        Field("param_ranges", Map(STR, List(INT))),
        Field("assumption_set", Set(STR)),
    ],
)
COST_MODEL = Struct(
    "cost_model", [Field("exponent", NON_EMPTY_STR), Field("constant", NON_EMPTY_STR), Field("crossover", INT)]
)
QUANTITIES = Struct("quantities", [Field("units", Map(STR, STR)), Field("cost_model", Optional(COST_MODEL))])
CLAIM_STATEMENT = Struct(
    "claim_statement",
    [
        Field("claim_id", NON_EMPTY_STR),
        Field("version", INT),
        Field("informal", NON_EMPTY_STR),
        Field("formal_source", Optional(STR)),
        Field("scope", SCOPE),
        Field("quantities", QUANTITIES),
        Field("source_claim_hash", Optional(STR)),
        Field("supersedes", Optional(STR)),
    ],
)
EVIDENCE_NODE = Struct(
    "evidence_node",
    [
        Field("kind", NON_EMPTY_STR),
        Field("target_statement_hash", NON_EMPTY_STR),
        Field("population", SCOPE),
        Field("assumptions", Set(STR)),
        Field("producer_identity", NON_EMPTY_STR),
        Field("producer_tag", NON_EMPTY_STR),
        Field("verdict", Optional(STR)),
        Field("in_sample_sizes", Optional(List(INT))),
        Field("attempt_id", Optional(STR)),
        Field("repro_record_hash", Optional(STR)),
    ],
)
REPRO_RECORD = Struct(
    "repro_record",
    [
        Field("attempt_id", NON_EMPTY_STR),
        Field("kind", NON_EMPTY_STR),
        Field("passed", BOOL),
        Field("at", NON_EMPTY_STR),
    ],
)
REVIEW_VERDICT = Struct(
    "review_verdict",
    [
        Field("statement_hash", NON_EMPTY_STR),
        Field("reviewer", NON_EMPTY_STR),
        Field("verdict", NON_EMPTY_STR),
        Field("checklist_template_hash", NON_EMPTY_STR),
        Field("gate_bundle_hash", NON_EMPTY_STR),
        Field("at", NON_EMPTY_STR),
        Field("supersedes", Optional(STR)),
    ],
)
GATE_RUN = Struct(
    "gate_run",
    [
        Field("gate", NON_EMPTY_STR),
        Field("bundle_hash", NON_EMPTY_STR),
        Field("pin_hash", NON_EMPTY_STR),
        Field("plan_step", Optional(STR)),
        Field("instance_hash", Optional(STR)),
        Field("statement_hash", Optional(STR)),
        Field("formal_statement_hash", Optional(STR)),
        Field("renderer_hash", Optional(STR)),
        Field("prelude_hash", Optional(STR)),
        Field("result", NON_EMPTY_STR),
        Field("reasons", List(STR)),
        Field("at", NON_EMPTY_STR),
    ],
)
TICKET = Struct(
    "ticket",
    [
        Field("hypothesis_key", NON_EMPTY_STR),
        Field("method_identity", keys.METHOD_IDENTITY),
        Field("statement_hash", Optional(STR)),
        Field("tier", INT),
        Field("kind", NON_EMPTY_STR),
        Field("node_hash", NON_EMPTY_STR),
        Field("bundle_hash", NON_EMPTY_STR),
    ],
)


class UnknownStatement(SubstrateError):
    pass


def jsonable(value):
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(jsonable(v) for v in value)
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def to_json(value):
    return json.dumps(jsonable(value), sort_keys=True, separators=(",", ":"))


def opt_json(value):
    return None if value is None else to_json(value)


def hypothesis_object_canonical(obj):
    return canon.encode(
        keys.HYPOTHESIS_OBJECT,
        {
            "target_family": obj.target_family,
            "claimed": obj.claimed,
            "method_identity": obj.method_identity,
            "declared_parameter_ranges": obj.declared_parameter_ranges,
            "sampling_distribution": obj.sampling_distribution,
        },
    )


def claim_statement_canonical(stmt):
    return canon.encode(
        CLAIM_STATEMENT,
        {
            "claim_id": stmt.claim_id,
            "version": stmt.version,
            "informal": stmt.informal,
            "formal_source": stmt.formal_source,
            "scope": stmt.scope,
            "quantities": stmt.quantities,
            "source_claim_hash": stmt.source_claim_hash,
            "supersedes": stmt.supersedes,
        },
    )


def evidence_node_canonical(node):
    return canon.encode(
        EVIDENCE_NODE,
        {
            "kind": node.kind,
            "target_statement_hash": node.target_statement_hash,
            "population": node.population,
            "assumptions": node.assumptions,
            "producer_identity": node.producer_identity,
            "producer_tag": node.producer_tag,
            "verdict": node.verdict,
            "in_sample_sizes": node.in_sample_sizes,
            "attempt_id": node.attempt_id,
            "repro_record_hash": node.repro_record_hash,
        },
    )


def repro_record_canonical(rec):
    return canon.encode(
        REPRO_RECORD, {"attempt_id": rec.attempt_id, "kind": rec.kind, "passed": rec.passed, "at": rec.at}
    )


def review_verdict_canonical(verdict):
    return canon.encode(
        REVIEW_VERDICT,
        {
            "statement_hash": verdict.statement_hash,
            "reviewer": verdict.reviewer,
            "verdict": verdict.verdict,
            "checklist_template_hash": verdict.checklist_template_hash,
            "gate_bundle_hash": verdict.gate_bundle_hash,
            "at": verdict.at,
            "supersedes": verdict.supersedes,
        },
    )


def gate_run_canonical(run):
    return canon.encode(
        GATE_RUN,
        {
            "gate": run.gate,
            "bundle_hash": run.bundle_hash,
            "pin_hash": run.pin_hash,
            "plan_step": run.plan_step,
            "instance_hash": run.instance_hash,
            "statement_hash": run.statement_hash,
            "formal_statement_hash": run.formal_statement_hash,
            "renderer_hash": run.renderer_hash,
            "prelude_hash": run.prelude_hash,
            "result": run.result,
            "reasons": list(run.reasons),
            "at": run.at,
        },
    )


def ticket_canonical(ticket):
    return canon.encode(
        TICKET,
        {
            "hypothesis_key": ticket.hypothesis_key,
            "method_identity": ticket.method_identity,
            "statement_hash": ticket.statement_hash,
            "tier": ticket.tier,
            "kind": ticket.kind,
            "node_hash": ticket.node_hash,
            "bundle_hash": ticket.bundle_hash,
        },
    )


def review_verdict_record(verdict):
    return canon.length_prefix(review_verdict_canonical(verdict))


def review_verdict_digest(verdict):
    return blob_hash(review_verdict_canonical(verdict))


@dataclass(frozen=True)
class HypothesisObject:
    target_family: str
    claimed: dict
    method_identity: dict
    declared_parameter_ranges: dict
    sampling_distribution: str | None = None
    claim_statement_hash: str | None = None
    supersedes: str | None = None
    created_at: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "hash", canon.digest(keys.TAG_HYPOTHESIS_KEY, hypothesis_object_canonical(self)))


@dataclass(frozen=True)
class ClaimStatement:
    claim_id: str
    version: int
    informal: str
    scope: dict
    quantities: dict
    formal_source: str | None = None
    source_claim_hash: str | None = None
    supersedes: str | None = None
    status: str = "open"
    created_at: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "hash", keys.node_hash("claim_statement", claim_statement_canonical(self)))


@dataclass(frozen=True)
class EvidenceNode:
    kind: str
    target_statement_hash: str
    population: dict
    assumptions: frozenset
    producer_identity: str
    producer_tag: str
    verdict: str | None = None
    in_sample_sizes: tuple | None = None
    attempt_id: str | None = None
    repro_record_hash: str | None = None
    created_at: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "hash", keys.node_hash("evidence_node", evidence_node_canonical(self)))


@dataclass(frozen=True)
class ReproRecord:
    attempt_id: str
    kind: str
    passed: bool
    at: str
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "hash", keys.node_hash("repro_record", repro_record_canonical(self)))


@dataclass(frozen=True)
class ReviewVerdict:
    statement_hash: str
    reviewer: str
    verdict: str
    checklist_template_hash: str
    gate_bundle_hash: str
    at: str
    supersedes: str | None = None
    file_offset: int = 0
    record_digest: str = field(init=False, compare=False)
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "record_digest", review_verdict_digest(self))
        object.__setattr__(self, "hash", keys.node_hash("review_verdict", review_verdict_canonical(self)))


@dataclass(frozen=True)
class GateRun:
    gate: str
    bundle_hash: str
    pin_hash: str
    result: str
    reasons: tuple
    at: str
    plan_step: str | None = None
    instance_hash: str | None = None
    statement_hash: str | None = None
    formal_statement_hash: str | None = None
    renderer_hash: str | None = None
    prelude_hash: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "hash", keys.node_hash("gate_run", gate_run_canonical(self)))


@dataclass(frozen=True)
class Ticket:
    hypothesis_key: str
    method_identity: dict
    tier: int
    kind: str
    node_hash: str
    bundle_hash: str
    statement_hash: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        if isinstance(self.tier, bool) or self.tier not in TIERS:
            raise ValueError(f"tier must be one of {TIERS}, got {self.tier!r}")
        object.__setattr__(self, "hash", keys.node_hash("ticket", ticket_canonical(self)))


def _insert_once(sub, table, pk_column, values, node_hash):
    row = sub.conn.execute(f"SELECT * FROM {table} WHERE {pk_column} = ?", (values[pk_column],)).fetchone()
    if row is not None:
        lg.info("write", table=table, hash=node_hash, status="exists")
        return False
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    sub.conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(values.values()))
    lg.info("write", table=table, hash=node_hash, status="inserted")
    return True


def write_hypothesis_object(sub, obj):
    canonical = hypothesis_object_canonical(obj)
    with sub._tx():
        sub._put_node("hypothesis_object", canonical, obj.hash, "Replayable", None)
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
    with sub._tx():
        sub._put_node("claim_statement", canonical, stmt.hash, "Replayable", None)
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
        )
    return stmt.hash


def write_evidence_node(sub, node, *, replay_grade="Replayable"):
    canonical = evidence_node_canonical(node)
    with sub._tx():
        sub._put_node("evidence_node", canonical, node.hash, replay_grade, node.producer_identity)
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
    with sub._tx():
        sub._put_node("repro_record", canonical, rec.hash, "Replayable", None)
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
    with sub._tx():
        sub._put_node("review_verdict", canonical, verdict.hash, "Replayable", verdict.reviewer)
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
    with sub._tx():
        sub._put_node("gate_run", canonical, run.hash, "Replayable", None)
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
                "result": run.result,
                "reasons": to_json(list(run.reasons)),
                "at": run.at,
            },
            run.hash,
        )
    return run.hash


def write_ticket(sub, ticket):
    canonical = ticket_canonical(ticket)
    with sub._tx():
        sub._put_node("ticket", canonical, ticket.hash, "Replayable", None)
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
    with sub._tx():
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
    with sub._tx():
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
    with sub._tx():
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


def verdict_matches_file(row, path):
    from cairn import attest

    return attest.attestation_record_matches(path, row["file_offset"], row["record_digest"])


def visible_review_verdicts(sub, statement_hash, path):
    return [row for row in review_verdicts_for(sub, statement_hash) if verdict_matches_file(row, path)]
