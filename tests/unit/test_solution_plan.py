import pytest

from cairn import container, solutionplan
from cairn.solutionplan import (
    KIND_AXIOMS,
    KIND_BUILD,
    KIND_IMPORT_ALLOWLIST,
    KIND_KERNEL_REPLAY,
    PlanInvalid,
    SolutionPlan,
    StepTimeout,
)

ARM = container.DEV_ARM


def _row(kind, *, step=None, blocking=True, timeout_s=600.0, expect=None):
    return {
        "step": step or kind,
        "kind": kind,
        "expect": solutionplan.KIND_EXPECTATION[kind] if expect is None else expect,
        "blocking": blocking,
        "timeout_s": timeout_s,
    }


def _plan_rows(*kinds):
    return [_row(kind) for kind in kinds]


COMPLETE = (KIND_IMPORT_ALLOWLIST, KIND_BUILD, KIND_AXIOMS, KIND_KERNEL_REPLAY)


def _observer(verdicts):
    def observe(step):
        outcome = verdicts[step.kind]
        if isinstance(outcome, StepTimeout):
            raise outcome
        return outcome, (), 3

    return observe


def _all_expected():
    return {kind: solutionplan.KIND_EXPECTATION[kind] for kind in COMPLETE}


def test_a_complete_plan_loads_in_the_declared_order():
    plan = SolutionPlan.load(_plan_rows(*COMPLETE), arm=ARM)
    assert [step.kind for step in plan.steps] == list(COMPLETE)
    assert plan.arm == ARM


@pytest.mark.parametrize("dropped", [KIND_AXIOMS, KIND_KERNEL_REPLAY])
def test_a_plan_carrying_one_checker_step_without_the_other_is_refused(dropped):
    kinds = [kind for kind in COMPLETE if kind != dropped]
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(_plan_rows(*kinds), arm=ARM)
    assert caught.value.reason == f"checker-steps-are-a-pair:missing:{dropped}"


@pytest.mark.parametrize("dropped", [KIND_IMPORT_ALLOWLIST, KIND_BUILD])
def test_a_plan_missing_a_mandatory_step_is_refused(dropped):
    kinds = [kind for kind in COMPLETE if kind != dropped]
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(_plan_rows(*kinds), arm=ARM)
    assert caught.value.reason == f"missing-mandatory-step:{dropped}"


def test_a_plan_carrying_neither_checker_step_names_the_first_missing_one():
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(_plan_rows(KIND_IMPORT_ALLOWLIST, KIND_BUILD), arm=ARM)
    assert caught.value.reason == f"missing-mandatory-step:{KIND_AXIOMS}"


def test_a_mandatory_step_declared_non_blocking_is_refused():
    rows = _plan_rows(*COMPLETE)
    rows[2]["blocking"] = False
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(rows, arm=ARM)
    assert caught.value.reason == f"mandatory-step-not-blocking:{KIND_AXIOMS}"


def test_the_import_allowlist_may_not_sit_after_the_build():
    kinds = (KIND_BUILD, KIND_IMPORT_ALLOWLIST, KIND_AXIOMS, KIND_KERNEL_REPLAY)
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(_plan_rows(*kinds), arm=ARM)
    assert caught.value.reason == "import-allowlist-after-build"


def test_a_checker_step_before_the_build_is_refused():
    kinds = (KIND_IMPORT_ALLOWLIST, KIND_AXIOMS, KIND_BUILD, KIND_KERNEL_REPLAY)
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(_plan_rows(*kinds), arm=ARM)
    assert caught.value.reason == f"checker-before-build:{KIND_AXIOMS}"


def test_a_duplicate_step_kind_is_refused():
    rows = [*_plan_rows(*COMPLETE), _row(KIND_AXIOMS, step="axioms_again")]
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(rows, arm=ARM)
    assert caught.value.reason == f"duplicate-step-kind:{KIND_AXIOMS}"


