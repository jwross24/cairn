import json
import sys
from pathlib import Path

import pytest

from cairn import bundle, challenge, container, lean, solutionbuild, solutionplan
from cairn.substrate import blob_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories

FORMAL = "theorem challenge_hello (n : Nat) : n + 0 = n := by\n  sorry\n"
SOLUTION = b"import Challenge.C_0123456789abcdef\n\ntheorem challenge_hello (n : Nat) : n + 0 = n := by\n  simp\n"
FSH = "a" * 64
OTHER_FSH = "b" * 64
THEOREMS = ("challenge_hello",)


@pytest.fixture
def gate(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


@pytest.fixture
def statement():
    return factories.claim_statement(seed=3, formal_source=FORMAL)


def _submission(hash_hex=FSH, blob=SOLUTION):
    return challenge.Submission(solution_module=blob, formal_statement_hash=hash_hex)


def _assemble(gate, statement, root, **kwargs):
    return solutionbuild.assemble(
        gate,
        statement,
        kwargs.pop("submission", _submission()),
        kwargs.pop("theorem_names", THEOREMS),
        root=root,
        formal_statement_hash=kwargs.pop("formal_statement_hash", FSH),
    )


def test_the_assembled_project_holds_the_four_inputs_and_the_comparator_config(gate, statement, tmp_path):
    root = tmp_path / "run"
    assembled = _assemble(gate, statement, root)
    assert sorted(assembled.inputs) == sorted(
        [
            "config.json",
            "lakefile.toml",
            "lean-toolchain",
            str(Path("Challenge") / f"C_{statement.hash[:16]}.lean"),
            str(Path("Solution") / f"S_{FSH[:16]}.lean"),
        ]
    )
    for relative in assembled.inputs:
        assert (root / relative).is_file()
    assert (root / "lean-toolchain").read_text() == gate.lean["toolchain"] + "\n"


def test_the_solution_module_name_comes_from_the_statement_hash_and_never_from_the_submitted_bytes(
    gate, statement, tmp_path
):
    named = b"module Solution.Challenge_C_0123456789abcdef\n" + SOLUTION
    assembled = _assemble(gate, statement, tmp_path / "run", submission=_submission(blob=named))
    assert assembled.solution_module == f"Solution.S_{FSH[:16]}"
    assert assembled.challenge_module == f"Challenge.C_{statement.hash[:16]}"
    assert assembled.solution_module != assembled.challenge_module


def test_a_submission_naming_another_formal_statement_hash_is_refused_before_any_file_is_written(
    gate, statement, tmp_path
):
    root = tmp_path / "run"
    with pytest.raises(solutionbuild.SolutionRefused) as caught:
        _assemble(gate, statement, root, submission=_submission(hash_hex=OTHER_FSH))
    assert caught.value.reason == f"{solutionbuild.STATEMENT_HASH_MISMATCH}:{OTHER_FSH}"
    assert not root.exists()


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"submission": _submission(blob=b"")}, solutionbuild.EMPTY_SOLUTION),
        ({"theorem_names": ()}, solutionbuild.EMPTY_THEOREM_NAMES),
    ],
)
def test_an_empty_solution_or_an_empty_theorem_list_is_refused_before_any_file_is_written(
    gate, statement, tmp_path, kwargs, reason
):
    root = tmp_path / "run"
    with pytest.raises(solutionbuild.SolutionRefused) as caught:
        _assemble(gate, statement, root, **kwargs)
    assert caught.value.reason == reason
    assert not root.exists()


def test_a_second_submission_cannot_reuse_a_root(gate, statement, tmp_path):
    root = tmp_path / "run"
    _assemble(gate, statement, root)
    with pytest.raises(FileExistsError):
        _assemble(gate, statement, root)


def test_the_challenge_source_is_rendered_from_the_bundles_prelude(gate, statement, tmp_path):
    root = tmp_path / "run"
    assembled = _assemble(gate, statement, root)
    written = (root / f"Challenge/C_{statement.hash[:16]}.lean").read_bytes()
    assert written == challenge.render(statement, gate.raw(challenge.PRELUDE_KIND))
    assert blob_hash(gate.raw(challenge.PRELUDE_KIND)) == gate.digest_of(challenge.PRELUDE_KIND)
    assert assembled.challenge_module == challenge.module_name(statement)


def test_the_config_carries_the_keys_the_comparator_reads_with_the_bundles_permitted_axioms(gate, statement, tmp_path):
    root = tmp_path / "run"
    assembled = _assemble(gate, statement, root)
    written = json.loads((root / solutionbuild.CONFIG_NAME).read_text())
    assert set(written) == {
        "challenge_module",
        "solution_module",
        "theorem_names",
        "permitted_axioms",
        "enable_nanoda",
    }
    assert written["challenge_module"] == assembled.challenge_module
    assert written["solution_module"] == assembled.solution_module
    assert written["theorem_names"] == list(THEOREMS)
    assert written["permitted_axioms"] == list(gate.lean["permitted_axioms"])
    assert written["enable_nanoda"] is False


