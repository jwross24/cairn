import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cairn import ladderplan

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = json.loads((ROOT / "bundle" / "ladder_plan.json").read_text())
TIERS = json.loads((ROOT / "bundle" / "tiers.json").read_text())
SEEDED_TODAY = ["rungs.trials", "design_radius", "clock.rate_ratio"]
MEASURED_FLOOR = {
    30: (41226, 29396, 497314),
    40: (1171749, 881490, 15440525),
    50: (44769554, 26116919, 477370808),
}
BYTES_PER_ENTRY = Decimal("18.278")


def _edit(path, value, *, delete=False):
    obj = copy.deepcopy(COMMITTED)
    node = obj
    parts = path.split(".")
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    key = int(parts[-1]) if isinstance(node, list) else parts[-1]
    if delete:
        del node[key]
    else:
        node[key] = value
    return obj


def _without(path):
    return _edit(path, None, delete=True)


def _swapped_roles():
    obj = _edit("rungs.2.role", "hold_out")
    obj["rungs"][2]["trials"] = 10
    obj["rungs"][3]["role"] = "fit"
    obj["rungs"][3]["trials"] = 130
    return obj


def _on_the_band_excess():
    obj = _edit("tolerances.clock", "0.1216")
    obj["clock"]["rate_ratio"] = "2.0"
    return obj


def _hold_out_only():
    obj = copy.deepcopy(COMMITTED)
    obj["rungs"] = [obj["rungs"][3]]
    return obj


REFUSALS = [
    (_without("tolerances"), "plan-missing-field:tolerances"),
    (_without("tolerances.clock"), r"plan-missing-field:tolerances\.clock"),
    (_without("rungs.2.refutation_floor.group_ops"), r"plan-missing-field:rungs\.2\.refutation_floor\.group_ops"),
    (_without("comparison.ci.coverage"), r"plan-missing-field:comparison\.ci\.coverage"),
    (_without("baseline.identity_bundle_hash"), r"plan-missing-field:baseline\.identity_bundle_hash"),
    (_without("provenance.design_radius"), "provenance-missing:design_radius"),
    (_edit("extra", 1), "plan-unknown-field:extra"),
    (_edit("rungs.0.cap", 1), r"plan-unknown-field:rungs\.0\.cap"),
    (_edit("provenance.extra", "policy:x"), "provenance-unknown:extra"),
    (_edit("rungs.0.trials", "130"), r"plan-field-wrong-type:rungs\.0\.trials"),
    (_edit("rungs.0.bits", True), r"plan-field-wrong-type:rungs\.0\.bits"),
    (_edit("design_radius", 0.12), "plan-field-wrong-type:design_radius"),
    (_edit("design_radius", "1.2e-1"), "plan-field-wrong-type:design_radius"),
    (_edit("rungs.0.floor_binds", 0), r"plan-field-wrong-type:rungs\.0\.floor_binds"),
    (_edit("rungs", {}), "plan-field-wrong-type:rungs"),
    (_edit("baseline.skill", ""), r"plan-field-wrong-type:baseline\.skill"),
    (_edit("baseline.method_identity.params", {"r": 32}), r"plan-field-wrong-type:baseline\.method_identity\.params"),
    (_edit("version", 2), "plan-version-unsupported:2"),
    (_edit("comparison.version", 0), "comparison-version-unsupported:0"),
    (_edit("rungs", []), "rungs-empty"),
    (_edit("rungs.1.bits", 30), "rungs-not-ascending:1"),
    (_edit("rungs.0.role", "warmup"), r"rung-role-unknown:0\.warmup"),
    (_edit("rungs.2.role", "hold_out"), "hold-out-rung-count:2"),
    (_edit("rungs.3.role", "fit"), "hold-out-rung-count:0"),
    (_swapped_roles(), "hold-out-rung-not-largest:50"),
    (_hold_out_only(), "fit-rung-count:0"),
    (_edit("rungs.0.trials", 99), r"trials-below-floor:30\.99"),
    (_edit("rungs.3.trials", 9), r"hold-out-trials-ne-m:60\.9!=10"),
    (_edit("hold_out_m", 0), "hold-out-m-not-positive:0"),
    (_edit("rungs.0.memory_cap_bytes", 983040), "memory-cap-without-floor:30"),
    (_edit("rungs.2.memory_cap_bytes", None), "floor-without-memory-cap:50"),
    (_edit("rungs.2.memory_cap_bytes", 1000000000), r"memory-cap-ne-floor-table:50\.1000000000!=477370808"),
    (_edit("rungs.1.refutation_floor.table_entries", 0), r"floor-not-positive:40\.table_entries"),
    (_edit("design_radius", "0.5"), r"design-radius-out-of-range:0\.5"),
    (_edit("design_radius", "0"), "design-radius-out-of-range:0"),
    (_edit("keep_band_floor", "1.0"), "keep-band-floor-not-above-one:1"),
    (_edit("tolerances.wall", "1.0"), r"tolerance-out-of-range:wall\.1"),
    (_edit("tolerances.count_divergence", "0"), r"tolerance-out-of-range:count_divergence\.0"),
    (_edit("clock.rate_ratio", "0.9"), r"rate-ratio-below-one:0\.9"),
    (_edit("tolerances.clock", "0.30"), r"clock-bound-violated:0\.3\*1=0\.3>=0\.2432"),
    (_edit("clock.rate_ratio", "2.5"), r"clock-bound-violated:0\.1\*2\.5=0\.25>=0\.2432"),
    (_on_the_band_excess(), r"clock-bound-violated:0\.1216\*2=0\.2432>=0\.2432"),
    (_edit("comparison.estimator.form", "trimmed"), "estimator-form-unknown:trimmed"),
    (_edit("comparison.estimator.statistic", "ratio"), "estimator-statistic-unknown:ratio"),
    (_edit("comparison.estimator.numerator", "claim_group_ops"), "estimator-numerator-unknown:claim_group_ops"),
    (
        _edit("comparison.estimator.denominator", "baseline_group_ops"),
        "estimator-denominator-unknown:baseline_group_ops",
    ),
    (_edit("comparison.pairing.arms", ["claimant", "baseline"]), r"pairing-arms-unknown:\['claimant', 'baseline'\]"),
    (_edit("comparison.pairing.instance_stream", "per_arm"), "pairing-instance-stream-unknown:per_arm"),
    (_edit("comparison.pairing.method_seeds", "worker"), "pairing-method-seeds-unknown:worker"),
    (_edit("comparison.ci.method", "t"), "ci-method-unknown:t"),
    (_edit("comparison.ci.coverage", "1.0"), "ci-coverage-out-of-range:1"),
    (_edit("comparison.ci.coverage", "0"), "ci-coverage-out-of-range:0"),
    (_edit("comparison.ci.coverage", "-0.5"), r"ci-coverage-out-of-range:-0\.5"),
    (_edit("comparison.every_rung_must_pass", False), "every-rung-must-pass-false"),
    (_edit("baseline.identity_bundle_hash", "ab" * 31), "baseline-hash-malformed:identity_bundle_hash"),
    (_edit("baseline.implementation_revision", "G" * 64), "baseline-hash-malformed:implementation_revision"),
    (_edit("patience_ceiling.multiplier", 0), "patience-multiplier-below-one:0"),
    (_edit("patience_ceiling.basis", "wall"), "patience-basis-unknown:wall"),
    (_edit("shape_departure_tolerance", "0"), "shape-tolerance-not-positive:0"),
    (_edit("provenance.baseline", "guessed:me"), "provenance-malformed:baseline"),
    (_edit("provenance.baseline", "seeded:"), "provenance-malformed:baseline"),
    (_edit("provenance.baseline", 7), "provenance-malformed:baseline"),
    ([], "plan-not-a-mapping:list"),
]


