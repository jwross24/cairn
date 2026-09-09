import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from cairn import ladderplan

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = json.loads((ROOT / "bundle" / "ladder_plan.json").read_text())
TIERS = json.loads((ROOT / "bundle" / "tiers.json").read_text())
REFERENCE = COMMITTED["clock"]["reference_cost"]
PLAUSIBLE_LOW = Decimal("0.000000001")
PLAUSIBLE_HIGH = Decimal("0.001")


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


def _reciprocal(text):
    return f"{Decimal(1) / Decimal(text):.4f}"


def _one_arm_of_throughputs():
    arm = REFERENCE["arms"][REFERENCE["arm"]]
    flipped = {
        "cost_s_per_group_op_min": _reciprocal(arm["cost_s_per_group_op_max"]),
        "cost_s_per_group_op_median": _reciprocal(arm["cost_s_per_group_op_median"]),
        "cost_s_per_group_op_max": _reciprocal(arm["cost_s_per_group_op_min"]),
        "cost_s_per_group_op_sd": _reciprocal(arm["cost_s_per_group_op_sd"]),
    }
    obj = _edit("clock.reference_cost.arms", {REFERENCE["arm"]: flipped})
    obj["clock"]["reference_cost"]["cost_s_per_group_op"] = flipped["cost_s_per_group_op_median"]
    return obj


def _every_arm_of_throughputs():
    arms = {}
    for name, row in REFERENCE["arms"].items():
        arms[name] = {
            "cost_s_per_group_op_min": _reciprocal(row["cost_s_per_group_op_max"]),
            "cost_s_per_group_op_median": _reciprocal(row["cost_s_per_group_op_median"]),
            "cost_s_per_group_op_max": _reciprocal(row["cost_s_per_group_op_min"]),
            "cost_s_per_group_op_sd": _reciprocal(row["cost_s_per_group_op_sd"]),
        }
    obj = _edit("clock.reference_cost.arms", arms)
    obj["clock"]["reference_cost"]["cost_s_per_group_op"] = arms[REFERENCE["arm"]]["cost_s_per_group_op_median"]
    return obj


def _slowest_arm_named():
    slowest = max(REFERENCE["arms"], key=lambda n: Decimal(REFERENCE["arms"][n]["cost_s_per_group_op_median"]))
    obj = _edit("clock.reference_cost.arm", slowest)
    obj["clock"]["reference_cost"]["cost_s_per_group_op"] = REFERENCE["arms"][slowest]["cost_s_per_group_op_median"]
    return obj, slowest


REFUSALS = [
    (_without("clock.reference_cost"), r"plan-missing-field:clock\.reference_cost"),
    (_without("clock.reference_cost.arm"), r"plan-missing-field:clock\.reference_cost\.arm"),
    (_without("clock.reference_cost.grounding"), r"plan-missing-field:clock\.reference_cost\.grounding"),
    (
        _without("clock.reference_cost.cost_s_per_group_op"),
        r"plan-missing-field:clock\.reference_cost\.cost_s_per_group_op",
    ),
    (
        _without("clock.reference_cost.arms.c_reference.cost_s_per_group_op_sd"),
        r"plan-missing-field:clock\.reference_cost\.arms\.c_reference\.cost_s_per_group_op_sd",
    ),
    (_edit("clock.reference_cost.extra", 1), r"plan-unknown-field:clock\.reference_cost\.extra"),
    (_edit("clock.reference_cost.arm", ""), r"plan-field-wrong-type:clock\.reference_cost\.arm"),
    (
        _edit("clock.reference_cost.cost_s_per_group_op", 2.1e-7),
        r"plan-field-wrong-type:clock\.reference_cost\.cost_s_per_group_op",
    ),
    (
        _edit("clock.reference_cost.arms.c_reference.cost_s_per_group_op_median", "2.1210e-7"),
        r"plan-field-wrong-type:clock\.reference_cost\.arms\.c_reference\.cost_s_per_group_op_median",
    ),
    (_edit("clock.reference_cost.arms", {}), r"plan-field-wrong-type:clock\.reference_cost\.arms"),
    (_edit("clock.reference_cost.arms", []), r"plan-field-wrong-type:clock\.reference_cost\.arms"),
    (
        _edit("clock.reference_cost.arms.c_reference.cost_s_per_group_op_sd", "-0.000000001"),
        "reference-cost-spread-negative:c_reference",
    ),
    (
        _edit("clock.reference_cost.arms.c_reference.cost_s_per_group_op_min", "0"),
        "reference-cost-not-positive:c_reference",
    ),
    (
        _edit("clock.reference_cost.arms.c_reference.cost_s_per_group_op_max", "0.000000100000"),
        "reference-cost-not-ordered:c_reference",
    ),
    (_edit("clock.reference_cost.arm", "rust_reference"), "reference-cost-arm-unmeasured:rust_reference"),
    (
        _edit("clock.reference_cost.cost_s_per_group_op", "0.000000212000"),
        r"reference-cost-not-its-arm-median:0\.000000212",
    ),
]


