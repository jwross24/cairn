import importlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import skill_contract

from cairn import substrate

ROOT = Path(__file__).resolve().parents[2]
multi_axis = importlib.import_module("skills.multi_axis")


def _certify(subject, ctx):
    return multi_axis.certify(
        ctx.sub,
        subject.inputs.get("fault", ""),
        subject.inputs.get("fault_axis", "implementation"),
        subject.inputs.get("extra_key", "passed"),
    )


def _subject(fault="", axis="implementation", extra_key="passed"):
    shared = {"seed": 1, "fault": fault, "fault_axis": axis, "extra_key": extra_key}
    return skill_contract.SkillSubject(
        name="multi_axis",
        module="skills.multi_axis",
        corpus_path=ROOT / "tests" / "fixtures" / "skills" / "multi_axis.py",
        floor_golden="",
        inputs={"bits": 20, **shared},
        out_of_range_inputs={"bits": 60, **shared},
        conforming=True,
        certify=_certify,
        transcript=lambda subject, ctx: b"",
        cross_check_inputs={
            "algorithm": {"inside": {"bits": 20, **shared}, "outside": {"bits": 30, **shared}},
            "implementation": {"inside": {"bits": 40, **shared}, "outside": {"bits": 20, **shared}},
        },
    )


@pytest.fixture
def axis_context(tmp_path):
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        yield skill_contract.Context(
            sub=sub,
            config=None,
            bundle_hash="a" * 64,
            scratch_root=tmp_path / "runs",
            fixtures_path=str(ROOT / "tests" / "fixtures"),
            repo_root=ROOT,
            workspace=tmp_path / "workspace",
        )


def test_two_axes_pass_with_their_own_ranges_and_seams(axis_context, popen_spy):
    subject = _subject()
    verdict = skill_contract.check_axis_declaration(subject, axis_context)
    assert verdict.status == skill_contract.PASS, verdict.reason
    assert "axis algorithm, range {'bits': [10, 20]}, 'agree' moves to 'disagree'" in verdict.reason
    assert "axis implementation, range {'bits': [30, 40]}, 'agree' moves to 'disagree'" in verdict.reason
    assert len(popen_spy) == 6
    certificate = skill_contract.certified(subject, axis_context)
    stored = axis_context.sub.get_certificate(certificate["identity_bundle_hash"])
    assert stored is not None
    assert json.loads(stored["selftest_summary"])["cross_check"] == [
        {"axis": declaration["axis"], "independent_range": declaration["independent_range"]}
        for declaration in multi_axis.CROSS_CHECKS
    ]


def test_second_inert_seam_fails_and_names_implementation(axis_context):
    verdict = skill_contract.check_axis_declaration(_subject("inert"), axis_context)
    assert verdict.status == skill_contract.FAIL
    assert "axis implementation:" in verdict.reason
    assert "whether or not skills.multi_axis.implementation_sum is planted" in verdict.reason


@pytest.mark.parametrize("axis", skill_contract.AXES)
@pytest.mark.parametrize(
    "fault", ["inert", "outside", "output_missing", "output_range", "ledger_missing", "ledger_range"]
)
def test_each_axis_refuses_its_failed_arm(axis_context, axis, fault):
    verdict = skill_contract.check_axis_declaration(_subject(fault, axis), axis_context)
    assert verdict.status == skill_contract.FAIL
    assert axis in verdict.reason


@pytest.mark.parametrize("axis", skill_contract.AXES)
@pytest.mark.parametrize("extra_key", ["passed", "result", "evidence", "status"])
def test_each_ledger_record_refuses_extra_keys(axis_context, axis, extra_key):
    verdict = skill_contract.check_axis_declaration(_subject("ledger_extra", axis, extra_key), axis_context)
    assert verdict.status == skill_contract.FAIL
    assert f"axis {axis}: ledger cross_check has keys" in verdict.reason
    assert extra_key in verdict.reason


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("axis", "vibes", "not one of"),
        ("independent_range", {}, "not an interval record"),
        ("independent_range", {"absent": [0, 1]}, "not an input field"),
        ("independent_range", {"bits": [40, 10]}, "not an interval"),
        ("independent_range", {"bits": ["low", 10]}, "not an interval"),
        ("seam", None, "declares no seam"),
    ],
)
def test_each_declaration_arm_refuses(axis_context, monkeypatch, index, field, value, reason):
    declarations = deepcopy(multi_axis.CROSS_CHECKS)
    declarations[index][field] = value
    monkeypatch.setattr(multi_axis, "CROSS_CHECKS", declarations)
    verdict = skill_contract.check_axis_declaration(_subject(), axis_context)
    assert verdict.status == skill_contract.FAIL
    assert reason in verdict.reason
    assert str(declarations[index]["axis"]) in verdict.reason


