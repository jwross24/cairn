import dataclasses

import pytest

from cairn import laddertable, prefilter, ticketlattice

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


REVISION = "bb" * 32
OTHER_REVISION = "bc" * 32


CANDIDATE = ticketlattice.Candidate(
    claim_kind=ticketlattice.ALGORITHMIC,
    node_kind=laddertable.NODE_KIND,
    node_hash="aa" * 32,
    verdict=laddertable.KEEP,
    hypothesis_key="cc" * 32,
    method_identity={"interface_version": "toy/1", "params": {}},
    implementation_revision=REVISION,
)


def candidate(**kw):
    return dataclasses.replace(CANDIDATE, **kw)


def bind(candidate, *, revision=REVISION, bits=60):
    return ticketlattice.mismatches(candidate, implementation_revision=revision, rung_bits=bits)


def test_a_table_of_the_launch_s_own_revision_binds():
    assert bind(candidate()) == ()


@pytest.mark.parametrize("revision", [OTHER_REVISION, None], ids=["differing", "omitted"])
def test_a_launch_that_does_not_carry_the_table_s_revision_is_unbound(revision):
    assert bind(candidate(), revision=revision) == (ticketlattice.REVISION_MISMATCH,)


def test_a_table_carrying_no_revision_binds_to_any_launch():
    assert bind(candidate(implementation_revision=None), revision=None) == ()


def test_a_scoped_ticket_binds_to_its_own_rung_and_no_other():
    scoped = candidate(verdict=laddertable.KEEP_IN_SAMPLE, scoped_rung_bits=60)
    assert bind(scoped, bits=60) == ()
    assert bind(scoped, bits=50) == (ticketlattice.SCOPE_MISMATCH,)


def test_an_unbound_ticket_names_every_way_it_fails_at_once():
    scoped = candidate(verdict=laddertable.KEEP_IN_SAMPLE, scoped_rung_bits=60)
    assert set(bind(scoped, revision=OTHER_REVISION, bits=50)) == {
        ticketlattice.REVISION_MISMATCH,
        ticketlattice.SCOPE_MISMATCH,
    }


def selection(claim_kind, admits):
    return ticketlattice.Selection(claim_kind, candidate() if admits else None, admits)


def test_a_claim_carrying_no_kind_at_all_reaches_no_tier_two():
    assert not ticketlattice.admits_tier_two(())


@pytest.mark.parametrize(
    "held",
    [(True,), (True, True), (True, True, True)],
    ids=["one", "two", "three"],
)
def test_every_kind_held_admits(held):
    kinds = ticketlattice.KINDS[: len(held)]
    assert ticketlattice.admits_tier_two(tuple(selection(k, a) for k, a in zip(kinds, held, strict=True)))


@pytest.mark.parametrize("absent", range(len(ticketlattice.KINDS)))
def test_any_single_kind_absent_denies_the_whole_claim(absent):
    selections = tuple(selection(kind, index != absent) for index, kind in enumerate(ticketlattice.KINDS))
    assert not ticketlattice.admits_tier_two(selections)


def test_the_lattice_is_total_over_the_claim_kinds():
    assert set(ticketlattice.ADMITTING_VERDICTS) == set(ticketlattice.KINDS)
    assert ticketlattice.KINDS == (ticketlattice.ALGORITHMIC, ticketlattice.CONJECTURE, ticketlattice.THEOREM)
