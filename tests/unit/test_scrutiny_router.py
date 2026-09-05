import inspect
import json
from fractions import Fraction
from pathlib import Path

import pytest

from cairn import scrutiny

ROOT = Path(__file__).resolve().parent.parent.parent
POLICY = json.loads((ROOT / "bundle" / "scrutiny.json").read_text())
SQRT = {"exponent": "1/2", "constant": "0.886", "crossover": "48"}
BELOW = {"exponent": "1/3", "constant": "1", "crossover": "40"}
ABOVE = {"exponent": "2/3", "constant": "1", "crossover": "40"}


@pytest.fixture
def policy():
    return scrutiny.Policy.from_object(POLICY)


def classify(policy, **kw):
    args = {"target_family": None, "scope_target_family": None, "cost_model": None, "nogo_flagged": False, **kw}
    return scrutiny.classify(policy, **args)


def test_the_shipped_policy_names_the_toy_curve_family_the_generic_bound_and_every_obligation(policy):
    assert policy.target_family == "toy_curve"
    assert policy.generic_bound_exponent == Fraction(1, 2)
    assert policy.obligations == scrutiny.OBLIGATIONS


def test_the_router_reads_no_prose():
    params = inspect.signature(scrutiny.classify).parameters
    assert tuple(params) == ("policy", "target_family", "scope_target_family", "cost_model", "nogo_flagged")
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for name, p in params.items() if name != "policy")


def test_a_hypothesis_naming_no_target_family_is_routine_whatever_it_claims(policy):
    assert classify(policy, target_family="model_curve", cost_model=BELOW, nogo_flagged=True) == scrutiny.ROUTINE
    assert classify(policy) == scrutiny.ROUTINE


def test_naming_the_target_family_is_elevated(policy):
    assert classify(policy, target_family="toy_curve") == scrutiny.ELEVATED
    assert classify(policy, scope_target_family="toy_curve") == scrutiny.ELEVATED
    assert classify(policy, target_family="toy_curve", cost_model=SQRT) == scrutiny.ELEVATED
    assert classify(policy, target_family="toy_curve", cost_model=ABOVE) == scrutiny.ELEVATED


def test_a_claimed_exponent_below_the_generic_bound_is_top(policy):
    assert classify(policy, target_family="toy_curve", cost_model=BELOW) == scrutiny.TOP
    assert classify(policy, scope_target_family="toy_curve", cost_model={"exponent": "0.499"}) == scrutiny.TOP


def test_a_nogo_flagged_branch_on_the_target_is_top(policy):
    assert classify(policy, target_family="toy_curve", nogo_flagged=True) == scrutiny.TOP


def test_a_malformed_exponent_is_refused_rather_than_read_as_routine(policy):
    with pytest.raises(scrutiny.PolicyError, match="not a rational"):
        classify(policy, target_family="toy_curve", cost_model={"exponent": "fast"})
    with pytest.raises(scrutiny.PolicyError, match="str or int"):
        classify(policy, target_family="toy_curve", cost_model={"exponent": 0.5})


def test_classes_rank_in_order():
    assert [scrutiny.rank(c) for c in scrutiny.CLASSES] == [0, 1, 2]
    with pytest.raises(scrutiny.ScrutinyError):
        scrutiny.rank("paranoid")


def test_every_obligation_names_one_refusal_reason():
    assert len(scrutiny.REASONS) == len(scrutiny.OBLIGATIONS) == 5
    assert scrutiny.REASON_FOR[scrutiny.EXPERT_SIGNOFF] == "expert-signoff-absent"
    assert len(set(scrutiny.REASONS)) == 5


@pytest.mark.parametrize(
    ("delta", "match"),
    [
        ({"classes": ["routine", "top"]}, "classes must be"),
        ({"top_obligations": ["ladder_keep", "vibes"]}, "names no obligation vibes"),
        ({"generic_bound_exponent": "one half"}, "not a rational"),
        ({"generic_bound_exponent": "1/0"}, "not a rational"),
        ({"target_family": ""}, "non-empty str"),
    ],
)
def test_a_policy_object_off_the_contract_is_refused(delta, match):
    with pytest.raises(scrutiny.PolicyError, match=match):
        scrutiny.Policy.from_object({**POLICY, **delta})


@pytest.mark.parametrize("missing", ["target_family", "generic_bound_exponent", "classes", "top_obligations"])
def test_a_policy_object_missing_a_field_is_refused(missing):
    with pytest.raises(scrutiny.PolicyError, match=f"carries no {missing}"):
        scrutiny.Policy.from_object({k: v for k, v in POLICY.items() if k != missing})
    with pytest.raises(scrutiny.PolicyError, match="must be a mapping"):
        scrutiny.Policy.from_object(["routine"])


def test_typed_fields_call_a_cost_model_algorithmic():
    assert scrutiny.Typed("toy_curve", None, SQRT, False).algorithmic
    assert not scrutiny.Typed("toy_curve", None, None, True).algorithmic


def test_the_stronger_of_two_cost_models_is_the_lower_exponent_whichever_side_states_it():
    third = {**SQRT, "exponent": "1/3"}
    assert scrutiny.stronger(SQRT, third) == third
    assert scrutiny.stronger(third, SQRT) == third
    assert scrutiny.stronger(SQRT, SQRT) == SQRT
    assert scrutiny.stronger(None, SQRT) == SQRT
    assert scrutiny.stronger(SQRT, None) == SQRT
    assert scrutiny.stronger(None, None) is None
    with pytest.raises(scrutiny.PolicyError, match="not a rational"):
        scrutiny.stronger(SQRT, {**SQRT, "exponent": "fast"})
