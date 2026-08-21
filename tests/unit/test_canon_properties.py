import json
import re
import sys
import unicodedata
from pathlib import Path

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from cairn import canon, keys
from cairn.canon import BLOBREF, BOOL, BYTES, INT, STR, CanonError, List, Map, Set

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _canon_decoder import decode, decode_int  # noqa: E402
from mutants import canon_mutants  # noqa: E402

CORPUS = Path(__file__).resolve().parent.parent / "fuzz_corpus" / "canon"
SIMPLE_SCHEMAS = {"str": STR, "int": INT, "list_bytes": List(BYTES), "list_bytes_hex": List(BYTES), "list_str": List(STR)}
LEAF_TYPES = {"INT": INT, "STR": STR, "BYTES": BYTES, "BOOL": BOOL, "BLOBREF": BLOBREF, "List(INT)": List(INT), "Map(STR,STR)": Map(STR, STR), "Set(INT)": Set(INT)}

hexdigest = st.binary(min_size=32, max_size=32).map(bytes.hex)
short_text = st.text(max_size=12)
RECIPE_EXAMPLE = {
    "skill_identity_hash": "aa" * 32,
    "inputs": {"b": ("11" * 32, 1), "a": ("22" * 32, 2)},
    "seed": 7,
    "tool_versions": {"gp": "2.17.4"},
    "container_digest": "cc" * 32,
    "salt": "s",
}

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
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.binary(max_size=8) | st.text(max_size=8),
    lambda child: st.lists(child, max_size=4) | st.dictionaries(st.text(max_size=8), child, max_size=4) | st.tuples(child, child),
    max_leaves=30,
)


def shuffled(value, data):
    if isinstance(value, dict):
        order = data.draw(st.permutations(list(value)))
        return {k: shuffled(value[k], data) for k in order}
    if isinstance(value, (list, tuple)):
        return [shuffled(v, data) for v in value]
    return value


def canonical_form(value):
    if isinstance(value, dict):
        return {canonical_form(k): canonical_form(v) for k, v in value.items()}
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str) and len(value[0]) == 64:
        return [value[0], value[1]]
    if isinstance(value, (list, tuple)):
        return [canonical_form(v) for v in value]
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
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


def check_mr1(recipe, permuted):
    assert canon.encode(keys.RECIPE, permuted) == canon.encode(keys.RECIPE, recipe)


def check_mr2(recipe):
    first = canon.encode(keys.RECIPE, recipe)
    assert canon.encode(keys.RECIPE, recipe) == first
    assert canon.encode(keys.RECIPE, decode(first)) == first


def check_mr3(s, i, j):
    assert canon.encode(List(BYTES), [s[:i], s[i:]]) != canon.encode(List(BYTES), [s[:j], s[j:]])


def check_mr4(body, tag1, tag2):
    assert (canon.digest(tag1, body) == canon.digest(tag2, body)) == (tag1 == tag2)


def check_mr5(recipe, changed):
    assert changed != recipe
    assert keys.recipe_key(changed) != keys.recipe_key(recipe)


def check_mr6(i):
    body = canon.encode_int_body(i)
    assert decode_int(body) == i
    if i:
        assert len(body) == len(canon.encode_int_body(-i))


@given(recipes, st.data())
def test_mr1_permutation_invariance(recipe, data):
    check_mr1(recipe, shuffled(recipe, data))


@given(recipes)
def test_mr1_raw_bytes_blobref_equals_hex_blobref(recipe):
    raw = {**recipe, "inputs": {k: (bytes.fromhex(h), n) for k, (h, n) in recipe["inputs"].items()}}
    check_mr1(recipe, raw)


@given(hypotheses, st.data())
def test_mr1_permutation_invariance_hypothesis_object(hyp, data):
    assert keys.hypothesis_key(shuffled(hyp, data)) == keys.hypothesis_key(hyp)


def test_mutant_dict_order_encoder_is_killed_by_mr1():
    permuted = {**RECIPE_EXAMPLE, "inputs": {"a": ("22" * 32, 2), "b": ("11" * 32, 1)}}
    check_mr1(RECIPE_EXAMPLE, permuted)
    with canon_mutants.dict_order_encoder(), pytest.raises(AssertionError):
        check_mr1(RECIPE_EXAMPLE, permuted)


@given(recipes)
def test_mr2_idempotence_and_fresh_encoder_agreement(recipe):
    check_mr2(recipe)


