"""The human queue as a typed substrate object: fifteen classes, a blocker or none, one closing rule.

An item is an append-only row and a node; closing it is a recorded event in a second table, never
a rewrite. The four closing paths are the only ones: a human-path record whose digest names the
bytes at its offset in the attestation file, the blocker clearing, the target reaching a terminal
status for an item that holds no blocker, or an acknowledgment record through the human path
naming the item. A closure row on a human path is visible only while the attestation file holds
its bytes, the same absent-unless-digest-matches rule review verdicts live under, and an
acknowledgment closure is visible only through an acknowledgment row whose re-derived digest names
that item. Record 0 of the attestation file is the gate plan's fixture waiver and closes nothing.
The terminal-status path verifies a statement target against claim_statements; for a branch, rung
or audit-cycle target, and for a blocker clearing, the calling gate's word is recorded as given,
because those objects have no status table before M3.
"""

from dataclasses import dataclass, field
from datetime import datetime

from cairn import attest, canon, claims, keys, log
from cairn.canon import NON_EMPTY_STR, STR, Field, Optional, Struct
from cairn.substrate import SubstrateError, _now, blob_hash

lg = log.get("human_queue")

STATEMENT_REVIEW = "statement_review"
NOGO_REVIEW = "nogo_review"
WAIVER_REQUEST = "waiver_request"
YANK_RULING = "yank_ruling"
REVISION_ADMISSION = "revision_admission"
EXPERT_SIGNOFF = "expert_signoff"
DISAGREEMENT = "disagreement"
NEAR_DUP_REVIEW = "near_dup_review"
SUPERSEDES_REFUTED_REVIEW = "supersedes_refuted_review"
NULL_CONTROL_PENDING = "null_control_pending"
CLOCK_INCONCLUSIVE = "clock_inconclusive"
SHAPE_DEPARTURE = "shape_departure"
LEAKED = "leaked"
COST_DRIFT = "cost_drift"
AUDIT_SHORTFALL = "audit_shortfall"
CLASSES = (
    STATEMENT_REVIEW,
    NOGO_REVIEW,
    WAIVER_REQUEST,
    YANK_RULING,
    REVISION_ADMISSION,
    EXPERT_SIGNOFF,
    DISAGREEMENT,
    NEAR_DUP_REVIEW,
    SUPERSEDES_REFUTED_REVIEW,
    NULL_CONTROL_PENDING,
    CLOCK_INCONCLUSIVE,
    SHAPE_DEPARTURE,
    LEAKED,
    COST_DRIFT,
    AUDIT_SHORTFALL,
)
NO_BLOCKER_CLASSES = (LEAKED, CLOCK_INCONCLUSIVE, SHAPE_DEPARTURE, COST_DRIFT, AUDIT_SHORTFALL)
BLOCKER_CLASSES = tuple(c for c in CLASSES if c not in NO_BLOCKER_CLASSES)
BLOCKERS = (*BLOCKER_CLASSES, "already_settled")
STATEMENT = "statement"
BRANCH = "branch"
RUNG = "rung"
AUDIT_CYCLE = "audit_cycle"
TARGET_KINDS = (STATEMENT, BRANCH, RUNG, AUDIT_CYCLE)
PATH_ATTESTATION = "attestation"
PATH_BLOCKER_CLEARED = "blocker_cleared"
PATH_TERMINAL_STATUS = "terminal_status"
PATH_ACKNOWLEDGMENT = "acknowledgment"
PATHS = (PATH_ATTESTATION, PATH_BLOCKER_CLEARED, PATH_TERMINAL_STATUS, PATH_ACKNOWLEDGMENT)
HUMAN_PATHS = (PATH_ATTESTATION, PATH_ACKNOWLEDGMENT)
ITEM_KIND = "human_queue_item"
ACK_KIND = "acknowledgment"
ACK_RECORD_FIELDS = ("item_id", "issued_by", "at", "note")
ITEMS = "human_queue_items"
CLOSURES = "human_queue_closures"
ACKS = "acknowledgments"
FIXTURE_WAIVER_OFFSET = 0

