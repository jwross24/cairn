import pytest

from cairn import measure

ELAPSED_S = 12.5
RHO40_ORDER = 945003441719


@pytest.mark.parametrize("ops", [0, 10**6 - 1, 10**6, 10**7], ids=["zero", "just-under-1e6", "1e6", "1e7"])
def test_rate_report_refuses_under_1e6_ops_and_reports_a_conjectural_wall_above_it(ops):
    if ops < 10**6:
        with pytest.raises(measure.RefusedTooFewOps, match="fewer than 1e6 ops"):
            measure.rate_report(ops, ELAPSED_S)
        return
    row = measure.rate_report(ops, ELAPSED_S)
    assert row.ops == ops
    assert row.elapsed_s == pytest.approx(ELAPSED_S)
    assert row.ops_per_s == pytest.approx(ops / ELAPSED_S, rel=1e-6)
    assert row.extrapolated_wall_s == pytest.approx(measure.RHO60_EXPECTED_OPS * ELAPSED_S / ops, rel=1e-6)
    assert row.tag == measure.EXTRAPOLATION_TAG == "CONJECTURE"
    assert row.expected_ops == measure.RHO60_EXPECTED_OPS


def test_rate_report_names_cap_ops_in_its_refusal():
    with pytest.raises(measure.RefusedTooFewOps, match="--cap-ops"):
        measure.rate_report(10**6 - 1, ELAPSED_S)


def test_expected_rho_ops_is_the_birthday_bound_of_the_order():
    assert measure.RHO60_ORDER == 866004985024698433
    assert measure.expected_rho_ops(measure.RHO60_ORDER) == 1166326476
    assert measure.RHO60_EXPECTED_OPS == 1166326476
    assert measure.expected_rho_ops(RHO40_ORDER) == 1218362
    assert measure.expected_rho_ops(4 * measure.RHO60_ORDER) == pytest.approx(2 * measure.RHO60_EXPECTED_OPS, rel=1e-6)


def test_rate_report_refuses_a_zero_elapsed_and_names_cap_ops():
    with pytest.raises(measure.RefusedTooFewOps, match="--cap-ops"):
        measure.rate_report(10**6, 0.0)


def test_the_progress_log_stride_lands_on_the_wall_clock_stride():
    assert measure.RHO_CLOCK_EVERY == 1000
    assert measure.RHO_LOG_EVERY == 10**6
    assert measure.RHO_LOG_EVERY % measure.RHO_CLOCK_EVERY == 0
