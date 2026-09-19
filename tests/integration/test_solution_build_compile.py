import json
import os
import shutil
import subprocess
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
    solutionplan.KIND_CLOSURE_COMPARISON,
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


@pytest.fixture
def comparator(monkeypatch):
    checkout = Path(os.environ.get("CAIRN_COMPARATOR_CHECKOUT", lean.REPO_ROOT / ".doctor/comparator")).resolve()
    pins = json.loads((lean.REPO_ROOT / "bundle/container.json").read_text())["comparator"]
    exporter = checkout / ".lake/packages/lean4export"
    for project, revision in ((checkout, pins["rev"]), (exporter, pins["lean4export_rev"])):
        assert project.is_dir(), "Provision the pinned comparator using README.md; set CAIRN_COMPARATOR_CHECKOUT"
        result = subprocess.run(
            ["/usr/bin/git", "-C", str(project), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        assert result.stdout.strip() == revision
        assert (project / "lean-toolchain").read_text().strip() == lean.source_pins()["toolchain"]
    binary = solutionchecks.comparator_binary(checkout)
    export_binary = exporter / ".lake/build/bin/lean4export"
    assert os.access(binary, os.X_OK), "Build the pinned comparator using README.md"
    assert os.access(export_binary, os.X_OK), "Build the pinned exporter using README.md"
    monkeypatch.setenv("COMPARATOR_LANDRUN", str(checkout / "scripts/fake-landrun.sh"))
    monkeypatch.setenv("COMPARATOR_LEAN4EXPORT", str(export_binary))
    return binary


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


def test_the_ordered_plan_runs_a_solution_end_to_end_on_the_dev_arm(
    mathlib_free_bundle, statement, tmp_path, comparator
):
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
        if step.kind == solutionplan.KIND_KERNEL_REPLAY:
            return solutionchecks.observe_kernel_replay(
                pins,
                assembled.solution_module,
                project_dir=assembled.root,
                timeout_s=step.timeout_s,
                variant=solutionchecks.REPLAY_TRUSTING_IMPORTS,
            )
        assert step.kind == solutionplan.KIND_CLOSURE_COMPARISON
        return solutionchecks.observe_closure_comparison(
            mathlib_free_bundle, assembled, comparator=comparator, timeout_s=step.timeout_s
        )

    result = solutionplan.SolutionPlan.load(_plan_rows(), arm=container.DEV_ARM).run(observe)
    lg.info("plan", steps=[(s.kind, s.result, s.observed, list(s.reasons)) for s in result.steps])
    assert ran == list(PLAN_KINDS)
    assert [step.result for step in result.steps] == [solutionplan.RESULT_PASS] * len(PLAN_KINDS)
    assert result.ok is True
    solutionbuild.assert_unchanged(assembled)


@pytest.mark.parametrize("tamper_manifest", [False, True])
def test_real_prelude_solution_and_challenge_build_with_private_pinned_dependencies(
    pinned_bundle, tmp_path, tamper_manifest, comparator
):
    gate = bundle.GateBundle.open(*pinned_bundle())
    formal = "theorem challenge_curve {R : Type} [CommRing R] (W : WeierstrassCurve R) : W.Δ = W.Δ := by\n  sorry\n"
    statement = factories.claim_statement(seed=4, formal_source=formal)
    proof = gate.challenge_prelude + formal.replace("sorry", "rfl").encode()
    if tamper_manifest:
        proof += b'\n#eval (IO.FS.writeFile "lake-manifest.json" "{}" : IO Unit)\n'
    assembled = solutionbuild.assemble(
        gate,
        statement,
        challenge.Submission(solution_module=proof, formal_statement_hash=FSH),
        ("challenge_curve",),
        root=tmp_path / "real-prelude",
        formal_statement_hash=FSH,
        dependency_project=lean.PROJECT_DIR,
    )
    observed, reasons, _ = solutionbuild.observe_build(gate, assembled)
    if tamper_manifest:
        assert (observed, reasons) == (
            solutionplan.OBSERVED_REFUSED,
            ("solution-inputs-changed:lake-manifest.json",),
        )
        return
    assert (observed, reasons) == (solutionplan.EXPECT_BUILT, ())
    root = Path(assembled.root)
    for module in (assembled.challenge_module, assembled.solution_module):
        assert (root / ".lake/build/lib/lean" / (module.replace(".", "/") + ".olean")).is_file()
    assert json.loads((root / "lake-manifest.json").read_text()) == gate.lake_manifest
    solutionbuild.assert_unchanged(assembled)
    compared = solutionchecks.observe_closure_comparison(gate, assembled, comparator=comparator, timeout_s=120)
    assert compared[:2] == (solutionplan.EXPECT_CLOSURE_MATCHED, ())
    source_readme = lean.PROJECT_DIR / ".lake/packages/mathlib/README.md"
    copied_readme = root / ".lake/packages/mathlib/README.md"
    original = source_readme.read_bytes()
    copied_readme.write_bytes(original + b"\nmodified dependency\n")
    assert source_readme.read_bytes() == original
    observed, reasons, _ = solutionbuild.observe_build(gate, assembled)
    assert (observed, reasons) == (
        solutionplan.OBSERVED_REFUSED,
        ("dependency-checkout-mismatch:mathlib:status",),
    )
    copied_readme.write_bytes(original)
    git_dir = copied_readme.parent / ".git"
    head = (git_dir / "HEAD").read_bytes()
    (git_dir / "HEAD").write_text("0" * 40 + "\n")
    observed, reasons, _ = solutionbuild.observe_build(gate, assembled)
    assert (observed, reasons) == (
        solutionplan.OBSERVED_REFUSED,
        ("dependency-checkout-mismatch:mathlib:rev-parse",),
    )
    (git_dir / "HEAD").write_bytes(head)
    config = (git_dir / "config").read_text()
    url = "https://github.com/leanprover-community/mathlib4"
    assert config.count(url) == 1
    (git_dir / "config").write_text(config.replace(url, url + "-unexpected"))
    observed, reasons, _ = solutionbuild.observe_build(gate, assembled)
    assert (observed, reasons) == (
        solutionplan.OBSERVED_REFUSED,
        ("dependency-checkout-mismatch:mathlib:remote",),
    )


def test_a_compiling_weaker_statement_fails_real_prelude_closure_comparison(pinned_bundle, tmp_path, comparator):
    gate = bundle.GateBundle.open(*pinned_bundle())
    formal = "theorem challenge_curve {R : Type} [CommRing R] (W : WeierstrassCurve R) : W.Δ = W.Δ := by\n  sorry\n"
    statement = factories.claim_statement(seed=4, formal_source=formal)
    proof = gate.challenge_prelude + b"theorem challenge_curve : True := by trivial\n"
    assembled = solutionbuild.assemble(
        gate,
        statement,
        challenge.Submission(solution_module=proof, formal_statement_hash=FSH),
        ("challenge_curve",),
        root=tmp_path / "weaker-statement",
        formal_statement_hash=FSH,
        dependency_project=lean.PROJECT_DIR,
    )
    built = solutionbuild.observe_build(gate, assembled)
    assert built[:2] == (solutionplan.EXPECT_BUILT, ())
    observed, reasons, _ = solutionchecks.observe_closure_comparison(
        gate, assembled, comparator=comparator, timeout_s=120
    )
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons[:2] == (solutionchecks.CLOSURE_MISMATCH, "rc:1")


@pytest.mark.timeout(900)
@pytest.mark.parametrize("case", ["exact", "sorry", "timeout"])
def test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks(
    pinned_bundle, tmp_path, comparator, popen_spy, case
):
    gate = bundle.GateBundle.open(*pinned_bundle())
    formal = "theorem challenge_curve {R : Type} [CommRing R] (W : WeierstrassCurve R) : W.Δ = W.Δ := by\n  sorry\n"
    statement = factories.claim_statement(seed=4, formal_source=formal)
    source = formal if case == "sorry" else formal.replace("sorry", "rfl")
    submission = challenge.Submission(
        solution_module=gate.challenge_prelude + source.encode(), formal_statement_hash=FSH
    )
    assembled = solutionbuild.assemble(
        gate,
        statement,
        submission,
        ("challenge_curve",),
        root=tmp_path / "ordered-real-prelude",
        formal_statement_hash=FSH,
        dependency_project=lean.PROJECT_DIR,
    )
    tool = lean.axiom_tool(gate, tmp_path / "axiom-tool", timeout_s=120)
    rows = _plan_rows()
    for row in rows:
        if row["kind"] == solutionplan.KIND_KERNEL_REPLAY:
            row["timeout_s"] = 0.001 if case == "timeout" else lean.DEFAULT_TIMEOUT_S
    ran = []

    def observe(step):
        ran.append(step.kind)
        if step.kind == solutionplan.KIND_STATEMENT_BINDING:
            return solutionbuild.observe_binding(submission, FSH)
        if step.kind == solutionplan.KIND_IMPORT_ALLOWLIST:
            return (*solutionplan.check_imports(submission.solution_module), 0)
        if step.kind == solutionplan.KIND_BUILD:
            return solutionbuild.observe_build(gate, assembled, timeout_s=step.timeout_s)
        if step.kind == solutionplan.KIND_AXIOMS:
            return solutionchecks.observe_axioms(
                gate,
                assembled.solution_module,
                list(assembled.theorem_names),
                project_dir=assembled.root,
                timeout_s=step.timeout_s,
                tool=tool,
            )
        if step.kind == solutionplan.KIND_KERNEL_REPLAY:
            return solutionchecks.observe_kernel_replay(
                gate.lean,
                assembled.solution_module,
                project_dir=assembled.root,
                timeout_s=step.timeout_s,
            )
        assert step.kind == solutionplan.KIND_CLOSURE_COMPARISON
        return solutionchecks.observe_closure_comparison(
            gate, assembled, comparator=comparator, timeout_s=step.timeout_s
        )

    result = solutionplan.SolutionPlan.load(rows, arm=container.DEV_ARM).run(observe)
    lg.info("real_prelude_plan", case=case, steps=[step.__dict__ for step in result.steps])
    assert [step.kind for step in result.steps] == list(PLAN_KINDS)
    assert [step.result for step in result.steps[:3]] == [solutionplan.RESULT_PASS] * 3
    replay_commands = [command for command in popen_spy if "leanchecker" in command]
    comparison_commands = [command for command in popen_spy if str(comparator) in command]
    if case == "sorry":
        assert result.ok is False
        assert ran == list(PLAN_KINDS[:4])
        assert result.first_failure == result.steps[3]
        assert result.steps[3].result == solutionplan.RESULT_FAIL
        assert "offending-axiom:sorryAx" in result.steps[3].reasons
        assert replay_commands == []
        assert comparison_commands == []
        for step in result.steps[4:]:
            assert step.result == solutionplan.RESULT_BLOCKED
            assert step.reasons == (f"blocked-by:{solutionplan.KIND_AXIOMS}",)
    else:
        assert replay_commands == [lean.command(gate.lean, "replay_fresh", module=assembled.solution_module)]
        assert "--fresh" in replay_commands[0]
        assert result.steps[3].result == solutionplan.RESULT_PASS
        if case == "timeout":
            assert result.ok is False
            assert ran == list(PLAN_KINDS[:5])
            assert result.first_failure == result.steps[4]
            assert result.steps[4].result == solutionplan.RESULT_TIMEOUT
            assert result.steps[4].reasons == (solutionplan.TIMEOUT_REASON, "timeout_s:0.001")
            assert result.steps[5].result == solutionplan.RESULT_BLOCKED
            assert result.steps[5].reasons == (f"blocked-by:{solutionplan.KIND_KERNEL_REPLAY}",)
            assert comparison_commands == []
        else:
            assert result.ok is True
            assert result.first_failure is None
            assert ran == list(PLAN_KINDS)
            assert [step.result for step in result.steps] == [solutionplan.RESULT_PASS] * len(PLAN_KINDS)
            assert comparison_commands == [solutionchecks.comparator_argv(gate.lean, comparator)]
    solutionbuild.assert_unchanged(assembled)
