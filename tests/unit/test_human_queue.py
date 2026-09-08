import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import attest, claims, human_queue
from cairn.human_queue import ClosingRuleViolation, Item, QueueError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _substrate_helpers import open_writer

T0 = "2026-09-02T00:00:00+00:00"
T1 = "2026-09-02T00:01:00+00:00"
T2 = "2026-09-02T00:02:00+00:00"
NOW = "2026-09-02T00:10:00+00:00"
RUNG = "rung-60-1"
BRANCH = "branch-7"
STATEMENT_HASH = "ab" * 32


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def attest_path(tmp_path, clear_flags):
    path = tmp_path / "attestations.log"
    clear_flags(path)
    attest.init(path, "f" * 64)
    return path


def _append_waiver(path, target="t"):
    canonical = attest.waiver_canonical(attest.fixture_waiver(target))
    return attest.append_record(path, canonical), attest.blob_hash(canonical)


def test_the_fifteen_classes_and_which_hold_a_blocker():
    assert human_queue.CLASSES == (
        "statement_review",
        "nogo_review",
        "waiver_request",
        "yank_ruling",
        "revision_admission",
        "expert_signoff",
        "disagreement",
        "near_dup_review",
        "supersedes_refuted_review",
        "null_control_pending",
        "clock_inconclusive",
        "shape_departure",
        "leaked",
        "cost_drift",
        "audit_shortfall",
    )
    assert human_queue.NO_BLOCKER_CLASSES == (
        "leaked",
        "clock_inconclusive",
        "shape_departure",
        "cost_drift",
        "audit_shortfall",
    )
    assert len(human_queue.BLOCKER_CLASSES) == 10
    assert set(human_queue.BLOCKERS) == {*human_queue.BLOCKER_CLASSES, "already_settled"}


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"item_class": "vibes", "target_kind": "rung", "target": RUNG}, "class must be one of"),
        ({"item_class": "leaked", "target_kind": "planet", "target": RUNG}, "target_kind must be one of"),
        ({"item_class": "leaked", "target_kind": "rung", "target": RUNG, "blocker": "leaked"}, "holds no blocker"),
        (
            {"item_class": "statement_review", "target_kind": "statement", "target": STATEMENT_HASH},
            "holds a blocker from",
        ),
        (
            {"item_class": "statement_review", "target_kind": "statement", "target": STATEMENT_HASH, "blocker": "mood"},
            "holds a blocker from",
        ),
        ({"item_class": "leaked", "target_kind": "rung", "target": ""}, "must not be empty"),
    ],
)
def test_an_item_outside_the_type_is_refused(fields, message):
    with pytest.raises(QueueError, match=message):
        Item(enqueued_at=T0, **fields)


def test_enqueue_writes_a_node_and_a_row_once(writer, db_snapshot):
    item = Item("statement_review", "statement", STATEMENT_HASH, T0, blocker="statement_review")
    item_id = human_queue.enqueue(writer, item)
    counts = db_snapshot(writer.conn, "enqueued")
    assert human_queue.enqueue(writer, item) == item_id
    assert db_snapshot(writer.conn, "again") == counts
    row = human_queue.get_item(writer, item_id)
    assert row == {
        "item_id": item.hash,
        "class": "statement_review",
        "target_kind": "statement",
        "target": STATEMENT_HASH,
        "blocker": "statement_review",
        "enqueued_at": T0,
    }
    assert writer.get_node(item_id)["kind"] == "human_queue_item"


def test_the_producer_apis_fix_class_and_target_kind(writer):
    clock = human_queue.enqueue_clock_inconclusive(writer, RUNG, at=T0)
    shape = human_queue.enqueue_shape_departure(writer, RUNG, at=T1)
    drift = human_queue.enqueue_cost_drift(writer, BRANCH, at=T2)
    rows = [human_queue.get_item(writer, i) for i in (clock, shape, drift)]
    assert [(r["class"], r["target_kind"], r["target"], r["blocker"]) for r in rows] == [
        ("clock_inconclusive", "rung", RUNG, None),
        ("shape_departure", "rung", RUNG, None),
        ("cost_drift", "branch", BRANCH, None),
    ]


