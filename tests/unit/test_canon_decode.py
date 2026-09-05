import sys
from pathlib import Path

import pytest

from cairn import canon, claims, keys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories


def test_a_recipe_decodes_to_the_fields_it_was_encoded_from():
    fields = helpers.recipe(seed=5, inputs={"curve": ("ab" * 32, 7)}, salt="s")
    encoded = canon.encode(keys.RECIPE, fields)
    decoded = canon.decode(keys.RECIPE, encoded)
    assert decoded["seed"] == 5 and decoded["salt"] == "s" and decoded["skill_identity_hash"] == "aa" * 32
    assert decoded["inputs"] == {"curve": ("ab" * 32, 7)}
    assert decoded["tool_versions"] == {"gp": "2.17.4"}
    assert canon.encode(keys.RECIPE, decoded) == encoded


def test_a_hypothesis_object_decodes_to_its_typed_fields():
    obj = factories.hypothesis_object(seed=3, cost_model={"exponent": "1/3", "constant": "1", "crossover": 40})
    decoded = canon.decode(keys.HYPOTHESIS_OBJECT, claims.hypothesis_object_canonical(obj))
    assert decoded["target_family"] == "toy_curve"
    assert decoded["claimed"]["exponent"] == "1/3" and decoded["claimed"]["kind"] == "cost_model"
    assert decoded["declared_parameter_ranges"] == {"bits": [30, 50]}


def test_trailing_bytes_are_refused():
    encoded = canon.encode(keys.RECIPE, helpers.recipe())
    with pytest.raises(canon.CanonError, match="trailing"):
        canon.decode(keys.RECIPE, encoded + b"\x00")


def test_a_truncated_record_is_refused():
    encoded = canon.encode(keys.RECIPE, helpers.recipe())
    with pytest.raises(canon.CanonError):
        canon.decode(keys.RECIPE, encoded[:-3])


def test_a_non_minimal_int_body_is_refused():
    leading_zero = b"\x00" + (2).to_bytes(8, "little") + b"\x00\x05"
    with pytest.raises(canon.CanonError, match="leading zero"):
        canon.decode_int_body(leading_zero, 0)
    negative_zero = b"\x01" + (0).to_bytes(8, "little")
    with pytest.raises(canon.CanonError, match="negative zero"):
        canon.decode_int_body(negative_zero, 0)
    assert canon.decode_int_body(b"\x00" + (1).to_bytes(8, "little") + b"\x05", 0) == (5, 10)
