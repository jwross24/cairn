import json
import os
from dataclasses import replace
from pathlib import Path

import _linux_dependencies as dependencies
import _substrate_helpers as substrate_helpers
import factories
import pytest
import test_container_statement_hash as linux_tests

from cairn import challenge, claims, container, lean, log, solutionbuild, solutionchecks, solutionplan

lg = log.get("test")
FORMAL = linux_tests.FORMAL
linux_bundle = linux_tests.linux_bundle
linux_image = linux_tests.linux_image
linux_dependencies = linux_tests.linux_dependencies
linux_project = linux_tests.linux_project


def test_cached_linux_image_is_resolved_by_exact_id_without_a_rebuild(linux_bundle, linux_image, tmp_path, popen_spy):
    dependencies.image_record(linux_bundle, tmp_path).write_text(
        json.dumps({"identity": linux_image.identity, "image_id": linux_image.image_id})
    )
    observed = dependencies.cached_image(linux_bundle, tmp_path)
    assert observed.image_id == linux_image.image_id
    assert len(popen_spy) == 2
    assert "inspect" in popen_spy[0]
    assert popen_spy[0][-1] == linux_image.image_id
    assert "--network" in popen_spy[1]
    assert popen_spy[1][popen_spy[1].index("--network") + 1] == "none"


@pytest.mark.timeout(1800)
def test_linux_dependency_cache_restores_without_provisioning(
    linux_bundle, linux_image, linux_dependencies, tmp_path, popen_spy, monkeypatch
):
    root = tmp_path / "private"
    entry = linux_dependencies / dependencies.cache_key(linux_bundle, linux_image)
    before = dependencies.inventory(entry / "project")
    dependencies.restore(linux_bundle, linux_image, linux_dependencies, root)
    assert all(argv[0] == solutionbuild.GIT for argv in popen_spy)
    statement = factories.claim_statement(seed=4, formal_source=FORMAL)
    prepared = solutionchecks.prepare_container(
        linux_bundle, linux_image, statement, ("challenge_curve",), root=tmp_path / "prepared", dependency_project=root
    )
    assert prepared.formal_statement_hash == "050203449ae9ec911926c65bcbb8786f41e86730ca16b2427bb240662b0b2b4d"
    docker = [argv for argv in popen_spy if "--network" in argv]
    assert docker
    assert all(argv[argv.index("--network") + 1] == "none" for argv in docker)
    assert not any(str(entry) in arg for argv in docker for arg in argv)
    artifact = next((root / ".lake/packages/mathlib").rglob("*.olean"))
    artifact.write_bytes(b"private mutation")
    assert dependencies.inventory(entry / "project") == before
    dependencies.validate(linux_bundle, linux_image, entry)
    real_copy = dependencies.shutil.copytree

    def copy_then_change(source, destination, *args, **kwargs):
        copied = real_copy(source, destination, *args, **kwargs)
        if Path(source) == entry / "project":
            artifact = next((Path(destination) / ".lake/packages/mathlib").rglob("*.olean"))
            artifact.write_bytes(b"changed during copy")
        return copied

    monkeypatch.setattr(dependencies.shutil, "copytree", copy_then_change)
    with pytest.raises(dependencies.CacheRefused, match="dependency-cache-copy-mismatch"):
        dependencies.restore(linux_bundle, linux_image, linux_dependencies, tmp_path / "corrupt-copy")
    assert dependencies.inventory(entry / "project") == before


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
    assert hashes[0] == "050203449ae9ec911926c65bcbb8786f41e86730ca16b2427bb240662b0b2b4d"
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
    assert prepared.formal_statement_hash == "928724caf7b2404b9a79315dc4bb8f65b999726d71a21f212d657ac2d5d490e4"
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
    sub = substrate_helpers.open_writer(tmp_path, "dev-run-substrate.sqlite")
    try:
        claims.write_claim_statement(sub, statement)
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
            sub=sub,
            root=candidate,
            prepared=prepared,
            comparator=tmp_path / "absent-comparator",
        )
    finally:
        sub.close()
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
        assert digest == "050203449ae9ec911926c65bcbb8786f41e86730ca16b2427bb240662b0b2b4d"
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