@pytest.mark.parametrize(("obj", "reason"), REFUSALS)
def test_every_planted_malformation_refuses_with_its_typed_reason(obj, reason):
    with pytest.raises(ladderplan.LadderPlanInvalid, match=f"^{reason}$"):
        ladderplan.LadderPlan.load(obj)


def test_the_committed_plan_loads_with_its_rungs_and_the_clock_bound_holding():
    plan = ladderplan.LadderPlan.load(copy.deepcopy(COMMITTED), tiers_ceiling=TIERS["ceiling_multiplier"])
    assert [(r.bits, r.role, r.trials) for r in plan.rungs] == [
        (30, "fit", 130),
        (40, "fit", 130),
        (50, "fit", 130),
        (60, "hold_out", 10),
    ]
    assert [r.bits for r in plan.fit_rungs] == [30, 40, 50]
    assert plan.hold_out_rung.bits == 60 and plan.hold_out_m == 10
    assert plan.rung(30).memory_cap_bytes is None and plan.rung(50).memory_cap_bytes == 477370808
    assert plan.baseline.skill == "rho_dp" and plan.baseline.method_identity["params"] == {
        "variant": "plain",
        "r": "32",
    }
    assert plan.patience_multiplier == TIERS["ceiling_multiplier"]
    bound = plan.clock_bound()
    assert bound.holds and bound.describe() == "0.1*1=0.1<0.2432"
    assert (plan.hash, plan.bundle_hash) == (None, None)
    with pytest.raises(KeyError, match="no 70-bit rung"):
        plan.rung(70)