def test_an_item_holding_a_blocker_closes_by_its_clearing_and_by_nothing_looser(writer, attest_path):
    item_id = human_queue.enqueue(
        writer, Item("null_control_pending", "branch", BRANCH, T0, blocker="null_control_pending")
    )
    with pytest.raises(ClosingRuleViolation, match="holds blocker null_control_pending"):
        human_queue.close_by_terminal_status(writer, item_id, attest_path=attest_path, status="withdrawn", ref="x")
    with pytest.raises(ClosingRuleViolation, match="an acknowledgment closes only an item holding none"):
        human_queue.acknowledgable(writer, item_id, attest_path)
    assert human_queue.depth(writer, attest_path) == 1
    human_queue.close_by_blocker_clear(writer, item_id, attest_path=attest_path, cleared_by="ladder:remeasured", at=T1)
    closure = human_queue.visible_closure(writer, item_id, attest_path)
    assert (closure["path"], closure["ref"], closure["closed_at"]) == ("blocker_cleared", "ladder:remeasured", T1)
    assert human_queue.depth(writer, attest_path) == 0
    with pytest.raises(ClosingRuleViolation, match="closed by blocker_cleared"):
        human_queue.close_by_blocker_clear(writer, item_id, attest_path=attest_path, cleared_by="again")


def test_an_item_holding_no_blocker_never_closes_by_a_blocker_clear(writer, attest_path):
    item_id = human_queue.enqueue_clock_inconclusive(writer, RUNG, at=T0)
    with pytest.raises(ClosingRuleViolation, match="holds no blocker to clear"):
        human_queue.close_by_blocker_clear(writer, item_id, attest_path=attest_path, cleared_by="x")
    seq = human_queue.close_by_terminal_status(
        writer, item_id, attest_path=attest_path, status="re-ran", ref="rung-60-2"
    )
    assert human_queue.visible_closure(writer, item_id, attest_path)["ref"] == "re-ran:rung-60-2"
    assert seq == 1


def test_a_statement_target_closes_by_terminal_status_only_once_the_statement_is_terminal(writer, attest_path):
    statement = factories.claim_statement(seed=2)
    claims.write_claim_statement(writer, statement)
    item_id = human_queue.enqueue(writer, Item("leaked", "statement", statement.hash, T0))
    with pytest.raises(ClosingRuleViolation, match="stands at 'open', not a terminal status"):
        human_queue.close_by_terminal_status(writer, item_id, attest_path=attest_path, status="refuted", ref="x")
    unknown = human_queue.enqueue(writer, Item("leaked", "statement", "cd" * 32, T1))
    with pytest.raises(ClosingRuleViolation, match="stands at None"):
        human_queue.close_by_terminal_status(writer, unknown, attest_path=attest_path, status="refuted", ref="x")
    claims.transition_status(writer, statement.hash, "refuted")
    human_queue.close_by_terminal_status(writer, item_id, attest_path=attest_path, status="ignored", ref="justify")
    assert human_queue.visible_closure(writer, item_id, attest_path)["ref"] == "refuted:justify"


def test_any_item_closes_by_a_human_path_record_that_the_file_holds(writer, attest_path):
    blocked = human_queue.enqueue(writer, Item("waiver_request", "branch", BRANCH, T0, blocker="waiver_request"))
    free = human_queue.enqueue_cost_drift(writer, BRANCH, at=T1)
    offset, digest = _append_waiver(attest_path)
    with pytest.raises(ClosingRuleViolation, match="holds no record at offset"):
        human_queue.close_by_attestation(
            writer, blocked, attest_path=attest_path, file_offset=offset + 1, record_digest=digest
        )
    with pytest.raises(ClosingRuleViolation, match="holds no record at offset"):
        human_queue.close_by_attestation(
            writer, blocked, attest_path=attest_path, file_offset=offset, record_digest="00" * 32
        )
    for item_id in (blocked, free):
        human_queue.close_by_attestation(
            writer, item_id, attest_path=attest_path, file_offset=offset, record_digest=digest
        )
        closure = human_queue.visible_closure(writer, item_id, attest_path)
        assert (closure["path"], closure["record_digest"], closure["file_offset"]) == ("attestation", digest, offset)
    assert human_queue.depth(writer, attest_path) == 0


def test_an_unknown_item_closes_by_nothing(writer, attest_path):
    for close in (
        lambda: human_queue.close_by_blocker_clear(writer, "nope", attest_path=attest_path, cleared_by="x"),
        lambda: human_queue.close_by_terminal_status(writer, "nope", attest_path=attest_path, status="s", ref="x"),
        lambda: human_queue.close_by_attestation(
            writer, "nope", attest_path=attest_path, file_offset=0, record_digest="0"
        ),
        lambda: human_queue.acknowledgable(writer, "nope", attest_path),
    ):
        with pytest.raises(QueueError, match="no human queue item nope"):
            close()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE human_queue_items SET blocker = NULL WHERE item_id = :item",
        "UPDATE human_queue_items SET class = 'leaked', blocker = NULL WHERE item_id = :item",
        "UPDATE human_queue_items SET enqueued_at = '2030-01-01T00:00:00+00:00' WHERE item_id = :item",
        "DELETE FROM human_queue_items WHERE item_id = :item",
    ],
)
def test_a_direct_write_to_an_open_item_is_refused(writer, attest_path, statement):
    item = human_queue.enqueue(writer, Item("yank_ruling", "branch", BRANCH, T0, blocker="yank_ruling"))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute(statement, {"item": item})
    assert human_queue.get_item(writer, item)["blocker"] == "yank_ruling"
    assert human_queue.depth(writer, attest_path) == 1


