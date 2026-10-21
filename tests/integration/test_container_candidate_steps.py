import uuid
from dataclasses import replace
from pathlib import Path

import pytest
import test_container_statement_hash as linux_tests

from cairn import challenge, container, lean, log, solutionbuild, solutionchecks

lg = log.get("test")
FORMAL = linux_tests.FORMAL
linux_bundle = linux_tests.linux_bundle
linux_image = linux_tests.linux_image
linux_dependencies = linux_tests.linux_dependencies
linux_project = linux_tests.linux_project
linux_prepared = linux_tests.linux_prepared


@pytest.mark.timeout(1800)
@pytest.mark.parametrize("proof", ["rfl", "sorry", "exact True.intro"])
def test_linux_candidate_compilation_is_not_proof_acceptance(
    linux_bundle, linux_image, linux_prepared, tmp_path, monkeypatch, popen_spy, proof
):
    statement, prepared = linux_prepared
    monkeypatch.setenv("ELAN_HOME", str(tmp_path / "absent-elan"))
    assert not lean.tool_path("lean").exists()
    source = linux_bundle.challenge_prelude + FORMAL.replace("sorry", proof).encode()
    compilation = solutionchecks.compile_container(
        linux_bundle,
        linux_image,
        statement,
        challenge.Submission(solution_module=source, formal_statement_hash=prepared.formal_statement_hash),
        ("challenge_curve",),
        prepared=prepared,
        root=tmp_path / "candidate",
    )
    result = compilation.result
    if proof == "exact True.intro":
        assert result.rc != 0
        assert "Type mismatch" in result.stdout
        assert "True.intro" in result.stdout
        tool = tmp_path / "axioms"
        with pytest.raises(lean.LeanRejected, match="Type mismatch"):
            solutionchecks.check_container_axioms(linux_bundle, compilation, work_dir=tool)
        assert not tool.exists()
    else:
        assert result.rc == 0, result.stdout + result.stderr
        for module in (compilation.project.solution_module, compilation.project.challenge_module):
            assert (
                Path(compilation.project.root) / ".lake/build/lib/lean" / (module.replace(".", "/") + ".olean")
            ).is_file()
        if proof == "sorry":
            assert "declaration uses `sorry`" in result.stdout
    solutionbuild.assert_unchanged(prepared.project)
    solutionbuild.assert_dependencies(linux_bundle, prepared.project)
    docker = [argv for argv in popen_spy if "--network" in argv]
    assert len(docker) == 2
    assert all(argv[argv.index("--network") + 1] == "none" for argv in docker)
    assert all(linux_image.image_id in argv for argv in docker)
    assert all(argv[argv.index("--user") + 1] == container.host_user() for argv in docker)
    assert all(prepared.project.root not in " ".join(argv) for argv in docker)
    assert compilation.project.solution_module in docker[-1]
    assert compilation.project.challenge_module in docker[-1]
    lg.info("candidate_compilation", proof=proof, rc=result.rc, stdout=result.stdout, image_id=linux_image.image_id)


