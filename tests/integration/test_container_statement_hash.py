import json
import os
import uuid
from dataclasses import replace
from pathlib import Path

import factories
import pytest

from cairn import bundle, challenge, container, lean, log, solutionbuild, solutionchecks, solutionplan

lg = log.get("test")
MATHLIB_MODULE = "Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point"
FORMAL = "theorem challenge_curve {R : Type} [CommRing R] (W : WeierstrassCurve R) : W.Δ = W.Δ := by\n  sorry\n"


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
                timeout_s=2,
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
    return container.build(ctx, linux_bundle.container_identity)


@pytest.fixture(scope="module")
def linux_project(linux_bundle, linux_image, tmp_path_factory):
    root = tmp_path_factory.mktemp("linux-challenge")
    lg.info("linux_project_owner", uid=os.getuid(), gid=os.getgid(), mode=oct(root.stat().st_mode & 0o777))
    (root / "Challenge").mkdir()
    pins = linux_bundle.lean
    (root / "lean-toolchain").write_text(pins["toolchain"] + "\n")
    (root / "lake-manifest.json").write_text(json.dumps(linux_bundle.lake_manifest))
    (root / "lakefile.toml").write_text(
        'name = "cairn_lean"\n\n[[lean_lib]]\nname = "Challenge"\nglobs = ["Challenge.+"]\n\n'
        '[[require]]\nname = "mathlib"\ngit = "https://github.com/leanprover-community/mathlib4"\n'
        f'rev = "{pins["mathlib_rev"]}"\n'
    )
    modules = []
    for source in (FORMAL, FORMAL.replace("W.Δ = W.Δ", "W.Δ + 0 = W.Δ")):
        statement = factories.claim_statement(seed=4, formal_source=source)
        challenge.module_path(statement, root / "Challenge").write_bytes(
            challenge.render(statement, linux_bundle.challenge_prelude)
        )
        modules.append(challenge.module_name(statement))
    result = container.run(
        linux_image.context,
        linux_image.image_id,
        ["lake", f"+{pins['toolchain']}", "exe", "cache", "get", MATHLIB_MODULE],
        mounts=((root, "/project", "readonly=false"),),
        workdir="/project",
        user=container.host_user(),
        env=(("HOME", "/project"),),
        network="bridge",
    )
    lg.info("linux_mathlib_provision", rc=result.rc, stdout=result.stdout[-1500:], stderr=result.stderr[-1500:])
    lean.require_success(result)
    assert json.loads((root / "lake-manifest.json").read_text()) == linux_bundle.lake_manifest
    return root, modules


@pytest.mark.timeout(1800)
def test_linux_hashes_real_challenges_and_rejects_absent_theorems(
    linux_bundle,
    linux_image,
    linux_project,
    tmp_path,
    popen_spy,
):
    root, modules = linux_project
    source_bytes = {path: path.read_bytes() for path in (root / "Challenge").glob("*.lean")}
    hashes = [
        container.formal_statement_hash(
            linux_bundle,
            replace(linux_image, tag="cairn-tag-must-not-resolve"),
            module,
            ["challenge_curve"],
            project_dir=root,
            work_dir=tmp_path / f"tool-{index}",
        )
        for index, module in enumerate(modules)
    ]
    assert hashes[0] == "f4cd161738602628f5d766379b78605147761457507b9320ef14dcf115aeaa42"
    assert hashes[0] != hashes[1]
    with pytest.raises(lean.LeanRejected, match="missing-theorem:absent_theorem"):
        container.formal_statement_hash(
            linux_bundle,
            linux_image,
            modules[0],
            ["absent_theorem"],
            project_dir=root,
            work_dir=tmp_path / "tool-absent",
        )
    assert all(path.read_bytes() == original for path, original in source_bytes.items())
    assert popen_spy
    assert all(command[command.index("--network") + 1] == "none" for command in popen_spy)
    assert all(linux_image.image_id in command for command in popen_spy)
    assert all(command[command.index("--user") + 1] == container.host_user() for command in popen_spy)
    lg.info("linux_hash_pair", hashes=hashes, image_id=linux_image.image_id)