def test_the_patience_ceiling_must_agree_with_the_tiers_object_when_one_is_given():
    with pytest.raises(ladderplan.LadderPlanInvalid, match=r"^patience-ceiling-ne-tiers:4!=8$"):
        ladderplan.LadderPlan.load(copy.deepcopy(COMMITTED), tiers_ceiling=8)


def test_the_committed_plan_seeds_exactly_the_fields_their_owner_beads_write():
    plan = ladderplan.LadderPlan.load(copy.deepcopy(COMMITTED))
    assert plan.seeded_fields() == SEEDED_TODAY
    owners = {key: plan.provenance[key].split(":", 1)[1] for key in SEEDED_TODAY}
    assert owners == {
        "rungs.trials": "cairn-m1-cqt.1.7",
        "design_radius": "cairn-m1-cqt.1.7",
        "clock.rate_ratio": "cairn-m1-cqt.1.4",
    }


@pytest.mark.parametrize("marker", ["measured:research/grounding/m1-dlp-skill-costs.md", "written:cairn-m1-cqt.2.1"])
def test_a_field_leaves_the_seeded_list_when_its_owner_records_the_replacement(marker):
    obj = copy.deepcopy(COMMITTED)
    obj["provenance"]["rungs.trials"] = marker
    plan = ladderplan.LadderPlan.load(obj)
    assert "rungs.trials" not in plan.seeded_fields()
    assert len(plan.seeded_fields()) == len(SEEDED_TODAY) - 1


def test_the_floor_and_cap_carry_the_measured_bsgs_figures_and_the_60_bit_extrapolation():
    plan = ladderplan.LadderPlan.load(copy.deepcopy(COMMITTED))
    for bits, (ops, entries, table_bytes) in MEASURED_FLOOR.items():
        floor = plan.rung(bits).refutation_floor
        assert (floor.group_ops, floor.table_entries, floor.memory_bytes) == (ops, entries, table_bytes)
    hold_out = plan.rung(60).refutation_floor
    assert hold_out.group_ops == round(2**30 * MEASURED_FLOOR[50][0] / MEASURED_FLOOR[50][1])
    assert hold_out.table_entries == 2**30
    assert hold_out.memory_bytes == int(2**30 * BYTES_PER_ENTRY)
    for rung in plan.rungs:
        assert rung.floor_binds == (rung.bits >= 50)
        assert rung.memory_cap_bytes == (rung.refutation_floor.memory_bytes if rung.floor_binds else None)
    for key in ("rungs.refutation_floor", "rungs.memory_cap_bytes"):
        assert plan.provenance[key].startswith("measured:research/grounding/m1-dlp-skill-costs.md")


def test_the_seeded_design_radius_is_the_independent_arms_radius_at_the_seeded_count():
    plan = ladderplan.LadderPlan.load(copy.deepcopy(COMMITTED))
    n = plan.rung(30).trials
    radius = Decimal("1.959964") * Decimal("0.5") * Decimal(2 / n).sqrt()
    assert abs(plan.design_radius - radius) < Decimal("0.0001")


def test_the_node_is_json_serializable_and_carries_the_hashes_it_was_loaded_with():
    plan = ladderplan.LadderPlan.load(copy.deepcopy(COMMITTED), plan_hash="a" * 64, bundle_hash="b" * 64)
    node = json.loads(json.dumps(plan.node(), sort_keys=True))
    assert (node["hash"], node["bundle_hash"]) == ("a" * 64, "b" * 64)
    assert node["seeded"] == SEEDED_TODAY
    assert node["clock_bound"] == {
        "clock_tolerance": "0.1",
        "rate_ratio": "1",
        "product": "0.1",
        "keep_band_excess": "0.2432",
        "holds": True,
    }
    assert node["tolerances"] == {"count_divergence": "0.01", "clock": "0.1", "wall": "0.25"}
    assert [r["bits"] for r in node["rungs"]] == [30, 40, 50, 60]


@given(
    tolerance=st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("0.9999"), places=4),
    ratio=st.decimals(min_value=Decimal(1), max_value=Decimal(20), places=2),
    radius=st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("0.4999"), places=4),
)
@settings(max_examples=200)
def test_the_clock_bound_refuses_exactly_when_the_product_reaches_the_band_excess(tolerance, ratio, radius):
    obj = _edit("tolerances.clock", str(tolerance))
    obj["clock"]["rate_ratio"] = str(ratio)
    obj["design_radius"] = str(radius)
    if tolerance * ratio < 2 * radius:
        plan = ladderplan.LadderPlan.load(obj)
        assert plan.clock_bound().holds and plan.clock_bound().product == tolerance * ratio
    else:
        with pytest.raises(ladderplan.LadderPlanInvalid, match=r"^clock-bound-violated:.*>=") as info:
            ladderplan.LadderPlan.load(obj)
        assert info.value.reason.endswith(f">={(2 * radius).normalize():f}")
