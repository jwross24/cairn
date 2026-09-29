import sys
from pathlib import Path
from typing import NamedTuple

import pytest
from test_solution_build_compile import comparator  # noqa: F401

from cairn import bundle, challenge, claims, container, lean, log, scrutiny, solutionbuild, solutionchecks, solutionplan

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as substrate_helpers
import factories

lg = log.get("test")

LIBRARY = lean.REPO_ROOT / "lean" / "Library"


class Item(NamedTuple):
    directory: str
    theorem: str
    seed: int


ITEMS = {
    "dlp": Item("Dlp", "cairn_dlp_iff", 61),
    "finite_point": Item("FinitePoint", "cairn_finite_point", 62),
}


def _rows():
    return [
        {
            "step": kind,
            "kind": kind,
            "expect": solutionplan.KIND_EXPECTATION[kind],
            "blocking": True,
            "timeout_s": lean.DEFAULT_TIMEOUT_S,
        }
        for kind in solutionplan.STEP_KINDS
    ]


@pytest.fixture(scope="module")
def gate(tmp_path_factory):
    out = tmp_path_factory.mktemp("library-gate")
    bundle_path, pin_path = out / "gate-bundle.sqlite", out / "gate-bundle.pin"
    bundle.build(lean.REPO_ROOT / "bundle", bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    return bundle.GateBundle.open(bundle_path, pin_path)


def _prepare(gate, item, root):
    spec = ITEMS[item]
    formal = (LIBRARY / spec.directory / "Statement.lean").read_text()
    statement = factories.claim_statement(seed=spec.seed, formal_source=formal)
    prepared = solutionchecks.prepare_dev(
        gate, statement, (spec.theorem,), root=root, dependency_project=lean.PROJECT_DIR
    )
    return statement, prepared


@pytest.mark.timeout(1800)
@pytest.mark.parametrize("item", sorted(ITEMS))
def test_library_items_pass_gate(gate, tmp_path, comparator, popen_spy, item):  # noqa: F811
    spec = ITEMS[item]
    statement, prepared = _prepare(gate, item, tmp_path / "challenge")
    lg.info(
        "library_challenge",
        item=item,
        theorem=spec.theorem,
        formal_statement_hash=prepared.formal_statement_hash,
    )
    solution = (LIBRARY / spec.directory / "Solution.lean").read_bytes()
    submission = challenge.Submission(
        solution_module=gate.challenge_prelude + solution, formal_statement_hash=prepared.formal_statement_hash
    )
    popen_spy.clear()
    sub = substrate_helpers.open_writer(tmp_path)
    try:
        claims.write_claim_statement(sub, statement)
        result = solutionchecks.run_dev(
            gate,
            statement,
            submission,
            (spec.theorem,),
            _rows(),
            sub=sub,
            root=tmp_path / "solution",
            prepared=prepared,
            comparator=comparator,
        )
        lg.info("library_plan", item=item, steps=[step.__dict__ for step in result.steps])
        assert result.arm == container.DEV_ARM
        assert [step.kind for step in result.steps] == list(solutionplan.STEP_KINDS)
        assert [step.result for step in result.steps] == [solutionplan.RESULT_PASS] * len(solutionplan.STEP_KINDS)
        assert result.ok is True
        assert result.first_failure is None
        replay = [command for command in popen_spy if "--fresh" in command]
        assert len(replay) == 1
        assert "leanchecker" in replay[0]
        persisted = sub.conn.execute(
            "SELECT plan_step, result, arm FROM gate_runs WHERE gate = ? ORDER BY rowid", (solutionplan.STEP_GATE,)
        ).fetchall()
        assert [tuple(row) for row in persisted] == [
            (step.step, step.result, container.DEV_ARM) for step in result.steps
        ]
        assert (
            sub.conn.execute("SELECT COUNT(*) FROM gate_runs WHERE gate = ?", (solutionplan.SUMMARY_GATE,)).fetchone()[
                0
            ]
            == 1
        )
        assert scrutiny._formalization_passed(sub, statement.hash) is False
    finally:
        sub.close()


@pytest.mark.timeout(900)
def test_a_stale_formal_statement_hash_stops_at_statement_binding_without_a_subprocess(gate, tmp_path, popen_spy):
    spec = ITEMS["dlp"]
    statement, prepared = _prepare(gate, "dlp", tmp_path / "challenge")
    assert prepared.formal_statement_hash != "0" * 64
    solution = (LIBRARY / spec.directory / "Statement.lean").read_bytes()
    submission = challenge.Submission(solution_module=gate.challenge_prelude + solution, formal_statement_hash="0" * 64)
    popen_spy.clear()
    root = tmp_path / "solution"
    sub = substrate_helpers.open_writer(tmp_path)
    try:
        claims.write_claim_statement(sub, statement)
        result = solutionchecks.run_dev(
            gate,
            statement,
            submission,
            (spec.theorem,),
            _rows(),
            sub=sub,
            root=root,
            prepared=prepared,
            comparator=None,
        )
        steps = result.steps
        assert result.ok is False
        assert result.first_failure == steps[0]
        assert [step.result for step in steps] == [solutionplan.RESULT_FAIL] + [solutionplan.RESULT_BLOCKED] * 5
        assert steps[0].reasons[-1].startswith(f"{solutionbuild.STATEMENT_HASH_MISMATCH}:")
        for step in steps[1:]:
            assert step.reasons == (f"blocked-by:{solutionplan.KIND_STATEMENT_BINDING}",)
        persisted = sub.conn.execute(
            "SELECT plan_step, result, arm FROM gate_runs WHERE gate = ? ORDER BY rowid", (solutionplan.STEP_GATE,)
        ).fetchall()
        assert [tuple(row) for row in persisted] == [(step.step, step.result, container.DEV_ARM) for step in steps]
        assert (
            sub.conn.execute("SELECT COUNT(*) FROM gate_runs WHERE gate = ?", (solutionplan.SUMMARY_GATE,)).fetchone()[
                0
            ]
            == 1
        )
        assert popen_spy == []
        assert not root.exists()
    finally:
        sub.close()
