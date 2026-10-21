import json
import os
from dataclasses import replace
from pathlib import Path

import _linux_dependencies as dependencies
import _substrate_helpers as substrate_helpers
import factories
import pytest

from cairn import (
    bundle,
    challenge,
    claims,
    container,
    lean,
    log,
    scrutiny,
    solutionbuild,
    solutionchecks,
    solutionplan,
    solutionreplay,
)

lg = log.get("test")
FORMAL = "theorem challenge_curve {R : Type} [CommRing R] (W : WeierstrassCurve R) : W.Δ = W.Δ := by\n  sorry\n"
REPLAY_ARGV = [solutionreplay.IMAGE_REPLAY_CHECKER, "--fresh", "-v"]


@pytest.fixture(scope="module")
def linux_bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("linux-bundle")
    database, pin = root / "bundle.sqlite", root / "bundle.pin"
    bundle.build(lean.REPO_ROOT / "bundle", database)
    bundle.write_pin(database, pin)
    yield bundle.GateBundle.open(database, pin)
    if hasattr(os, "chflags"):
        os.chflags(pin, 0)
    pin.chmod(0o644)
    database.chmod(0o644)


@pytest.fixture(scope="module")
def linux_image(linux_bundle):
    ctx = container.context()
    lg.info("container_daemon", context=ctx, info=container.daemon_info(ctx))
    configured = os.environ.get(dependencies.CACHE_ENV)
    if configured:
        return dependencies.cached_image(linux_bundle, configured)
    return container.build(ctx, linux_bundle.container_identity)


@pytest.fixture(scope="module")
def linux_dependencies(linux_bundle, linux_image, tmp_path_factory):
    configured = os.environ.get(dependencies.CACHE_ENV)
    if configured:
        cache = Path(configured)
        dependencies.validate(linux_bundle, linux_image, cache / dependencies.cache_key(linux_bundle, linux_image))
    else:
        cache = tmp_path_factory.mktemp("linux-dependencies")
        dependencies.prepare(linux_bundle, linux_image, cache)
    return cache


@pytest.fixture(scope="module")
def linux_project(linux_bundle, linux_image, linux_dependencies, tmp_path_factory):
    root = tmp_path_factory.mktemp("linux-challenge") / "project"
    dependencies.restore(linux_bundle, linux_image, linux_dependencies, root)
    lg.info("linux_project_owner", uid=os.getuid(), gid=os.getgid(), mode=oct(root.stat().st_mode & 0o777))
    (root / "Challenge").mkdir()
    modules = []
    for source in (FORMAL, FORMAL.replace("W.Δ = W.Δ", "W.Δ + 0 = W.Δ")):
        statement = factories.claim_statement(seed=4, formal_source=source)
        challenge.module_path(statement, root / "Challenge").write_bytes(
            challenge.render(statement, linux_bundle.challenge_prelude)
        )
        modules.append(challenge.module_name(statement))
    return root, modules


@pytest.fixture(scope="module")
def linux_prepared(linux_bundle, linux_image, linux_project, tmp_path_factory):
    statement = factories.claim_statement(seed=4, formal_source=FORMAL)
    prepared = solutionchecks.prepare_container(
        linux_bundle,
        linux_image,
        statement,
        ("challenge_curve",),
        root=tmp_path_factory.mktemp("linux-candidate") / "prepared",
        dependency_project=linux_project[0],
    )
    return statement, prepared


def _compile(linux_bundle, linux_image, linux_prepared, tmp_path, source):
    statement, prepared = linux_prepared
    compilation = solutionchecks.compile_container(
        linux_bundle,
        linux_image,
        statement,
        challenge.Submission(solution_module=source, formal_statement_hash=prepared.formal_statement_hash),
        ("challenge_curve",),
        prepared=prepared,
        root=tmp_path / "candidate",
    )
    lean.require_success(compilation.result)
    return compilation