@pytest.mark.timeout(1800)
@pytest.mark.parametrize("proof", ["rfl", "sorry"])
def test_linux_candidate_axioms(linux_bundle, linux_image, linux_prepared, tmp_path, monkeypatch, popen_spy, proof):
    statement, prepared = linux_prepared
    monkeypatch.setenv("ELAN_HOME", str(tmp_path / "absent-elan"))
    assert not lean.tool_path("lean").exists()
    source = linux_bundle.challenge_prelude + FORMAL.replace("sorry", proof).encode()
    compilation = solutionchecks.compile_container(
        linux_bundle,
        linux_image,
        statement,
        challenge.Submission(solution_module=source, formal_statement_hash=prepared.formal_statement_hash),
        ("challenge_curve",),
        prepared=prepared,
        root=tmp_path / "candidate",
    )
    assert compilation.result.rc == 0
    popen_spy.clear()
    tool = tmp_path / "axioms"
    record = solutionchecks.check_container_axioms(linux_bundle, compilation, work_dir=tool)
    assert record["passed"] is (proof == "rfl")
    assert record["offending_axioms"] == ([] if proof == "rfl" else ["sorryAx"])
    assert set(record["theorems"]) == {"challenge_curve"}
    assert (tool / "Cairn/Axioms.lean").read_bytes() == linux_bundle.raw(lean.AXIOM_KIND)
    docker = [argv for argv in popen_spy if "--network" in argv]
    assert len(docker) == 4
    assert all(argv[argv.index("--network") + 1] == "none" for argv in docker)
    assert all(linux_image.image_id in argv for argv in docker)
    assert all(argv[argv.index("--user") + 1] == container.host_user() for argv in docker)
    assert not any(str(tool) in arg for arg in docker[-2])
    assert f"type=bind,source={tool},target=/axiom-tool,readonly=true" in docker[-1]
    assert f"type=bind,source={Path(compilation.project.root).absolute()},target=/project,readonly=true" in docker[-1]
    assert "lake" not in docker[-1]
    solutionbuild.assert_unchanged(compilation.project)
    solutionbuild.assert_dependencies(linux_bundle, compilation.project)
    lg.info("candidate_axioms", proof=proof, record=record, image_id=linux_image.image_id)
    if proof == "rfl":
        popen_spy.clear()
        cases = (
            (replace(compilation, bundle_hash="0" * 64), solutionbuild.SolutionRefused, "bundle_hash"),
            (replace(compilation, pin_hash="0" * 64), solutionbuild.SolutionRefused, "pin_hash"),
            (
                replace(compilation, image=replace(linux_image, identity="0" * 64)),
                container.ContainerError,
                "image-mismatch",
            ),
        )
        for index, (candidate, error, reason) in enumerate(cases):
            refused_tool = tmp_path / f"refused-{index}"
            with pytest.raises(error, match=reason):
                solutionchecks.check_container_axioms(linux_bundle, candidate, work_dir=refused_tool)
            assert not refused_tool.exists()
        assert all(argv[0] == solutionbuild.GIT for argv in popen_spy)
        missing = replace(compilation, project=replace(compilation.project, theorem_names=("missing",)))
        with pytest.raises(lean.LeanRejected, match="missing-theorem:missing"):
            solutionchecks.check_container_axioms(linux_bundle, missing, work_dir=tmp_path / "missing")
    real_check = container.check_axioms
    changed = (
        solutionbuild.module_path(compilation.project.formal_statement_hash, compilation.project.root)
        if proof == "rfl"
        else Path(compilation.project.root) / ".lake/package-overrides.json"
    )
    mutation = changed.read_bytes() + b"\n" if proof == "rfl" else b"{}"
    reason = "solution-inputs-changed" if proof == "rfl" else "dependency-overrides-refused"

    def check_then_change(*args, **kwargs):
        observed = real_check(*args, **kwargs)
        assert observed == record
        changed.write_bytes(mutation)
        return observed

    monkeypatch.setattr(container, "check_axioms", check_then_change)
    with pytest.raises(solutionbuild.SolutionRefused, match=reason):
        solutionchecks.check_container_axioms(linux_bundle, compilation, work_dir=tmp_path / "mutating")
    assert changed.read_bytes() == mutation
    popen_spy.clear()
    with pytest.raises(solutionbuild.SolutionRefused, match=reason):
        solutionchecks.check_container_axioms(linux_bundle, compilation, work_dir=tmp_path / "changed")
    assert not (tmp_path / "changed").exists()
    assert all(argv[0] == solutionbuild.GIT for argv in popen_spy)


@pytest.mark.timeout(1800)
@pytest.mark.parametrize("mutation", ["lake-manifest.json", ".lake/package-overrides.json"])
def test_linux_candidate_refuses_project_mutation(linux_bundle, linux_image, linux_prepared, tmp_path, mutation):
    statement, prepared = linux_prepared
    source = linux_bundle.challenge_prelude + FORMAL.replace("sorry", "rfl").encode()
    source += f'\n#eval (IO.FS.writeFile "{mutation}" "{{}}" : IO Unit)\n'.encode()
    with pytest.raises(solutionbuild.SolutionRefused, match=r"solution-inputs-changed|dependency-overrides-refused"):
        solutionchecks.compile_container(
            linux_bundle,
            linux_image,
            statement,
            challenge.Submission(solution_module=source, formal_statement_hash=prepared.formal_statement_hash),
            ("challenge_curve",),
            prepared=prepared,
            root=tmp_path / "candidate",
        )
    assert (tmp_path / "candidate" / mutation).read_text() == "{}"
    solutionbuild.assert_unchanged(prepared.project)
    solutionbuild.assert_dependencies(linux_bundle, prepared.project)


