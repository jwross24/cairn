import dataclasses
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from cairn import ec, witness
from cairn.skills import rho_dp

VECTORS = Path(__file__).resolve().parent.parent / "vectors"
INSTANCES = json.loads((VECTORS / "dlp_instances.json").read_text())["instances"]
CORPUS = json.loads(Path(rho_dp.REPO_ROOT, "src/cairn/skills/rho_dp_corpus.json").read_text())
F5 = {"p": 5, "a": 2, "b": 1, "n": 7, "P": [0, 1], "Q": [3, 3], "x": 3}
GF101 = {"p": 101, "a": 90, "b": 44, "n": 89, "P": [2, 38], "Q": [12, 23], "x": 2}


def _case(case_id):
    case = next(c for c in CORPUS["cases"] if c["id"] == case_id)
    return {name: field["value"] for name, field in case["fields"].items()}


def _args(inst, seed=1, **overrides):
    inst = {**inst, **overrides}
    return (inst["p"].bit_length(), seed, inst["p"], inst["a"], inst["b"], inst["n"], inst["P"], inst["Q"])


def _digest(text):
    return len(text), hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture(scope="module")
def bits20():
    return _case("bits20_seed1")


@pytest.fixture(scope="module")
def out20(bits20):
    return rho_dp.run(*_args(bits20))


def test_two_runs_under_one_seed_are_byte_identical_and_a_second_seed_walks_apart(bits20):
    first = rho_dp.run(*_args(bits20)).to_json()
    second = rho_dp.run(*_args(bits20)).to_json()
    assert _digest(first) == _digest(second)
    other = rho_dp.run(*_args(bits20, seed=2))
    assert other.x == bits20["x"]
    assert other.walk["multipliers"] != json.loads(first)["walk"]["multipliers"]
    assert other.witness != rho_dp.RhoOutput.from_json(first).witness


@pytest.mark.parametrize(("bits", "expected"), [(3, 0), (20, 0), (22, 1), (28, 4), (30, 5), (40, 10), (50, 15)])
def test_theta_bits_keeps_the_stored_distinguished_points_near_a_thousand(bits, expected):
    assert rho_dp.theta_bits(bits) == expected


def test_the_witness_point_satisfies_the_distinguished_point_predicate(out20):
    mask = (1 << out20.walk["theta_bits"]) - 1
    assert out20.witness["collision"] == rho_dp.COLLISION_DISTINGUISHED
    assert out20.witness["X"][0] & mask == 0
    assert out20.walk["dp_predicate"] == rho_dp.DP_PREDICATE and out20.walk["index_function"] == rho_dp.INDEX_FUNCTION


def test_the_output_carries_the_whole_walk_definition_and_both_triples(out20, bits20):
    doc = out20.to_dict()
    assert set(doc["walk"]) == set(rho_dp.WALK.names)
    assert set(doc["witness"]) == set(rho_dp.WITNESS.names)
    assert doc["walk"]["variant"] == rho_dp.VARIANT_PLAIN and doc["walk"]["r"] == rho_dp.R
    assert len(doc["walk"]["multipliers"]) == rho_dp.R
    assert all(1 <= u < bits20["n"] and 1 <= v < bits20["n"] for u, v in doc["walk"]["multipliers"])
    p, a = bits20["p"], bits20["a"]
    P, Q, X = tuple(bits20["P"]), tuple(bits20["Q"]), tuple(doc["witness"]["X"])
    for name in ("first", "second"):
        alpha, beta = doc["witness"][name]
        assert ec.add(p, a, ec.mul(p, a, P, alpha), ec.mul(p, a, Q, beta)) == X
    assert (doc["witness"]["second"][1] - doc["witness"]["first"][1]) % bits20["n"] != 0
    assert rho_dp.check_postcondition(out20) is out20
    assert set(witness.witness_from_output(doc)) == {"p", "a", "b", "n", "P", "Q", "X", "first", "second"}


