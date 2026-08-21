import json
import re
import sys
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from cairn import canon, keys
from cairn.canon import BYTES, STR, CanonError, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _canon_decoder import decode, decode_int  # noqa: E402
from mutants import canon_mutants  # noqa: E402

CORPUS = Path(__file__).resolve().parent.parent / "fuzz_corpus" / "canon"
SIMPLE_SCHEMAS = {"str": STR, "int": canon.INT, "list_bytes": List(BYTES), "list_bytes_hex": List(BYTES), "list_str": List(STR)}

hexdigest = st.binary(min_size=32, max_size=32).map(bytes.hex)
RECIPE_EXAMPLE = {
    "skill_identity_hash": "aa" * 32,
    "inputs": {"b": ("11" * 32, 1), "a": ("22" * 32, 2)},
    "seed": 7,
    "tool_versions": {"gp": "2.17.4"},
    "container_digest": "cc" * 32,
    "salt": "s",
}
short_text = st.text(max_size=12)

recipes = st.fixed_dictionaries(
    {
        "skill_identity_hash": hexdigest,
        "inputs": st.dictionaries(short_text, st.tuples(hexdigest, st.integers(0, 2**40)), max_size=4),
        "seed": st.integers(),
        "tool_versions": st.dictionaries(short_text, short_text, max_size=4),
        "container_digest": st.text(min_size=1, max_size=64),
        "salt": short_text,
    }
)
hypotheses = st.fixed_dictionaries(
    {
        "target_family": short_text,
        "claimed": st.dictionaries(short_text, short_text, max_size=4),
        "method_identity": st.fixed_dictionaries({"interface_version": short_text, "params": st.dictionaries(short_text, short_text, max_size=3)}),
        "declared_parameter_ranges": st.dictionaries(short_text, st.lists(st.integers(), min_size=2, max_size=2), max_size=3),
        "sampling_distribution": st.none() | short_text,
    }
)
payloads = st.recursive(
    st.none() | st.booleans() | st.integers() | st.binary(max_size=8) | st.text(max_size=8),
    lambda child: st.lists(child, max_size=4) | st.dictionaries(st.text(max_size=8), child, max_size=4),
    max_leaves=50,
)


def shuffled(value, data):
    if isinstance(value, dict):
        order = data.draw(st.permutations(list(value)))
        return {k: shuffled(value[k], data) for k in order}
    if isinstance(value, (list, tuple)):
        return [shuffled(v, data) for v in value]
    return value


def mutate_field(obj, field, data):
    if field == "seed":
        return {**obj, field: obj[field] + data.draw(st.integers(1, 10**6))}
    if field in ("inputs", "tool_versions"):
        key = data.draw(short_text)
        new = dict(obj[field])
        new[key] = (data.draw(hexdigest), 0) if field == "inputs" else "changed"
        if new == obj[field]:
            new[key + "_"] = new[key]
        return {**obj, field: new}
    return {**obj, field: obj[field] + "x"}


@given(recipes, st.data())
def test_mr1_permutation_invariance(recipe, data):
    assert canon.encode(keys.RECIPE, shuffled(recipe, data)) == canon.encode(keys.RECIPE, recipe)


@given(hypotheses, st.data())
def test_mr1_permutation_invariance_hypothesis_object(hyp, data):
    assert keys.hypothesis_key(shuffled(hyp, data)) == keys.hypothesis_key(hyp)


def test_mutant_dict_order_encoder_is_killed():
    recipe = RECIPE_EXAMPLE
    permuted = {**recipe, "inputs": {"a": ("22" * 32, 2), "b": ("11" * 32, 1)}}
    with canon_mutants.dict_order_encoder():
        assert canon.encode(keys.RECIPE, permuted) != canon.encode(keys.RECIPE, recipe)


@given(recipes)
def test_mr2_idempotence_and_fresh_encoder_agreement(recipe):
    first = canon.encode(keys.RECIPE, recipe)
    assert canon.encode(keys.RECIPE, decode(first)) == first
    assert canon.encode(keys.RECIPE, recipe) == first


def test_mutant_salted_encoder_is_killed():
    recipe = RECIPE_EXAMPLE
    with canon_mutants.salted_encoder():
        assert canon.encode(keys.RECIPE, recipe) != canon.encode(keys.RECIPE, recipe)


@given(st.binary(max_size=40), st.data())
@example(s=b"a\x03b", data=None)
def test_mr3_length_prefix_injectivity(s, data):
    if data is None:
        i, j = 1, 2
    else:
        i = data.draw(st.integers(0, len(s)))
        j = data.draw(st.integers(0, len(s)).filter(lambda v: v != i)) if len(s) else None
        if j is None:
            return
    assert canon.encode(List(BYTES), [s[:i], s[i:]]) != canon.encode(List(BYTES), [s[:j], s[j:]])