@pytest.mark.timeout(1800)
def test_linux_candidate_admission_precedes_writes_and_processes(
    linux_bundle, linux_image, linux_prepared, tmp_path, popen_spy
):
    statement, prepared = linux_prepared
    source = linux_bundle.challenge_prelude + FORMAL.replace("sorry", "rfl").encode()
    submission = challenge.Submission(solution_module=source, formal_statement_hash=prepared.formal_statement_hash)
    cases = (
        (replace(submission, formal_statement_hash="0" * 64), prepared, "statement-hash-mismatch"),
        (replace(submission, solution_module=b"import Lake\n"), prepared, "import"),
        (submission, replace(prepared, image=None), "prepared-challenge-mismatch:image"),
        (submission, replace(prepared, statement_hash="0" * 64), "prepared-challenge-mismatch:statement_hash"),
        (submission, replace(prepared, pin_hash="0" * 64), "prepared-challenge-mismatch:pin_hash"),
    )
    for index, (candidate, handoff, reason) in enumerate(cases):
        root = tmp_path / str(index)
        with pytest.raises(solutionbuild.SolutionRefused, match=reason):
            solutionchecks.compile_container(
                linux_bundle, linux_image, statement, candidate, ("challenge_curve",), prepared=handoff, root=root
            )
        assert not root.exists()
    assert popen_spy == []


def test_container_timeout_stops_only_its_own_work(linux_image, tmp_path):
    sibling = "cairn-sibling-" + uuid.uuid4().hex
    ctx = linux_image.context
    lean.require_success(
        container.run_docker(ctx, "run", "--rm", "--detach", "--name", sibling, linux_image.image_id, "sleep", "60")
    )
    owned = None
    try:
        with pytest.raises(lean.LeanTimeout) as timeout:
            container.run(
                ctx,
                linux_image.image_id,
                ["sh", "-c", "touch /project/started; sleep 60"],
                user=container.host_user(),
                mounts=((tmp_path, "/project", "readonly=false"),),
                env=(("HOME", "/project"), (sibling, "owned elsewhere")),
                timeout_s=15,
            )
        argv = timeout.value.argv
        owned = argv[argv.index("--name") + 1]
        assert (tmp_path / "started").is_file()
        running = container.run_docker(ctx, "ps", "--format", "{{.Names}}")
        lean.require_success(running)
        assert owned not in running.stdout.splitlines()
        assert sibling in running.stdout.splitlines()
        lg.info("container_timeout_stopped", owned=owned, sibling=sibling, timeout_s=timeout.value.timeout_s)
    finally:
        lean.require_success(container.run_docker(ctx, "stop", "--time", "0", sibling))
        if owned is not None:
            container.run_docker(ctx, "stop", "--time", "0", owned)


def test_container_exit_preserves_its_status_and_output(linux_image):
    for code in (0, 7):
        result = container.run(
            linux_image.context,
            linux_image.image_id,
            ["sh", "-c", f"printf output; printf diagnostic >&2; exit {code}"],
            user=container.host_user(),
        )
        assert (result.rc, result.stdout, result.stderr) == (code, "output", "diagnostic")
        lg.info("container_exit_preserved", rc=result.rc, stdout=result.stdout, stderr=result.stderr)


def test_container_timeout_reports_failed_cleanup(linux_image, tmp_path, monkeypatch):
    real_run = container.run_docker
    absent_context = "cairn-absent-" + uuid.uuid4().hex

    def unavailable_cleanup(ctx, *args, **kwargs):
        return real_run(absent_context if args[0] == "stop" else ctx, *args, **kwargs)

    monkeypatch.setattr(container, "run_docker", unavailable_cleanup)
    owned = None
    try:
        with pytest.raises(container.ContainerError, match="container-timeout-cleanup-unconfirmed") as failure:
            container.run(
                linux_image.context,
                linux_image.image_id,
                ["sh", "-c", "touch /project/started; sleep 60"],
                user=container.host_user(),
                mounts=((tmp_path, "/project", "readonly=false"),),
                timeout_s=2,
            )
        cause = failure.value.__cause__
        assert isinstance(cause, lean.LeanTimeout)
        owned = cause.argv[cause.argv.index("--name") + 1]
        assert owned in str(failure.value)
        assert absent_context in str(failure.value)
        assert (tmp_path / "started").is_file()
        running = real_run(linux_image.context, "ps", "--format", "{{.Names}}")
        lean.require_success(running)
        assert owned in running.stdout.splitlines()
        lg.info("container_cleanup_failure_reported", name=owned, reason=str(failure.value))
    finally:
        if owned is not None:
            lean.require_success(real_run(linux_image.context, "stop", "--time", "0", owned))
