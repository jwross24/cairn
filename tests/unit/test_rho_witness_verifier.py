import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cairn import ec, keys, witness
from cairn.skills import rho_dp

CORPUS = json.loads(Path(rho_dp.REPO_ROOT, "src/cairn/skills/rho_dp_corpus.json").read_text())


def _case(case_id):
    case = next(c for c in CORPUS["cases"] if c["id"] == case_id)
    return {name: field["value"] for name, field in case["fields"].items()}


BITS20 = _case("bits20_seed1")
COMPOSITE = _case("composite_order")


def _witness(inst, seed=1):
    out = rho_dp.run(inst["p"].bit_length(), seed, inst["p"], inst["a"], inst["b"], inst["n"], inst["P"], inst["Q"])
    return witness.witness_from_output(out.to_dict()), out


@pytest.fixture(scope="module")
def good():
    return _witness(BITS20)[0]


def test_a_valid_witness_is_accepted_with_the_instance_hash_and_x(good):
    verdict = witness.verify(good)
    assert verdict.accepted and verdict.reason is None and verdict.x == BITS20["x"]
    assert verdict.instance_hash == keys.instance_hash({k: good[k] for k in ("p", "a", "b", "n", "P", "Q")})
    assert set(verdict.node()) == {"accepted", "reason", "x", "instance_hash", "wall_s"}


def test_a_wire_form_witness_with_decimal_strings_is_accepted(good):
    wire = {k: (str(v) if isinstance(v, int) else [str(c) for c in v]) for k, v in good.items()}
    assert witness.verify(wire).x == BITS20["x"]


def test_b_equal_to_d_is_refused_outright_rather_than_retried(good):
    n = good["n"]
    same = {**good, "second": list(good["first"])}
    shifted = {**good, "second": [good["first"][0] + n, good["first"][1] + n]}
    for form in (same, shifted):
        verdict = witness.verify(form)
        assert not verdict.accepted and verdict.reason == witness.B_EQ_D and verdict.x is None


def test_a_witness_whose_x_fails_xp_eq_q_is_refused(good):
    wrong_modulus = {**good, "n": good["n"] + 2}
    verdict = witness.verify(wrong_modulus)
    assert not verdict.accepted and verdict.reason == witness.XP_NE_Q
    assert verdict.x is not None and verdict.x != BITS20["x"]


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda w: {**w, "first": [w["first"][0] + 1, w["first"][1]]}, witness.FIRST_TRIPLE_NE_X),
        (lambda w: {**w, "second": [w["second"][0], w["second"][1] + 1]}, witness.SECOND_TRIPLE_NE_X),
        (lambda w: {**w, "X": [w["X"][0], (w["X"][1] + 1) % w["p"]]}, witness.X_OFF_CURVE),
        (lambda w: {**w, "P": [w["P"][0], (w["P"][1] + 1) % w["p"]]}, witness.P_OFF_CURVE),
        (lambda w: {**w, "Q": [w["Q"][0], (w["Q"][1] + 1) % w["p"]]}, witness.Q_OFF_CURVE),
        (lambda w: {k: v for k, v in w.items() if k != "second"}, witness.BAD_FIELD),
        (lambda w: {**w, "n": "seven"}, witness.BAD_FIELD),
        (lambda w: {**w, "n": "\u00b2"}, witness.BAD_FIELD),
        (lambda w: {**w, "a": "--5"}, witness.BAD_FIELD),
        (lambda w: {**w, "first": [True, 2]}, witness.BAD_FIELD),
        (lambda w: {**w, "X": [w["X"][0] + w["p"], w["X"][1]]}, witness.BAD_FIELD),
        (lambda w: [w], witness.BAD_FIELD),
    ],
    ids=[
        "first-triple",
        "second-triple",
        "X-off",
        "P-off",
        "Q-off",
        "missing-second",
        "n-not-int",
        "superscript-digit",
        "double-minus",
        "bool-scalar",
        "unreduced-X",
        "not-a-mapping",
    ],
)
def test_every_planted_form_is_refused_with_its_typed_reason(good, mutate, reason):
    verdict = witness.verify(mutate(good))
    assert not verdict.accepted and verdict.reason == reason
    assert reason in witness.REASONS