@pytest.mark.timeout(1800)
def test_linux_build_error_returns_no_hash(linux_bundle, linux_image, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "lakefile.toml").write_text('name = "broken"\n\n[[lean_lib]]\nname = "Challenge"\n')
    (project / "lean-toolchain").write_text(linux_bundle.lean["toolchain"] + "\n")
    (project / "Challenge.lean").write_text("theorem broken : False := by exact True.intro\n")
    with pytest.raises(lean.LeanRejected, match="Type mismatch") as rejected:
        container.formal_statement_hash(
            linux_bundle,
            linux_image,
            "Challenge",
            ["broken"],
            project_dir=project,
            work_dir=tmp_path / "tool",
        )
    assert "True.intro" in str(rejected.value)
    assert "False" in str(rejected.value)


def test_wrong_image_identity_refuses_before_creating_a_project(linux_bundle, tmp_path, popen_spy):
    image = container.Image("0" * 64, "unused", "sha256:" + "1" * 64, None)
    with pytest.raises(container.ContainerError, match="statement-hasher-image-mismatch"):
        container.formal_statement_hash(
            linux_bundle,
            image,
            "Challenge",
            ["target"],
            project_dir=tmp_path,
            work_dir=tmp_path / "tool",
        )
    assert not (tmp_path / "tool").exists()
    assert popen_spy == []


def test_root_host_user_is_refused(monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 0)
    with pytest.raises(container.ContainerError, match="container-host-user-root"):
        container.host_user()


@pytest.mark.timeout(1800)
def test_container_preparation_binds_the_claim_without_host_lean(
    linux_bundle, linux_image, linux_project, tmp_path, monkeypatch, popen_spy
):
    dependencies, _ = linux_project
    monkeypatch.setenv("ELAN_HOME", str(tmp_path / "absent-elan"))
    assert not lean.tool_path("lean").exists()
    statement = factories.claim_statement(seed=4, formal_source=FORMAL.replace("W.Δ = W.Δ", "W.Δ + 0 = W.Δ"))
    prepared = solutionchecks.prepare_container(
        linux_bundle,
        linux_image,
        statement,
        ("challenge_curve",),
        root=tmp_path / "prepared",
        dependency_project=dependencies,
    )
    assert prepared.formal_statement_hash == "556a38bd0fd7f32b31c6f4fefebd92ad7568788e3639a5f2a0b7102f4eaf53ac"
    assert prepared.statement_hash == statement.hash
    assert prepared.bundle_hash == linux_bundle.hash
    assert prepared.pin_hash == linux_bundle.pin_hash
    assert prepared.renderer_hash == linux_bundle.digest_of(challenge.RENDERER_KIND)
    assert prepared.prelude_hash == linux_bundle.digest_of(challenge.PRELUDE_KIND)
    assert prepared.image == linux_image
    assert prepared.project.theorem_names == ("challenge_curve",)
    root = Path(prepared.project.root)
    assert not list((root / "Solution").rglob("*.lean"))
    rendered = challenge.module_path(statement, root / "Challenge")
    assert rendered.read_bytes() == challenge.render(statement, linux_bundle.challenge_prelude)
    solutionbuild.assert_dependencies(linux_bundle, prepared.project)
    solutionchecks.assert_prepared(linux_bundle, statement, ("challenge_curve",), prepared, image=linux_image)
    assert all(command[0] == container.DOCKER or command[0] == solutionbuild.GIT for command in popen_spy)
    popen_spy.clear()
    for field in ("statement_hash", "bundle_hash", "pin_hash", "renderer_hash", "prelude_hash"):
        with pytest.raises(solutionbuild.SolutionRefused, match=f"prepared-challenge-mismatch:{field}"):
            solutionchecks.assert_prepared(
                linux_bundle, statement, ("challenge_curve",), replace(prepared, **{field: "0" * 64}), image=linux_image
            )
    with pytest.raises(solutionbuild.SolutionRefused, match="prepared-challenge-mismatch:image"):
        solutionchecks.assert_prepared(
            linux_bundle,
            statement,
            ("challenge_curve",),
            prepared,
            image=replace(linux_image, image_id="sha256:" + "0" * 64),
        )
    candidate = tmp_path / "candidate"
    result = solutionchecks.run_dev(
        linux_bundle,
        statement,
        challenge.Submission(solution_module=b"", formal_statement_hash=prepared.formal_statement_hash),
        ("challenge_curve",),
        [
            {
                "step": kind,
                "kind": kind,
                "expect": solutionplan.KIND_EXPECTATION[kind],
                "blocking": True,
                "timeout_s": 120,
            }
            for kind in solutionplan.STEP_KINDS
        ],
        root=candidate,
        prepared=prepared,
        comparator=tmp_path / "absent-comparator",
    )
    assert not result.ok
    assert "prepared-challenge-mismatch:image" in result.first_failure.reasons
    assert all(step.result == solutionplan.RESULT_BLOCKED for step in result.steps[1:])
    assert not candidate.exists()
    rendered.write_bytes(rendered.read_bytes() + b"\n")
    with pytest.raises(solutionbuild.InputsChanged):
        solutionchecks.assert_prepared(linux_bundle, statement, ("challenge_curve",), prepared, image=linux_image)
    assert popen_spy == []
    lg.info("container_prepared_claim", claim=statement.hash, formal_hash=prepared.formal_statement_hash)


