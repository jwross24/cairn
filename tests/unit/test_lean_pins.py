import os
import tomllib

import pytest

from cairn import bundle, lean

FAKE_PINS = {
    "toolchain": "leanprover/lean4:v9.9.9",
    "checker": {"replay_fresh": ["lake", "env", "leanchecker", "--fresh", "-v", "{module}"]},
}
NO_DEFAULT_TOOLCHAIN = "error: no default toolchain configured. run `elan default stable` to install & configure.\n"


def _fake_tool(home, name, body):
    (home / "bin").mkdir(exist_ok=True)
    path = home / "bin" / name
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)
    return path


def test_the_bundle_pins_name_the_toolchain_the_lake_project_declares():
    assert lean.TOOLCHAIN_FILE.read_text().strip() == lean.source_pins()["toolchain"]


def test_the_bundle_pins_name_the_mathlib_rev_the_lake_manifest_holds():
    pins = lean.source_pins()
    assert len(pins["mathlib_rev"]) == 40
    assert lean.manifest_rev(lean.manifest_object()) == pins["mathlib_rev"]


def test_the_lakefile_requires_mathlib_at_the_pinned_rev():
    lakefile = tomllib.loads((lean.PROJECT_DIR / "lakefile.toml").read_text())
    revs = [entry["rev"] for entry in lakefile["require"] if entry["name"] == "mathlib"]
    assert revs == [lean.source_pins()["mathlib_rev"]]


def test_the_lean_commit_pin_is_a_full_sha_and_the_toolchain_version_parses():
    pins = lean.source_pins()
    assert len(bytes.fromhex(pins["lean_commit"])) == 20
    assert lean.toolchain_version(pins["toolchain"]) == "4.34.0-rc1"


def test_a_lean_that_exits_zero_without_identifying_a_toolchain_is_reported_missing(monkeypatch):
    monkeypatch.setattr(
        lean,
        "run",
        lambda pins, tool, args, **kw: lean.Run(("lean", "--version"), None, 0, NO_DEFAULT_TOOLCHAIN, "", 1.0),
    )
    with pytest.raises(lean.LeanMissing, match="did not identify a toolchain"):
        lean.version(FAKE_PINS)


def test_a_missing_lake_manifest_refuses_the_bundle_build_with_a_classified_error(monkeypatch, tmp_path):
    monkeypatch.setattr(lean, "MANIFEST_PATH", tmp_path / "absent" / "lake-manifest.json")
    with pytest.raises(bundle.BundleError, match=r"lake manifest .* does not exist"):
        bundle.source_objects(bundle.REPO_ROOT / "bundle")


def test_the_child_sees_the_resolved_elan_home_and_a_hung_tool_is_killed(monkeypatch, tmp_path):
    monkeypatch.delenv("ELAN_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    home = tmp_path / ".elan"
    home.mkdir()
    _fake_tool(home, "lean", 'printf "%s\\n" "${ELAN_HOME:-unset}"')
    _fake_tool(home, "lake", "sleep 30")
    result = lean.run(FAKE_PINS, "lean", ["--version"])
    assert (result.rc, result.stdout.strip()) == (0, str(home))
    assert result.argv[1] == "+leanprover/lean4:v9.9.9"
    assert "ELAN_HOME" not in os.environ
    with pytest.raises(lean.LeanTimeout) as caught:
        lean.run(FAKE_PINS, "lake", ["build"], timeout_s=0.3)
    assert caught.value.argv[0] == str(home / "bin" / "lake")
    assert caught.value.timeout_s == 0.3


def test_every_checker_command_names_a_pinned_tool():
    pins = lean.source_pins()
    assert set(pins["checker"]) >= {"version", "build", "replay", "replay_fresh"}
    for name, template in pins["checker"].items():
        assert template[0] in lean.TOOLS, name


def test_argv_resolves_under_elan_home_with_the_explicit_toolchain(monkeypatch, tmp_path):
    monkeypatch.setenv("ELAN_HOME", str(tmp_path))
    assert lean.elan_home() == tmp_path
    assert lean.argv(FAKE_PINS, "lean", "--version") == [
        str(tmp_path / "bin" / "lean"),
        "+leanprover/lean4:v9.9.9",
        "--version",
    ]
    assert lean.command(FAKE_PINS, "replay_fresh", module="Hello") == [
        str(tmp_path / "bin" / "lake"),
        "+leanprover/lean4:v9.9.9",
        "env",
        "leanchecker",
        "--fresh",
        "-v",
        "Hello",
    ]
    assert lean.resolver_argv("toolchain", "list") == [str(tmp_path / "bin" / "elan"), "toolchain", "list"]
    assert lean.tool_paths() == {str(tmp_path / "bin" / tool) for tool in ("elan", *lean.TOOLS)}


def test_elan_home_defaults_to_the_dot_elan_under_home(monkeypatch, tmp_path):
    monkeypatch.delenv("ELAN_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert lean.elan_home() == tmp_path / ".elan"


@pytest.mark.parametrize("tool", ["leanc", "lake-manifest", "python"])
def test_a_tool_outside_the_pinned_set_is_refused(tool):
    with pytest.raises(ValueError, match="is not a pinned lean tool"):
        lean.tool_path(tool)


def test_the_resolver_takes_no_toolchain_override():
    with pytest.raises(ValueError, match="takes no \\+toolchain"):
        lean.argv(FAKE_PINS, "elan", "toolchain", "list")


def test_a_missing_binary_is_reported_before_any_spawn(monkeypatch, tmp_path):
    monkeypatch.setenv("ELAN_HOME", str(tmp_path))
    with pytest.raises(lean.LeanMissing) as caught:
        lean.run(FAKE_PINS, "lean", ["--version"])
    assert str(caught.value) == str(tmp_path / "bin" / "lean")


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("leanprover/lean4:v4.34.0-rc1\n", ["leanprover/lean4:v4.34.0-rc1"]),
        ("leanprover/lean4:v4.34.0-rc1 (default)\nstable\n", ["leanprover/lean4:v4.34.0-rc1", "stable"]),
        ("no installed toolchains\n", []),
        ("", []),
    ],
    ids=["one", "default-marked-and-channel", "none-installed", "empty"],
)
def test_parse_toolchain_list_keeps_names_and_drops_the_empty_marker(stdout, expected):
    assert lean.parse_toolchain_list(stdout) == expected


def test_manifest_rev_returns_none_for_an_absent_package():
    assert lean.manifest_rev({"packages": [{"name": "batteries", "rev": "abc"}]}) is None
    assert lean.manifest_rev({}) is None
