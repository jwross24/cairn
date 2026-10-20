"""Per-key production charges (PLAN §5): what the tier gate has admitted against a hypothesis key.

A charge accrues at admission as the launch's declared core seconds and reconciles once, to the
receipt's cpu_user_s + cpu_sys_s, when its attempt closes. Only the sum over a key's `worker`
charges under the Tier-1 ticket is compared against the bundle's Tier-1 cumulative edge; a
`gate-owned` or `recorded-rerun` charge is recorded and never compared. `bind` and `reconcile`
are the only writers of an existing row, and the `key_charges_bind_reconcile_once` trigger
refuses any other UPDATE.
"""

from cairn import log
from cairn.substrate import SubstrateError, _now

lg = log.get("keycharge")

TABLE = "key_charges"
EDGE_KEY = "tier1_cumulative_edge"
ORIGIN_WORKER = "worker"
ORIGIN_GATE_OWNED = "gate-owned"
ORIGIN_RECORDED_RERUN = "recorded-rerun"
ORIGINS = (ORIGIN_WORKER, ORIGIN_GATE_OWNED, ORIGIN_RECORDED_RERUN)
EXEMPT_ORIGINS = (ORIGIN_GATE_OWNED, ORIGIN_RECORDED_RERUN)


class ChargeError(SubstrateError):
    pass


def edge_from(tiers):
    edge = tiers.get(EDGE_KEY)
    if edge is None:
        return None
    if isinstance(edge, bool) or not isinstance(edge, int | float) or edge <= 0:
        raise ChargeError(f"{EDGE_KEY} is null or a positive number of core seconds, not {edge!r}")
    return float(edge)


def accrue(sub, hypothesis_key, ticket_tier, origin, declared_core_s, *, at=None):
    if origin not in ORIGINS:
        raise ChargeError(f"unknown charge origin {origin!r}")
    accrued_at = at or _now()
    with sub._tx():
        cur = sub.conn.execute(
            f"INSERT INTO {TABLE} (hypothesis_key, ticket_tier, origin, declared_core_s, accrued_at) VALUES (?, ?, ?, ?, ?)",
            (hypothesis_key, ticket_tier, origin, declared_core_s, accrued_at),
        )
    charge_id = cur.lastrowid
    lg.info(
        "accrue",
        charge_id=charge_id,
        hypothesis_key=hypothesis_key,
        ticket_tier=ticket_tier,
        origin=origin,
        declared_core_s=declared_core_s,
    )
    return charge_id


def charge(sub, charge_id):
    row = sub.conn.execute(f"SELECT * FROM {TABLE} WHERE charge_id = ?", (charge_id,)).fetchone()
    return None if row is None else dict(row)


def for_attempt(sub, attempt_id):
    row = sub.conn.execute(f"SELECT * FROM {TABLE} WHERE attempt_id = ?", (attempt_id,)).fetchone()
    return None if row is None else dict(row)


def rows(sub, hypothesis_key):
    found = sub.conn.execute(f"SELECT * FROM {TABLE} WHERE hypothesis_key = ? ORDER BY charge_id", (hypothesis_key,))
    return [dict(row) for row in found.fetchall()]


def standing(row):
    return row["declared_core_s"] if row["measured_core_s"] is None else row["measured_core_s"]


def metered(sub, hypothesis_key, ticket_tier):
    found = sub.conn.execute(
        f"SELECT COALESCE(SUM(COALESCE(measured_core_s, declared_core_s)), 0.0) AS total FROM {TABLE}"
        " WHERE hypothesis_key = ? AND ticket_tier = ? AND origin = ?",
        (hypothesis_key, ticket_tier, ORIGIN_WORKER),
    ).fetchone()
    return found["total"]


def crosses(edge, metered_core_s, launch_core_s):
    return edge is not None and metered_core_s + launch_core_s > edge


def bind(sub, charge_id, attempt_id):
    with sub._tx():
        cur = sub.conn.execute(
            f"UPDATE {TABLE} SET attempt_id = ? WHERE charge_id = ? AND attempt_id IS NULL", (attempt_id, charge_id)
        )
        if cur.rowcount == 0:
            raise ChargeError(f"charge {charge_id} is absent or already bound to an attempt")
    lg.info("bind", charge_id=charge_id, attempt_id=attempt_id)


def _reconcile_row(sub, charge_id, measured_core_s, at):
    reconciled_at = at or _now()
    with sub._tx():
        cur = sub.conn.execute(
            f"UPDATE {TABLE} SET measured_core_s = ?, reconciled_at = ? WHERE charge_id = ? AND measured_core_s IS NULL",
            (measured_core_s, reconciled_at, charge_id),
        )
        if cur.rowcount == 0:
            raise ChargeError(f"charge {charge_id} is absent or already reconciled")
    return charge(sub, charge_id)


def reconcile(sub, attempt_id, *, at=None):
    """Replace the declared figure with the receipt's measured core seconds; a charge with no receipt keeps its declaration."""
    row = for_attempt(sub, attempt_id)
    if row is None or row["measured_core_s"] is not None:
        return None
    attempt = sub.get_attempt(attempt_id)
    receipt = None if attempt is None or attempt["receipt_hash"] is None else sub.get_receipt(attempt["receipt_hash"])
    if receipt is None:
        lg.info("reconcile_skipped", charge_id=row["charge_id"], attempt_id=attempt_id, reason="no-receipt")
        return None
    measured = receipt["cpu_user_s"] + receipt["cpu_sys_s"]
    settled = _reconcile_row(sub, row["charge_id"], measured, at)
    lg.info(
        "reconcile",
        charge_id=row["charge_id"],
        attempt_id=attempt_id,
        declared_core_s=row["declared_core_s"],
        measured_core_s=measured,
    )
    return settled


def reconcile_served(sub, charge_id, *, at=None):
    """A launch served from the cache ran nothing, so its charge settles at zero."""
    settled = _reconcile_row(sub, charge_id, 0.0, at)
    lg.info("reconcile_served", charge_id=charge_id)
    return settled


def settle_launch(sub, charge_id, attempt, *, at=None):
    if charge_id is None:
        return None
    if attempt.served_from_cache:
        return reconcile_served(sub, charge_id, at=at)
    bind(sub, charge_id, attempt.attempt_id)
    return reconcile(sub, attempt.attempt_id, at=at)
