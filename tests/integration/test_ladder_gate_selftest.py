import dataclasses
import sys
from pathlib import Path

import pytest

from cairn import attest, bundle, gateplan, ladder, ladderplan, laddertable, substrate

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers


@pytest.fixture
def gate_env(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle(name="ladder-selftest")
    gate_bundle = bundle.GateBundle.open(bundle_path, pin_path)
    attest_path = tmp_path / "ladder-selftest-attest.log"
    attest.init(attest_path, gate_bundle.waiver_target())
    sub = helpers.open_writer(tmp_path, name="ladder-selftest.sqlite")
    yield gate_bundle, sub, attest_path
    sub.close()


def test_the_method_refusal_precedes_a_persisted_honest_baseline_table(gate_env):
    gate_bundle, sub, attest_path = gate_env
    result = gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    assert result.ok
    assert [step.step for step in result.steps[-2:]] == [
        "ladder_selftest_method_identity",
        "ladder_selftest_baseline",
    ]
    method_step, baseline_step = result.steps[-2:]
    assert method_step.expected == gateplan.EXPECT_LADDER_METHOD_IDENTITY
    assert method_step.observed == gateplan.EXPECT_LADDER_METHOD_IDENTITY
    assert "refusal:method-identity-mismatch" in method_step.reasons
    assert baseline_step.expected == gateplan.EXPECT_LADDER_BASELINE
    assert baseline_step.observed == gateplan.EXPECT_LADDER_BASELINE
    table_hash = next(reason.removeprefix("table:") for reason in baseline_step.reasons if reason.startswith("table:"))
    plan_hash = next(
        reason.removeprefix("fixture-plan:") for reason in baseline_step.reasons if reason.startswith("fixture-plan:")
    )
    raw_fixture_plan = sub.get_blob(plan_hash)
    assert raw_fixture_plan is not None
    fixture = bundle._decode(raw_fixture_plan)
    source = gate_bundle.object(ladderplan.KIND)
    assert plan_hash == substrate.blob_hash(bundle.canonical_bytes(ladderplan.KIND, fixture))
    assert plan_hash != gate_bundle.digest_of(ladderplan.KIND)
    assert fixture["baseline"] == source["baseline"]
    assert fixture["hold_out_m"] == 1
    assert [(rung["bits"], rung["role"], rung["trials"]) for rung in fixture["rungs"]] == [
        (30, ladderplan.ROLE_FIT, 100),
        (40, ladderplan.ROLE_HOLD_OUT, 1),
    ]
    assert fixture["rungs"][0]["refutation_floor"] == source["rungs"][0]["refutation_floor"]
    assert fixture["rungs"][1]["refutation_floor"] == source["rungs"][1]["refutation_floor"]
    table = laddertable.read(sub, table_hash)
    assert table is not None and table.hash == table_hash and table.plan_hash == plan_hash
    assert len(table.trials) == 301
    expected = {(arm, 30, trial) for arm in ladderplan.ARMS for trial in range(100)} | {(ladder.CLAIMANT, 40, 0)}
    assert {(trial.arm, trial.bits, trial.trial) for trial in table.trials} == expected
    assert all(trial.gate_ops.kind == laddertable.OPS_UNKNOWN for trial in table.trials)
    assert all(not trial.output_complete or trial.recovered for trial in table.trials)
    verdict = laddertable.recorded_verdict(sub, table_hash)
    assert (verdict.kind, verdict.predicate) == (laddertable.INCONCLUSIVE, laddertable.UNCOUNTED_BACKEND)


def test_removing_the_method_identity_guard_fails_and_blocks_the_baseline(gate_env, monkeypatch):
    gate_bundle, sub, attest_path = gate_env
    original = ladder.check_dispatch

    def without_method_identity(sub, gate_bundle, dispatch, plan):
        hypothesis = ladder._hypothesis(sub, dispatch.hypothesis_hash)
        expected = ladder.expected_identity(plan, dispatch.arm, hypothesis)
        if dispatch.method_identity != expected:
            dispatch = dataclasses.replace(dispatch, method_identity=expected)
        return original(sub, gate_bundle, dispatch, plan)

    monkeypatch.setattr(ladder, "check_dispatch", without_method_identity)
    result = gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    failed = result.first_failure
    assert failed.step == "ladder_selftest_method_identity"
    assert failed.expected == gateplan.EXPECT_LADDER_METHOD_IDENTITY
    assert failed.observed == "admitted"
    blocked = result.steps[-1]
    assert blocked.step == "ladder_selftest_baseline" and blocked.result == gateplan.RESULT_BLOCKED
    assert blocked.reasons == (f"{gateplan.BLOCKED_PREFIX}ladder_selftest_method_identity",)
    assert sub.conn.execute(f"SELECT COUNT(*) FROM {laddertable.TABLES}").fetchone()[0] == 0
