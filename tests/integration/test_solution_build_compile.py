import shutil
import sys
from pathlib import Path

import pytest

from cairn import bundle, challenge, container, lean, log, solutionbuild, solutionchecks, solutionplan

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories

lg = log.get("test")

TEST_PRELUDE = b"set_option autoImplicit false\n"
FORMAL = "theorem challenge_hello (n : Nat) : n + 0 = n := by\n  sorry\n"
FSH = "c" * 64
THEOREMS = ("challenge_hello",)
PLAN_KINDS = (
    solutionplan.KIND_STATEMENT_BINDING,
    solutionplan.KIND_IMPORT_ALLOWLIST,
    solutionplan.KIND_BUILD,
    solutionplan.KIND_AXIOMS,
    solutionplan.KIND_KERNEL_REPLAY,
)


def _plan_rows():
    return [
        {
            "step": kind,
            "kind": kind,
            "expect": solutionplan.KIND_EXPECTATION[kind],
            "blocking": True,
            "timeout_s": 120.0,
        }
        for kind in PLAN_KINDS
    ]


PROOF = "theorem challenge_hello (n : Nat) : n + 0 = n := by\n  simp\n"


def _honest():
    return PROOF.encode()


def _rewrites_the_challenge(challenge_relative):
    return (
        f'#eval (IO.FS.writeFile "{challenge_relative}" "theorem challenge_hello (n : Nat) : n + 0 = n := by\\n  simp\\n" : IO Unit)\n'
        f"\n{PROOF}"
    ).encode()


@pytest.fixture(scope="module")
def mathlib_free_bundle(tmp_path_factory):
    from cairn import bundle as bundle_module

    src = tmp_path_factory.mktemp("bundle-src") / "bundle"
    shutil.copytree(Path(__file__).resolve().parents[2] / "bundle", src)
    prelude = src / "challenge_prelude.lean"
    prelude.write_bytes(TEST_PRELUDE)
    out = tmp_path_factory.mktemp("bundle-out")
    bundle_path, pin_path = out / "gate-bundle.sqlite", out / "gate-bundle.pin"
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(challenge, "PRELUDE_PATH", prelude)
        bundle_module.build(src, bundle_path)
    bundle_module.write_pin(bundle_path, pin_path)
    return bundle.GateBundle.open(bundle_path, pin_path)


@pytest.fixture(scope="module")
def statement():
    return factories.claim_statement(seed=11, formal_source=FORMAL)


def _assemble(gate, statement, root, blob):
    return solutionbuild.assemble(
        gate,
        statement,
        challenge.Submission(solution_module=blob, formal_statement_hash=FSH),
        THEOREMS,
        root=root,
        formal_statement_hash=FSH,
    )


def _log(event, result, **fields):
    lg.info(
        event,
        command=" ".join(result.argv),
        cwd=result.cwd,
        rc=result.rc,
        stdout=result.stdout[-1500:],
        stderr=result.stderr[-1500:],
        wall_ms=result.wall_ms,
        **fields,
    )
    return result


def test_an_honest_solution_builds_in_the_assembled_project_and_the_inputs_are_unchanged(
    mathlib_free_bundle, statement, tmp_path
):
    assembled = _assemble(mathlib_free_bundle, statement, tmp_path / "honest", _honest())
    result = _log("solution_build", solutionbuild.build(mathlib_free_bundle, assembled))
    assert result.rc == 0, result.stderr
    olean = Path(assembled.root) / ".lake" / "build" / "lib" / "lean" / "Solution" / f"S_{FSH[:16]}.olean"
    assert olean.is_file()
    solutionbuild.assert_unchanged(assembled)


def test_a_solution_that_rewrites_the_challenge_during_its_build_is_named_by_the_fingerprint(
    mathlib_free_bundle, statement, tmp_path
):
    relative = str(Path("Challenge") / f"C_{statement.hash[:16]}.lean")
    root = tmp_path / "tamper"
    assembled = _assemble(mathlib_free_bundle, statement, root, _rewrites_the_challenge(relative))
    before = (root / relative).read_bytes()
    observed, reasons, _ = solutionbuild.observe_build(mathlib_free_bundle, assembled)
    assert (root / relative).read_bytes() != before
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons == (f"solution-inputs-changed:{relative}",)


def test_the_ordered_plan_runs_a_solution_end_to_end_on_the_dev_arm(mathlib_free_bundle, statement, tmp_path):
    assembled = _assemble(mathlib_free_bundle, statement, tmp_path / "plan", _honest())
    submission = challenge.Submission(solution_module=_honest(), formal_statement_hash=FSH)
    pins = mathlib_free_bundle.lean
    tool = lean.axiom_tool(mathlib_free_bundle, tmp_path / "axiom-tool")
    ran = []

    def observe(step):
        ran.append(step.kind)
        if step.kind == solutionplan.KIND_STATEMENT_BINDING:
            return solutionbuild.observe_binding(submission, FSH)
        if step.kind == solutionplan.KIND_IMPORT_ALLOWLIST:
            return (*solutionplan.check_imports(submission.solution_module), 0)
        if step.kind == solutionplan.KIND_BUILD:
            return solutionbuild.observe_build(mathlib_free_bundle, assembled, timeout_s=step.timeout_s)
        if step.kind == solutionplan.KIND_AXIOMS:
            return solutionchecks.observe_axioms(
                mathlib_free_bundle,
                assembled.solution_module,
                list(assembled.theorem_names),
                project_dir=assembled.root,
                timeout_s=step.timeout_s,
                tool=tool,
            )
        return solutionchecks.observe_kernel_replay(
            pins,
            assembled.solution_module,
            project_dir=assembled.root,
            timeout_s=step.timeout_s,
            variant=solutionchecks.REPLAY_TRUSTING_IMPORTS,
        )

    result = solutionplan.SolutionPlan.load(_plan_rows(), arm=container.DEV_ARM).run(observe)
    lg.info("plan", steps=[(s.kind, s.result, s.observed, list(s.reasons)) for s in result.steps])
    assert ran == list(PLAN_KINDS)
    assert [step.result for step in result.steps] == [solutionplan.RESULT_PASS] * len(PLAN_KINDS)
    assert result.ok is True
    solutionbuild.assert_unchanged(assembled)