def test_a_duplicate_step_name_is_refused():
    rows = _plan_rows(*COMPLETE)
    rows[3]["step"] = rows[2]["step"]
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(rows, arm=ARM)
    assert caught.value.reason.startswith("duplicate-step-name:")


def test_an_expectation_belonging_to_another_kind_is_refused():
    rows = _plan_rows(*COMPLETE)
    rows[1]["expect"] = solutionplan.EXPECT_REPLAYED
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(rows, arm=ARM)
    assert caught.value.reason == f"expect-not-this-kind:1.{KIND_BUILD}.{solutionplan.EXPECT_REPLAYED}"


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda row: row.pop("timeout_s"), "step-missing-field:0.timeout_s"),
        (lambda row: row.update(blocking="yes"), "step-field-wrong-type:0.blocking"),
        (lambda row: row.update(timeout_s=0), "step-field-wrong-type:0.timeout_s"),
        (lambda row: row.update(timeout_s=True), "step-field-wrong-type:0.timeout_s"),
        (lambda row: row.update(kind="lint"), "unknown-step-kind:0.'lint'"),
        (lambda row: row.update(extra=1), "unknown-step-field:0.'extra'"),
    ],
)
def test_a_malformed_step_is_refused_by_field(mutate, reason):
    rows = _plan_rows(*COMPLETE)
    mutate(rows[0])
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(rows, arm=ARM)
    assert caught.value.reason == reason


@pytest.mark.parametrize(("rows", "reason"), [({}, "plan-not-a-list:dict"), ([], "plan-empty")])
def test_a_plan_that_is_not_a_non_empty_list_is_refused(rows, reason):
    with pytest.raises(PlanInvalid) as caught:
        SolutionPlan.load(rows, arm=ARM)
    assert caught.value.reason == reason


def test_an_arm_outside_the_container_arms_is_refused():
    with pytest.raises(container.ArmUnknown) as caught:
        SolutionPlan.load(_plan_rows(*COMPLETE), arm="laptop")
    assert caught.value.arm == "laptop"


def test_every_step_passes_when_each_observation_matches_its_expectation():
    plan = SolutionPlan.load(_plan_rows(*COMPLETE), arm=ARM)
    result = plan.run(_observer(_all_expected()))
    assert result.ok is True
    assert result.first_failure is None
    assert [step.result for step in result.steps] == [solutionplan.RESULT_PASS] * 4


def test_a_failed_step_blocks_every_step_below_it_and_the_checkers_never_run():
    verdicts = {**_all_expected(), KIND_IMPORT_ALLOWLIST: "refused:Lean"}
    plan = SolutionPlan.load(_plan_rows(*COMPLETE), arm=ARM)
    result = plan.run(_observer(verdicts))
    assert result.ok is False
    assert result.first_failure.step == KIND_IMPORT_ALLOWLIST
    assert [step.result for step in result.steps] == [
        solutionplan.RESULT_FAIL,
        *[solutionplan.RESULT_BLOCKED] * 3,
    ]
    assert result.steps[0].reasons == (solutionplan.MISMATCH_REASON, "observed:refused:Lean")
    assert result.steps[1].reasons == (f"{solutionplan.BLOCKED_PREFIX}{KIND_IMPORT_ALLOWLIST}",)


def test_a_timeout_is_its_own_result_and_is_not_a_failed_verdict():
    verdicts = {**_all_expected(), KIND_KERNEL_REPLAY: StepTimeout(KIND_KERNEL_REPLAY, 600.0)}
    plan = SolutionPlan.load(_plan_rows(*COMPLETE), arm=ARM)
    result = plan.run(_observer(verdicts))
    replay = result.steps[-1]
    assert replay.result == solutionplan.RESULT_TIMEOUT
    assert replay.result != solutionplan.RESULT_FAIL
    assert replay.reasons == (solutionplan.TIMEOUT_REASON, "timeout_s:600.0")
    assert result.ok is False
    assert result.first_failure.step == KIND_KERNEL_REPLAY