def test_mutant_salted_encoder_is_killed_by_mr2():
    check_mr2(RECIPE_EXAMPLE)
    with canon_mutants.salted_encoder(), pytest.raises(AssertionError):
        check_mr2(RECIPE_EXAMPLE)


@st.composite
def split_points(draw):
    s = draw(st.binary(min_size=1, max_size=40))
    i = draw(st.integers(0, len(s)))
    j = draw(st.integers(0, len(s)).filter(lambda v: v != i))
    return s, i, j


@given(split_points())
@example((b"a\x03b", 1, 2))
def test_mr3_length_prefix_injectivity(case):
    check_mr3(*case)


def test_mr3_ab_c_vs_a_bc_example():
    assert canon.encode(List(STR), ["ab", "c"]) != canon.encode(List(STR), ["a", "bc"])


def test_mutant_concat_encoder_is_killed_by_mr3():
    check_mr3(b"a\x03b", 1, 2)
    with canon_mutants.concat_encoder(), pytest.raises(AssertionError):
        check_mr3(b"a\x03b", 1, 2)


@given(recipes, st.sampled_from(keys.DOMAIN_TAGS), st.sampled_from(keys.DOMAIN_TAGS))
def test_mr4_domain_separation(recipe, tag1, tag2):
    check_mr4(canon.encode(keys.RECIPE, recipe), tag1, tag2)


def test_mutant_untagged_hasher_is_killed_by_mr4():
    body = canon.encode(keys.RECIPE, RECIPE_EXAMPLE)
    check_mr4(body, keys.TAG_RECIPE_KEY, keys.TAG_NODE)
    with canon_mutants.untagged_hasher(), pytest.raises(AssertionError):
        check_mr4(body, keys.TAG_RECIPE_KEY, keys.TAG_NODE)


@given(recipes, st.sampled_from(keys.RECIPE.names), st.data())
def test_mr5_field_sensitivity(recipe, field, data):
    check_mr5(recipe, mutate_field(recipe, field, data))


def test_mutant_first_n_fields_encoder_is_killed_by_mr5():
    changed = {**RECIPE_EXAMPLE, "salt": RECIPE_EXAMPLE["salt"] + "x"}
    check_mr5(RECIPE_EXAMPLE, changed)
    with canon_mutants.first_n_fields_encoder(), pytest.raises(AssertionError):
        check_mr5(RECIPE_EXAMPLE, changed)


@given(st.integers(-(2**300), 2**300))
@example(0)
@example(2**64)
@example(-(2**64))
def test_mr6_integer_encoding(i):
    check_mr6(i)


def test_mr6_zero_is_one_fixed_byte_string():
    assert canon.encode_int_body(0) == b"\x00" + canon.u64le(0)


def test_mutant_fixed_width_int_encoder_is_killed_by_mr6():
    check_mr6(2**70)
    with canon_mutants.fixed_width_int_encoder(), pytest.raises(AssertionError):
        check_mr6(2**70)


@given(st.sampled_from(sorted(LEAF_TYPES)), payloads)
def test_fuzz_leaf_encoders_raise_only_canon_error(type_name, payload):
    try:
        canon.encode(LEAF_TYPES[type_name], payload)
    except CanonError:
        pass


@given(recipes, st.sampled_from(keys.RECIPE.names), payloads)
def test_fuzz_spliced_recipe_field_raises_only_canon_error_or_encodes(recipe, field, payload):
    try:
        canon.encode(keys.RECIPE, {**recipe, field: payload})
    except CanonError:
        pass


@given(recipes, st.text(min_size=1, max_size=12).filter(lambda k: k not in keys.RECIPE.names))
def test_fuzz_undeclared_key_is_named(recipe, key):
    with pytest.raises(CanonError, match=re.escape(repr(key))):
        canon.encode(keys.RECIPE, {**recipe, key: 1})


@given(recipes, st.sampled_from(["seed", "inputs", "tool_versions"]), st.floats(allow_nan=False))
def test_fuzz_float_anywhere_is_refused(recipe, field, value):
    poisoned = {**recipe, field: value if field == "seed" else {**recipe[field], "f": value}}
    with pytest.raises(CanonError, match="float"):
        canon.encode(keys.RECIPE, poisoned)


@given(recipes)
def test_fuzz_round_trip_recovers_the_canonical_form(recipe):
    assert decode(canon.encode(keys.RECIPE, recipe)) == canonical_form(recipe)


@given(st.text())
def test_nfc_and_nfd_spellings_encode_identically(text):
    assert canon.encode(STR, unicodedata.normalize("NFD", text)) == canon.encode(STR, unicodedata.normalize("NFC", text))


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