def test_mr3_ab_c_vs_a_bc_example():
    assert canon.encode(List(STR), ["ab", "c"]) != canon.encode(List(STR), ["a", "bc"])


def test_mutant_concat_encoder_is_killed():
    with canon_mutants.concat_encoder():
        assert canon.encode(List(BYTES), [b"a", b"\x03b"]) == canon.encode(List(BYTES), [b"a\x03", b"b"])


@given(recipes, st.sampled_from(keys.DOMAIN_TAGS), st.sampled_from(keys.DOMAIN_TAGS))
def test_mr4_domain_separation(recipe, tag1, tag2):
    body = canon.encode(keys.RECIPE, recipe)
    assert (canon.digest(tag1, body) == canon.digest(tag2, body)) == (tag1 == tag2)


def test_mutant_untagged_hasher_is_killed():
    body = canon.encode(keys.RECIPE, RECIPE_EXAMPLE)
    with canon_mutants.untagged_hasher():
        assert canon.digest(keys.TAG_RECIPE_KEY, body) == canon.digest(keys.TAG_NODE, body)


@given(recipes, st.sampled_from(keys.RECIPE.names), st.data())
def test_mr5_field_sensitivity(recipe, field, data):
    changed = mutate_field(recipe, field, data)
    assert changed != recipe
    assert keys.recipe_key(changed) != keys.recipe_key(recipe)


def test_mutant_first_n_fields_encoder_is_killed():
    recipe = RECIPE_EXAMPLE
    with canon_mutants.first_n_fields_encoder():
        assert keys.recipe_key({**recipe, "salt": recipe["salt"] + "x"}) == keys.recipe_key(recipe)


@given(st.integers(-(2**300), 2**300))
@example(0)
@example(2**64)
@example(-(2**64))
def test_mr6_integer_encoding(i):
    body = canon.encode_int_body(i)
    assert decode_int(body) == i
    if i:
        assert len(body) == len(canon.encode_int_body(-i))
    assert canon.encode_int_body(0) == b"\x00" + canon.u64le(0)


def test_mutant_fixed_width_int_encoder_is_killed():
    with canon_mutants.fixed_width_int_encoder():
        assert decode_int(canon.encode_int_body(2**70)) != 2**70


@given(payloads)
def test_fuzz_encoder_raises_only_canon_error(payload):
    try:
        canon.encode(keys.RECIPE, payload)
    except CanonError:
        pass


@given(recipes, st.text(min_size=1, max_size=12).filter(lambda k: k not in keys.RECIPE.names))
def test_fuzz_undeclared_key_is_named(recipe, key):
    with pytest.raises(CanonError) as info:
        canon.encode(keys.RECIPE, {**recipe, key: 1})
    assert repr(key) in str(info.value)


@given(recipes, st.sampled_from(["seed", "inputs", "tool_versions"]), st.floats(allow_nan=False))
def test_fuzz_float_anywhere_is_refused(recipe, field, value):
    poisoned = {**recipe, field: value if field == "seed" else {**recipe[field], "f": value}}
    with pytest.raises(CanonError, match="float"):
        canon.encode(keys.RECIPE, poisoned)


@given(recipes)
def test_fuzz_round_trip_through_test_decoder(recipe):
    encoded = canon.encode(keys.RECIPE, recipe)
    assert canon.encode(keys.RECIPE, decode(encoded)) == encoded


def test_nfc_and_nfd_spellings_encode_identically():
    assert canon.encode(STR, "é") == canon.encode(STR, "é")


def _corpus_cases():
    return sorted(CORPUS.glob("*.json"))


@pytest.mark.parametrize("path", _corpus_cases(), ids=lambda p: p.stem)
def test_fuzz_corpus_replay(path):
    case = json.loads(path.read_text())
    schema = keys.SCHEMAS.get(case["schema"]) or SIMPLE_SCHEMAS[case["schema"]]
    if case["expect"] == "CanonError":
        with pytest.raises(CanonError, match=re.escape(case["match"])):
            canon.encode(schema, case["input"])
        return
    if case["expect"] == "round_trip":
        value = int(case["input"])
        assert decode_int(canon.encode_int_body(value)) == value
        return
    inputs = case["inputs"]
    if case["schema"] == "list_bytes_hex":
        inputs = [[bytes.fromhex(h) for h in group] for group in inputs]
    elif case["schema"] == "list_bytes":
        inputs = [[s.encode() for s in group] for group in inputs]
    encodings = [canon.encode(schema, value) for value in inputs]
    assert (encodings[0] == encodings[1]) == (case["expect"] == "equal")