@pytest.mark.parametrize(("obj", "reason"), REFUSALS)
def test_every_planted_malformation_of_the_reference_cost_refuses(obj, reason):
    with pytest.raises(ladderplan.LadderPlanInvalid, match=f"^{reason}$"):
        ladderplan.LadderPlan.load(obj)


def test_naming_a_slower_arm_than_the_fastest_measured_one_refuses():
    obj, slowest = _slowest_arm_named()
    with pytest.raises(ladderplan.LadderPlanInvalid, match=f"^reference-cost-not-the-fastest-arm:{slowest}!="):
        ladderplan.LadderPlan.load(obj)


def test_a_throughput_planted_where_the_cost_belongs_refuses_as_not_a_per_operation_cost():
    obj = _one_arm_of_throughputs()
    stored = obj["clock"]["reference_cost"]["cost_s_per_group_op"]
    assert Decimal(stored) > ladderplan.MAX_GROUP_OP_COST_S
    with pytest.raises(ladderplan.LadderPlanInvalid, match=r"^reference-cost-not-a-per-operation-cost:"):
        ladderplan.LadderPlan.load(obj)


def test_every_arm_reciprocated_refuses_before_the_unit_check_because_the_fastest_arm_inverts():
    with pytest.raises(ladderplan.LadderPlanInvalid, match=r"^reference-cost-not-the-fastest-arm:"):
        ladderplan.LadderPlan.load(_every_arm_of_throughputs())


@pytest.fixture
def plan():
    return ladderplan.LadderPlan.load(copy.deepcopy(COMMITTED), tiers_ceiling=TIERS["ceiling_multiplier"])


def test_the_committed_plan_carries_the_reference_cost_with_its_declared_shape(plan):
    reference = plan.reference_cost
    assert reference.arm in reference.arms
    assert set(reference.arms) == set(REFERENCE["arms"])
    for row in reference.arms.values():
        assert set(row) == set(ladderplan.REFERENCE_ARM_FIELDS)
        assert all(isinstance(value, Decimal) for value in row.values())


def test_the_recorded_figure_is_a_cost_in_seconds_per_group_operation(plan):
    cost = plan.reference_cost.cost_s_per_group_op
    assert PLAUSIBLE_LOW < cost < PLAUSIBLE_HIGH
    assert cost < ladderplan.MAX_GROUP_OP_COST_S
    assert Decimal(1) / cost > Decimal(1000)


def test_the_recorded_figure_is_the_fastest_arms_median(plan):
    reference = plan.reference_cost
    medians = {name: row["cost_s_per_group_op_median"] for name, row in reference.arms.items()}
    assert reference.cost_s_per_group_op == medians[reference.arm]
    assert reference.cost_s_per_group_op == min(medians.values())


def test_every_arm_reports_an_ordered_positive_spread(plan):
    for row in plan.reference_cost.arms.values():
        assert row["cost_s_per_group_op_min"] > 0
        assert row["cost_s_per_group_op_min"] <= row["cost_s_per_group_op_median"] <= row["cost_s_per_group_op_max"]
        assert row["cost_s_per_group_op_sd"] >= 0
        assert row["cost_s_per_group_op_sd"] < row["cost_s_per_group_op_median"]


def test_the_grounding_the_plan_names_is_a_file_in_the_tree(plan):
    assert (ROOT / plan.reference_cost.grounding).is_file()


def test_the_reference_cost_carries_a_measured_provenance_entry(plan):
    entry = plan.provenance["clock.reference_cost"]
    assert entry.startswith("measured:")
    assert plan.reference_cost.grounding in entry


def test_the_reference_cost_is_part_of_the_plan_identity(plan):
    moved = ladderplan.LadderPlan.load(
        _edit("clock.reference_cost.grounding", "research/grounding/elsewhere.md"),
        tiers_ceiling=TIERS["ceiling_multiplier"],
    )
    assert moved.node() != plan.node()