@pytest.mark.timeout(1800)
@pytest.mark.parametrize("proof", ["rfl", "sorry", "forged"])
def test_linux_candidate_fresh_replay(
    linux_bundle, linux_image, linux_prepared, tmp_path, monkeypatch, popen_spy, proof
):
    monkeypatch.setenv("ELAN_HOME", str(tmp_path / "absent-elan"))
    assert not lean.tool_path("lean").exists()
    source = linux_bundle.challenge_prelude
    if proof == "forged":
        fixture = (Path(__file__).parents[1] / "fixtures/solution_forgery/forge_unchecked_theorem.lean").read_text()
        assert fixture.startswith("import Lean\n")
        source += fixture.removeprefix("import Lean\n").encode() + b"\n"
    source += FORMAL.replace("sorry", "exact False.elim forged" if proof == "forged" else proof).encode()
    compilation = _compile(linux_bundle, linux_image, linux_prepared, tmp_path, source)
    popen_spy.clear()
    if proof == "rfl":
        for field in ("bundle_hash", "pin_hash"):
            with pytest.raises(solutionbuild.SolutionRefused, match=f"container-compilation-mismatch:{field}"):
                solutionchecks.observe_container_replay(
                    linux_bundle, replace(compilation, **{field: "0" * 64}), work_dir=tmp_path / field
                )
            assert not (tmp_path / field).exists()
        assert popen_spy == []
    observed, reasons, wall_ms = solutionchecks.observe_container_replay(
        linux_bundle, compilation, work_dir=tmp_path / "axioms"
    )
    lg.info("candidate_replay", proof=proof, observed=observed, reasons=reasons, wall_ms=wall_ms)
    replay = [argv for argv in popen_spy if solutionreplay.IMAGE_REPLAY_CHECKER in argv]
    if proof == "sorry":
        assert observed == solutionplan.OBSERVED_REFUSED
        assert reasons == ("offending-axiom:sorryAx",)
        assert replay == []
    else:
        assert len(replay) == 1
        assert replay[0][-4:] == [*REPLAY_ARGV, compilation.project.solution_module]
        assert "lake" not in replay[0]
        project_mount = f"type=bind,source={Path(compilation.project.root).absolute()},target=/project,readonly=true"
        assert project_mount in replay[0]
        if proof == "rfl":
            assert (observed, reasons) == (solutionplan.EXPECT_REPLAYED, ())
        else:
            assert observed == solutionplan.OBSERVED_REFUSED
            assert reasons[:2] == (solutionchecks.KERNEL_REJECTED, "rc:1")
            assert any("while replaying declaration 'forged'" in reason for reason in reasons)
    docker = [argv for argv in popen_spy if "--network" in argv]
    assert docker
    assert all(linux_image.image_id in argv for argv in docker)
    assert all(argv[argv.index("--network") + 1] == "none" for argv in docker)
    assert all(argv[argv.index("--user") + 1] == container.host_user() for argv in docker)
    axioms = [argv for argv in docker if "/axiom-tool/.lake/build/bin/axioms" in argv]
    assert len(axioms) == 1
    if replay:
        assert docker.index(axioms[0]) < docker.index(replay[0])
    solutionbuild.assert_unchanged(compilation.project)
    solutionbuild.assert_dependencies(linux_bundle, compilation.project)


@pytest.mark.timeout(1800)
def test_linux_candidate_closure_comparison_matches_exact_statement(
    linux_bundle, linux_image, linux_prepared, tmp_path, monkeypatch, popen_spy, json_test_log
):
    monkeypatch.setenv("ELAN_HOME", str(tmp_path / "absent-elan"))
    assert not lean.tool_path("lean").exists()
    source = linux_bundle.challenge_prelude + FORMAL.replace("sorry", "rfl").encode()
    compilation = _compile(linux_bundle, linux_image, linux_prepared, tmp_path, source)
    written_config = json.loads((Path(compilation.project.root) / solutionbuild.CONFIG_NAME).read_text())
    assert written_config["external_kernels"] == linux_bundle.lean["external_kernels"]
    assert "enable_nanoda" not in written_config
    popen_spy.clear()
    observed, reasons, wall_ms = solutionchecks.observe_container_comparison(linux_bundle, compilation)
    assert (observed, reasons) == (solutionplan.EXPECT_CLOSURE_MATCHED, ())
    assert wall_ms >= 0
    events = [json.loads(line) for line in json_test_log.read_text().splitlines()]
    comparisons = [event for event in events if event["event"] == "container_comparison"]
    assert len(comparisons) == 1
    assert "nanoda kernel accepts the solution" in comparisons[0]["result"]["stdout"]
    comparison = [argv for argv in popen_spy if "/home/cairn/comparator/.lake/build/bin/comparator" in argv]
    assert len(comparison) == 1
    assert comparison[0][-5:] == [
        "lake",
        f"+{linux_bundle.lean['toolchain']}",
        "env",
        "/home/cairn/comparator/.lake/build/bin/comparator",
        solutionbuild.CONFIG_NAME,
    ]
    assert comparison[0][comparison[0].index("--network") + 1] == "none"
    assert linux_image.image_id in comparison[0]
    assert comparison[0][comparison[0].index("--user") + 1] == container.host_user()
    solutionbuild.assert_unchanged(compilation.project)
    solutionbuild.assert_dependencies(linux_bundle, compilation.project)
    popen_spy.clear()
    with pytest.raises(solutionplan.StepTimeout) as expired:
        solutionchecks.observe_container_comparison(linux_bundle, compilation, timeout_s=2.0)
    assert (expired.value.step, expired.value.timeout_s) == (solutionplan.KIND_CLOSURE_COMPARISON, 2.0)
    timed_comparison = [argv for argv in popen_spy if solutionchecks.CONTAINER_COMPARATOR_BINARY in argv]
    assert len(timed_comparison) == 1
    assert any("stop" in argv for argv in popen_spy)


