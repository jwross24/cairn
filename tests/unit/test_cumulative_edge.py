import contextlib
import sqlite3
from types import SimpleNamespace

import pytest

from cairn import keycharge, substrate, tiergate

KEY = "ab" * 32
OTHER_KEY = "cd" * 32
RECEIPT_HASH = "ee" * 32


class MemorySub:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(substrate.schema_text())

    @contextlib.contextmanager
    def _tx(self):
        with self.conn:
            yield

    def get_attempt(self, attempt_id):
        row = self.conn.execute("SELECT * FROM attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
        return None if row is None else dict(row)

    def get_receipt(self, digest):
        row = self.conn.execute("SELECT * FROM receipts WHERE receipt_hash = ?", (digest,)).fetchone()
        return None if row is None else dict(row)

    def attempt_with_receipt(self, attempt_id, *, cpu_user_s, cpu_sys_s, receipt_hash=RECEIPT_HASH, wall_s=99.0):
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO receipts VALUES (?, ?, 0, 1, ?, ?, ?, 0, 0, 0, ?, ?, ?, 'tree')",
                (receipt_hash, "aa" * 32, cpu_user_s, cpu_sys_s, wall_s, "bb" * 32, "bb" * 32, "bb" * 32),
            )
            self.conn.execute(
                "INSERT INTO attempts (attempt_id, recipe_key, receipt_hash, status, replay_grade, started_at, ended_at)"
                " VALUES (?, ?, ?, 'OK', 'Replayable', 't0', 't1')",
                (attempt_id, "dd" * 32, receipt_hash),
            )

    def attempt_without_receipt(self, attempt_id):
        with self.conn:
            self.conn.execute(
                "INSERT INTO attempts (attempt_id, recipe_key, status, replay_grade, started_at, ended_at)"
                " VALUES (?, ?, 'FAIL', 'Replayable', 't0', 't1')",
                (attempt_id, "dd" * 32),
            )


@pytest.fixture
def sub():
    return MemorySub()


def worker(sub, core_s, *, key=KEY, tier=0, origin=keycharge.ORIGIN_WORKER):
    return keycharge.accrue(sub, key, tier, origin, core_s)


@pytest.mark.parametrize("edge", [None, 1, 3600, 4.5, 3600.0])
def test_a_null_or_positive_edge_reads_back(edge):
    expected = None if edge is None else float(edge)
    assert keycharge.edge_from({keycharge.EDGE_KEY: edge}) == expected


@pytest.mark.parametrize("edge", [0, -1, "3600", True, [], float("-inf")])
def test_a_malformed_edge_is_refused_rather_than_read_as_absent(edge):
    with pytest.raises(keycharge.ChargeError, match=keycharge.EDGE_KEY):
        keycharge.edge_from({keycharge.EDGE_KEY: edge})


def test_a_tiers_object_naming_no_edge_reads_as_no_metering():
    assert keycharge.edge_from({}) is None


@pytest.mark.parametrize(
    ("edge", "metered", "launch", "crossed"),
    [
        (None, 10**9, 10**9, False),
        (100, 50, 50, False),
        (100, 50, 50.000001, True),
        (100, 99, 1, False),
        (100, 100, 0, False),
        (100, 100, 0.000001, True),
        (100, 0, 100, False),
        (100, 0, 100.5, True),
    ],
    ids=[
        "no-edge",
        "lands-on-edge",
        "just-over",
        "one-below",
        "zero-launch-at-edge",
        "past-by-epsilon",
        "single-at-edge",
        "single-over",
    ],
)
def test_the_launch_that_would_carry_the_charge_past_the_edge_is_the_crossing_one(edge, metered, launch, crossed):
    assert keycharge.crosses(edge, metered, launch) is crossed