@pytest.mark.parametrize(
    ("item_fields", "closure", "message"),
    [
        (("clock_inconclusive", "rung", RUNG, None), ("blocker_cleared", "x", None, None), "closing rule"),
        (
            ("disagreement", "statement", STATEMENT_HASH, "disagreement"),
            ("terminal_status", "x", None, None),
            "closing rule",
        ),
        (
            ("disagreement", "statement", STATEMENT_HASH, "disagreement"),
            ("acknowledgment", "x", "00" * 32, 0),
            "closing rule",
        ),
        (("leaked", "statement", STATEMENT_HASH, None), ("terminal_status", "x", None, None), "closing rule"),
        (("leaked", "rung", RUNG, None), ("attestation", "x", None, None), "CHECK"),
        (("leaked", "rung", RUNG, None), ("acknowledgment", "x", "00" * 32, None), "CHECK"),
        (
            ("disagreement", "statement", STATEMENT_HASH, "disagreement"),
            ("blocker_cleared", "x", None, None),
            "blocker clearing rule",
        ),
        (
            ("null_control_pending", "branch", BRANCH, "null_control_pending"),
            ("blocker_cleared", "x", "00" * 32, 0),
            "blocker clearing rule",
        ),
        (
            ("disagreement", "statement", STATEMENT_HASH, "disagreement"),
            ("blocker_cleared", "x", "00" * 32, None),
            "CHECK",
        ),
        (("leaked", "rung", RUNG, None), ("vanished", "x", None, None), "CHECK"),
    ],
)
def test_the_schema_refuses_a_closure_row_outside_the_rule(writer, attest_path, item_fields, closure, message):
    item_class, target_kind, target, blocker = item_fields
    item = human_queue.enqueue(writer, Item(item_class, target_kind, target, T0, blocker=blocker))
    path, ref, digest, offset = closure
    with pytest.raises(sqlite3.IntegrityError, match=message):
        writer.conn.execute(
            "INSERT INTO human_queue_closures (item_id, path, ref, record_digest, file_offset, closed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (item, path, ref, digest, offset, T1),
        )
    assert human_queue.depth(writer, attest_path) == 1


def test_a_closure_naming_no_item_is_refused(writer):
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        writer.conn.execute(
            "INSERT INTO human_queue_closures (item_id, path, ref, record_digest, file_offset, closed_at) VALUES ('ghost', 'attestation', 'x', ?, 0, ?)",
            ("00" * 32, T1),
        )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE human_queue_closures SET path = 'blocker_cleared', record_digest = NULL, file_offset = NULL WHERE item_id = :item",
        "UPDATE human_queue_closures SET closed_at = '1999-01-01T00:00:00+00:00' WHERE item_id = :item",
        "DELETE FROM human_queue_closures WHERE item_id = :item",
    ],
)
def test_a_recorded_closure_is_append_only(writer, attest_path, statement):
    item = human_queue.enqueue_cost_drift(writer, BRANCH, at=T0)
    human_queue.close_by_terminal_status(writer, item, attest_path=attest_path, status="terminal", ref="x", at=T1)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute(statement, {"item": item})
    assert human_queue.visible_closure(writer, item, attest_path)["closed_at"] == T1


def test_a_forged_human_path_closure_leaves_the_item_open(writer, attest_path):
    item = human_queue.enqueue_cost_drift(writer, BRANCH, at=T0)
    writer.conn.execute(
        "INSERT INTO human_queue_closures (item_id, path, ref, record_digest, file_offset, closed_at) VALUES (?, 'acknowledgment', 'x', ?, 0, ?)",
        (item, "00" * 32, T1),
    )
    assert human_queue.closures_of(writer, item) != []
    assert human_queue.visible_closure(writer, item, attest_path) is None
    assert human_queue.depth(writer, attest_path) == 1
    offset, digest = _append_waiver(attest_path)
    human_queue.close_by_attestation(writer, item, attest_path=attest_path, file_offset=offset, record_digest=digest)
    assert human_queue.visible_closure(writer, item, attest_path)["path"] == "attestation"
    assert human_queue.depth(writer, attest_path) == 0


