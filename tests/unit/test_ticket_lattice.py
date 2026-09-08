import pytest

from cairn import prefilter

ALL_QUIET = dict.fromkeys(prefilter.REQUIRED_FILTERS, prefilter.QUIET)


def result(verdicts, flags=()):
    return prefilter.PrefilterResult(
        statement_hash="b" * 64,
        gate_bundle_hash="a" * 64,
        verdicts=verdicts,
        flags=tuple(flags),
        at="2026-09-08T00:00:00.000000+00:00",
    )


def test_a_complete_quiet_battery_passes():
    assert result(ALL_QUIET).passed


@pytest.mark.parametrize("name", prefilter.REQUIRED_FILTERS)
def test_any_single_rejecting_filter_denies_and_names_itself(name):
    denied = result({**ALL_QUIET, name: prefilter.REJECT})
    assert denied.rejected == (name,)
    assert not denied.passed


@pytest.mark.parametrize("name", prefilter.REQUIRED_FILTERS)
def test_any_single_flagging_filter_passes_and_keeps_its_flag(name):
    flagged = result({**ALL_QUIET, name: prefilter.FLAG}, flags=(name,))
    assert flagged.flagged == (name,)
    assert flagged.rejected == ()
    assert flagged.passed


@pytest.mark.parametrize("name", prefilter.REQUIRED_FILTERS)
def test_any_single_unrun_filter_denies_and_is_not_a_quiet_one(name):
    partial = {other: prefilter.QUIET for other in prefilter.REQUIRED_FILTERS if other != name}
    unrun = result(partial)
    assert unrun.missing == (name,)
    assert unrun.rejected == ()
    assert not unrun.passed


def test_an_empty_battery_denies():
    empty = result({})
    assert empty.missing == prefilter.REQUIRED_FILTERS
    assert not empty.passed


def test_a_reject_beats_a_flag_on_the_same_battery():
    mixed = result(
        {**ALL_QUIET, prefilter.VACUITY: prefilter.REJECT, prefilter.BOUNDED_PROVER: prefilter.FLAG},
        flags=(prefilter.BOUNDED_PROVER,),
    )
    assert mixed.flagged == (prefilter.BOUNDED_PROVER,)
    assert mixed.rejected == (prefilter.VACUITY,)
    assert not mixed.passed


def test_the_battery_is_the_five_named_filters():
    assert prefilter.REQUIRED_FILTERS == (
        prefilter.VACUITY,
        prefilter.EXISTS_IMPLICATION,
        prefilter.STUB_OR_AXIOM,
        prefilter.BOUNDED_PROVER,
        prefilter.ROUNDTRIP_DIVERGENCE,
    )
    assert prefilter.VERDICTS == (prefilter.REJECT, prefilter.FLAG, prefilter.QUIET)