ITEM = Struct(
    ITEM_KIND,
    [
        Field("item_class", NON_EMPTY_STR),
        Field("target_kind", NON_EMPTY_STR),
        Field("target", NON_EMPTY_STR),
        Field("blocker", Optional(STR)),
        Field("enqueued_at", NON_EMPTY_STR),
    ],
)
ACKNOWLEDGMENT = Struct(
    ACK_KIND,
    [
        Field("kind", NON_EMPTY_STR),
        Field("item_id", NON_EMPTY_STR),
        Field("issued_by", NON_EMPTY_STR),
        Field("at", NON_EMPTY_STR),
        Field("note", STR),
    ],
)


class QueueError(SubstrateError):
    pass


class ClosingRuleViolation(QueueError):
    pass


@dataclass(frozen=True)
class Item:
    item_class: str
    target_kind: str
    target: str
    enqueued_at: str
    blocker: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        if self.item_class not in CLASSES:
            raise QueueError(f"class must be one of {CLASSES}, got {self.item_class!r}")
        if self.target_kind not in TARGET_KINDS:
            raise QueueError(f"target_kind must be one of {TARGET_KINDS}, got {self.target_kind!r}")
        if self.item_class in NO_BLOCKER_CLASSES:
            if self.blocker is not None:
                raise QueueError(f"a {self.item_class} item holds no blocker, got {self.blocker!r}")
        elif self.blocker not in BLOCKERS:
            raise QueueError(f"a {self.item_class} item holds a blocker from {BLOCKERS}, got {self.blocker!r}")
        object.__setattr__(self, "hash", keys.node_hash(ITEM_KIND, item_canonical(self)))

    @property
    def holds_blocker(self):
        return self.blocker is not None


def item_canonical(item):
    try:
        return canon.encode(
            ITEM,
            {
                "item_class": item.item_class,
                "target_kind": item.target_kind,
                "target": item.target,
                "blocker": item.blocker,
                "enqueued_at": item.enqueued_at,
            },
        )
    except canon.CanonError as exc:
        raise QueueError(f"human queue item: {exc}") from None


def enqueue(sub, item):
    canonical = item_canonical(item)
    with sub._tx():
        sub._put_node(ITEM_KIND, canonical, item.hash, "Replayable", None)
        row = sub.conn.execute(f"SELECT item_id FROM {ITEMS} WHERE item_id = ?", (item.hash,)).fetchone()
        if row is None:
            sub.conn.execute(
                f"INSERT INTO {ITEMS} (item_id, class, target_kind, target, blocker, enqueued_at) VALUES (?, ?, ?, ?, ?, ?)",
                (item.hash, item.item_class, item.target_kind, item.target, item.blocker, item.enqueued_at),
            )
    lg.info(
        "enqueue",
        item_id=item.hash,
        item_class=item.item_class,
        target_kind=item.target_kind,
        target=item.target,
        blocker=item.blocker,
        status="inserted" if row is None else "exists",
    )
    return item.hash


def enqueue_clock_inconclusive(sub, rung, *, at=None):
    return enqueue(sub, Item(CLOCK_INCONCLUSIVE, RUNG, rung, at or _now()))


def enqueue_shape_departure(sub, rung, *, at=None):
    return enqueue(sub, Item(SHAPE_DEPARTURE, RUNG, rung, at or _now()))


def enqueue_cost_drift(sub, branch, *, at=None):
    return enqueue(sub, Item(COST_DRIFT, BRANCH, branch, at or _now()))


def get_item(sub, item_id):
    row = sub.conn.execute(f"SELECT * FROM {ITEMS} WHERE item_id = ?", (item_id,)).fetchone()
    return None if row is None else dict(row)


def closures_of(sub, item_id):
    rows = sub.conn.execute(f"SELECT * FROM {CLOSURES} WHERE item_id = ? ORDER BY seq", (item_id,)).fetchall()
    return [dict(r) for r in rows]


def _ack_of(row):
    return {"kind": ACK_KIND, **{name: row[name] for name in ACK_RECORD_FIELDS}}


