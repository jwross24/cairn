import sys
from pathlib import Path

import pytest

from cairn import bundle, challenge, lean, solutionbuild, solutionchecks, solutionplan

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories

FORMAL = "theorem challenge_hello (n : Nat) : n + 0 = n := by\n  sorry\n"
SOLUTION = b"import Challenge.C_0123456789abcdef\n\ntheorem challenge_hello (n : Nat) : n + 0 = n := by\n  simp\n"
FSH = "d" * 64
THEOREMS = ("challenge_hello",)


@pytest.fixture
def gate(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


@pytest.fixture
def assembled(gate, tmp_path):
    return solutionbuild.assemble(
        gate,
        factories.claim_statement(seed=5, formal_source=FORMAL),
        challenge.Submission(solution_module=SOLUTION, formal_statement_hash=FSH),
        THEOREMS,
        root=tmp_path / "run",
        formal_statement_hash=FSH,
    )


@pytest.fixture
def comparator(tmp_path):
    binary = solutionchecks.comparator_binary(tmp_path / "comparator")
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"")
    return binary


def _run(rc=0, stdout="Your solution is okay!\n", stderr=""):
    def call(argv, *, cwd=None, timeout_s=None):
        return lean.Run(argv=tuple(argv), cwd=cwd, rc=rc, stdout=stdout, stderr=stderr, wall_ms=12.0)

    return call


def _observe(gate, assembled, comparator, call, **kwargs):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(lean, "run_argv", call)
        return solutionchecks.observe_closure_comparison(
            gate, assembled, comparator=comparator, timeout_s=kwargs.pop("timeout_s", 120.0)
        )


def test_a_matching_closure_is_the_expectation(gate, assembled, comparator):
    observed, reasons, wall_ms = _observe(gate, assembled, comparator, _run())
    assert (observed, reasons) == (solutionplan.EXPECT_CLOSURE_MATCHED, ())
    assert wall_ms >= 0


def test_the_comparator_runs_in_the_assembled_root_on_the_config_the_gate_wrote(gate, assembled, comparator):
    seen = {}

    def call(argv, *, cwd=None, timeout_s=None):
        seen["argv"] = list(argv)
        seen["cwd"] = cwd
        return lean.Run(argv=tuple(argv), cwd=cwd, rc=0, stdout="", stderr="", wall_ms=1.0)

    _observe(gate, assembled, comparator, call)
    assert seen["cwd"] == assembled.root
    assert seen["argv"][-2:] == [str(comparator), solutionbuild.CONFIG_NAME]
    assert seen["argv"][1] == f"+{gate.lean['toolchain']}"
    assert (Path(assembled.root) / solutionbuild.CONFIG_NAME).is_file()


def test_a_comparator_binary_that_is_not_there_refuses_and_never_runs_a_command(gate, assembled, tmp_path):
    def call(argv, *, cwd=None, timeout_s=None):
        raise AssertionError("the observer ran a command without a comparator")

    missing = solutionchecks.comparator_binary(tmp_path / "absent")
    observed, reasons, _ = _observe(gate, assembled, missing, call)
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons == (f"{solutionchecks.COMPARATOR_ABSENT_PREFIX}{missing}",)


def test_a_nonzero_comparator_names_the_mismatch_its_rc_and_the_first_output_line(gate, assembled, comparator):
    observed, reasons, _ = _observe(gate, assembled, comparator, _run(rc=1, stdout="\nThe statements differ.\nmore\n"))
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons == (solutionchecks.CLOSURE_MISMATCH, "rc:1", "The statements differ.")


def test_an_input_rewritten_during_the_comparison_refuses_even_on_a_zero_rc(gate, assembled, comparator):
    target = next(name for name in assembled.inputs if name.startswith(solutionbuild.CHALLENGE_DIR))

    def call(argv, *, cwd=None, timeout_s=None):
        (Path(assembled.root) / target).write_bytes(b"theorem challenge_hello : True := trivial\n")
        return lean.Run(argv=tuple(argv), cwd=cwd, rc=0, stdout="", stderr="", wall_ms=1.0)

    observed, reasons, _ = _observe(gate, assembled, comparator, call)
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons == (f"solution-inputs-changed:{target}",)


def test_a_comparison_that_exceeds_its_timeout_is_a_step_timeout_and_never_a_mismatch(gate, assembled, comparator):
    def call(argv, *, cwd=None, timeout_s=None):
        raise lean.LeanTimeout(tuple(argv), 0.25)

    with pytest.raises(solutionplan.StepTimeout) as caught:
        _observe(gate, assembled, comparator, call, timeout_s=0.25)
    assert caught.value.step == solutionplan.KIND_CLOSURE_COMPARISON
    assert caught.value.timeout_s == 0.25
