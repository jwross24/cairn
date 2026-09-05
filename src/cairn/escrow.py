"""Escrow settlement (PLAN §5): a reservation bound to the node, spent once or released once.

The tier gate's launch reserves the verification component of the declared cost profile against the
attempt. The reservation is spent where the §3 re-run policy's first check runs and released unspent
only where the attempt ended with status ≠ OK or the node was disowned. A branch reaching a terminal
status touches no reservation, so a deferred Tier-2/3 check stays funded after its branch is gone.
`spend` and `release` are the only writers; the `escrow_settle_once` trigger refuses any other UPDATE,
so a settlement written elsewhere is a defect the schema catches, not one a grep must find.
"""

from cairn import log
from cairn.substrate import SubstrateError, UnknownAttempt, _now

lg = log.get("escrow")

TABLE = "escrow"
STATUS_OK = "OK"
STATUS_RUNNING = "RUNNING"
RELEASE_DISOWNED = "disowned"
SETTLEMENT_COLUMNS = ("spent_at", "spent_by", "released_at", "released_by")


class EscrowError(SubstrateError):
    pass


class NoReservation(EscrowError):
    pass


class AlreadySettled(EscrowError):
    pass


class ReleaseRefused(EscrowError):
    pass


def reservation(sub, attempt_id):
    row = sub.conn.execute(f"SELECT * FROM {TABLE} WHERE attempt_id = ?", (attempt_id,)).fetchone()
    return None if row is None else dict(row)


def unsettled(row):
    return row["spent_at"] is None and row["released_at"] is None


def standing(sub, attempt_id):
    row = reservation(sub, attempt_id)
    return row is not None and unsettled(row)


def _require(sub, attempt_id):
    row = reservation(sub, attempt_id)
    if row is None:
        raise NoReservation(f"attempt {attempt_id} holds no reservation")
    return row


def _settled_how(row):
    if row["spent_at"] is not None:
        return f"spent at {row['spent_at']} by {row['spent_by']}"
    return f"released at {row['released_at']} ({row['released_by']})"


def spend(sub, attempt_id, *, check_event, at=None):
    if not isinstance(check_event, str) or not check_event:
        raise EscrowError("a spend names the check event that spent the reservation")
    row = _require(sub, attempt_id)
    if not unsettled(row):
        raise AlreadySettled(f"reservation on {attempt_id} was {_settled_how(row)}")
    spent_at = at or _now()
    with sub._tx():
        cur = sub.conn.execute(
            f"UPDATE {TABLE} SET spent_at = ?, spent_by = ? WHERE attempt_id = ? AND spent_at IS NULL AND released_at IS NULL",
            (spent_at, check_event, attempt_id),
        )
        if cur.rowcount == 0:
            raise AlreadySettled(f"reservation on {attempt_id} settled under this write")
    lg.info("spend", attempt_id=attempt_id, check_event=check_event, reserved=row["reserved"], at=spent_at)
    return reservation(sub, attempt_id)


def release_reason(attempt):
    if attempt["disowned_at"] is not None:
        return RELEASE_DISOWNED
    if attempt["status"] not in (STATUS_RUNNING, STATUS_OK):
        return f"status:{attempt['status']}"
    return None


def release(sub, attempt_id, *, at=None):
    row = _require(sub, attempt_id)
    if not unsettled(row):
        raise AlreadySettled(f"reservation on {attempt_id} was {_settled_how(row)}")
    attempt = sub.get_attempt(attempt_id)
    if attempt is None:
        raise UnknownAttempt(f"no attempt {attempt_id}")
    reason = release_reason(attempt)
    if reason is None:
        raise ReleaseRefused(
            f"attempt {attempt_id} is {attempt['status']} and not disowned; a reservation releases only on status ≠ OK or disown"
        )
    released_at = at or _now()
    with sub._tx():
        cur = sub.conn.execute(
            f"UPDATE {TABLE} SET released_at = ?, released_by = ? WHERE attempt_id = ? AND spent_at IS NULL AND released_at IS NULL",
            (released_at, reason, attempt_id),
        )
        if cur.rowcount == 0:
            raise AlreadySettled(f"reservation on {attempt_id} settled under this write")
    lg.info("release", attempt_id=attempt_id, reason=reason, reserved=row["reserved"], at=released_at)
    return reservation(sub, attempt_id)


def first_check(sub, attempt_id, *, check_event, at=None):
    """Spend on the policy's first check; a later check finds the reservation settled and spends nothing."""
    row = reservation(sub, attempt_id)
    if row is None:
        lg.info("first_check", attempt_id=attempt_id, check_event=check_event, reservation=None)
        return None
    if unsettled(row):
        return spend(sub, attempt_id, check_event=check_event, at=at)
    lg.info("first_check", attempt_id=attempt_id, check_event=check_event, settled=_settled_how(row))
    return row


def settle_on_close(sub, attempt_id, status, *, at=None):
    if status == STATUS_OK or not standing(sub, attempt_id):
        return None
    return release(sub, attempt_id, at=at)


def settle_on_disown(sub, attempt_id, *, at=None):
    if not standing(sub, attempt_id):
        return None
    return release(sub, attempt_id, at=at)