@pytest.mark.parametrize("inst", [F5, GF101, "bits20_seed1", "bits24_seed1"], ids=["F5", "GF101", "bits20", "bits24"])
def test_plain_and_negation_map_walks_recover_x_and_verify_gate_side(inst):
    inst = _case(inst) if isinstance(inst, str) else inst
    plain = rho_dp.run(*_args(inst))
    variant = rho_dp.run(*_args(inst), negation_map=True)
    assert plain.x == variant.x == inst["x"]
    assert plain.walk["variant"] == rho_dp.VARIANT_PLAIN and variant.walk["variant"] == rho_dp.VARIANT_NEGATION_MAP
    assert plain.walk["cycle_window"] == 0 and variant.walk["cycle_window"] == rho_dp.CYCLE_WINDOW
    for out in (plain, variant):
        verdict = witness.verify(witness.witness_from_output(out.to_wire()))
        assert verdict.accepted and verdict.x == inst["x"], verdict
        assert out.status == "OK" and out.cross_check["result"] == "agree"
        assert rho_dp.RhoOutput.from_json(out.to_json()).to_json() == out.to_json()


def test_the_method_identity_parameter_separates_the_variant_from_the_baseline():
    assert rho_dp.method_params(False) == {"variant": rho_dp.VARIANT_PLAIN, "r": str(rho_dp.R)}
    assert rho_dp.method_params(True) == {"variant": rho_dp.VARIANT_NEGATION_MAP, "r": str(rho_dp.R)}
    assert rho_dp.method_params(False) != rho_dp.method_params(True)


def test_the_module_docstring_states_the_baseline_trap():
    doc = rho_dp.__doc__ or ""
    assert "baseline names plain rho" in doc
    assert "claimant" in doc and "never the baseline" in doc
    assert "control (j)" in doc


def test_discrete_log_is_the_seam_shape_and_returns_a_bare_int(bits20):
    x = rho_dp.discrete_log(bits20["p"], bits20["a"], bits20["b"], bits20["n"], bits20["P"], bits20["Q"], 1)
    assert isinstance(x, int) and x == bits20["x"]


def test_expected_ops_uses_the_birthday_constants():
    assert rho_dp.expected_ops(1 << 40) == int(rho_dp.PLAIN_CONSTANT * (1 << 20))
    assert rho_dp.expected_ops(1 << 40, True) == int(rho_dp.NEGATION_CONSTANT * (1 << 20))
    assert rho_dp.expected_ops(7) == 8


def test_an_exhausted_walk_names_its_cap(monkeypatch, bits20):
    monkeypatch.setattr(rho_dp, "CAP_MULTIPLIER", 0)
    with pytest.raises(rho_dp.WalkExhausted, match="no collision after 0 restarts"):
        rho_dp.run(*_args(bits20))


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"n": 21}, "not prime"),
        ({"Q": [1, 1]}, "not on the curve"),
        ({"a": 0, "b": 0}, "singular"),
        ({"n": 579641 * 2 + 1}, "Hasse|not prime"),
    ],
)
def test_run_refuses_a_malformed_instance_with_a_typed_reason(bits20, override, match):
    with pytest.raises(rho_dp.InputError, match=match):
        rho_dp.run(*_args(bits20, **override))


def test_run_refuses_a_bits_field_that_disagrees_with_p(bits20):
    args = list(_args(bits20))
    args[0] = 21
    with pytest.raises(rho_dp.InputError, match="bits = 21 but p has 20 bits"):
        rho_dp.run(*args)


def test_parse_inputs_accepts_decimal_strings_and_defaults_the_variant(bits20):
    doc = {"bits": 20, "seed": 1, **{k: str(bits20[k]) for k in ("p", "a", "b", "n")}}
    doc["P"] = [str(c) for c in bits20["P"]]
    doc["Q"] = [str(c) for c in bits20["Q"]]
    parsed = rho_dp.parse_inputs(json.dumps(doc))
    assert parsed["p"] == bits20["p"] and parsed["P"] == bits20["P"] and parsed["negation_map"] is False
    assert rho_dp.parse_inputs(json.dumps({**doc, "negation_map": True}))["negation_map"] is True


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("", "empty stdin"),
        ("[]", "not a JSON object"),
        ('{"bits": 20}', "missing field"),
        ('{"bits": 20, "seed": 1, "p": "x", "a": 1, "b": 1, "n": 7, "P": [0, 1], "Q": [3, 3]}', "decimal string"),
        ('{"bits": 20, "seed": 1, "p": 5, "a": 2, "b": 1, "n": 7, "P": [0, 1], "Q": [3, 3], "extra": 1}', "undeclared"),
    ],
)
def test_parse_inputs_refuses_malformed_stdin(text, match):
    with pytest.raises(rho_dp.InputError, match=match):
        rho_dp.parse_inputs(text)