def _acknowledgment_row_matches(sub, row):
    rows = sub.conn.execute(
        f"SELECT * FROM {ACKS} WHERE item_id = ? AND record_digest = ? AND file_offset = ?",
        (row["item_id"], row["record_digest"], row["file_offset"]),
    ).fetchall()
    return any(acknowledgment_digest(_ack_of(ack)) == row["record_digest"] for ack in rows)


def _attestation_binding(sub, item, record_digest, file_offset):
    if file_offset == FIXTURE_WAIVER_OFFSET:
        return f"record {FIXTURE_WAIVER_OFFSET} is the gate plan's fixture waiver, never an operator's act"
    if item["target_kind"] == STATEMENT and not any(
        v["record_digest"] == record_digest and v["file_offset"] == file_offset
        for v in claims.review_verdicts_for(sub, item["target"])
    ):
        return f"no review verdict on statement {item['target']} is mirrored at offset {file_offset} with digest {record_digest}"
    if item["class"] == NOGO_REVIEW:
        from cairn import nogo

        if not nogo.mirrored(sub, item["target"], record_digest, file_offset):
            return f"no nogo_review on branch {item['target']} is mirrored at offset {file_offset} with digest {record_digest}"
    return None


def closure_visible(sub, item, row, attest_path):
    if row["path"] not in HUMAN_PATHS:
        return True
    if row["path"] == PATH_ACKNOWLEDGMENT and not _acknowledgment_row_matches(sub, row):
        return False
    if row["path"] == PATH_ATTESTATION and _attestation_binding(sub, item, row["record_digest"], row["file_offset"]):
        return False
    return attest.attestation_record_matches(attest_path, row["file_offset"], row["record_digest"])


def visible_closure(sub, item_id, attest_path):
    item = get_item(sub, item_id)
    if item is None:
        return None
    for row in closures_of(sub, item_id):
        if closure_visible(sub, item, row, attest_path):
            return row
    return None


def _require_open(sub, item_id, attest_path):
    item = get_item(sub, item_id)
    if item is None:
        raise QueueError(f"no human queue item {item_id}")
    closure = visible_closure(sub, item_id, attest_path)
    if closure is not None:
        raise ClosingRuleViolation(f"item {item_id} closed by {closure['path']} at {closure['closed_at']}")
    return item


def _record_closure(sub, item_id, path, *, ref, record_digest=None, file_offset=None, at=None):
    closed_at = at or _now()
    with sub._tx():
        cur = sub.conn.execute(
            f"INSERT INTO {CLOSURES} (item_id, path, ref, record_digest, file_offset, closed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, path, ref, record_digest, file_offset, closed_at),
        )
        seq = cur.lastrowid
    lg.info("close", item_id=item_id, path=path, ref=ref, seq=seq)
    return seq


def close_by_attestation(sub, item_id, *, attest_path, file_offset, record_digest, at=None):
    item = _require_open(sub, item_id, attest_path)
    unbound = _attestation_binding(sub, item, record_digest, file_offset)
    if unbound:
        raise ClosingRuleViolation(unbound)
    if not attest.attestation_record_matches(attest_path, file_offset, record_digest):
        raise ClosingRuleViolation(f"{attest_path} holds no record at offset {file_offset} with digest {record_digest}")
    return _record_closure(
        sub, item_id, PATH_ATTESTATION, ref=record_digest, record_digest=record_digest, file_offset=file_offset, at=at
    )


def close_by_blocker_clear(sub, item_id, *, attest_path, cleared_by, at=None):
    item = _require_open(sub, item_id, attest_path)
    if item["blocker"] is None:
        raise ClosingRuleViolation(f"item {item_id} ({item['class']}) holds no blocker to clear")
    return _record_closure(sub, item_id, PATH_BLOCKER_CLEARED, ref=cleared_by, at=at)