def test_an_acknowledgment_closure_binds_to_the_record_naming_its_item(writer, attest_path):
    first = human_queue.enqueue_cost_drift(writer, BRANCH, at=T0)
    second = human_queue.enqueue_clock_inconclusive(writer, RUNG, at=T1)
    third = human_queue.enqueue_shape_departure(writer, RUNG, at=T2)
    ack = human_queue.acknowledgment_from({"item_id": first, "issued_by": "op", "at": T1, "note": ""})
    offset = attest.append_record(attest_path, human_queue.acknowledgment_canonical(ack))
    human_queue.write_acknowledgment(writer, ack, attest_path=attest_path, file_offset=offset)
    digest = human_queue.acknowledgment_digest(ack)
    waiver_digest = attest.blob_hash(attest.read_record(attest_path, 0))
    closure = "INSERT INTO human_queue_closures (item_id, path, ref, record_digest, file_offset, closed_at) VALUES (?, 'acknowledgment', ?, ?, ?, ?)"
    writer.conn.execute(closure, (second, digest, digest, offset, T2))
    writer.conn.execute(closure, (third, waiver_digest, waiver_digest, 0, T2))
    writer.conn.execute(
        "INSERT INTO acknowledgments (item_id, issued_by, at, note, record_digest, file_offset) VALUES (?, 'op', ?, '', ?, ?)",
        (second, T1, digest, offset),
    )
    assert human_queue.visible_closure(writer, first, attest_path)["path"] == "acknowledgment"
    assert human_queue.visible_closure(writer, second, attest_path) is None
    assert human_queue.visible_closure(writer, third, attest_path) is None
    assert human_queue.visible_acknowledgments(writer, second, attest_path) == []
    assert [r["item_id"] for r in human_queue.visible_acknowledgments(writer, first, attest_path)] == [first]
    assert human_queue.depth(writer, attest_path) == 2


def test_an_attestation_closure_binds_a_statement_item_to_a_verdict_on_its_statement(writer, attest_path):
    statement, other = factories.claim_statement(seed=6), factories.claim_statement(seed=7)
    claims.write_claim_statement(writer, statement)
    claims.write_claim_statement(writer, other)
    item = human_queue.enqueue(
        writer, Item("statement_review", "statement", statement.hash, T0, blocker="statement_review")
    )
    waiver_digest = attest.blob_hash(attest.read_record(attest_path, 0))
    with pytest.raises(ClosingRuleViolation, match="record 0 is the gate plan's fixture waiver"):
        human_queue.close_by_attestation(
            writer, item, attest_path=attest_path, file_offset=0, record_digest=waiver_digest
        )
    offset, digest = _append_waiver(attest_path)
    with pytest.raises(ClosingRuleViolation, match=f"no review verdict on statement {statement.hash}"):
        human_queue.close_by_attestation(
            writer, item, attest_path=attest_path, file_offset=offset, record_digest=digest
        )

    def mirrored_verdict(target, seed):
        verdict = factories.review_verdict(target, seed=seed, file_offset=attest_path.stat().st_size)
        assert attest.append_record(attest_path, claims.review_verdict_canonical(verdict)) == verdict.file_offset
        claims.write_review_verdict(writer, verdict)
        return verdict

    elsewhere = mirrored_verdict(other.hash, 1)
    with pytest.raises(ClosingRuleViolation, match="no review verdict on statement"):
        human_queue.close_by_attestation(
            writer,
            item,
            attest_path=attest_path,
            file_offset=elsewhere.file_offset,
            record_digest=elsewhere.record_digest,
        )
    here = mirrored_verdict(statement.hash, 2)
    human_queue.close_by_attestation(
        writer, item, attest_path=attest_path, file_offset=here.file_offset, record_digest=here.record_digest
    )
    assert human_queue.visible_closure(writer, item, attest_path)["record_digest"] == here.record_digest
    branch_item = human_queue.enqueue_cost_drift(writer, BRANCH, at=T1)
    writer.conn.execute(
        "INSERT INTO human_queue_closures (item_id, path, ref, record_digest, file_offset, closed_at) VALUES (?, 'attestation', ?, ?, 0, ?)",
        (branch_item, waiver_digest, waiver_digest, T2),
    )
    assert human_queue.visible_closure(writer, branch_item, attest_path) is None
    assert human_queue.depth(writer, attest_path) == 1


