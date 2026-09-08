import pytest

from cairn import runner, substrate


def test_the_receipt_carries_a_measurement_scope():
    assert "measurement_scope" in substrate.RECEIPT_FIELDS


def test_a_run_with_no_sampled_descendant_is_a_tree_figure():
    scope = runner.measurement_scope(sampled_extra=False, survivors=frozenset(), killed=False, sampled=True)
    assert scope == runner.SCOPE_TREE
    assert runner.scope_is_verified_complete(scope)


def test_a_sampled_descendant_under_a_normal_exit_is_not_verified_complete():
    scope = runner.measurement_scope(sampled_extra=True, survivors=frozenset(), killed=False, sampled=True)
    assert scope == runner.SCOPE_REAPED_DESCENDANTS
    assert not runner.scope_is_verified_complete(scope)


@pytest.mark.parametrize(
    ("survivors", "killed"),
    [(frozenset({4242}), False), (frozenset(), True), (frozenset({4242}), True)],
    ids=["outlived", "killed", "both"],
)
def test_a_survivor_or_a_kill_truncates_the_figure(survivors, killed):
    scope = runner.measurement_scope(sampled_extra=True, survivors=survivors, killed=killed, sampled=True)
    assert scope == runner.SCOPE_TRUNCATED
    assert not runner.scope_is_verified_complete(scope)


def test_an_unobservable_process_group_denies_rather_than_claiming_a_tree_figure():
    scope = runner.measurement_scope(sampled_extra=False, survivors=frozenset(), killed=False, sampled=False)
    assert scope == runner.SCOPE_UNSAMPLED
    assert not runner.scope_is_verified_complete(scope)


def test_every_scope_the_classifier_returns_is_declared():
    produced = {
        runner.measurement_scope(sampled_extra=e, survivors=s, killed=k, sampled=p)
        for e in (False, True)
        for s in (frozenset(), frozenset({7}))
        for k in (False, True)
        for p in (False, True)
    }
    assert produced <= set(runner.MEASUREMENT_SCOPES)
    assert produced == set(runner.MEASUREMENT_SCOPES)