@pytest.mark.parametrize("axis", skill_contract.AXES)
@pytest.mark.parametrize("kind", ["inside", "outside"])
def test_probe_must_be_complete_and_on_the_declared_side(axis_context, axis, kind):
    subject = _subject()
    probes = deepcopy(subject.cross_check_inputs)
    probes[axis][kind] = dict(probes[axis]["outside" if kind == "inside" else "inside"])
    verdict = skill_contract.check_axis_declaration(replace(subject, cross_check_inputs=probes), axis_context)
    assert verdict.status == skill_contract.FAIL
    assert f"axis {axis}: {kind} probe is on the wrong side" in verdict.reason


@pytest.mark.parametrize("axis", skill_contract.AXES)
def test_missing_axis_probe_refuses(axis_context, axis):
    subject = _subject()
    probes = {name: value for name, value in subject.cross_check_inputs.items() if name != axis}
    verdict = skill_contract.check_axis_declaration(replace(subject, cross_check_inputs=probes), axis_context)
    assert verdict.status == skill_contract.FAIL
    assert f"axis {axis}: no complete inside/outside probe pair" in verdict.reason


@pytest.mark.parametrize("axis", skill_contract.AXES)
def test_incomplete_axis_probe_refuses(axis_context, axis):
    subject = _subject()
    probes = deepcopy(subject.cross_check_inputs)
    probes[axis]["inside"].pop("seed")
    verdict = skill_contract.check_axis_declaration(replace(subject, cross_check_inputs=probes), axis_context)
    assert verdict.status == skill_contract.FAIL
    assert f"axis {axis}: inside probe omits input fields" in verdict.reason


def test_outside_probe_without_a_declared_cost_refuses(axis_context):
    subject = _subject()
    probes = deepcopy(subject.cross_check_inputs)
    probes["implementation"]["outside"]["bits"] = 50
    verdict = skill_contract.check_axis_declaration(replace(subject, cross_check_inputs=probes), axis_context)
    assert verdict.status == skill_contract.FAIL
    assert "axis implementation: outside probe size 50 has no declared cost" in verdict.reason


@pytest.mark.parametrize("records", [None, [], {}, [None]])
def test_malformed_plural_declarations_refuse(axis_context, monkeypatch, records):
    monkeypatch.setattr(multi_axis, "CROSS_CHECKS", records)
    verdict = skill_contract.check_axis_declaration(_subject(), axis_context)
    assert verdict.status == skill_contract.FAIL


def test_repeated_axis_declaration_refuses(axis_context, monkeypatch):
    declarations = deepcopy(multi_axis.CROSS_CHECKS)
    declarations[1]["axis"] = declarations[0]["axis"]
    monkeypatch.setattr(multi_axis, "CROSS_CHECKS", declarations)
    verdict = skill_contract.check_axis_declaration(_subject(), axis_context)
    assert verdict.status == skill_contract.FAIL
    assert "axis algorithm: repeated declaration" in verdict.reason


def test_tuple_intervals_are_valid(axis_context, monkeypatch):
    declarations = deepcopy(multi_axis.CROSS_CHECKS)
    for declaration in declarations:
        declaration["independent_range"]["bits"] = tuple(declaration["independent_range"]["bits"])
    monkeypatch.setattr(multi_axis, "CROSS_CHECKS", declarations)
    verdict = skill_contract.check_axis_declaration(_subject(), axis_context)
    assert verdict.status == skill_contract.PASS, verdict.reason