@pytest.mark.timeout(1800)
def test_linux_candidate_closure_comparison_refuses_weaker_statement(
    linux_bundle, linux_image, linux_prepared, tmp_path, monkeypatch, popen_spy
):
    monkeypatch.setenv("ELAN_HOME", str(tmp_path / "absent-elan"))
    assert not lean.tool_path("lean").exists()
    source = linux_bundle.challenge_prelude + b"theorem challenge_curve : True := by trivial\n"
    compilation = _compile(linux_bundle, linux_image, linux_prepared, tmp_path, source)
    popen_spy.clear()
    observed, reasons, wall_ms = solutionchecks.observe_container_comparison(linux_bundle, compilation)
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons[:2] == (solutionchecks.CLOSURE_MISMATCH, "rc:1")
    assert "Challenge and solution theorem statement do not match: 'challenge_curve'" in reasons[2]
    assert wall_ms >= 0
    comparison = [argv for argv in popen_spy if solutionchecks.CONTAINER_COMPARATOR_BINARY in argv]
    assert len(comparison) == 1
    assert comparison[0][comparison[0].index("--network") + 1] == "none"
    assert linux_image.image_id in comparison[0]
    assert comparison[0][comparison[0].index("--user") + 1] == container.host_user()
    solutionbuild.assert_unchanged(compilation.project)
    solutionbuild.assert_dependencies(linux_bundle, compilation.project)


@pytest.mark.timeout(1800)
@pytest.mark.parametrize("case", ["exact", "sorry", "weaker", "stale-hash"])
def test_linux_ordered_plan_runs_each_step_in_order(
    linux_bundle, linux_image, linux_prepared, tmp_path, monkeypatch, popen_spy, case
):
    statement, prepared = linux_prepared
    monkeypatch.setenv("ELAN_HOME", str(tmp_path / "absent-elan"))
    assert not lean.tool_path("lean").exists()
    if case == "weaker":
        source = linux_bundle.challenge_prelude + b"theorem challenge_curve : True := by trivial\n"
    else:
        source = (
            linux_bundle.challenge_prelude + FORMAL.replace("sorry", "sorry" if case == "sorry" else "rfl").encode()
        )
    submission = challenge.Submission(
        solution_module=source,
        formal_statement_hash="0" * 64 if case == "stale-hash" else prepared.formal_statement_hash,
    )
    rows = [
        {
            "step": kind,
            "kind": kind,
            "expect": solutionplan.KIND_EXPECTATION[kind],
            "blocking": True,
            "timeout_s": container.RUN_TIMEOUT_S
            if kind in (solutionplan.KIND_BUILD, solutionplan.KIND_AXIOMS)
            else lean.DEFAULT_TIMEOUT_S,
        }
        for kind in solutionplan.STEP_KINDS
    ]
    root, work_dir = tmp_path / "candidate", tmp_path / "axioms"
    popen_spy.clear()
    sub = substrate_helpers.open_writer(tmp_path)
    try:
        claims.write_claim_statement(sub, statement)
        result = solutionchecks.run_container(
            linux_bundle,
            linux_image,
            statement,
            submission,
            ("challenge_curve",),
            rows,
            sub=sub,
            root=root,
            work_dir=work_dir,
            prepared=prepared,
        )
        lg.info("candidate_ordered_plan", case=case, steps=[step.__dict__ for step in result.steps])
        steps = result.steps
        persisted = sub.conn.execute(
            "SELECT plan_step, result, arm FROM gate_runs WHERE gate = ? ORDER BY rowid", (solutionplan.STEP_GATE,)
        ).fetchall()
        assert [tuple(row) for row in persisted] == [(step.step, step.result, container.GOLD_ARM) for step in steps]
        assert (
            sub.conn.execute("SELECT COUNT(*) FROM gate_runs WHERE gate = ?", (solutionplan.SUMMARY_GATE,)).fetchone()[
                0
            ]
            == 1
        )
        assert scrutiny._formalization_passed(sub, statement.hash) is (case == "exact")
    finally:
        sub.close()
    assert result.arm == container.GOLD_ARM
    assert [step.kind for step in steps] == list(solutionplan.STEP_KINDS)
    results = [step.result for step in steps]
    replay = [argv for argv in popen_spy if solutionreplay.IMAGE_REPLAY_CHECKER in argv]
    comparison = [argv for argv in popen_spy if solutionchecks.CONTAINER_COMPARATOR_BINARY in argv]
    axioms = [argv for argv in popen_spy if "/axiom-tool/.lake/build/bin/axioms" in argv]
    docker = [argv for argv in popen_spy if "--network" in argv]
    if case == "stale-hash":
        assert results == [solutionplan.RESULT_FAIL] + [solutionplan.RESULT_BLOCKED] * 5
        assert result.first_failure == steps[0]
        assert steps[0].reasons[-1].startswith(f"{solutionbuild.STATEMENT_HASH_MISMATCH}:")
        for step in steps[1:]:
            assert step.reasons == (f"blocked-by:{solutionplan.KIND_STATEMENT_BINDING}",)
        assert popen_spy == []
        assert not root.exists()
        assert not work_dir.exists()
        return
    assert docker
    assert all(argv[argv.index("--network") + 1] == "none" for argv in docker)
    assert all(linux_image.image_id in argv for argv in docker)
    assert all(argv[argv.index("--user") + 1] == container.host_user() for argv in docker)
    solutionbuild.assert_unchanged(prepared.project)
    solutionbuild.assert_dependencies(linux_bundle, prepared.project)
    if case == "sorry":
        assert (
            results == [solutionplan.RESULT_PASS] * 3 + [solutionplan.RESULT_FAIL] + [solutionplan.RESULT_BLOCKED] * 2
        )
        assert result.first_failure == steps[3]
        assert "offending-axiom:sorryAx" in steps[3].reasons
        for step in steps[4:]:
            assert step.reasons == (f"blocked-by:{solutionplan.KIND_AXIOMS}",)
        assert replay == []
        assert comparison == []
        assert len(axioms) == 1
        return
    assert len(axioms) == len(replay) == len(comparison) == 1
    assert replay[0][-4:] == [*REPLAY_ARGV, solutionbuild.module_name(prepared.formal_statement_hash)]
    assert popen_spy.index(axioms[0]) < popen_spy.index(replay[0]) < popen_spy.index(comparison[0])
    if case == "exact":
        assert result.ok is True
        assert result.first_failure is None
        assert results == [solutionplan.RESULT_PASS] * 6
    else:
        assert results == [solutionplan.RESULT_PASS] * 5 + [solutionplan.RESULT_FAIL]
        assert result.first_failure == steps[5]
        assert solutionchecks.CLOSURE_MISMATCH in steps[5].reasons