def test_from_json_refuses_a_document_that_is_not_the_output_shape():
    with pytest.raises(rho_dp.InputError, match="does not match rho_dp_output"):
        rho_dp.RhoOutput.from_json('{"bits": 20}')
    with pytest.raises(rho_dp.InputError, match="not JSON"):
        rho_dp.RhoOutput.from_json("{")


def test_main_writes_canonical_json_for_a_well_formed_document(bits20, capsys):
    import io

    doc = {"bits": 20, "seed": 1, **{k: bits20[k] for k in ("p", "a", "b", "n", "P", "Q")}}
    out, err = io.StringIO(), io.StringIO()
    assert rho_dp.main(io.StringIO(json.dumps(doc)), out, err) == 0
    text = out.getvalue()
    assert text == json.dumps(json.loads(text), sort_keys=True, separators=(",", ":")) + "\n"
    assert rho_dp.main(io.StringIO("{}"), io.StringIO(), err) == 1 and "error:" in err.getvalue()


def _revision_tree(tmp_path):
    root = tmp_path / "tree"
    for rel in rho_dp.IDENTITY_SOURCES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(rho_dp.REPO_ROOT / rel, target)
    return root


@pytest.mark.parametrize("rel", rho_dp.IDENTITY_SOURCES, ids=lambda r: Path(r).name)
def test_implementation_revision_moves_when_one_byte_of_any_identity_source_changes(tmp_path, rel):
    root = _revision_tree(tmp_path)
    assert rho_dp.implementation_revision(root) == rho_dp.implementation_revision()
    path = root / rel
    path.write_bytes(path.read_bytes() + b"\n")
    assert rho_dp.implementation_revision(root) != rho_dp.implementation_revision()


def test_the_witness_verifier_is_not_part_of_the_producers_identity():
    assert "src/cairn/witness.py" not in rho_dp.IDENTITY_SOURCES
    assert "src/cairn/skills/rho_dp.py" in rho_dp.IDENTITY_SOURCES


@pytest.mark.parametrize(
    ("mutate", "clause"),
    [
        (lambda o: dataclasses.replace(o, witness={**o.witness, "second": list(o.witness["first"])}), "b-ne-d"),
        (lambda o: dataclasses.replace(o, x=o.x % (o.n - 1) + 1), "xP-eq-Q"),
        (lambda o: dataclasses.replace(o, x=o.n), "x-range"),
        (
            lambda o: dataclasses.replace(
                o, witness={**o.witness, "first": [o.witness["first"][0] + 1, o.witness["first"][1]]}
            ),
            "triple",
        ),
        (
            lambda o: dataclasses.replace(
                o, witness={**o.witness, "X": [o.witness["X"][0], (o.witness["X"][1] + 1) % o.p]}
            ),
            "oncurve",
        ),
        (lambda o: dataclasses.replace(o, P=(o.P[0], (o.P[1] + 1) % o.p)), "oncurve"),
    ],
    ids=["b-eq-d", "x-plus-one", "x-out-of-range", "first-triple", "X-off-curve", "P-off-curve"],
)
def test_the_postcondition_refuses_each_planted_wrong_witness(out20, mutate, clause):
    with pytest.raises(rho_dp.PostconditionFailed, match=clause):
        rho_dp.check_postcondition(mutate(out20))