def test_a_non_invertible_difference_on_a_composite_order_is_named():
    c = COMPOSITE
    p, a, P = c["p"], c["a"], tuple(c["P"])
    Q = ec.mul(p, a, P, 2)
    form = {
        "p": p,
        "a": a,
        "b": c["b"],
        "n": 21,
        "P": list(P),
        "Q": list(Q),
        "X": list(P),
        "first": [1, 0],
        "second": [8, 7],
    }
    verdict = witness.verify(form)
    assert not verdict.accepted and verdict.reason == witness.D_MINUS_B_NOT_INVERTIBLE


def test_the_verifier_uses_libpari_not_the_producers_arithmetic(monkeypatch, good):
    calls = []
    real = ec.mul

    def spy(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(ec, "mul", spy)
    assert witness.verify(good).accepted
    assert calls == []


@given(x=st.integers(min_value=1, max_value=BITS20["n"] - 1), seed=st.integers(min_value=1, max_value=1 << 32))
@settings(max_examples=60, deadline=None)
def test_property_a_fresh_witness_verifies_and_a_tampered_one_does_not(x, seed):
    p, a, b, n, P = BITS20["p"], BITS20["a"], BITS20["b"], BITS20["n"], tuple(BITS20["P"])
    Q = ec.mul(p, a, P, x)
    definition, solution = rho_dp.solve(p, a, b, n, P, Q, seed)
    form = {
        "p": p,
        "a": a,
        "b": b,
        "n": n,
        "P": list(P),
        "Q": list(Q),
        "X": list(solution.X),
        "first": list(solution.first),
        "second": list(solution.second),
    }
    verdict = witness.verify(form)
    assert verdict.accepted and verdict.x == x
    tampered = witness.verify({**form, "second": list(solution.first)})
    assert not tampered.accepted and tampered.reason == witness.B_EQ_D


def test_reasons_are_the_closed_vocabulary_the_ladder_reads():
    assert witness.REASONS == (
        "bad-field",
        "P-off-curve",
        "Q-off-curve",
        "X-off-curve",
        "first-triple-ne-X",
        "second-triple-ne-X",
        "b-eq-d",
        "d-minus-b-not-invertible",
        "xP-ne-Q",
    )


@pytest.mark.parametrize(
    ("mutate", "detail"),
    [
        (lambda w: {**w, "p": 3}, "prime-order toy curve"),
        (lambda w: {**w, "n": 1}, "prime-order toy curve"),
        (lambda w: {**w, "a": w["p"]}, "not reduced mod p"),
        (lambda w: {**w, "first": [1, 2, 3]}, "not a pair"),
        (lambda w: {**w, "second": 7}, "not a pair"),
    ],
    ids=["p-below-5", "n-below-2", "a-unreduced", "triple-of-three", "scalar-second"],
)
def test_structural_guards_refuse_before_any_curve_arithmetic(good, mutate, detail):
    with pytest.raises(witness.WitnessFieldError, match=detail):
        witness.parse(mutate(good))
    verdict = witness.verify(mutate(good))
    assert not verdict.accepted and verdict.reason == witness.BAD_FIELD and verdict.instance_hash is None


def test_a_triple_summing_to_the_identity_is_a_mismatch_not_a_crash(good):
    verdict = witness.verify({**good, "first": [0, 0]})
    assert not verdict.accepted and verdict.reason == witness.FIRST_TRIPLE_NE_X
    verdict = witness.verify({**good, "second": [good["n"], good["n"]]})
    assert not verdict.accepted and verdict.reason == witness.SECOND_TRIPLE_NE_X
