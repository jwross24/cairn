"""The REFUTED/PARKED ledger entry: what a ladder REJECT and a hunt KILLED write, and nothing reads before M2.

An entry names the hypothesis key it refutes, the evidence node behind it, the method identity and
the parameter points it was measured at, so the M2 preflight can compute its reach from fields
and range jitter cannot mint a clean key. The retry predicate is derived from the refutation kind
by this module and never accepted from a caller, because a predicate the refuted party authors is
a ledger it can unlock. Every entry is a node, a GC root, and an append-only row.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from cairn import canon, claims, keys, log
from cairn.canon import INT, NON_EMPTY_STR, STR, Field, List, Map, Optional, Struct
from cairn.substrate import EDGE_INPUT, SubstrateError, _now

lg = log.get("ledger")

REFUTED = "REFUTED"
PARKED = "PARKED"
DECISIONS = (REFUTED, PARKED)
FORMAL = "formal"
MEASURED = "measured"
IMPLEMENTATION = "implementation"
KINDS = (FORMAL, MEASURED, IMPLEMENTATION)
RETRY_NEW_CERTIFIED_REVISION = "new_certified_revision"
RETRY_GATE_OWNED_REMEASUREMENT = "gate_owned_remeasurement"
LADDER = "ladder"
HUNT = "hunt"
FORMAL_WRITER = "formal"
PREFLIGHT = "preflight"
WRITERS = (LADDER, HUNT, FORMAL_WRITER, PREFLIGHT)
SHAPES = {
    LADDER: ("ladder_table", "REJECT", (MEASURED, IMPLEMENTATION)),
    HUNT: ("counterexample_hunt_record", "KILLED", (MEASURED,)),
}
FORMAL_EVIDENCE_KINDS = ("lean_artifact", "model_proof")
MEASUREMENT_KINDS = ("ladder_table", "counterexample_hunt_record")
REFUTING_VERDICTS = (None, "REJECT", "KILLED")
BLOCKERS = ("null_control_pending", "near_dup_review", "supersedes_refuted_review", "already_settled")
NODE_KIND = "ledger_entry"
ROOT_KIND = "ledger_row"
TABLE = "ledger_entries"

POINT = Struct("measured_point", [Field("numeric", Map(STR, INT)), Field("categorical", Map(STR, STR))])
RESULT = Struct(
    "result", [Field("summary", NON_EMPTY_STR), Field("value", Optional(STR)), Field("ci", Optional(List(STR)))]
)
RETRY = Struct("retry_predicate", [Field("kind", NON_EMPTY_STR), Field("target", NON_EMPTY_STR)])
LEDGER_ENTRY = Struct(
    "ledger_entry",
    [
        Field("hypothesis_key", NON_EMPTY_STR),
        Field("decision", NON_EMPTY_STR),
        Field("refutation_kind", Optional(STR)),
        Field("evidence_node", NON_EMPTY_STR),
        Field("method", keys.METHOD_IDENTITY),
        Field("measured_points", List(POINT)),
        Field("result", Optional(RESULT)),
        Field("retry_predicate", Optional(RETRY)),
        Field("caught_by", NON_EMPTY_STR),
        Field("blocker", Optional(STR)),
        Field("faulting_revision", Optional(STR)),
        Field("at", NON_EMPTY_STR),
    ],
)


class LedgerError(SubstrateError):
    pass


class RetryPredicateNotYours(LedgerError):
    pass


def retry_predicate_for(kind, *, hypothesis_key, faulting_revision):
    if kind == IMPLEMENTATION:
        return {"kind": RETRY_NEW_CERTIFIED_REVISION, "target": faulting_revision}
    if kind == MEASURED:
        return {"kind": RETRY_GATE_OWNED_REMEASUREMENT, "target": hypothesis_key}
    return None


def writer_of(caught_by):
    writer, sep, detail = caught_by.partition(":")
    if not sep or not detail or writer not in WRITERS:
        raise LedgerError(f"caught_by {caught_by!r} must read <writer>:<predicate> with writer in {WRITERS}")
    return writer


def _validate(entry):
    if entry.decision not in DECISIONS:
        raise LedgerError(f"decision must be one of {DECISIONS}, got {entry.decision!r}")
    writer = writer_of(entry.caught_by)
    if entry.decision == PARKED:
        if entry.refutation_kind is not None:
            raise LedgerError("a PARKED entry carries no refutation kind")
        if entry.blocker not in BLOCKERS:
            raise LedgerError(f"a PARKED entry carries a typed blocker from {BLOCKERS}, got {entry.blocker!r}")
        if writer != PREFLIGHT:
            raise LedgerError(f"a PARKED entry is the preflight's write, not {writer!r}'s")
        return
    if entry.refutation_kind not in KINDS:
        raise LedgerError(f"refutation_kind must be one of {KINDS}, got {entry.refutation_kind!r}")
    if entry.blocker is not None:
        raise LedgerError("a REFUTED entry holds no blocker")
    if writer == PREFLIGHT:
        raise LedgerError("the preflight parks; it never refutes")
    if writer in SHAPES and entry.refutation_kind not in SHAPES[writer][2]:
        raise LedgerError(f"a {writer} entry is one of {SHAPES[writer][2]}, not {entry.refutation_kind!r}")
    if writer == FORMAL_WRITER and entry.refutation_kind != FORMAL:
        raise LedgerError(f"a formal writer writes a {FORMAL} entry, not {entry.refutation_kind!r}")
    if entry.refutation_kind == MEASURED:
        if not entry.measured_points:
            raise LedgerError("a measured entry carries the parameter points it was measured at")
        if any(
            not isinstance(p, dict) or not (p.get("numeric") or p.get("categorical")) for p in entry.measured_points
        ):
            raise LedgerError("a measured point names at least one numeric or categorical field")
        ci = None if entry.result is None else entry.result.get("ci")
        if not isinstance(ci, (list, tuple)) or len(ci) != 2 or not all(isinstance(c, str) and c for c in ci):
            raise LedgerError("a measured entry carries a result with a two-sided CI")
        try:
            low, high = (Decimal(c) for c in ci)
        except InvalidOperation:
            raise LedgerError("CI bounds are decimal strings") from None
        if low > high:
            raise LedgerError("CI low bound exceeds its high bound")
    if entry.refutation_kind == IMPLEMENTATION and not entry.faulting_revision:
        raise LedgerError("an implementation entry names the faulting revision")
    if entry.refutation_kind != IMPLEMENTATION and entry.faulting_revision is not None:
        raise LedgerError(f"only an implementation entry names a faulting revision, not a {entry.refutation_kind} one")


@dataclass(frozen=True)
class LedgerEntry:
    hypothesis_key: str
    decision: str
    evidence_node: str
    method: dict
    caught_by: str
    at: str
    refutation_kind: str | None = None
    measured_points: tuple = ()
    result: dict | None = None
    blocker: str | None = None
    faulting_revision: str | None = None
    retry_predicate: dict | None = field(init=False, compare=False)
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "measured_points", tuple(self.measured_points))
        _validate(self)
        object.__setattr__(
            self,
            "retry_predicate",
            retry_predicate_for(
                self.refutation_kind, hypothesis_key=self.hypothesis_key, faulting_revision=self.faulting_revision
            ),
        )
        object.__setattr__(self, "hash", keys.node_hash(NODE_KIND, entry_canonical(self)))

    @property
    def writer(self):
        return writer_of(self.caught_by)


def entry_canonical(entry):
    try:
        return canon.encode(
            LEDGER_ENTRY,
            {
                "hypothesis_key": entry.hypothesis_key,
                "decision": entry.decision,
                "refutation_kind": entry.refutation_kind,
                "evidence_node": entry.evidence_node,
                "method": entry.method,
                "measured_points": list(entry.measured_points),
                "result": entry.result,
                "retry_predicate": entry.retry_predicate,
                "caught_by": entry.caught_by,
                "blocker": entry.blocker,
                "faulting_revision": entry.faulting_revision,
                "at": entry.at,
            },
        )
    except canon.CanonError as exc:
        raise LedgerError(f"ledger entry: {exc}") from None


def _check_evidence(entry, node):
    writer = entry.writer
    if writer in SHAPES:
        kind, verdict, _ = SHAPES[writer]
        if node["kind"] != kind or node["verdict"] != verdict:
            raise LedgerError(
                f"a {writer} entry cites a {kind} node with verdict {verdict}, "
                f"not a {node['kind']} node with verdict {node['verdict']!r}"
            )
    elif writer == FORMAL_WRITER:
        if node["kind"] not in FORMAL_EVIDENCE_KINDS or node["verdict"] not in REFUTING_VERDICTS:
            raise LedgerError(
                f"a formal entry cites one of {FORMAL_EVIDENCE_KINDS} carrying no supporting verdict, "
                f"not a {node['kind']} node with verdict {node['verdict']!r}"
            )
    elif node["kind"] not in MEASUREMENT_KINDS:
        raise LedgerError(f"a PARKED entry cites a measurement from {MEASUREMENT_KINDS}, not a {node['kind']} node")


def write(sub, **fields):
    if "retry_predicate" in fields:
        raise RetryPredicateNotYours(
            "the retry predicate is written by the gate that writes the entry, never supplied by its caller"
        )
    try:
        entry = LedgerEntry(**fields)
    except TypeError as exc:
        raise LedgerError(f"ledger entry: {exc}") from None
    return write_entry(sub, entry)


def write_entry(sub, entry):
    node = claims.get_evidence_node(sub, entry.evidence_node)
    if node is None:
        raise LedgerError(f"evidence node {entry.evidence_node} is not in the substrate")
    _check_evidence(entry, node)
    canonical = entry_canonical(entry)
    with sub._tx():
        sub._put_node(NODE_KIND, canonical, entry.hash, "Replayable", entry.writer)
        row = sub.conn.execute(f"SELECT hash FROM {TABLE} WHERE hash = ?", (entry.hash,)).fetchone()
        if row is None:
            sub.conn.execute(
                f"INSERT INTO {TABLE} (hash, hypothesis_key, decision, refutation_kind, evidence_node, method, measured_points, result, retry_predicate, caught_by, blocker, faulting_revision, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry.hash,
                    entry.hypothesis_key,
                    entry.decision,
                    entry.refutation_kind,
                    entry.evidence_node,
                    claims.to_json(entry.method),
                    claims.to_json(entry.measured_points),
                    claims.opt_json(entry.result),
                    claims.opt_json(entry.retry_predicate),
                    entry.caught_by,
                    entry.blocker,
                    entry.faulting_revision,
                    _now(),
                ),
            )
        sub._add_lineage(entry.hash, entry.evidence_node, EDGE_INPUT)
        sub._add_root(ROOT_KIND, entry.hash)
    lg.info(
        "write",
        table=TABLE,
        hash=entry.hash,
        hypothesis_key=entry.hypothesis_key,
        decision=entry.decision,
        refutation_kind=entry.refutation_kind,
        caught_by=entry.caught_by,
        status="inserted" if row is None else "exists",
    )
    return entry.hash


def get_entry(sub, digest):
    row = sub.conn.execute(f"SELECT * FROM {TABLE} WHERE hash = ?", (digest,)).fetchone()
    return None if row is None else dict(row)


def entries_for(sub, hypothesis_key):
    rows = sub.conn.execute(
        f"SELECT * FROM {TABLE} WHERE hypothesis_key = ? ORDER BY rowid", (hypothesis_key,)
    ).fetchall()
    return [dict(r) for r in rows]
