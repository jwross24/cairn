import dataclasses

import pytest
from _ladder_run_helpers import FIT_BITS, MAKER_CEILING, RUN_ID
from _ladder_run_helpers import attest_path as attest_path
from _ladder_run_helpers import dispatched as dispatched
from _ladder_run_helpers import hypothesis_object as hypothesis_object
from _ladder_run_helpers import plan as plan
from _ladder_run_helpers import shipped as shipped
from _ladder_run_helpers import writer as writer

from cairn import escrow, instances, ladder, ladderplan, runner, verifier
from cairn.skills import bsgs, instance_maker, rho_dp


@pytest.mark.parametrize("cpu_core_s", [0.3, 0.0], ids=["measured-overage", "standing-verification"])
def test_a_run_debits_the_maker_before_the_first_arm_spawn(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, popen_spy, monkeypatch, cpu_core_s
):
    real_spawn = runner.spawn_and_wait

    def measured_spawn(*args, **kwargs):
        result = real_spawn(*args, **kwargs)
        return dataclasses.replace(result, cpu_user_s=cpu_core_s, cpu_sys_s=0.0)

    monkeypatch.setattr(runner, "spawn_and_wait", measured_spawn)
    evaluation = bsgs.COST_PROFILE.evaluate(FIT_BITS)
    grant = (
        runner.ceiling_for(evaluation.expected_core_s, plan.patience_multiplier)
        + evaluation.expected_verification_core_s
    )
    with pytest.raises(runner.BudgetRefused):
        ladder.run(
            writer,
            shipped,
            plan=plan,
            plan_hash=ladderplan.plan_digest(shipped),
            run_id=RUN_ID,
            hypothesis_hash=hypothesis_object.hash,
            nonce=dispatched,
            scratch_root=tmp_path / "runs",
            budget_remaining=grant,
            ceiling_multiplier=40,
            attest_path=attest_path,
        )
    launches = [args for args in popen_spy if "-m" in args]
    assert len(launches) == 1 and instance_maker.__name__ in launches[0]
    attempts = writer.conn.execute("SELECT status FROM attempts").fetchall()
    assert [row["status"] for row in attempts] == [runner.STATUS_OK]


def test_a_run_debits_an_arm_before_the_next_arm_spawn(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, popen_spy, monkeypatch
):
    real_spawn = runner.spawn_and_wait

    def measured_spawn(*args, **kwargs):
        result = real_spawn(*args, **kwargs)
        return dataclasses.replace(result, cpu_user_s=0.3, cpu_sys_s=0.0)

    monkeypatch.setattr(runner, "spawn_and_wait", measured_spawn)
    maker = instance_maker.COST_PROFILE.evaluate(FIT_BITS)
    claimant = bsgs.COST_PROFILE.evaluate(FIT_BITS)
    baseline = rho_dp.COST_PROFILE.evaluate(FIT_BITS)
    grant = (
        runner.ceiling_for(baseline.expected_core_s, plan.patience_multiplier)
        + baseline.expected_verification_core_s
        + maker.expected_core_s
        + maker.expected_verification_core_s
        + claimant.expected_core_s
        + claimant.expected_verification_core_s
    )
    with pytest.raises(runner.BudgetRefused):
        ladder.run(
            writer,
            shipped,
            plan=plan,
            plan_hash=ladderplan.plan_digest(shipped),
            run_id=RUN_ID,
            hypothesis_hash=hypothesis_object.hash,
            nonce=dispatched,
            scratch_root=tmp_path / "runs",
            budget_remaining=grant,
            ceiling_multiplier=40,
            attest_path=attest_path,
        )
    launches = [args for args in popen_spy if "-m" in args]
    assert len(launches) == 2
    assert instance_maker.__name__ in launches[0] and bsgs.__name__ in launches[1]


def test_a_run_debits_completed_trials_before_the_next_instance_spawn(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, popen_spy, monkeypatch
):
    plan = dataclasses.replace(
        plan,
        rungs=(dataclasses.replace(plan.rungs[0], role=ladderplan.ROLE_HOLD_OUT),),
        patience_multiplier=40,
    )
    real_spawn = runner.spawn_and_wait

    def measured_spawn(*args, **kwargs):
        result = real_spawn(*args, **kwargs)
        return dataclasses.replace(result, cpu_user_s=0.3, cpu_sys_s=0.0)

    monkeypatch.setattr(runner, "spawn_and_wait", measured_spawn)
    maker = instance_maker.COST_PROFILE.evaluate(FIT_BITS)
    claimant = bsgs.COST_PROFILE.evaluate(FIT_BITS)
    grant = (
        runner.ceiling_for(maker.expected_core_s, 40)
        + maker.expected_verification_core_s
        + maker.expected_core_s
        + maker.expected_verification_core_s
        + claimant.expected_core_s
        + claimant.expected_verification_core_s
    )
    with pytest.raises(runner.BudgetRefused):
        ladder.run(
            writer,
            shipped,
            plan=plan,
            plan_hash=ladderplan.plan_digest(shipped),
            run_id=RUN_ID,
            hypothesis_hash=hypothesis_object.hash,
            nonce=dispatched,
            scratch_root=tmp_path / "runs",
            budget_remaining=grant,
            ceiling_multiplier=40,
            attest_path=attest_path,
        )
    launches = [args for args in popen_spy if "-m" in args]
    assert len(launches) == 2
    assert instance_maker.__name__ in launches[0] and bsgs.__name__ in launches[1]


