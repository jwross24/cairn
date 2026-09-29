import sys
from pathlib import Path

import pytest

from cairn import claims, container, scrutiny, solutionplan
from cairn.solutionplan import PlanInvalid, PlanResult, StepResult

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories

ARM = container.DEV_ARM
FORMAL = "f0" * 32
RENDERER = "e1" * 32
PRELUDE = "d2" * 32


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


def step_result(kind, result="pass", reasons=()):
    return StepResult(
        step=kind,
        kind=kind,
        expected=solutionplan.KIND_EXPECTATION[kind],
        observed=result if result != "pass" else solutionplan.KIND_EXPECTATION[kind],
        result=result,
        reasons=tuple(reasons),
        wall_ms=1,
    )


def plan_result(**overrides):
    steps = tuple(step_result(kind, **overrides.get(kind, {})) for kind in solutionplan.STEP_KINDS)
    return PlanResult(steps, ARM)


def persist(sub, result, statement, **overrides):
    binding = {
        "bundle_hash": "b3" * 32,
        "pin_hash": "a4" * 32,
        "statement_hash": statement.hash,
        "formal_statement_hash": FORMAL,
        "renderer_hash": RENDERER,
        "prelude_hash": PRELUDE,
        "at": factories.CREATED_AT,
    }
    binding.update(overrides)
    return solutionplan.persist(sub, result, **binding)


@pytest.fixture
def statement(writer):
    stmt = factories.claim_statement(seed=31, formal_source="theorem T : True := trivial")
    claims.write_claim_statement(writer, stmt)
    return stmt


def rows(sub, gate):
    return [
        dict(r)
        for r in sub.conn.execute("SELECT * FROM gate_runs WHERE gate = ? ORDER BY plan_step", (gate,)).fetchall()
    ]


def test_the_scrutiny_constants_equal_the_plan_constants():
    assert scrutiny.FORMALIZATION_GATE_NAME == solutionplan.SUMMARY_GATE
    assert scrutiny.FORMALIZATION_SUMMARY_STEP == solutionplan.SUMMARY_STEP


def test_an_all_pass_plan_persists_six_step_rows_and_one_passing_summary(writer, statement):
    summary_hash, step_hashes = persist(writer, plan_result(), statement)
    assert len(step_hashes) == len(set(step_hashes)) == len(solutionplan.STEP_KINDS)
    steps = rows(writer, solutionplan.STEP_GATE)
    assert sorted(r["plan_step"] for r in steps) == sorted(solutionplan.STEP_KINDS)
    assert {r["run_id"] for r in steps} == set(step_hashes)
    for r in steps:
        assert (r["result"], r["arm"], r["statement_hash"], r["formal_statement_hash"]) == (
            "pass",
            ARM,
            statement.hash,
            FORMAL,
        )
        assert (r["renderer_hash"], r["prelude_hash"]) == (RENDERER, PRELUDE)
    (summary,) = rows(writer, solutionplan.SUMMARY_GATE)
    assert summary["run_id"] == summary_hash
    assert (summary["plan_step"], summary["result"], summary["arm"]) == (solutionplan.SUMMARY_STEP, "pass", ARM)
    assert summary["formal_statement_hash"] == FORMAL
    assert scrutiny._formalization_passed(writer, statement.hash) is True


def test_a_timed_out_step_persists_as_timeout_never_fail_and_the_summary_fails(writer, statement):
    result = plan_result(
        build={"result": "timeout", "reasons": (solutionplan.TIMEOUT_REASON, "timeout_s:600.0")},
        axiom_computation={"result": "blocked", "reasons": ("blocked-by:build",)},
        kernel_replay={"result": "blocked", "reasons": ("blocked-by:build",)},
        closure_comparison={"result": "blocked", "reasons": ("blocked-by:build",)},
    )
    summary_hash, _ = persist(writer, result, statement)
    by_step = {r["plan_step"]: r for r in rows(writer, solutionplan.STEP_GATE)}
    assert by_step["build"]["result"] == solutionplan.RESULT_TIMEOUT
    assert solutionplan.TIMEOUT_REASON in by_step["build"]["reasons"]
    assert "fail" not in {row["result"] for row in by_step.values()}
    assert by_step["kernel_replay"]["result"] == "blocked"
    (summary,) = rows(writer, solutionplan.SUMMARY_GATE)
    assert summary["run_id"] == summary_hash
    assert summary["result"] == "fail"
    assert "first-failure:build" in summary["reasons"]
    assert scrutiny._formalization_passed(writer, statement.hash) is False


def test_a_plan_missing_a_step_kind_fails_the_summary(writer, statement):
    full = plan_result()
    short = PlanResult(full.steps[:-1], ARM)
    persist(writer, short, statement)
    (summary,) = rows(writer, solutionplan.SUMMARY_GATE)
    assert summary["result"] == "fail"
    assert solutionplan.INCOMPLETE_PLAN_REASON in summary["reasons"]
    assert scrutiny._formalization_passed(writer, statement.hash) is False


@pytest.mark.parametrize("formal", [None, ""])
def test_an_all_pass_plan_without_a_formal_statement_hash_fails_the_summary(writer, statement, formal):
    persist(writer, plan_result(), statement, formal_statement_hash=formal)
    (summary,) = rows(writer, solutionplan.SUMMARY_GATE)
    assert summary["result"] == "fail"
    assert scrutiny._formalization_passed(writer, statement.hash) is False


def test_an_empty_result_is_refused_and_writes_nothing(writer, statement):
    with pytest.raises(PlanInvalid) as caught:
        persist(writer, PlanResult((), ARM), statement)
    assert caught.value.reason == "plan-result-empty"
    assert writer.conn.execute("SELECT COUNT(*) FROM gate_runs").fetchone()[0] == 0


def test_a_step_result_outside_the_vocabulary_is_refused_and_writes_nothing(writer, statement):
    result = plan_result(build={"result": "green"})
    with pytest.raises(PlanInvalid, match="unknown-step-result"):
        persist(writer, result, statement)
    assert writer.conn.execute("SELECT COUNT(*) FROM gate_runs").fetchone()[0] == 0


def test_a_plan_result_naming_no_arm_is_refused_and_writes_nothing(writer, statement):
    result = PlanResult(plan_result().steps, "no-such-arm")
    with pytest.raises(container.ArmUnknown):
        persist(writer, result, statement)
    assert writer.conn.execute("SELECT COUNT(*) FROM gate_runs").fetchone()[0] == 0


def test_persisting_the_same_result_twice_is_idempotent(writer, statement):
    first = persist(writer, plan_result(), statement)
    second = persist(writer, plan_result(), statement)
    assert first == second
    assert writer.conn.execute("SELECT COUNT(*) FROM gate_runs").fetchone()[0] == len(solutionplan.STEP_KINDS) + 1
