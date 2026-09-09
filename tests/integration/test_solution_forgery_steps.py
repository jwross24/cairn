import os
from pathlib import Path

import pytest

from cairn import bundle, lean, solutionchecks, solutionplan

GROUNDING = lean.REPO_ROOT / "research" / "grounding" / "solution-forgery-2026-09-08"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "solution_forgery"
MODULE = "Forge"
LAKEFILE = f'name = "forge"\n\n[[lean_lib]]\nname = "{MODULE}"\n'
FORGERIES = ("forge_unchecked_theorem.lean", "forge_unchecked_axiom.lean")
TIMEOUT_S = 600.0
# --fresh replays every import, which for a module importing Lean is 302 s against a 180 s per-test
# cap (research/grounding/solution-forgery-2026-09-08/probe.log); both variants refuse the same
# forgery with the same kernel exception.
VARIANT = solutionchecks.REPLAY_TRUSTING_IMPORTS


@pytest.fixture
def gate(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


@pytest.fixture(scope="module")
def module_gate(tmp_path_factory):
    directory = tmp_path_factory.mktemp("deploy")
    bundle_path, pin_path = directory / "gate-bundle.sqlite", directory / "gate-bundle.pin"
    bundle.build(lean.REPO_ROOT / "bundle", bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    yield bundle.GateBundle.open(bundle_path, pin_path)
    os.chflags(pin_path, 0)
    pin_path.chmod(0o644)


@pytest.fixture(scope="module")
def shared_axiom_tool(tmp_path_factory, module_gate):
    return lean.axiom_tool(module_gate, tmp_path_factory.mktemp("axiomtool") / "tool", timeout_s=TIMEOUT_S)


@pytest.fixture(scope="module")
def planted(tmp_path_factory):
    built = {}

    def make(fixture):
        if fixture not in built:
            built[fixture] = _planted(tmp_path_factory.mktemp(fixture.removesuffix(".lean")) / "proj", fixture)
        return built[fixture]

    return make


def _planted(root, fixture):
    root.mkdir(parents=True, exist_ok=True)
    pins = lean.source_pins()
    (root / "lean-toolchain").write_text(pins["toolchain"] + "\n")
    (root / "lakefile.toml").write_text(LAKEFILE)
    (root / f"{MODULE}.lean").write_bytes((FIXTURES / fixture).read_bytes())
    lean.require_success(lean.run_argv(lean.command(pins, "build", module=MODULE), cwd=root, timeout_s=TIMEOUT_S))
    return root, pins


def test_the_axiom_step_needs_exactly_one_of_a_work_dir_and_a_prebuilt_tool(module_gate, planted):
    root, _ = planted("forge_unchecked_axiom.lean")
    for kwargs in ({}, {"work_dir": root / "unused", "tool": root / "unused"}):
        with pytest.raises(lean.LeanRejected) as caught:
            lean.check_axioms(module_gate, MODULE, ["forged_false"], project_dir=root, **kwargs)
        assert str(caught.value) == "axiom-tool-needs-a-work-dir-or-a-prebuilt-tool"


def test_a_prebuilt_tool_that_is_not_on_disk_is_refused(module_gate, planted):
    root, _ = planted("forge_unchecked_axiom.lean")
    with pytest.raises(lean.LeanRejected) as caught:
        lean.check_axioms(module_gate, MODULE, ["forged_false"], project_dir=root, tool=root / "absent")
    assert str(caught.value).startswith("axiom-tool-absent:")


@pytest.mark.parametrize("fixture", FORGERIES)
def test_each_forgery_fixture_is_the_bytes_the_grounding_probe_measured(fixture):
    assert (FIXTURES / fixture).read_bytes() == (GROUNDING / fixture).read_bytes()


@pytest.mark.parametrize("fixture", FORGERIES)
def test_each_forgery_builds_so_the_build_step_alone_admits_it(planted, fixture):
    root, _ = planted(fixture)
    assert (root / ".lake" / "build" / "lib" / "lean" / f"{MODULE}.olean").is_file()


def test_the_kernel_replay_refuses_the_forged_unchecked_theorem(planted):
    root, pins = planted("forge_unchecked_theorem.lean")
    observed, reasons, _ = solutionchecks.observe_kernel_replay(
        pins, MODULE, project_dir=root, timeout_s=TIMEOUT_S, variant=VARIANT
    )
    assert observed == solutionplan.OBSERVED_REFUSED
    assert reasons[0] == solutionchecks.KERNEL_REJECTED
    assert reasons[1] != "rc:0"


def test_the_axiom_step_passes_the_forged_unchecked_theorem_the_replay_catches(tmp_path, gate, planted):
    root, _ = planted("forge_unchecked_theorem.lean")
    observed, reasons, _ = solutionchecks.observe_axioms(
        gate,
        MODULE,
        ["forged"],
        project_dir=root,
        work_dir=tmp_path / "axiomtool",
        timeout_s=TIMEOUT_S,
    )
    assert (observed, reasons) == (solutionplan.EXPECT_NO_OFFENDING_AXIOM, ())


def test_the_axiom_step_refuses_the_forged_unchecked_axiom(module_gate, planted, shared_axiom_tool):
    root, _ = planted("forge_unchecked_axiom.lean")
    observed, reasons, _ = solutionchecks.observe_axioms(
        module_gate,
        MODULE,
        ["forged_false"],
        project_dir=root,
        tool=shared_axiom_tool,
        timeout_s=TIMEOUT_S,
    )
    assert observed == solutionplan.OBSERVED_REFUSED
    assert f"{solutionchecks.OFFENDING_AXIOM_PREFIX}forged" in reasons


def test_the_kernel_replay_passes_the_forged_unchecked_axiom_the_axiom_step_catches(planted):
    root, pins = planted("forge_unchecked_axiom.lean")
    observed, reasons, _ = solutionchecks.observe_kernel_replay(
        pins, MODULE, project_dir=root, timeout_s=TIMEOUT_S, variant=VARIANT
    )
    assert (observed, reasons) == (solutionplan.EXPECT_REPLAYED, ())
