import copy
import json
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cairn import gateplan

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mutants import gateplan_mutants  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = json.loads((ROOT / "bundle" / "gate_plan.json").read_text())["steps"]


def _without(step_name):
    return [row for row in copy.deepcopy(COMMITTED) if row["step"] != step_name]


def _mutate(index, **fields):
    rows = copy.deepcopy(COMMITTED)
    rows[index].update(fields)
    return rows


def _duplicated():
    rows = copy.deepcopy(COMMITTED)
    rows[2]["step"] = rows[1]["step"]
    return rows


REFUSALS = [
    *[(_without(name), f"missing-required-selftest:{name}") for name in gateplan.REQUIRED_STEPS],
    (_mutate(0, kind="not-a-kind"), r"unknown-step-kind:0\."),
    (_duplicated(), r"duplicate-step-name:2\."),
    (_mutate(1, expect="not-in-the-vocabulary"), r"expect-outside-vocabulary:1\."),
    ([], "plan-empty"),
]


@pytest.mark.parametrize("plan_rows,expected_reason", REFUSALS)
def test_an_invalid_plan_is_refused_before_any_step_runs(plan_rows, expected_reason):
    with pytest.raises(gateplan.PlanInvalid, match=expected_reason):
        gateplan.GatePlan.load(plan_rows)


def test_the_committed_plan_loads_and_carries_every_required_step():
    plan = gateplan.GatePlan.load(copy.deepcopy(COMMITTED))
    names = [step.step for step in plan.steps]
    assert set(gateplan.REQUIRED_STEPS) <= set(names)
    assert len(names) == len(set(names))


def _synthetic(count):
    return tuple(gateplan.Step(step=f"s{i}", kind=gateplan.KIND_CANON_KAT, expect=gateplan.EXPECT_PASS) for i in range(count))


def _observer(outcomes):
    scripted = dict(zip((f"s{i}" for i in range(len(outcomes))), outcomes))
    seen = []

    def observe(step):
        seen.append(step.step)
        return (gateplan.EXPECT_PASS if scripted[step.step] == "pass" else "observed-fail"), (), (None, None)

    return observe, seen


@given(outcomes=st.lists(st.sampled_from(["pass", "fail"]), min_size=1, max_size=20))
@settings(max_examples=500)
def test_the_first_failure_blocks_every_later_step_and_each_blocked_row_names_the_blocker(outcomes):
    steps = _synthetic(len(outcomes))
    observe, executed = _observer(outcomes)
    rows = list(gateplan.plan_outcomes(steps, observe))
    assert [row[0].step for row in rows] == [step.step for step in steps]
    results = [row[2] for row in rows]
    if "fail" not in outcomes:
        assert results == [gateplan.RESULT_PASS] * len(outcomes)
        assert executed == [step.step for step in steps]
        return
    first = outcomes.index("fail")
    assert results[:first] == [gateplan.RESULT_PASS] * first
    assert results[first] == gateplan.RESULT_FAIL
    assert results[first + 1 :] == [gateplan.RESULT_BLOCKED] * (len(outcomes) - first - 1)
    for row in rows[first + 1 :]:
        assert row[3] == (f"{gateplan.BLOCKED_PREFIX}s{first}",)
    assert executed == [f"s{i}" for i in range(first + 1)]


def _blocking_property_holds(outcomes):
    steps = _synthetic(len(outcomes))
    observe, executed = _observer(outcomes)
    rows = list(gateplan.plan_outcomes(steps, observe))
    first = outcomes.index("fail")
    if [row[2] for row in rows][first + 1 :] != [gateplan.RESULT_BLOCKED] * (len(outcomes) - first - 1):
        return False
    if any(row[3] != (f"{gateplan.BLOCKED_PREFIX}s{first}",) for row in rows[first + 1 :]):
        return False
    return executed == [f"s{i}" for i in range(first + 1)]


FAIL_THEN_TWO = ["pass", "fail", "pass", "pass"]


def test_continue_after_failure_mutant_is_killed():
    assert _blocking_property_holds(FAIL_THEN_TWO)
    with gateplan_mutants.continue_after_failure():
        assert not _blocking_property_holds(FAIL_THEN_TWO)


def test_blocks_name_wrong_step_mutant_is_killed():
    assert _blocking_property_holds(FAIL_THEN_TWO)
    with gateplan_mutants.blocks_name_wrong_step():
        assert not _blocking_property_holds(FAIL_THEN_TWO)