@pytest.mark.timeout(1800)
def test_linux_replay_timeouts_keep_their_stage_and_check_inputs(
    linux_bundle, linux_image, linux_prepared, tmp_path, monkeypatch, popen_spy
):
    monkeypatch.setenv("ELAN_HOME", str(tmp_path / "absent-elan"))
    source = linux_bundle.challenge_prelude + FORMAL.replace("sorry", "rfl").encode()
    compilation = _compile(linux_bundle, linux_image, linux_prepared, tmp_path, source)
    for stage, bounds in (
        (solutionplan.KIND_AXIOMS, {"axiom_timeout_s": 2.0}),
        (solutionplan.KIND_KERNEL_REPLAY, {"timeout_s": 2.0}),
    ):
        popen_spy.clear()
        with pytest.raises(solutionplan.StepTimeout) as expired:
            solutionchecks.observe_container_replay(linux_bundle, compilation, work_dir=tmp_path / stage, **bounds)
        assert (expired.value.step, expired.value.timeout_s) == (stage, 2.0)
        replay = [argv for argv in popen_spy if solutionreplay.IMAGE_REPLAY_CHECKER in argv]
        assert len(replay) == (1 if stage == solutionplan.KIND_KERNEL_REPLAY else 0)
        assert any("stop" in argv for argv in popen_spy)
        lg.info("candidate_replay_timeout", step=expired.value.step, timeout_s=expired.value.timeout_s)
    real_run = container.run
    changed = Path(compilation.project.root) / ".lake/package-overrides.json"

    def change_after_timeout(ctx, image, argv, **kwargs):
        try:
            return real_run(ctx, image, argv, **kwargs)
        except lean.LeanTimeout:
            if solutionreplay.IMAGE_REPLAY_CHECKER in argv:
                changed.write_text("{}")
            raise

    monkeypatch.setattr(container, "run", change_after_timeout)
    with pytest.raises(solutionbuild.SolutionRefused, match="dependency-overrides-refused"):
        solutionchecks.observe_container_replay(
            linux_bundle, compilation, work_dir=tmp_path / "mutating", timeout_s=2.0
        )
    assert changed.read_text() == "{}"
    popen_spy.clear()
    with pytest.raises(solutionbuild.SolutionRefused, match="dependency-overrides-refused"):
        solutionchecks.observe_container_replay(linux_bundle, compilation, work_dir=tmp_path / "changed")
    assert not (tmp_path / "changed").exists()
    assert not any("--network" in argv for argv in popen_spy)
