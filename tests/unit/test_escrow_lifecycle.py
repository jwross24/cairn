import pytest

from cairn import escrow

TERMINAL_NOT_OK = ("FAIL", "DISAGREE", "BUDGET_EXCEEDED", "BLOCKED", "SKILL_YANKED", "INTERRUPTED")


def attempt(status="OK", disowned_at=None):
    return {"status": status, "disowned_at": disowned_at}


def row(spent_at=None, released_at=None):
    return {"spent_at": spent_at, "released_at": released_at, "spent_by": None, "released_by": None}


def test_an_ok_owned_attempt_holds_its_reservation():
    assert escrow.release_reason(attempt()) is None


def test_a_running_attempt_holds_its_reservation_until_it_ends():
    assert escrow.release_reason(attempt("RUNNING")) is None


@pytest.mark.parametrize("status", TERMINAL_NOT_OK)
def test_every_status_other_than_ok_names_itself_as_the_release_reason(status):
    assert escrow.release_reason(attempt(status)) == f"status:{status}"


def test_a_disowned_attempt_releases_whatever_its_status():
    assert escrow.release_reason(attempt("OK", "2026-09-01T00:00:00+00:00")) == escrow.RELEASE_DISOWNED
    assert escrow.release_reason(attempt("FAIL", "2026-09-01T00:00:00+00:00")) == escrow.RELEASE_DISOWNED


def test_unsettled_means_neither_spent_nor_released():
    assert escrow.unsettled(row())
    assert not escrow.unsettled(row(spent_at="t"))
    assert not escrow.unsettled(row(released_at="t"))


def test_the_settlement_columns_are_exactly_the_four_the_trigger_admits():
    assert escrow.SETTLEMENT_COLUMNS == ("spent_at", "spent_by", "released_at", "released_by")