def _draw_instance(writer, shipped, tmp_path, hypothesis_object, nonce, attest_path):
    attempt, out = instances.launch_trial(
        writer,
        shipped,
        nonce=nonce,
        bits=FIT_BITS,
        trial=0,
        scratch_root=tmp_path / "runs",
        method_identity=hypothesis_object.method_identity,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        attest_path=attest_path,
    )
    assert out is not None
    return attempt, out


def _run_claimant_arm(writer, shipped, tmp_path, plan, out, *, budget_remaining, attest_path):
    return ladder.run_arm(
        writer,
        shipped,
        ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT],
        plan=plan,
        instance=verifier.Instance(**out.instance()),
        instance_hash=out.instance_hash,
        bits=FIT_BITS,
        trial=0,
        scratch_root=tmp_path / "runs",
        budget_remaining=budget_remaining,
        attest_path=attest_path,
    )


def test_an_arm_is_refused_when_the_budget_covers_its_ceiling_but_not_its_ceiling_plus_verification(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, popen_spy
):
    _, out = _draw_instance(writer, shipped, tmp_path, hypothesis_object, dispatched, attest_path)
    evaluation = bsgs.COST_PROFILE.evaluate(FIT_BITS)
    ceiling = runner.ceiling_for(
        evaluation.expected_core_s,
        plan.patience_multiplier,
        subprocess_startup_ms=shipped.tiers["subprocess_startup_ms"],
    )
    budget_remaining = ceiling + evaluation.expected_verification_core_s / 2
    assert evaluation.expected_core_s + evaluation.expected_verification_core_s <= budget_remaining
    spawned = len(popen_spy)
    attempts = writer.conn.execute("SELECT count(*) AS n FROM attempts").fetchone()["n"]

    with pytest.raises(runner.BudgetRefused) as raised:
        _run_claimant_arm(
            writer, shipped, tmp_path, plan, out, budget_remaining=budget_remaining, attest_path=attest_path
        )

    assert raised.value.ceiling_core_s == pytest.approx(ceiling)
    assert raised.value.remaining == pytest.approx(budget_remaining - evaluation.expected_verification_core_s)
    assert len(popen_spy) == spawned
    assert writer.conn.execute("SELECT count(*) AS n FROM attempts").fetchone()["n"] == attempts


def test_a_run_budget_counts_standing_verification_and_not_a_released_reservation(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, monkeypatch
):
    maker, out = _draw_instance(writer, shipped, tmp_path, hypothesis_object, dispatched, attest_path)
    real_spawn = runner.spawn_and_wait

    def overage_spawn(*args, **kwargs):
        result = real_spawn(*args, **kwargs)
        return dataclasses.replace(result, cpu_user_s=5.0, cpu_sys_s=0.0)

    monkeypatch.setattr(runner, "spawn_and_wait", overage_spawn)
    trial = _run_claimant_arm(writer, shipped, tmp_path, plan, out, budget_remaining=10_000.0, attest_path=attest_path)

    assert trial.status == runner.STATUS_BUDGET_EXCEEDED
    assert escrow.reservation(writer, trial.attempt_id)["released_at"] is not None
    assert escrow.standing(writer, maker.attempt_id)
    maker_receipt = writer.get_receipt(writer.get_attempt(maker.attempt_id)["receipt_hash"])
    maker_core_s = maker_receipt["cpu_user_s"] + maker_receipt["cpu_sys_s"]
    standing_core_s = instance_maker.COST_PROFILE.evaluate(FIT_BITS).expected_verification_core_s
    released_core_s = bsgs.COST_PROFILE.evaluate(FIT_BITS).expected_verification_core_s
    assert released_core_s > 0

    budget = ladder.RunBudget(10_000.0, [maker.attempt_id, trial.attempt_id])

    assert budget.snapshot(writer) == {
        "granted_core_s": 10_000.0,
        "production_core_s": pytest.approx(maker_core_s + 5.0),
        "verification_core_s": pytest.approx(standing_core_s),
        "budget_remaining_core_s": pytest.approx(10_000.0 - maker_core_s - 5.0 - standing_core_s),
    }
