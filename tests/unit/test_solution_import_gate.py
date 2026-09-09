import pytest

from cairn import challenge, container, solutionplan
from cairn.solutionplan import (
    KIND_AXIOMS,
    KIND_BUILD,
    KIND_IMPORT_ALLOWLIST,
    KIND_KERNEL_REPLAY,
    KIND_STATEMENT_BINDING,
    ImportsUnparsable,
    SolutionPlan,
    check_imports,
    imported_modules,
)

PRELUDE_IMPORT = "Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point"
HONEST = f"import {PRELUDE_IMPORT}\nimport Challenge.C_0123456789abcdef\n\ntheorem answer : True := trivial\n".encode()
FORGED = b"import Lean\nimport Mathlib\nopen Lean\n\ntheorem answer : True := trivial\n"


def _rows():
    return [
        {
            "step": kind,
            "kind": kind,
            "expect": solutionplan.KIND_EXPECTATION[kind],
            "blocking": True,
            "timeout_s": 600.0,
        }
        for kind in (KIND_STATEMENT_BINDING, KIND_IMPORT_ALLOWLIST, KIND_BUILD, KIND_AXIOMS, KIND_KERNEL_REPLAY)
    ]


def test_the_challenge_module_prefix_starts_with_an_admitted_root():
    assert challenge.MODULE_PREFIX.partition(".")[0] in solutionplan.ADMITTED_ROOTS


def test_the_shipped_prelude_only_imports_admitted_modules():
    observed, reasons = check_imports(challenge.prelude_bytes())
    assert (observed, reasons) == (solutionplan.EXPECT_ADMITTED, ())


def test_an_honest_solution_is_admitted():
    assert check_imports(HONEST) == (solutionplan.EXPECT_ADMITTED, ())


def test_a_solution_importing_lean_is_refused_and_names_the_module():
    observed, reasons = check_imports(FORGED)
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons == (f"{solutionplan.IMPORT_REFUSED_PREFIX}Lean",)


def test_the_refused_solution_never_reaches_the_build_or_the_checkers():
    ran = []

    def observe(step):
        ran.append(step.kind)
        if step.kind == KIND_IMPORT_ALLOWLIST:
            return (*check_imports(FORGED), 2)
        return step.expect, (), 2

    result = SolutionPlan.load(_rows(), arm=container.DEV_ARM).run(observe)
    assert ran == [KIND_STATEMENT_BINDING, KIND_IMPORT_ALLOWLIST]
    assert result.ok is False
    assert result.steps[1].result == solutionplan.RESULT_FAIL
    assert f"{solutionplan.IMPORT_REFUSED_PREFIX}Lean" in result.steps[1].reasons
    assert [step.result for step in result.steps[2:]] == [solutionplan.RESULT_BLOCKED] * 3


@pytest.mark.parametrize(
    "source",
    [
        b"/- import Lean -/\nimport Mathlib\n",
        b"-- import Lean\nimport Mathlib\n",
        b"/- outer /- inner import Lean -/ still hidden -/\nimport Mathlib\n",
        b"import Mathlib -- import Lean\n",
    ],
)
def test_an_import_inside_a_comment_is_not_an_import(source):
    assert check_imports(source) == (solutionplan.EXPECT_ADMITTED, ())


@pytest.mark.parametrize(
    "source",
    [
        b"import Mathlib\nsection\nimport Lean\n",
        b"theorem answer : True := trivial\nimport Lean\n",
        b"  import Lean\n",
    ],
)
def test_an_import_anywhere_in_the_file_is_read(source):
    observed, reasons = check_imports(source)
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons == (f"{solutionplan.IMPORT_REFUSED_PREFIX}Lean",)


@pytest.mark.parametrize("name", ["Lean", "Lean.Elab.Command", "Std", "Init.System.IO", "Cairn.Axioms"])
def test_every_module_outside_the_admitted_roots_is_refused(name):
    observed, reasons = check_imports(f"import {name}\n".encode())
    assert (observed, reasons) == (solutionplan.OBSERVED_REFUSED, (f"{solutionplan.IMPORT_REFUSED_PREFIX}{name}",))


@pytest.mark.parametrize("name", ["Mathlib", "Mathlib.Tactic", PRELUDE_IMPORT, "Challenge.C_00"])
def test_every_module_under_an_admitted_root_is_admitted(name):
    assert check_imports(f"import {name}\n".encode()) == (solutionplan.EXPECT_ADMITTED, ())


def test_a_root_an_admitted_root_is_a_prefix_of_is_still_refused():
    observed, reasons = check_imports(b"import MathlibExtras.Evil\n")
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons == (f"{solutionplan.IMPORT_REFUSED_PREFIX}MathlibExtras.Evil",)


def test_every_refused_module_is_named_not_only_the_first():
    observed, reasons = check_imports(b"import Lean\nimport Mathlib\nimport Std\n")
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons == (
        f"{solutionplan.IMPORT_REFUSED_PREFIX}Lean",
        f"{solutionplan.IMPORT_REFUSED_PREFIX}Std",
    )


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        (b"import Mathlib.\n", f"{solutionplan.UNPARSABLE_IMPORT_PREFIX}1"),
        (b"import 9Lives\n", f"{solutionplan.UNPARSABLE_IMPORT_PREFIX}1"),
        (b"import Mathlib Lean\n", f"{solutionplan.UNPARSABLE_IMPORT_PREFIX}1"),
        (b"/- unclosed\nimport Mathlib\n", solutionplan.UNTERMINATED_COMMENT),
    ],
)
def test_a_head_the_gate_cannot_parse_is_refused_rather_than_admitted(source, reason):
    assert check_imports(source) == (solutionplan.OBSERVED_REFUSED, (reason,))


def test_a_source_that_is_not_utf8_is_refused():
    assert check_imports(b"import Mathlib\n\xff\xfe") == (
        solutionplan.OBSERVED_REFUSED,
        (solutionplan.UNDECODABLE_SOURCE,),
    )


def test_importsunparsable_carries_the_reason_it_refused_on():
    with pytest.raises(ImportsUnparsable) as caught:
        imported_modules("import Mathlib.\n")
    assert caught.value.reason == f"{solutionplan.UNPARSABLE_IMPORT_PREFIX}1"


def test_a_word_beginning_with_import_is_not_an_import():
    assert imported_modules("imports Lean\nimportant := 1\n") == ()
