import io
import json
from pathlib import Path

import pytest

from cairn import canon, keys, pari
from cairn.skills import toy_curve
from cairn.skills.toy_curve import InputError, ToyCurveOutput

CROSS_AGREE = {"axis": "algorithm", "independent_range": {"bits": [0, 50]}, "result": "agree"}
CROSS_DISAGREE = {"axis": "algorithm", "independent_range": {"bits": [0, 50]}, "result": "disagree"}
FIXED_OK = ToyCurveOutput(
    30, 1, 922854029, 736418726, 866050641, 922807351, (432221713, 837442395), 48, CROSS_AGREE, "OK"
)
FIXED_DISAGREE = ToyCurveOutput(
    40,
    1,
    945002525923,
    52505748614,
    460290291066,
    945003441719,
    (177882803709, 442326880217),
    40,
    CROSS_DISAGREE,
    "DISAGREE",
    (
        {
            "call": "ellcard",
            "curve": [52505748614, 460290291066, 945002525923],
            "result": 945003441719,
            "digest": "aa" * 32,
        },
        {
            "call": "ellsea",
            "curve": [52505748614, 460290291066, 945002525923],
            "result": 945003441721,
            "digest": "bb" * 32,
        },
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


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("", "not JSON"),
        ("[]", "not a JSON object"),
        ('{"bits": 30}', "does not match"),
        (FIXED_OK.to_json().replace('"status":"OK"', '"status":"OK","x":1'), "undeclared"),
    ],
)
def test_from_json_refuses_malformed_output(text, reason):
    with pytest.raises(InputError, match=reason):
        ToyCurveOutput.from_json(text)


@pytest.mark.parametrize(
    ("text", "match"),
    MALFORMED,
    ids=[
        "empty",
        "non-json",
        "array",
        "missing-seed",
        "bits-str",
        "bits-bool",
        "extra-key",
        "bits-zero",
        "seed-zero",
        "bits-float",
    ],
)
def test_malformed_stdin_is_refused_with_a_typed_error_before_any_pari_call(text, match, pari_spy):
    with pytest.raises(InputError, match=match):
        toy_curve.parse_inputs(text)
    out, err = io.StringIO(), io.StringIO()
    assert toy_curve.main(stdin=io.StringIO(text), stdout=out, stderr=err) == 1
    assert out.getvalue() == "" and err.getvalue().startswith("error: ")
    assert pari_spy == []


def test_well_formed_stdin_parses_without_touching_pari(pari_spy):
    assert toy_curve.parse_inputs('{"seed": 1, "bits": 30}') == (30, 1)
    assert toy_curve.parse_inputs('{"bits": 4000, "seed": 2**31}'.replace("2**31", str(2**31))) == (4000, 2**31)
    assert pari_spy == []


@pytest.mark.parametrize(
    ("bits", "seed", "match"),
    [
        ("40", 1, "bits must be an int, got str"),
        (40, None, "seed must be an int, got NoneType"),
        (0, 1, "bits must be >= 1"),
        (40, 0, "seed must be >= 1"),
        (True, 1, "bits must be an int, got bool"),
    ],
    ids=["bits-str", "seed-none", "bits-zero", "seed-zero", "bits-bool"],
)
def test_run_validates_its_arguments_before_any_pari_call(bits, seed, match, pari_spy):
    with pytest.raises(InputError, match=match):
        toy_curve.run(bits, seed)
    assert pari_spy == []


def _revision_tree(tmp_path):
    for rel in toy_curve.IDENTITY_SOURCES:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        source = toy_curve.REPO_ROOT / rel
        target.write_bytes(source.read_bytes() if source.is_file() else b'{"cases": []}\n')
    return tmp_path


@pytest.mark.parametrize("rel", toy_curve.IDENTITY_SOURCES, ids=lambda r: Path(r).name)
def test_implementation_revision_changes_when_one_byte_of_a_source_changes(tmp_path, rel, pari_spy):
    root = _revision_tree(tmp_path)
    base = toy_curve.implementation_revision(root)
    assert toy_curve.implementation_revision(root) == base and len(base) == 64
    path = root / rel
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))
    assert toy_curve.implementation_revision(root) != base
    assert pari_spy == []


def test_implementation_revision_is_sensitive_to_a_source_appearing(tmp_path):
    root = _revision_tree(tmp_path)
    base = toy_curve.implementation_revision(root)
    (root / toy_curve.IDENTITY_SOURCES[-1]).unlink()
    assert toy_curve.implementation_revision(root) != base


def test_implementation_revision_is_order_independent_of_the_source_listing(tmp_path, monkeypatch):
    root = _revision_tree(tmp_path)
    base = toy_curve.implementation_revision(root)
    monkeypatch.setattr(toy_curve, "IDENTITY_SOURCES", tuple(reversed(toy_curve.IDENTITY_SOURCES)))
    assert toy_curve.implementation_revision(root) == base
