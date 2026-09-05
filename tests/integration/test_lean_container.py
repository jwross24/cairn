import pytest

from cairn import bundle, container, lean, log

lg = log.get("test")
COMPARATOR_PROJECTS = "/home/cairn/comparator/tests/projects"
COMPARATOR_CMD = "cd {projects}/{project} && lake env $COMPARATOR_BIN config.json"
OKAY = "Your solution is okay!"
CHATTR_SCRIPT = (
    "set -x; f=/work/append_only.log; echo first > $f; chattr +a $f; lsattr $f; "
    "echo second >> $f; echo trunc > $f; rm -f $f; cat $f; exit 0"
)
CHATTR_AS_USER = "set -x; f=/work/shared.log; ls -l $f; lsattr $f; echo appended-by-user >> $f; echo truncated-by-user > $f; rm -f $f; cat $f; exit 0"


def _gold_arm_or_skip():
    ctx = container.context()
    try:
        info = container.daemon_info(ctx)
    except container.DaemonUnavailable as exc:
        pytest.skip(f"gold arm unavailable on this host: {exc}")
    lg.info("daemon", context=ctx, info=info)
    return ctx


def _bundle(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


def _log(step, result, **fields):
    lg.info(
        step, rc=result.rc, wall_ms=result.wall_ms, stdout=result.stdout[-1500:], stderr=result.stderr[-1500:], **fields
    )
    return result


def test_the_containerfile_pins_agree_with_container_json():
    text = container.containerfile_text()
    spec = container.spec()
    assert container.containerfile_args(text) == container.pinned_args(spec)
    assert container.containerfile_base(text) == spec["base_image"]


def test_the_container_pins_agree_with_the_lean_pins():
    spec = container.spec()
    pins = lean.source_pins()
    assert spec["toolchain"]["name"] == pins["toolchain"]
    assert spec["toolchain"]["lean_commit"] == pins["lean_commit"]
    assert spec["mathlib"]["rev"] == pins["mathlib_rev"]
    for name in ("elan", "toolchain", "landrun"):
        assert len(bytes.fromhex(spec[name]["sha256"])) == 32, name
    assert len(bytes.fromhex(spec["comparator"]["rev"])) == 20


def test_the_identity_is_a_function_of_the_spec_and_the_containerfile_only(pinned_bundle):
    gate_bundle = _bundle(pinned_bundle)
    spec_bytes = gate_bundle.raw(container.SPEC_KIND)
    file_bytes = gate_bundle.raw(container.FILE_KIND)
    same = container.identity(spec_bytes, file_bytes)
    assert same == gate_bundle.container_identity
    assert container.identity(spec_bytes, file_bytes + b"\n") != same
    assert container.identity(spec_bytes[:-1] + bytes([spec_bytes[-1] ^ 1]), file_bytes) != same
    assert container.image_tag(same) == f"cairn-gate:{same[:16]}"


@pytest.mark.parametrize("arm", [None, "", "linux", "gold-linux-container ", "macos"])
def test_an_arm_outside_the_two_is_refused(arm):
    with pytest.raises(container.ArmUnknown):
        container.assert_arm(arm)


@pytest.mark.timeout(3600)
def test_the_gold_image_builds_and_the_checker_runs_under_landrun_inside_it(pinned_bundle):
    ctx = _gold_arm_or_skip()
    identity = _bundle(pinned_bundle).container_identity
    image = container.build(ctx, identity)
    again = container.build(ctx, identity)
    lg.info("rebuild", identity=identity, first_image_id=image.image_id, second_image_id=again.image_id)
    assert again.identity == image.identity == identity

    version = _log(
        "lean_version_in_container",
        container.run(ctx, image, ["lean", f"+{lean.source_pins()['toolchain']}", "--version"]),
    )
    assert version.rc == 0
    assert f"commit {lean.source_pins()['lean_commit']}" in version.stdout

    landrun = _log("landrun_version", container.run(ctx, image, ["landrun", "--version"]))
    assert landrun.rc == 0
    assert container.spec()["landrun"]["version"] in landrun.stdout + landrun.stderr

    denied = _log(
        "landrun_ro_root_denies_a_write",
        container.run(
            ctx, image, ["landrun", "--best-effort", "--ro", "/", "--", "/bin/sh", "-c", "echo probe > /work/probe"]
        ),
    )
    assert denied.rc != 0
    allowed = _log(
        "landrun_rw_work_allows_the_write",
        container.run(
            ctx,
            image,
            [
                "landrun",
                "--best-effort",
                "--ro",
                "/",
                "--rw",
                "/work",
                "--",
                "/bin/sh",
                "-c",
                "echo probe > /work/probe && cat /work/probe",
            ],
        ),
    )
    assert (allowed.rc, allowed.stdout.strip()) == (0, "probe")

    okay = _log(
        "comparator_simple_match_under_landrun",
        container.run(
            ctx, image, ["/bin/sh", "-c", COMPARATOR_CMD.format(projects=COMPARATOR_PROJECTS, project="simple_match")]
        ),
        project="simple_match",
    )
    assert okay.rc == 0
    assert OKAY in okay.stdout
    mismatch = _log(
        "comparator_simple_mismatch_under_landrun",
        container.run(
            ctx,
            image,
            ["/bin/sh", "-c", COMPARATOR_CMD.format(projects=COMPARATOR_PROJECTS, project="simple_mismatch")],
        ),
        project="simple_mismatch",
    )
    assert mismatch.rc != 0
    assert "don't match" in mismatch.stdout + mismatch.stderr


@pytest.mark.timeout(3600)
def test_the_chattr_probe_inside_the_container_is_recorded(pinned_bundle):
    ctx = _gold_arm_or_skip()
    image = container.build(ctx, _bundle(pinned_bundle).container_identity)
    as_user = _log("chattr_default_caps_as_user", container.run(ctx, image, ["/bin/sh", "-c", CHATTR_SCRIPT]))
    as_root = _log(
        "chattr_default_caps_as_root", container.run(ctx, image, ["/bin/sh", "-c", CHATTR_SCRIPT], user="root")
    )
    with_cap = _log(
        "chattr_with_linux_immutable_as_root",
        container.run(ctx, image, ["/bin/sh", "-c", CHATTR_SCRIPT], user="root", cap_add=("LINUX_IMMUTABLE",)),
    )
    assert "Operation not permitted" in as_user.stderr
    assert "Operation not permitted" in as_root.stderr
    assert "-----a" in with_cap.stdout
    assert "second" in with_cap.stdout
