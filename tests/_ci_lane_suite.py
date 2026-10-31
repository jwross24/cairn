from _ci_lanes import (
    CONTAINER_COMPARISON_TESTS,
    CONTAINER_PLAN_CASES,
    CONTAINER_PLAN_TESTS,
    CONTAINER_REPLAY_TESTS,
    CONTAINER_TEST_PATHS,
    GATEPLAN_TEST_PATHS,
    M0_ABORT_CASES,
    M0_ABORT_TEST,
    M0_TEST_CASES,
    M0_TEST_PATHS,
    PROVEN_DEV_TEST,
    PROVEN_GOLD_TEST,
    PROVEN_TEST_PATH,
    SOLUTION_LIBRARY_BINDING_TEST,
    SOLUTION_LIBRARY_CASE_TEST,
    SOLUTION_LIBRARY_ITEMS,
    SOLUTION_LIBRARY_TEST_PATHS,
    SOLUTION_PLAN_EXACT_TEST_PATHS,
    SOLUTION_TEST_PATHS,
)

SOLUTION_CASES = (
    "test_real_prelude_solution_and_challenge_build_with_private_pinned_dependencies",
    "test_a_compiling_weaker_statement_fails_real_prelude_closure_comparison",
    "test_real_prelude_forgery_passes_axioms_but_fails_fresh_replay",
)
PLAN_CASE = "test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks"
PLAN_VARIANTS = ("exact", "sorry", "timeout")
LIBRARY_GATE_PATH = SOLUTION_LIBRARY_TEST_PATHS[0]
LIBRARY_GATE_CASE = SOLUTION_LIBRARY_CASE_TEST
LIBRARY_GATE_BINDING_CASE = SOLUTION_LIBRARY_BINDING_TEST
LIBRARY_GATE_ITEMS = SOLUTION_LIBRARY_ITEMS
LIBRARY_GATE_IDS = ("display-dlp", "display-finite-point")
M0_GATE_PATH = M0_TEST_PATHS[0]
SWEEP_PATH = "tests/integration/test_slopemodel_sweep.py"
FULL_SWEEP_TEST = "test_all_validation_primes_agree"


def full_sweep_source(primes):
    return (
        f'import pytest\n@pytest.mark.parametrize("ell", {list(primes)!r})\n'
        f"def {FULL_SWEEP_TEST}(ell):\n    assert ell >= 0\n"
    )


def m0_source(failing_test=None):
    lines = ["import pytest"]
    for names in M0_TEST_CASES.values():
        for name in names:
            if name == M0_ABORT_TEST:
                expected = "pin_mismatch" if failing_test == name else "never"
                lines.extend(
                    (
                        f"@pytest.mark.parametrize('name', {M0_ABORT_CASES!r})",
                        f"def {name}(name):",
                        f"    assert name != {expected!r}",
                    )
                )
            else:
                assertion = "assert False" if name == failing_test else "assert True"
                lines.extend((f"def {name}():", f"    {assertion}"))
    return "\n".join(lines) + "\n"


def write_suite(pytester):
    pytester.makeconftest('pytest_plugins = ["_ci_lanes"]')
    for relative in (
        "tests/integration/test_lean_toolchain.py",
        "tests/integration/test_solution_build_compile.py",
        "tests/integration/test_container_statement_hash.py",
        "tests/integration/test_unlisted.py",
        *SOLUTION_PLAN_EXACT_TEST_PATHS,
        "tests/unit/test_unlisted.py",
    ):
        path = pytester.path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_pass():\n    assert True\n")
    m0_path = pytester.path / M0_GATE_PATH
    m0_path.parent.mkdir(parents=True, exist_ok=True)
    m0_path.write_text(m0_source())
    for relative in GATEPLAN_TEST_PATHS:
        path = pytester.path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_pass():\n    assert True\n")
    (pytester.path / LIBRARY_GATE_PATH).write_text(
        f'import pytest\n@pytest.mark.parametrize("item", {LIBRARY_GATE_ITEMS!r}, ids={LIBRARY_GATE_IDS!r})\n'
        f"def {LIBRARY_GATE_CASE}(item):\n    assert True\n"
        f"def {LIBRARY_GATE_BINDING_CASE}():\n    assert True\n"
    )
    (pytester.path / PROVEN_TEST_PATH).write_text(
        f"def {PROVEN_GOLD_TEST}():\n    assert True\ndef {PROVEN_DEV_TEST}():\n    assert True\n"
    )
    path = pytester.path / SOLUTION_TEST_PATHS[0]
    with path.open("a") as stream:
        stream.write("import pytest\n")
        for name in SOLUTION_CASES:
            stream.write(f'@pytest.mark.parametrize("case", [0, 1])\ndef {name}(case):\n    assert True\n')
        stream.write(f'@pytest.mark.parametrize("case", {PLAN_VARIANTS!r})\ndef {PLAN_CASE}(case):\n    assert True\n')
    with (pytester.path / CONTAINER_TEST_PATHS[0]).open("a") as stream:
        stream.write("import pytest\n")
        stream.write(
            f'@pytest.mark.parametrize("proof", ["rfl"])\ndef {CONTAINER_REPLAY_TESTS[0]}(proof):\n    assert True\n'
        )
        stream.write(f"def {CONTAINER_REPLAY_TESTS[1]}():\n    assert True\n")
        for name in CONTAINER_COMPARISON_TESTS:
            stream.write(f"def {name}():\n    assert True\n")
        stream.write(
            f'@pytest.mark.parametrize("case", {CONTAINER_PLAN_CASES!r})\ndef {CONTAINER_PLAN_TESTS[0]}(case):\n    assert True\n'
        )
