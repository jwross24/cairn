import json
from dataclasses import dataclass, field

from cairn import canon, container, keys
from cairn.canon import BOOL, INT, NON_EMPTY_STR, STR, Field, List, Map, Optional, Set, Struct
from cairn.substrate import SubstrateError, blob_hash

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
    "solution_plan_step",
)
GATE_RESULTS = ("pass", "fail", "refused", "blocked", "admitted", "timeout")
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
FORMALIZATION_GATES = frozenset({"challenge_render", "solution_plan_step"})
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
        Field("arm", Optional(STR)),
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
            "arm": run.arm,
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
    arm: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        if self.gate in FORMALIZATION_GATES:
            container.assert_arm(self.arm)
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
