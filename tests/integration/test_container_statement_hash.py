import json
import os
from dataclasses import replace

import factories
import pytest

from cairn import bundle, challenge, container, lean, log

lg = log.get("test")
MATHLIB_MODULE = "Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point"
FORMAL = "theorem challenge_curve {R : Type} [CommRing R] (W : WeierstrassCurve R) : W.Δ = W.Δ := by\n  sorry\n"


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
