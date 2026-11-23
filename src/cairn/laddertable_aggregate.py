import statistics
from decimal import ROUND_FLOOR as _ROUND_FLOOR
from decimal import Decimal

from cairn import ladderplan, runner
from cairn.laddertable_rows import OPS_EXACT, OPS_LOWER_BOUND, OPS_UNKNOWN, LadderTableError, RungRow


def _decimal_text(value, places, *, rounding=None):
    return str(Decimal(value).quantize(Decimal(places), rounding=rounding))


def _speedup_ci(plan, claimant, baseline):
    if plan.comparison.ci_method != ladderplan.CI_METHODS[0]:
        raise LadderTableError(f"ci method {plan.comparison.ci_method} is not built")
    claimant_by_trial = {t.trial: t for t in claimant}
    baseline_by_trial = {t.trial: t for t in baseline}
    if claimant_by_trial.keys() != baseline_by_trial.keys() or len(claimant_by_trial) < 2:
        return None, None
    pairs = [(claimant_by_trial[key], baseline_by_trial[key]) for key in sorted(claimant_by_trial)]
    if any(
        claim.gate_ops.kind != OPS_EXACT
        or base.gate_ops.kind != OPS_EXACT
        or claim.gate_ops.value == 0
        or claim.status != runner.STATUS_OK
        or base.status != runner.STATUS_OK
        or not claim.output_complete
        or not base.output_complete
        or not claim.recovered
        or not base.recovered
        or claim.instance_hash != base.instance_hash
        for claim, base in pairs
    ):
        return None, None
    ratios = [Decimal(base.gate_ops.value) / Decimal(claim.gate_ops.value) for claim, base in pairs]
    if len(ratios) < 2:
        return None, None
    mean = sum(ratios) / Decimal(len(ratios))
    variance = sum((ratio - mean) ** 2 for ratio in ratios) / Decimal(len(ratios) - 1)
    z = Decimal(str(statistics.NormalDist().inv_cdf(float(1 - (1 - plan.comparison.ci_coverage) / 2))))
    half = z * (variance / Decimal(len(ratios))).sqrt()
    return _decimal_text(mean - half, "0.000001"), _decimal_text(mean + half, "0.000001")


def aggregate_rung(plan, rung, trials, *, model_prediction, reference_rate, declared_shape):
    by_arm = {}
    for trial in trials:
        by_arm.setdefault(trial.arm, []).append(trial)
    claimant = sorted(by_arm.get(ladderplan.ARMS[0], ()), key=lambda t: t.trial)
    if not claimant:
        raise LadderTableError(f"rung {rung.bits} has no claimant observations")
    observations = [t.gate_ops for t in claimant]
    if any(observation.kind == OPS_UNKNOWN for observation in observations):
        ops_kind, mean_ops, sd_ops, shape = OPS_UNKNOWN, None, None, None
    else:
        values = [Decimal(observation.value) for observation in observations]
        mean = sum(values) / Decimal(len(values))
        if any(observation.kind == OPS_LOWER_BOUND for observation in observations):
            ops_kind, mean_ops, sd_ops, shape = (
                OPS_LOWER_BOUND,
                _decimal_text(mean, "0.000001", rounding=_ROUND_FLOOR),
                None,
                None,
            )
        else:
            sd = (
                (sum((value - mean) ** 2 for value in values) / Decimal(len(values) - 1)).sqrt()
                if len(values) >= 2
                else Decimal(0)
            )
            prediction = Decimal(model_prediction)
            ops_kind = OPS_EXACT
            mean_ops = _decimal_text(mean, "0.000001")
            sd_ops = _decimal_text(sd, "0.000001")
            shape = _decimal_text(mean / prediction, "0.000001")
    baseline = by_arm.get(ladderplan.ARMS[1], ())
    low, high = _speedup_ci(plan, claimant, baseline) if baseline else (None, None)
    successes = sum(t.status == runner.STATUS_OK and t.output_complete and t.recovered for t in claimant)
    prediction = Decimal(model_prediction)
    rate = Decimal(reference_rate)
    return RungRow(
        bits=rung.bits,
        role=rung.role,
        trials=len(claimant),
        ops_kind=ops_kind,
        mean_ops=mean_ops,
        sd_ops=sd_ops,
        cpu_seconds=_decimal_text(sum(Decimal(t.cpu_seconds) for t in claimant), "0.000001"),
        reference_rate=_decimal_text(rate, "0.000001"),
        memory_bytes=max(t.reported_memory_bytes for t in claimant),
        success_rate=_decimal_text(Decimal(successes) / Decimal(len(claimant)), "0.0001"),
        radius=str(plan.design_radius),
        claim_ci_low=low,
        claim_ci_high=high,
        model_prediction=_decimal_text(prediction, "0.000001"),
        model_band=str(plan.design_radius),
        shape_statistic=shape,
        declared_shape=declared_shape,
    )
