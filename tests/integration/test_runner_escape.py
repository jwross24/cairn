import time

from test_runner_tree_measurement import BURNER_BUDGET, _launch

from cairn import runner, substrate


def _await_burn(tmp_path, attempt):
    burned = tmp_path / "runs" / attempt.attempt_id / "scratch" / "burned"
    deadline = time.monotonic() + 30
    while not burned.exists() or not burned.read_text():
        assert time.monotonic() < deadline
        time.sleep(0.05)
    return float(burned.read_text())


def test_a_descendant_in_a_new_session_is_not_a_verified_complete_figure(tmp_path):
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        attempt = _launch(sub, tmp_path, "skills.escapes_session", 77, BURNER_BUDGET)
        receipt = sub.get_receipt(attempt.receipt_hash)
        assert _await_burn(tmp_path, attempt) >= 1.0
        assert attempt.status == "OK"
        assert receipt["measurement_scope"] == runner.SCOPE_TRUNCATED
        assert not runner.scope_is_verified_complete(receipt["measurement_scope"])
