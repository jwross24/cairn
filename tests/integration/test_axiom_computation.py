import copy
import json
import shutil

import pytest

from cairn import bundle, lean

SOURCES = {
    "Clean": "theorem target : True := True.intro\n",
    "Sorry": "theorem target : True := by sorry\n",
    "NativeDecide": "import Lean\ntheorem target : 2 + 2 = 4 := by decide +native\n",
    "BvDecide": "import Std.Tactic.BVDecide\ntheorem target (x y : BitVec 8) : x * y = y * x := by bv_decide\n",
    "BvSimplified": "import Std.Tactic.BVDecide\ntheorem target (x : BitVec 8) : x + 0 = x := by bv_decide\n",
    "CustomAxiom": "axiom planted : False\ntheorem target : False := planted\n",
    "UnusedSorry": "theorem unusedAdmission : False := by sorry\ntheorem target : True := True.intro\n",
}


def project_at(root, pins):
    root.mkdir()
    (root / "lean-toolchain").write_text(pins["toolchain"] + "\n")
    (root / "lakefile.toml").write_text(
        'name = "axiom_probe"\n' + "".join(f'\n[[lean_lib]]\nname = "{name}"\n' for name in SOURCES)
    )
    for name, source in SOURCES.items():
        (root / f"{name}.lean").write_text(source)


@pytest.mark.timeout(600)
def test_real_axiom_matrix(pinned_bundle, tmp_path, assert_golden):
    gate = bundle.GateBundle.open(*pinned_bundle())
    project = tmp_path / "project"
    project_at(project, gate.lean)
    records = {}
    for module in SOURCES:
        record = lean.check_axioms(gate, module, ["target"], project_dir=project, work_dir=tmp_path / module)
        records[module] = record
        print(json.dumps({"fixture": module, **record}, sort_keys=True))
        assert record["passed"] is (module in {"Clean", "BvSimplified", "UnusedSorry"})
    assert records["Clean"]["theorems"] == {"target": []}
    assert records["Sorry"]["offending_axioms"] == ["sorryAx"]
    assert records["CustomAxiom"]["offending_axioms"] == ["planted"]
    assert any("._native.decide.ax_" in n for n in records["NativeDecide"]["offending_axioms"])
    assert any("._native.bv_decide.ax_" in n for n in records["BvDecide"]["offending_axioms"])
    assert records["UnusedSorry"]["unused_admissions"] == ["unusedAdmission"]
    assert_golden("axiom_computation", json.dumps(records, sort_keys=True, indent=2) + "\n")
    replay = lean.require_success(lean.run_argv(lean.command(gate.lean, "replay", module="Sorry"), cwd=project))
    assert "replaying Sorry" in replay.stdout
    print(json.dumps(replay.__dict__, sort_keys=True))


@pytest.mark.parametrize(("names", "reason"), [([], "empty-theorem-names"), (["missing"], "missing-theorem")])
def test_empty_or_missing_targets_refuse(pinned_bundle, tmp_path, names, reason):
    gate = bundle.GateBundle.open(*pinned_bundle())
    project = tmp_path / "project"
    project_at(project, gate.lean)
    with pytest.raises(lean.LeanRejected, match=reason) as caught:
        lean.check_axioms(gate, "Clean", names, project_dir=project, work_dir=tmp_path / "tool")
    print(str(caught.value))


@pytest.mark.parametrize("field", ["permitted_axioms", "checker", "external_kernels"])
def test_checker_configuration_mismatch_precedes_compilation(pinned_bundle, tmp_path, popen_spy, field):
    gate = bundle.GateBundle.open(*pinned_bundle())
    config = {key: copy.deepcopy(gate.lean[key]) for key in ("permitted_axioms", "checker", "external_kernels")}
    config[field] = ["untrusted"]
    with pytest.raises(lean.LeanRejected, match="checker-config-mismatch") as caught:
        lean.check_axioms(
            gate, "Clean", ["target"], project_dir=tmp_path, work_dir=tmp_path / "tool", checker_config=config
        )
    assert popen_spy == []
    assert not (tmp_path / "tool").exists()
    print(json.dumps({"field": field, "reason": str(caught.value), "spawned": popen_spy}))


def test_pin_mismatch_precedes_lake(pinned_bundle, tmp_path, popen_spy, json_test_log):
    pins = {**lean.source_pins(), "lean_commit": "0" * 40}
    source = tmp_path / "bundle-source"
    shutil.copytree(bundle.REPO_ROOT / "bundle", source)
    (source / "lean.json").write_text(json.dumps(pins))
    gate = bundle.GateBundle.open(*pinned_bundle(src=source))
    with pytest.raises(lean.LeanPinMismatch) as caught:
        lean.check_axioms(gate, "Clean", ["target"], project_dir=tmp_path, work_dir=tmp_path / "tool")
    assert not any(argv[0] == str(lean.tool_path("lake")) for argv in popen_spy)
    assert not (tmp_path / "tool").exists()
    events = [json.loads(line) for line in json_test_log.read_text().splitlines()]
    assert any(event["event"] == "pin_mismatch" for event in events)
    print(json.dumps({"reason": str(caught.value), "spawned": popen_spy, "events": events}, sort_keys=True))


def test_axiom_source_is_in_the_bundle(pinned_bundle):
    gate = bundle.GateBundle.open(*pinned_bundle())
    assert gate.raw(lean.AXIOM_KIND) == lean.AXIOM_PATH.read_bytes()
    objects = bundle.source_objects(bundle.REPO_ROOT / "bundle")
    before = bundle.bundle_hash(bundle.rows_for(objects))
    objects[lean.AXIOM_KIND] += b"\n"
    assert bundle.bundle_hash(bundle.rows_for(objects)) != before


def test_human_axiom_output_refuses():
    result = lean.Run((), None, 0, "'target' depends on axioms: [sorryAx]\n", "", 0)
    with pytest.raises(lean.LeanRejected, match="non-canonical-json") as caught:
        lean.axiom_result(result, ["target"], lean.source_pins()["permitted_axioms"])
    print(str(caught.value))


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ({}, "invalid-axiom-output"),
        ({"theorems": {}, "unused_admissions": []}, "axiom-theorem-names-mismatch"),
        ({"theorems": {"target": "sorryAx"}, "unused_admissions": []}, "invalid-axiom-names"),
        ({"theorems": {"target": ["sorryAx", "sorryAx"]}, "unused_admissions": []}, "non-canonical-axiom-names"),
        ({"theorems": {"target": ["sorryAx", "propext"]}, "unused_admissions": []}, "non-canonical-axiom-names"),
        ({"theorems": {"target": []}, "unused_admissions": [None]}, "invalid-axiom-names"),
    ],
)
def test_malformed_axiom_contract_refuses(value, reason):
    result = lean.Run((), None, 0, json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", "", 0)
    with pytest.raises(lean.LeanRejected, match=reason):
        lean.axiom_result(result, ["target"], lean.source_pins()["permitted_axioms"])