def close_by_terminal_status(sub, item_id, *, attest_path, status, ref, at=None):
    item = _require_open(sub, item_id, attest_path)
    if item["blocker"] is not None:
        raise ClosingRuleViolation(f"item {item_id} holds blocker {item['blocker']}; only its clearing closes it")
    if item["target_kind"] == STATEMENT:
        statement = claims.get_claim_statement(sub, item["target"])
        if statement is None or statement["status"] not in claims.TERMINAL_STATEMENT_STATUSES:
            found = None if statement is None else statement["status"]
            raise ClosingRuleViolation(f"statement {item['target']} stands at {found!r}, not a terminal status")
        status = statement["status"]
    return _record_closure(sub, item_id, PATH_TERMINAL_STATUS, ref=f"{status}:{ref}", at=at)


def acknowledgment_from(fields):
    unknown = sorted(set(fields) - set(ACK_RECORD_FIELDS))
    if unknown:
        raise QueueError(f"an acknowledgment record carries no field {', '.join(unknown)}")
    missing = sorted(f for f in ACK_RECORD_FIELDS if f not in fields)
    if missing:
        raise QueueError(f"an acknowledgment record is missing {', '.join(missing)}")
    return {"kind": ACK_KIND, **{name: str(fields[name]) for name in ACK_RECORD_FIELDS}}


def acknowledgment_canonical(ack):
    try:
        return canon.encode(ACKNOWLEDGMENT, ack)
    except canon.CanonError as exc:
        raise QueueError(f"acknowledgment: {exc}") from None


def acknowledgment_digest(ack):
    return blob_hash(acknowledgment_canonical(ack))


def acknowledgable(sub, item_id, attest_path):
    item = _require_open(sub, item_id, attest_path)
    if item["blocker"] is not None:
        raise ClosingRuleViolation(
            f"item {item_id} holds blocker {item['blocker']}; an acknowledgment closes only an item holding none"
        )
    return item


def write_acknowledgment(sub, ack, *, attest_path, file_offset, at=None):
    ack = acknowledgment_from({k: v for k, v in ack.items() if k != "kind"})
    acknowledgable(sub, ack["item_id"], attest_path)
    canonical = acknowledgment_canonical(ack)
    digest = blob_hash(canonical)
    if not attest.attestation_record_matches(attest_path, file_offset, digest):
        raise ClosingRuleViolation(
            f"{attest_path} holds no acknowledgment at offset {file_offset} with digest {digest}"
        )
    node_hash = keys.node_hash(ACK_KIND, canonical)
    with sub._tx():
        sub._put_node(ACK_KIND, canonical, node_hash, "Replayable", ack["issued_by"])
        cur = sub.conn.execute(
            f"INSERT INTO {ACKS} (item_id, issued_by, at, note, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?)",
            (ack["item_id"], ack["issued_by"], ack["at"], ack["note"], digest, file_offset),
        )
        row_id = cur.lastrowid
        sub.conn.execute(
            f"INSERT INTO {CLOSURES} (item_id, path, ref, record_digest, file_offset, closed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ack["item_id"], PATH_ACKNOWLEDGMENT, digest, digest, file_offset, at or _now()),
        )
    lg.info("acknowledge", item_id=ack["item_id"], issued_by=ack["issued_by"], row_id=row_id, offset=file_offset)
    return row_id


def acknowledgments_for(sub, item_id):
    rows = sub.conn.execute(f"SELECT * FROM {ACKS} WHERE item_id = ? ORDER BY row_id", (item_id,)).fetchall()
    return [dict(r) for r in rows]


def visible_acknowledgments(sub, item_id, attest_path):
    return [
        row
        for row in acknowledgments_for(sub, item_id)
        if acknowledgment_digest(_ack_of(row)) == row["record_digest"]
        and attest.attestation_record_matches(attest_path, row["file_offset"], row["record_digest"])
    ]


def open_items(sub, attest_path):
    rows = sub.conn.execute(f"SELECT * FROM {ITEMS} ORDER BY enqueued_at, rowid").fetchall()
    return [dict(r) for r in rows if visible_closure(sub, r["item_id"], attest_path) is None]


def depth(sub, attest_path):
    return len(open_items(sub, attest_path))


def ages(sub, attest_path, *, now=None):
    moment = datetime.fromisoformat(now or _now())
    return {
        row["item_id"]: (moment - datetime.fromisoformat(row["enqueued_at"])).total_seconds()
        for row in open_items(sub, attest_path)
    }