def test_a_crossed_edge_adds_its_reason_after_the_predicate_reasons_and_an_uncrossed_one_adds_nothing():
    base = (tiergate.UNCERTIFIED, tiergate.BUDGET)
    assert tiergate.with_edge_reason(base, False) == base
    assert tiergate.with_edge_reason(base, True) == (*base, tiergate.CUMULATIVE_EDGE)
    assert tiergate.with_edge_reason((), True) == (tiergate.CUMULATIVE_EDGE,)
    assert tiergate.CUMULATIVE_EDGE not in tiergate.REASON_ORDER


def test_a_launch_defaults_to_the_metered_origin_and_refuses_an_unknown_one():
    def make(**extra):
        return tiergate.Launch(
            cost_profile=None,
            inputs=1,
            budget_remaining=1.0,
            hypothesis_key=KEY,
            method_identity={},
            skill_identity_hash=None,
            declared_tier=0,
            **extra,
        )

    assert make().origin == keycharge.ORIGIN_WORKER
    with pytest.raises(ValueError, match="origin"):
        make(origin="orchestrator")


def test_the_exempt_origins_are_the_gate_owned_and_the_recorded_rerun_alone():
    assert set(keycharge.EXEMPT_ORIGINS) == {keycharge.ORIGIN_GATE_OWNED, keycharge.ORIGIN_RECORDED_RERUN}
    assert keycharge.ORIGIN_WORKER not in keycharge.EXEMPT_ORIGINS


def test_an_accrued_charge_stands_at_its_declared_cost(sub):
    charge_id = worker(sub, 12.5)
    row = keycharge.charge(sub, charge_id)
    assert (row["declared_core_s"], row["measured_core_s"], row["attempt_id"]) == (12.5, None, None)
    assert keycharge.standing(row) == 12.5
    assert keycharge.metered(sub, KEY, 0) == 12.5


def test_metering_sums_worker_charges_of_one_key_and_one_ticket_tier_only(sub):
    worker(sub, 10)
    worker(sub, 5)
    worker(sub, 1000, origin=keycharge.ORIGIN_GATE_OWNED)
    worker(sub, 2000, origin=keycharge.ORIGIN_RECORDED_RERUN)
    worker(sub, 4000, tier=1)
    worker(sub, 8000, tier=None)
    worker(sub, 16000, key=OTHER_KEY)
    assert keycharge.metered(sub, KEY, 0) == 15
    assert keycharge.metered(sub, KEY, 1) == 4000
    assert keycharge.metered(sub, OTHER_KEY, 0) == 16000
    assert keycharge.metered(sub, "ef" * 32, 0) == 0.0
    assert len(keycharge.rows(sub, KEY)) == 6


def test_an_unknown_origin_is_refused_before_a_row_is_written(sub):
    with pytest.raises(keycharge.ChargeError, match="origin"):
        keycharge.accrue(sub, KEY, 0, "orchestrator", 1.0)
    assert keycharge.rows(sub, KEY) == []


def test_reconciliation_replaces_the_declared_figure_with_user_plus_system_cpu_not_wall(sub):
    charge_id = worker(sub, 100)
    sub.attempt_with_receipt("att-1", cpu_user_s=3.0, cpu_sys_s=0.5, wall_s=250.0)
    keycharge.bind(sub, charge_id, "att-1")
    settled = keycharge.reconcile(sub, "att-1")
    assert settled["measured_core_s"] == 3.5
    assert settled["declared_core_s"] == 100
    assert keycharge.standing(settled) == 3.5
    assert keycharge.metered(sub, KEY, 0) == 3.5


def test_an_understated_declaration_is_raised_to_the_measured_cost(sub):
    charge_id = worker(sub, 1)
    sub.attempt_with_receipt("att-1", cpu_user_s=40.0, cpu_sys_s=2.0)
    keycharge.bind(sub, charge_id, "att-1")
    keycharge.reconcile(sub, "att-1")
    assert keycharge.metered(sub, KEY, 0) == 42.0


