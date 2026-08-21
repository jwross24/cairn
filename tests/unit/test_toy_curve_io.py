import io
import json
import shutil
from pathlib import Path

import pytest

from cairn import canon, env, keys, pari
from cairn.skills import toy_curve
from cairn.skills.toy_curve import InputError, ToyCurveOutput

CROSS_AGREE = {"axis": "algorithm", "independent_range": {"bits": [0, 50]}, "result": "agree"}
CROSS_DISAGREE = {"axis": "algorithm", "independent_range": {"bits": [0, 50]}, "result": "disagree"}
FIXED_OK = ToyCurveOutput(30, 1, 922854029, 736418726, 866050641, 922807351, (432221713, 837442395), 48, CROSS_AGREE, "OK")
FIXED_DISAGREE = ToyCurveOutput(
    40, 1, 945002525923, 52505748614, 460290291066, 945003441719, (177882803709, 442326880217), 40, CROSS_DISAGREE, "DISAGREE",
    (
        {"call": "ellcard", "curve": [52505748614, 460290291066, 945002525923], "result": 945003441719, "digest": "aa" * 32},
        {"call": "ellsea", "curve": [52505748614, 460290291066, 945002525923], "result": 945003441721, "digest": "bb" * 32},
    ),
)
MALFORMED = [
    ("", "empty stdin"),
    ("{", "not JSON"),
    ("[1, 2]", "not a JSON object"),
    ('{"bits": 30}', r"missing field\(s\) \['seed'\]"),
    ('{"bits": "30", "seed": 1}', "bits: expected int, got str"),
    ('{"bits": true, "seed": 1}', "bits: expected int, got bool"),
    ('{"bits": 30, "seed": 1, "extra": 1}', r"undeclared field\(s\) \['extra'\]"),
    ('{"bits": 0, "seed": 1}', "bits must be >= 1"),
    ('{"bits": 30, "seed": 0}', "seed must be >= 1"),
    ('{"bits": 30.0, "seed": 1}', "float"),
]


@pytest.fixture
def pari_spy(monkeypatch):
    calls = []
    for name in ("ellcard", "ellsea", "ellorder"):
        real = getattr(pari, name)
        monkeypatch.setattr(pari, name, lambda *a, _n=name, _r=real, **k: (calls.append(_n), _r(*a, **k))[1])
    real_run = toy_curve.run
    monkeypatch.setattr(toy_curve, "run", lambda *a, **k: (calls.append("run"), real_run(*a, **k))[1])
    return calls


@pytest.mark.parametrize("fixed", [FIXED_OK, FIXED_DISAGREE], ids=["ok", "disagree"])
def test_json_contract_round_trips_a_fixed_output(fixed):
    text = fixed.to_json()
    assert text.endswith("\n") and text.count("\n") == 1
    wire = json.loads(text)
    assert isinstance(wire["p"], str) and all(isinstance(c, str) for c in wire["P"])
    assert ToyCurveOutput.from_json(text) == fixed
    assert ToyCurveOutput.from_json(text).to_json() == text
    assert fixed.manifest() == canon.encode(toy_curve.OUTPUT, fixed.to_dict())
    assert fixed.manifest_hash() == keys.node_hash("toy_curve_output", fixed.manifest())
    assert len(fixed.manifest_hash()) == 64


def test_two_fixed_outputs_have_different_manifests():
    assert FIXED_OK.manifest_hash() != FIXED_DISAGREE.manifest_hash()


@pytest.mark.parametrize(("text", "reason"), [("", "not JSON"), ("[]", "not a JSON object"), ('{"bits": 30}', "does not match"), (FIXED_OK.to_json().replace('"status":"OK"', '"status":"OK","x":1'), "undeclared")])
def test_from_json_refuses_malformed_output(text, reason):
    with pytest.raises(InputError, match=reason):
        ToyCurveOutput.from_json(text)


@pytest.mark.parametrize(("text", "match"), MALFORMED, ids=["empty", "non-json", "array", "missing-seed", "bits-str", "bits-bool", "extra-key", "bits-zero", "seed-zero", "bits-float"])
def test_malformed_stdin_is_refused_with_a_typed_error_before_any_pari_call(text, match, pari_spy):
    with pytest.raises(InputError, match=match):
        toy_curve.parse_inputs(text)
    out, err = io.StringIO(), io.StringIO()
    assert toy_curve.main(stdin=io.StringIO(text), stdout=out, stderr=err) == 1
    assert out.getvalue() == "" and err.getvalue().startswith("error: ")
    assert pari_spy == []


def test_well_formed_stdin_parses_and_main_writes_exactly_one_document():
    assert toy_curve.parse_inputs('{"seed": 1, "bits": 30}') == (30, 1)
    out, err = io.StringIO(), io.StringIO()
    assert toy_curve.main(stdin=io.StringIO('{"bits": 30, "seed": 1}'), stdout=out, stderr=err) == 0
    assert out.getvalue().count("\n") == 1
    assert ToyCurveOutput.from_json(out.getvalue()) == toy_curve.run(30, 1)


def test_identity_hash_is_stable_across_two_computations():
    first = toy_curve.skill_identity_hash()
    second = toy_curve.skill_identity_hash()
    bundle = toy_curve.identity_bundle()
    assert first == second == keys.identity_bundle_hash(bundle)
    assert bundle["interface_version"] == "toy_curve/1"
    assert set(bundle["tool_digests"]) == {"gp_binary_sha256", "cypari2", "libpari"}
    assert bundle["tool_digests"]["libpari"] == pari.pari_versions()["libpari"]
    assert bundle["container_digest"] == keys.env_manifest_digest(env.manifest())
    assert bundle["numeric_profile"] is None
    assert len(bundle["implementation_revision"]) == 64
    canon.encode(keys.IDENTITY_BUNDLE, bundle)


def _identity_tree(tmp_path):
    for rel in toy_curve.IDENTITY_SOURCES:
        src = toy_curve.REPO_ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy(src, dst)
        else:
            dst.write_bytes(b'{"cases": []}\n')
    return tmp_path


@pytest.mark.parametrize("rel", toy_curve.IDENTITY_SOURCES, ids=lambda r: Path(r).name)
def test_identity_hash_changes_when_one_byte_of_a_source_file_changes(tmp_path, rel):
    root = _identity_tree(tmp_path)
    base = toy_curve.skill_identity_hash(root=root)
    assert toy_curve.skill_identity_hash(root=root) == base
    path = root / rel
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))
    assert toy_curve.skill_identity_hash(root=root) != base
    assert toy_curve.implementation_revision(root) != toy_curve.implementation_revision(toy_curve.REPO_ROOT) or not (toy_curve.REPO_ROOT / rel).is_file()


def test_identity_revision_is_sensitive_to_a_source_appearing(tmp_path):
    root = _identity_tree(tmp_path)
    base = toy_curve.implementation_revision(root)
    (root / toy_curve.IDENTITY_SOURCES[-1]).unlink()
    assert toy_curve.implementation_revision(root) != base