def test_an_untouched_project_passes_the_fingerprint(gate, statement, tmp_path):
    assembled = _assemble(gate, statement, tmp_path / "run")
    solutionbuild.assert_unchanged(assembled)
    assert solutionbuild.fingerprint(assembled.root, assembled.inputs) == assembled.fingerprint


@pytest.mark.parametrize("index", range(5))
def test_a_rewrite_of_any_input_is_named_by_the_fingerprint(gate, statement, tmp_path, index):
    assembled = _assemble(gate, statement, tmp_path / "run")
    target = sorted(assembled.inputs)[index]
    (Path(assembled.root) / target).write_bytes(b"tampered\n")
    with pytest.raises(solutionbuild.InputsChanged) as caught:
        solutionbuild.assert_unchanged(assembled)
    assert caught.value.paths == (target,)


def test_a_deleted_input_is_named_rather_than_read_as_unchanged(gate, statement, tmp_path):
    assembled = _assemble(gate, statement, tmp_path / "run")
    target = str(Path("Challenge") / f"C_{statement.hash[:16]}.lean")
    (Path(assembled.root) / target).unlink()
    with pytest.raises(solutionbuild.InputsChanged) as caught:
        solutionbuild.assert_unchanged(assembled)
    assert caught.value.paths == (target,)


def test_a_file_lake_generates_during_the_build_does_not_trip_the_fingerprint(gate, statement, tmp_path):
    assembled = _assemble(gate, statement, tmp_path / "run")
    (Path(assembled.root) / "lake-manifest.json").write_text('{"version": "1.1.0"}\n')
    (Path(assembled.root) / ".lake").mkdir()
    solutionbuild.assert_unchanged(assembled)


def test_the_fingerprint_binds_content_to_its_path(gate, statement, tmp_path):
    first = _assemble(gate, statement, tmp_path / "a")
    second = _assemble(gate, statement, tmp_path / "b")
    assert first.fingerprint == second.fingerprint
    swapped = tuple(reversed(first.inputs))
    assert solutionbuild.fingerprint(first.root, swapped) != first.fingerprint


def test_the_binding_step_admits_the_matching_hash_and_refuses_any_other():
    observed, reasons, wall_ms = solutionbuild.observe_binding(_submission(), FSH)
    assert (observed, reasons) == (solutionplan.EXPECT_BOUND, ())
    assert wall_ms >= 0
    observed, reasons, _ = solutionbuild.observe_binding(_submission(hash_hex=OTHER_FSH), FSH)
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons == (f"{solutionbuild.STATEMENT_HASH_MISMATCH}:{OTHER_FSH}",)


def test_a_submission_naming_another_hash_blocks_every_later_step_including_the_build():
    ran = []
    kinds = (
        solutionplan.KIND_STATEMENT_BINDING,
        solutionplan.KIND_IMPORT_ALLOWLIST,
        solutionplan.KIND_BUILD,
        solutionplan.KIND_AXIOMS,
        solutionplan.KIND_KERNEL_REPLAY,
    )
    rows = [
        {
            "step": kind,
            "kind": kind,
            "expect": solutionplan.KIND_EXPECTATION[kind],
            "blocking": True,
            "timeout_s": 600.0,
        }
        for kind in kinds
    ]

    def observe(step):
        ran.append(step.kind)
        if step.kind == solutionplan.KIND_STATEMENT_BINDING:
            return solutionbuild.observe_binding(_submission(hash_hex=OTHER_FSH), FSH)
        return step.expect, (), 1

    result = solutionplan.SolutionPlan.load(rows, arm=container.DEV_ARM).run(observe)
    assert ran == [solutionplan.KIND_STATEMENT_BINDING]
    assert result.steps[0].result == solutionplan.RESULT_FAIL
    assert [step.result for step in result.steps[1:]] == [solutionplan.RESULT_BLOCKED] * 4


def test_a_build_that_exceeds_its_timeout_is_a_step_timeout_and_never_a_failed_verdict(gate, statement, tmp_path):
    assembled = _assemble(gate, statement, tmp_path / "run")

    def slow(*args, **kwargs):
        raise lean.LeanTimeout(("lake", "build"), 0.5)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(lean, "run_argv", slow)
        with pytest.raises(solutionplan.StepTimeout) as caught:
            solutionbuild.observe_build(gate, assembled, timeout_s=0.5)
    assert caught.value.step == solutionplan.KIND_BUILD
    assert caught.value.timeout_s == 0.5


def test_the_build_command_names_the_solution_module_under_the_pinned_toolchain(gate, statement, tmp_path):
    assembled = _assemble(gate, statement, tmp_path / "run")
    assert lean.command(gate.lean, "build", module=assembled.solution_module)[-1] == assembled.solution_module