def test_solve_refuses_a_collision_whose_x_fails_xp_eq_q(monkeypatch, bits20):
    monkeypatch.setattr(rho_dp, "_solve_from", lambda prev, alpha, beta, n: (prev[0] + 1) % n)
    with pytest.raises(rho_dp.PostconditionFailed, match="xP-eq-Q"):
        rho_dp.solve(bits20["p"], bits20["a"], bits20["b"], bits20["n"], tuple(bits20["P"]), tuple(bits20["Q"]), 1)


def test_a_planted_disagreement_at_the_seam_surfaces_as_disagree(monkeypatch, bits20):
    from cairn.skills import bsgs

    real = bsgs.discrete_log
    monkeypatch.setattr(bsgs, "discrete_log", lambda *a, **k: real(*a, **k) + 2)
    out = rho_dp.run(*_args(bits20))
    assert out.status == "DISAGREE" and out.cross_check["result"] == "disagree"
    assert out.transcripts is not None
    assert [t["call"] for t in out.transcripts] == ["rho_dp", "bsgs"]
    assert len({t["digest"] for t in out.transcripts}) == 2 and out.x == bits20["x"]
    assert rho_dp.run(*_args(INSTANCES["bits30_seed1"])).cross_check["result"] == "untested"


def test_the_fruitless_cycle_escape_doubles_the_point_and_its_coefficients(bits20):
    p, a, n = bits20["p"], bits20["a"], bits20["n"]
    P, Q = tuple(bits20["P"]), tuple(bits20["Q"])
    alpha, beta = 12345, 678
    cur, flipped = ec.canonical(p, ec.add(p, a, ec.mul(p, a, P, alpha), ec.mul(p, a, Q, beta)))
    if flipped:
        alpha, beta = (-alpha) % n, (-beta) % n
    doubled, alpha2, beta2 = rho_dp._escape(p, a, n, cur, alpha, beta)
    assert doubled == ec.canonical(p, ec.double(p, a, cur))[0] and doubled != cur
    assert ec.add(p, a, ec.mul(p, a, P, alpha2), ec.mul(p, a, Q, beta2)) == doubled


def test_with_no_distinguished_points_the_cycle_window_finds_the_collision_or_exhausts(monkeypatch):
    monkeypatch.setattr(rho_dp, "theta_bits", lambda bits: 64)
    out = rho_dp.run(*_args(GF101, seed=2), negation_map=True)
    assert out.witness["collision"] == rho_dp.COLLISION_CYCLE_WINDOW and out.x == GF101["x"]
    assert out.distinguished_points == 0
    assert witness.verify(witness.witness_from_output(out.to_dict())).accepted
    with pytest.raises(rho_dp.WalkExhausted, match="no collision after 64 restarts"):
        rho_dp.run(*_args(GF101, seed=1), negation_map=True)


def test_a_degenerate_collision_restarts_the_plain_walk_and_keeps_the_table():
    out = rho_dp.run(*_args(GF101, seed=13))
    assert out.walk["restarts"] == 1 and out.x == GF101["x"]
    f5 = rho_dp.run(*_args(F5))
    assert f5.walk["restarts"] == 2 and f5.x == F5["x"]


def test_the_negation_map_walk_records_its_look_ahead_retries_and_the_plain_walk_none():
    inst = _case("bits24_seed1")
    variant = rho_dp.run(*_args(inst), negation_map=True)
    plain = rho_dp.run(*_args(inst))
    assert variant.walk["lookahead_retries"] > 0 and variant.walk["fruitless_escapes"] > 0
    assert plain.walk["lookahead_retries"] == 0 and plain.walk["fruitless_escapes"] == 0


LADDER_PLAN = json.loads(Path(rho_dp.REPO_ROOT, "bundle/ladder_plan.json").read_text())


def test_the_ladder_plan_baseline_is_the_shipped_plain_walk_revision_not_a_seed():
    baseline = LADDER_PLAN["baseline"]
    assert baseline["skill"] == "rho_dp"
    assert baseline["method_identity"] == {
        "interface_version": rho_dp.INTERFACE_VERSION,
        "params": rho_dp.method_params(False),
    }
    assert baseline["implementation_revision"] == rho_dp.implementation_revision()
    assert LADDER_PLAN["provenance"]["baseline"].startswith("written:cairn-m1-cqt.2.1")
