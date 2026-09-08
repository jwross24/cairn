import copy
import dataclasses
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cairn import allowlist, bundle, claims, ladder, ladderplan, runner
from cairn.skills import bsgs, rho_dp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = json.loads((ROOT / "bundle" / "ladder_plan.json").read_text())
BACKEND = os.path.realpath(sys.executable)
RUN_ID = "run-fuzz-1"
fixture_ok = settings(deadline=None, max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])

hex64 = st.text(alphabet="0123456789abcdef", min_size=64, max_size=64)


@pytest.fixture
def shipped(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def plan():
    obj = copy.deepcopy(COMMITTED)
    obj["baseline"]["implementation_revision"] = rho_dp.implementation_revision()
    return ladderplan.LadderPlan.load(obj)


@pytest.fixture
def valid(writer, shipped, tmp_path, plan):
    obj = claims.HypothesisObject(
        target_family="dlp",
        claimed={"model": "c_sqrt_n_ops"},
        method_identity={"interface_version": bsgs.INTERFACE_VERSION, "params": {}},
        declared_parameter_ranges={"bits": [28, 30]},
        sampling_distribution=None,
    )
    claims.write_hypothesis_object(writer, obj)
    _, nonce = ladder.commit_entropy(writer, hypothesis_hash=obj.hash, run_id=RUN_ID)
    identity = bsgs.identity_bundle()
    digest = writer.put_identity_bundle(identity)
    writer.put_certificate(digest, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    allow = allowlist.instantiate(
        shipped,
        hypothesis={
            "target_family": obj.target_family,
            "claimed": obj.claimed,
            "method_identity": obj.method_identity,
            "declared_parameter_ranges": obj.declared_parameter_ranges,
            "sampling_distribution": obj.sampling_distribution,
        },
        counted_object=BACKEND,
        scratch_dir=scratch,
    )
    return ladder.Dispatch(
        run_id=RUN_ID,
        arm=ladder.CLAIMANT,
        nonce=nonce.nonce,
        hypothesis_hash=obj.hash,
        method_identity=obj.method_identity,
        skill=bsgs.__name__,
        implementation_revision=identity["implementation_revision"],
        identity_bundle=identity,
        identity_bundle_hash=digest,
        allow_list=allow.as_dict(),
        allow_list_hash=allow.hash,
        gate_bundle_hash=shipped.hash,
        plan_hash="dd" * 32,
        at="2026-09-08T00:00:00Z",
    )


def _mutated(value, field, replacement):
    if field == "allow_list":
        return dataclasses.replace(value, allow_list={**value.allow_list, "bundle_hash": replacement})
    if field == "method_identity":
        return dataclasses.replace(value, method_identity={"interface_version": replacement, "params": {}})
    return dataclasses.replace(value, **{field: replacement})


MUTABLE = (
    "hypothesis_hash",
    "nonce",
    "method_identity",
    "identity_bundle_hash",
    "implementation_revision",
    "allow_list",
)


@fixture_ok
@given(field=st.sampled_from(MUTABLE), replacement=hex64)
def test_a_mutated_dispatch_field_is_refused_before_any_spawn(
    writer, shipped, plan, valid, popen_spy, field, replacement
):
    ladder.check_dispatch(writer, shipped, valid, plan)
    with pytest.raises(ladder.RunRefused) as raised:
        ladder.check_dispatch(writer, shipped, _mutated(valid, field, replacement), plan)
    assert raised.value.reason in ladder.PRE_SPAWN_REASONS
    assert popen_spy == []


@fixture_ok
@given(
    bits=st.integers(min_value=1, max_value=64),
    trial=st.integers(min_value=0, max_value=1000),
    arms=st.permutations(list(ladderplan.ARMS)),
)
def test_every_arm_draws_a_distinct_seed_the_gate_can_redraw(valid, bits, trial, arms):
    seeds = [ladder.method_seed(valid.nonce, valid.hypothesis_hash, arm, bits, trial) for arm in arms]
    assert len(set(seeds)) == len(arms)
    assert all(0 < seed < 1 << 63 for seed in seeds)
    assert seeds == [ladder.method_seed(valid.nonce, valid.hypothesis_hash, arm, bits, trial) for arm in arms]


def _arm_trial(arm, bits, trial, ops, *, completed=True):
    return ladder.ArmTrial(
        arm=arm,
        bits=bits,
        trial=trial,
        seed=1,
        status=runner.STATUS_OK if completed else runner.STATUS_BUDGET_EXCEEDED,
        ops=ops,
        recovered=completed,
        completed=completed,
        cpu_seconds="0.010000",
        wall_seconds="0.010000",
        peak_rss_bytes=1000,
        scratch_bytes=0,
        reported_memory_bytes=1000,
        replay_grade="Replayable",
        measurement_scope=runner.SCOPE_TREE,
        attempt_id="attempt-1",
        instance_hash="aa" * 32,
    )


@settings(deadline=None, max_examples=50)
@given(
    outcomes=st.lists(st.booleans(), min_size=1, max_size=8),
    ops=st.integers(min_value=1, max_value=10**9),
)
def test_the_success_rate_counts_only_completed_and_recovered_trials(outcomes, ops):
    plan = ladderplan.LadderPlan.load(copy.deepcopy(COMMITTED))
    rung = plan.rung(30)
    claim = [_arm_trial(ladder.CLAIMANT, 30, i, ops, completed=done) for i, done in enumerate(outcomes)]
    base = [_arm_trial(ladder.BASELINE, 30, i, ops * 2) for i, _ in enumerate(outcomes)]
    row = ladder._rung_row(plan, rung, bsgs, claim, {ladder.BASELINE: base})
    expected = Decimal(sum(1 for done in outcomes if done)) / Decimal(len(outcomes))
    assert Decimal(row.success_rate) == expected.quantize(Decimal("0.0001"))
    assert Decimal(row.mean_ops) == Decimal(ops)
    assert Decimal(row.sd_ops) == 0
    if row.claim_ci_low is not None:
        assert Decimal(row.claim_ci_low) <= Decimal(row.claim_ci_high)