def test_depth_and_age_fall_only_through_a_lawful_close(writer, attest_path):
    first = human_queue.enqueue_clock_inconclusive(writer, RUNG, at=T0)
    second = human_queue.enqueue(writer, Item("near_dup_review", "branch", BRANCH, T1, blocker="near_dup_review"))
    third = human_queue.enqueue_cost_drift(writer, BRANCH, at=T2)
    trace = []

    def observe(step):
        ages = human_queue.ages(writer, attest_path, now=NOW)
        trace.append((step, human_queue.depth(writer, attest_path), max(ages.values(), default=0.0)))

    observe("enqueued")
    with pytest.raises(sqlite3.IntegrityError):
        writer.conn.execute("UPDATE human_queue_items SET enqueued_at = ? WHERE item_id = ?", (NOW, first))
    observe("update-refused")
    with pytest.raises(sqlite3.IntegrityError):
        writer.conn.execute("DELETE FROM human_queue_items WHERE item_id = ?", (first,))
    observe("delete-refused")
    writer.conn.execute(
        "INSERT INTO human_queue_closures (item_id, path, ref, record_digest, file_offset, closed_at) VALUES (?, 'attestation', 'x', ?, 0, ?)",
        (first, "00" * 32, NOW),
    )
    observe("forged-closure")
    with pytest.raises(sqlite3.IntegrityError):
        writer.conn.execute(
            "INSERT INTO human_queue_closures (item_id, path, ref, record_digest, file_offset, closed_at) VALUES (?, 'terminal_status', 'x', NULL, NULL, ?)",
            (second, NOW),
        )
    observe("out-of-rule-closure-refused")
    human_queue.close_by_terminal_status(
        writer, first, attest_path=attest_path, status="re-ran", ref="rung-60-2", at=NOW
    )
    observe("first-closed-lawfully")
    offset, digest = _append_waiver(attest_path)
    human_queue.close_by_blocker_clear(
        writer,
        second,
        attest_path=attest_path,
        cleared_by="librarian",
        record_digest=digest,
        file_offset=offset,
        at=NOW,
    )
    observe("second-closed-lawfully")
    assert trace == [
        ("enqueued", 3, 600.0),
        ("update-refused", 3, 600.0),
        ("delete-refused", 3, 600.0),
        ("forged-closure", 3, 600.0),
        ("out-of-rule-closure-refused", 3, 600.0),
        ("first-closed-lawfully", 2, 540.0),
        ("second-closed-lawfully", 1, 480.0),
    ]
    assert [row["item_id"] for row in human_queue.open_items(writer, attest_path)] == [third]


def test_an_acknowledgment_closes_only_an_open_item_holding_no_blocker_and_only_once(writer, attest_path):
    free = human_queue.enqueue_cost_drift(writer, BRANCH, at=T0)
    blocked = human_queue.enqueue(writer, Item("expert_signoff", "branch", BRANCH, T0, blocker="expert_signoff"))

    def filed(item_id):
        ack = human_queue.acknowledgment_from({"item_id": item_id, "issued_by": "op", "at": T1, "note": ""})
        return ack, attest.append_record(attest_path, human_queue.acknowledgment_canonical(ack))

    ack, offset = filed(blocked)
    with pytest.raises(ClosingRuleViolation, match="holds blocker expert_signoff"):
        human_queue.write_acknowledgment(writer, ack, attest_path=attest_path, file_offset=offset)
    ack, offset = filed(free)
    assert human_queue.write_acknowledgment(writer, ack, attest_path=attest_path, file_offset=offset) == 1
    again, later = filed(free)
    with pytest.raises(ClosingRuleViolation, match="closed by acknowledgment"):
        human_queue.write_acknowledgment(writer, again, attest_path=attest_path, file_offset=later)
    assert len(human_queue.closures_of(writer, free)) == 1
    assert human_queue.acknowledgments_for(writer, free)[0]["file_offset"] == offset
    assert human_queue.depth(writer, attest_path) == 1


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"item_id": "i", "issued_by": "op", "at": T0}, "missing note"),
        ({"item_id": "i", "issued_by": "op", "at": T0, "note": "", "mood": "fine"}, "carries no field mood"),
    ],
)
def test_an_acknowledgment_record_carries_exactly_its_fields(fields, message):
    with pytest.raises(QueueError, match=message):
        human_queue.acknowledgment_from(fields)


def test_an_acknowledgment_canonical_is_typed(writer):
    ack = human_queue.acknowledgment_from({"item_id": "i", "issued_by": "op", "at": T0, "note": ""})
    assert ack["kind"] == "acknowledgment"
    assert human_queue.acknowledgment_digest(ack) == attest.blob_hash(human_queue.acknowledgment_canonical(ack))
    with pytest.raises(QueueError, match="must not be empty"):
        human_queue.acknowledgment_canonical({**ack, "issued_by": ""})
