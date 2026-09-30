import json
import sys
from pathlib import Path

import pytest

from cairn import bundle, challenge, claims, container, justify, scrutiny, solutionbuild, solutionchecks, solutionplan
from cairn.solutionplan import PlanInvalid, PlanResult, StepResult, StepTimeout

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories

ARM = container.GOLD_ARM
FORMAL = "f0" * 32
RENDERER = "e1" * 32
PRELUDE = "d2" * 32


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def gate(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


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


def _plan_rows():
    return [
        {
            "step": kind,
            "kind": kind,
            "expect": solutionplan.KIND_EXPECTATION[kind],
            "blocking": True,
            "timeout_s": 31.0,
        }
        for kind in solutionplan.STEP_KINDS
    ]


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


@pytest.mark.parametrize(
    ("mode", "summary_result", "failed_step"),
    [
        ("pass", "pass", None),
        ("fail", "fail", solutionplan.KIND_IMPORT_ALLOWLIST),
        ("timeout", "fail", solutionplan.KIND_BUILD),
    ],
)
def test_run_persists_every_step_and_summary_with_the_execution_bindings(
    writer, statement, mode, summary_result, failed_step
):
    plan = solutionplan.SolutionPlan.load(_plan_rows(), arm=ARM)

    def observe(step):
        if mode == "fail" and step.kind == solutionplan.KIND_IMPORT_ALLOWLIST:
            return solutionplan.OBSERVED_REFUSED, ("import-refused:Lean",), 12
        if mode == "timeout" and step.kind == solutionplan.KIND_BUILD:
            raise StepTimeout(step.step, step.timeout_s)
        return step.expect, (), 9

    binding = {
        "bundle_hash": "b3" * 32,
        "pin_hash": "a4" * 32,
        "statement_hash": statement.hash,
        "formal_statement_hash": FORMAL,
        "renderer_hash": RENDERER,
        "prelude_hash": PRELUDE,
        "at": factories.CREATED_AT,
    }
    result = plan.run(observe, writer, **binding)
    persisted_steps = rows(writer, solutionplan.STEP_GATE)
    by_step = {row["plan_step"]: row for row in persisted_steps}
    assert len(persisted_steps) == len(solutionplan.STEP_KINDS)
    assert len(by_step) == len(solutionplan.STEP_KINDS)
    for step in result.steps:
        row = by_step[step.step]
        assert row["gate"] == solutionplan.STEP_GATE
        assert row["result"] == step.result
        assert tuple(json.loads(row["reasons"])) == step.reasons
        for field, value in binding.items():
            assert row[field] == value
        assert row["arm"] == result.arm
    (summary,) = rows(writer, solutionplan.SUMMARY_GATE)
    assert summary["gate"] == solutionplan.SUMMARY_GATE
    assert summary["plan_step"] == solutionplan.SUMMARY_STEP
    assert summary["result"] == summary_result
    assert tuple(json.loads(summary["reasons"])) == (
        () if failed_step is None else (f"{solutionplan.FIRST_FAILURE_PREFIX}{failed_step}",)
    )
    for field, value in binding.items():
        assert summary[field] == value
    assert summary["arm"] == result.arm
    assert writer.conn.execute("SELECT COUNT(*) FROM gate_runs").fetchone()[0] == len(solutionplan.STEP_KINDS) + 1
    if mode == "timeout":
        build = by_step[solutionplan.KIND_BUILD]
        assert build["result"] == solutionplan.RESULT_TIMEOUT
        assert tuple(json.loads(build["reasons"])) == (solutionplan.TIMEOUT_REASON, "timeout_s:31.0")
        assert [step.result for step in result.steps[3:]] == [solutionplan.RESULT_BLOCKED] * 3


def test_run_dev_persists_a_stale_submission_refusal_automatically(gate, writer, statement, tmp_path, monkeypatch):
    theorem_names = ("answer",)
    project = solutionbuild.prepare_challenge(gate, statement, theorem_names, root=tmp_path / "prepared")
    prepared = solutionchecks.PreparedChallenge(
        project=project,
        statement_hash=statement.hash,
        bundle_hash=gate.hash,
        pin_hash=gate.pin_hash,
        renderer_hash=gate.digest_of(challenge.RENDERER_KIND),
        prelude_hash=gate.digest_of(challenge.PRELUDE_KIND),
        formal_statement_hash=FORMAL,
        image=None,
    )
    monkeypatch.setattr(solutionchecks.cli, "now_iso", lambda: factories.CREATED_AT)
    result = solutionchecks.run_dev(
        gate,
        statement,
        challenge.Submission(solution_module=b"", formal_statement_hash="0" * 64),
        theorem_names,
        _plan_rows(),
        sub=writer,
        root=tmp_path / "candidate",
        prepared=prepared,
        comparator=None,
    )
    assert result.ok is False
    assert result.first_failure == result.steps[0]
    assert [step.result for step in result.steps] == [solutionplan.RESULT_FAIL] + [solutionplan.RESULT_BLOCKED] * 5
    step_rows = rows(writer, solutionplan.STEP_GATE)
    by_step = {row["plan_step"]: row for row in step_rows}
    assert len(step_rows) == len(solutionplan.STEP_KINDS)
    assert set(by_step) == set(solutionplan.STEP_KINDS)
    binding = {
        "bundle_hash": gate.hash,
        "pin_hash": gate.pin_hash,
        "statement_hash": statement.hash,
        "formal_statement_hash": prepared.formal_statement_hash,
        "renderer_hash": gate.digest_of(challenge.RENDERER_KIND),
        "prelude_hash": gate.digest_of(challenge.PRELUDE_KIND),
        "arm": container.DEV_ARM,
        "at": factories.CREATED_AT,
    }
    for step in result.steps:
        row = by_step[step.step]
        assert row["gate"] == solutionplan.STEP_GATE
        assert row["result"] == step.result
        assert tuple(json.loads(row["reasons"])) == step.reasons
        for field, value in binding.items():
            assert row[field] == value
    (summary,) = rows(writer, solutionplan.SUMMARY_GATE)
    assert summary["plan_step"] == solutionplan.SUMMARY_STEP
    assert summary["result"] == "fail"
    assert tuple(json.loads(summary["reasons"])) == (
        f"{solutionplan.FIRST_FAILURE_PREFIX}{solutionplan.KIND_STATEMENT_BINDING}",
    )
    for field, value in binding.items():
        assert summary[field] == value
    assert writer.conn.execute("SELECT COUNT(*) FROM gate_runs").fetchone()[0] == len(solutionplan.STEP_KINDS) + 1


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


def test_a_complete_passing_plan_emits_one_artifact_bound_to_its_summary_and_steps(writer, statement):
    summary_hash, step_hashes = persist(writer, plan_result(), statement)
    (artifact,) = claims.evidence_for(writer, statement.hash)
    assert (artifact["kind"], artifact["producer_identity"], artifact["producer_tag"], artifact["verdict"]) == (
        "lean_artifact",
        summary_hash,
        "gate",
        None,
    )
    assert json.loads(artifact["population"]) == json.loads(claims.to_json(statement.scope))
    assert set(json.loads(artifact["assumptions"])) == set(statement.scope["assumption_set"])
    assert [(edge["parent_hash"], edge["edge_kind"]) for edge in writer.lineage_of(artifact["hash"])] == [
        (summary_hash, "input")
    ]
    assert {edge["parent_hash"] for edge in writer.lineage_of(summary_hash)} == set(step_hashes)
    persist(writer, plan_result(), statement)
    assert len(claims.evidence_for(writer, statement.hash)) == 1


@pytest.mark.parametrize("failure", ["fail", "timeout"])
def test_a_nonpassing_plan_emits_no_lean_artifact(writer, statement, failure):
    persist(writer, plan_result(build={"result": failure}), statement)
    assert claims.evidence_for(writer, statement.hash) == []


def test_a_passing_summary_with_a_different_pin_is_refused_as_proof_evidence(writer, statement):
    persist(writer, plan_result(), statement)
    (artifact,) = claims.evidence_for(writer, statement.hash)
    run, reason = justify._formalization(writer, artifact, claims.get_claim_statement(writer, statement.hash))
    assert run is None
    assert reason == "lean-gate-binding"


@pytest.mark.parametrize("producer", ["isolated-summary", "individual-step", "extra-input", "another-statement"])
def test_an_artifact_requires_the_complete_bound_gate_run(writer, statement, producer):
    summary_hash, step_hashes = persist(writer, plan_result(), statement, pin_hash="b3" * 32)
    (emitted,) = claims.evidence_for(writer, statement.hash)
    source = summary_hash
    expected = "lean-gate-binding"
    if producer == "isolated-summary":
        summary = claims.GateRun(
            gate=solutionplan.SUMMARY_GATE,
            plan_step=solutionplan.SUMMARY_STEP,
            bundle_hash="b3" * 32,
            pin_hash="b3" * 32,
            statement_hash=statement.hash,
            formal_statement_hash=FORMAL,
            renderer_hash=RENDERER,
            prelude_hash=PRELUDE,
            arm=ARM,
            result="pass",
            reasons=(),
            at="2026-09-30T12:00:00Z",
        )
        source = claims.write_gate_run(writer, summary)
        expected = "lean-gate-incomplete"
    elif producer == "individual-step":
        source = step_hashes[0]
    elif producer == "extra-input":
        writer.add_lineage(emitted["hash"], step_hashes[0], "input")
    evidence = claims.EvidenceNode(
        kind="lean_artifact",
        target_statement_hash=statement.hash,
        population=statement.scope,
        assumptions=frozenset(statement.scope["assumption_set"]),
        producer_identity=source,
        producer_tag="gate",
    )
    claims.write_evidence_node(writer, evidence)
    writer.add_lineage(evidence.hash, source, "input")
    stored = claims.get_claim_statement(writer, statement.hash)
    if producer == "another-statement":
        replacement = factories.claim_statement(seed=33, supersedes=statement.hash)
        claims.write_claim_statement(writer, replacement)
        stored = claims.get_claim_statement(writer, replacement.hash)
    row = claims.get_evidence_node(writer, evidence.hash)
    run, reason = justify._formalization(writer, row, stored)
    assert run is None
    assert reason == expected


def test_an_all_pass_dev_arm_plan_persists_a_passing_summary_that_meets_no_obligation(writer, statement):
    persist(writer, PlanResult(plan_result().steps, container.DEV_ARM), statement)
    (summary,) = rows(writer, solutionplan.SUMMARY_GATE)
    assert (summary["result"], summary["arm"]) == ("pass", container.DEV_ARM)
    assert scrutiny._formalization_passed(writer, statement.hash) is False
    persist(writer, plan_result(), statement)
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