def test_an_attempt_with_no_receipt_leaves_the_declared_charge_standing(sub):
    charge_id = worker(sub, 7)
    sub.attempt_without_receipt("att-1")
    keycharge.bind(sub, charge_id, "att-1")
    assert keycharge.reconcile(sub, "att-1") is None
    assert keycharge.metered(sub, KEY, 0) == 7


def test_an_attempt_bound_to_no_charge_reconciles_nothing(sub):
    sub.attempt_with_receipt("att-1", cpu_user_s=1.0, cpu_sys_s=1.0)
    assert keycharge.reconcile(sub, "att-1") is None


def test_a_charge_reconciles_once(sub):
    charge_id = worker(sub, 7)
    sub.attempt_with_receipt("att-1", cpu_user_s=1.0, cpu_sys_s=1.0)
    keycharge.bind(sub, charge_id, "att-1")
    keycharge.reconcile(sub, "att-1")
    assert keycharge.reconcile(sub, "att-1") is None
    with pytest.raises(keycharge.ChargeError, match="already reconciled"):
        keycharge.reconcile_served(sub, charge_id)
    assert keycharge.metered(sub, KEY, 0) == 2.0


def test_a_charge_binds_to_one_attempt_once_and_one_attempt_holds_one_charge(sub):
    first, second = worker(sub, 1), worker(sub, 2)
    keycharge.bind(sub, first, "att-1")
    with pytest.raises(keycharge.ChargeError, match="already bound"):
        keycharge.bind(sub, first, "att-2")
    with pytest.raises(sqlite3.IntegrityError):
        keycharge.bind(sub, second, "att-1")


def test_a_launch_served_from_the_cache_settles_at_zero_and_binds_no_attempt(sub):
    charge_id = worker(sub, 50)
    served = SimpleNamespace(served_from_cache=True, attempt_id="original-attempt")
    settled = keycharge.settle_launch(sub, charge_id, served)
    assert settled["measured_core_s"] == 0.0 and settled["attempt_id"] is None
    assert keycharge.metered(sub, KEY, 0) == 0.0


def test_settling_a_run_launch_binds_then_reconciles(sub):
    charge_id = worker(sub, 50)
    sub.attempt_with_receipt("att-1", cpu_user_s=4.0, cpu_sys_s=1.0)
    ran = SimpleNamespace(served_from_cache=False, attempt_id="att-1")
    settled = keycharge.settle_launch(sub, charge_id, ran)
    assert (settled["attempt_id"], settled["measured_core_s"]) == ("att-1", 5.0)


def test_settling_a_launch_that_carries_no_charge_is_a_no_op(sub):
    assert keycharge.settle_launch(sub, None, SimpleNamespace(served_from_cache=False, attempt_id="x")) is None


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE key_charges SET declared_core_s = 0",
        "UPDATE key_charges SET origin = 'gate-owned'",
        "UPDATE key_charges SET hypothesis_key = 'x'",
        "UPDATE key_charges SET ticket_tier = 1",
        "UPDATE key_charges SET measured_core_s = 1.0",
        "UPDATE key_charges SET attempt_id = 'a', measured_core_s = 1.0, reconciled_at = 't'",
        "DELETE FROM key_charges",
    ],
    ids=["declared", "origin", "key", "tier", "measured-without-time", "bind-and-reconcile-together", "delete"],
)
def test_the_schema_refuses_any_write_other_than_bind_and_reconcile(sub, statement):
    worker(sub, 9)
    with pytest.raises(sqlite3.DatabaseError):
        sub.conn.execute(statement)
    assert keycharge.metered(sub, KEY, 0) == 9


def test_a_bound_charge_cannot_be_rebound_or_unbound_by_sql(sub):
    charge_id = worker(sub, 9)
    keycharge.bind(sub, charge_id, "att-1")
    with pytest.raises(sqlite3.DatabaseError):
        sub.conn.execute("UPDATE key_charges SET attempt_id = 'att-2'")
    with pytest.raises(sqlite3.DatabaseError):
        sub.conn.execute("UPDATE key_charges SET attempt_id = NULL")