def test_container_preparation_rejects_the_wrong_image_before_writing(linux_bundle, tmp_path, popen_spy):
    image = container.Image("0" * 64, "unused", "sha256:" + "1" * 64, None)
    with pytest.raises(container.ContainerError, match="statement-hasher-image-mismatch"):
        solutionchecks.prepare_container(
            linux_bundle,
            image,
            factories.claim_statement(seed=4, formal_source=FORMAL),
            ("challenge_curve",),
            root=tmp_path / "prepared",
        )
    assert not (tmp_path / "prepared").exists()
    assert popen_spy == []


@pytest.mark.timeout(1800)
def test_container_preparation_returns_no_value_when_compilation_fails(linux_bundle, linux_image, tmp_path):
    with pytest.raises(lean.LeanRejected, match="unknown module prefix 'Mathlib'"):
        solutionchecks.prepare_container(
            linux_bundle,
            linux_image,
            factories.claim_statement(seed=4, formal_source=FORMAL),
            ("challenge_curve",),
            root=tmp_path / "prepared",
        )


@pytest.mark.timeout(1800)
def test_container_preparation_rejects_inputs_changed_during_hashing(
    linux_bundle, linux_image, linux_project, tmp_path, monkeypatch
):
    dependencies, _ = linux_project
    statement = factories.claim_statement(seed=4, formal_source=FORMAL)
    real_hash = container.formal_statement_hash

    def hash_then_change(*args, **kwargs):
        digest = real_hash(*args, **kwargs)
        assert digest == "f4cd161738602628f5d766379b78605147761457507b9320ef14dcf115aeaa42"
        source = challenge.module_path(statement, Path(kwargs["project_dir"]) / "Challenge")
        source.write_bytes(source.read_bytes() + b"\n")
        return digest

    monkeypatch.setattr(container, "formal_statement_hash", hash_then_change)
    with pytest.raises(solutionbuild.InputsChanged):
        solutionchecks.prepare_container(
            linux_bundle,
            linux_image,
            statement,
            ("challenge_curve",),
            root=tmp_path / "prepared",
            dependency_project=dependencies,
        )
