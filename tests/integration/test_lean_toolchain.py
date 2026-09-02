import pytest

from cairn import bundle, lean, log

HELLO_MODULE = "Hello"
HELLO_SOURCE = "theorem hello (n : Nat) : n + 0 = n := Nat.add_zero n\n"
LAKEFILE = 'name = "hello"\n\n[[lean_lib]]\nname = "Hello"\n'
PINNED_VERSION = "4.34.0-rc1"
WRONG_COMMIT = "0" * 40


def _log(event, result, **fields):
    log.get("grounding.lean").info(
        event,
        command=" ".join(result.argv),
        cwd=result.cwd,
        rc=result.rc,
        stdout=result.stdout,
        stderr=result.stderr,
        wall_ms=result.wall_ms,
        **fields,
    )


def _hello_project(root, pins):
    root.mkdir()
    (root / "lean-toolchain").write_text(pins["toolchain"] + "\n")
    (root / "lakefile.toml").write_text(LAKEFILE)
    (root / f"{HELLO_MODULE}.lean").write_text(HELLO_SOURCE)
    return root


def test_the_pinned_toolchain_resolves_and_reports_the_pinned_commit():
    pins = lean.source_pins()
    observed = lean.assert_pinned(pins)
    log.get("grounding.lean").info(
        "lean_version",
        command=" ".join(lean.argv(pins, "lean", "--version")),
        elan_home=str(lean.elan_home()),
        observed=observed,
    )
    assert observed["version"] == PINNED_VERSION == lean.toolchain_version(pins["toolchain"])
    assert observed["commit"] == pins["lean_commit"]
    assert observed["build"] == "Release"


def test_a_pin_naming_another_commit_is_refused_before_any_compile():
    pins = {**lean.source_pins(), "lean_commit": WRONG_COMMIT}
    with pytest.raises(lean.LeanPinMismatch) as caught:
        lean.assert_pinned(pins)
    assert caught.value.pinned == {"version": PINNED_VERSION, "commit": WRONG_COMMIT}
    assert caught.value.observed == {"version": PINNED_VERSION, "commit": lean.source_pins()["lean_commit"]}


def test_an_absent_toolchain_is_refused_before_the_proxy_can_download_it(monkeypatch, tmp_path):
    real_elan = lean.tool_path("elan")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "elan").symlink_to(real_elan)
    monkeypatch.setenv("ELAN_HOME", str(tmp_path))
    with pytest.raises(lean.LeanMissing) as caught:
        lean.assert_pinned(lean.source_pins())
    assert "is not installed under" in str(caught.value)
    assert not (tmp_path / "toolchains").exists()


def test_hello_theorem_builds_and_leanchecker_replays_it_from_empty(tmp_path):
    pins = lean.source_pins()
    project = _hello_project(tmp_path / "hello", pins)
    build = lean.run_argv(lean.command(pins, "build", module=HELLO_MODULE), cwd=project)
    _log("lake_build", build)
    assert build.rc == 0, build.stderr
    assert (project / ".lake" / "build" / "lib" / "lean" / f"{HELLO_MODULE}.olean").is_file()
    replay = lean.run_argv(lean.command(pins, "replay", module=HELLO_MODULE), cwd=project)
    _log("leanchecker", replay)
    fresh = lean.run_argv(lean.command(pins, "replay_fresh", module=HELLO_MODULE), cwd=project)
    _log("leanchecker_fresh", fresh)
    assert replay.rc == 0, replay.stderr
    assert fresh.rc == 0, fresh.stderr
    assert f"replaying {HELLO_MODULE}" in replay.stdout
    assert f"replaying {HELLO_MODULE}" in fresh.stdout


def test_the_gate_bundle_carries_the_lake_manifest_and_the_pins(pinned_bundle):
    gate = bundle.GateBundle.open(*pinned_bundle())
    assert gate.lake_manifest == lean.manifest_object()
    assert gate.lean == lean.source_pins()
    assert lean.manifest_rev(gate.lake_manifest) == gate.lean["mathlib_rev"]
    assert gate.lean["toolchain"] == lean.TOOLCHAIN_FILE.read_text().strip()
