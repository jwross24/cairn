import json
import re
import shutil
import sys
from pathlib import Path

import pytest

from cairn import canon, cli, kat, keys
from cairn.canon import BLOBREF, BOOL, INT, STR, CanonError, List, Map, Set

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _canon_decoder import decode  # noqa: E402

VECTOR_FILE = "canon_kat.json"
DIGEST_A = "11" * 32
DIGEST_B = "22" * 32

RECIPE_A = {
    "skill_identity_hash": "aa" * 32,
    "inputs": {"b_input": (DIGEST_B, 2048), "a_input": (DIGEST_A, 7)},
    "seed": 1,
    "tool_versions": {"gp": "2.17.4", "cypari2": "2.2.4"},
    "container_digest": "cc" * 32,
    "salt": "",
}
RECIPE_A_PERMUTED = {
    "salt": "",
    "container_digest": "cc" * 32,
    "tool_versions": {"cypari2": "2.2.4", "gp": "2.17.4"},
    "seed": 1,
    "inputs": {"a_input": [DIGEST_A, 7], "b_input": [DIGEST_B, 2048]},
    "skill_identity_hash": "aa" * 32,
}
RECIPE_NEGATIVE = {**RECIPE_A, "seed": 2}
HYPOTHESIS = {
    "target_family": "toy_curve",
    "claimed": {"kind": "cost_model", "exponent": "1/2", "constant": "0.886"},
    "method_identity": {"interface_version": "rho_dp/1", "params": {"r": "20", "theta": "2^-10"}},
    "declared_parameter_ranges": {"bits": [30, 60]},
    "sampling_distribution": None,
}
IDENTITY = {
    "interface_version": "toy_curve/1",
    "implementation_revision": "dd" * 32,
    "tool_digests": {"gp": "ee" * 32, "libpari": "2.17.2"},
    "container_digest": "cc" * 32,
    "numeric_profile": None,
}
ENV = {"os": "macOS 26.6 Darwin 25.6.0 arm64", "python": "3.14.0", "cypari2": "2.2.4", "libpari": "2.17.2", "blake3": "1.0.9", "gp_binary_sha256": "ff" * 32}
INSTANCE = {"p": 5, "a": 2, "b": 1, "n": 7, "P": [0, 1], "Q": [3, 3]}

VECTOR_SPECS = [
    ("recipe_a", "recipe", RECIPE_A, None),
    ("recipe_a_permuted", "recipe", RECIPE_A_PERMUTED, {"equals": "recipe_a"}),
    ("recipe_negative_seed2", "recipe", RECIPE_NEGATIVE, {"differs": "recipe_a"}),
    ("hypothesis_key", "hypothesis_object", HYPOTHESIS, None),
    ("identity_bundle", "identity_bundle", IDENTITY, None),
    ("env_manifest", "env_manifest", ENV, None),
    ("instance", "instance", INSTANCE, None),
    ("node", "node", {"node_kind": "test", "payload": "payload"}, None),
]


def build_vectors():
    vectors = []
    for name, kind, value, relation in VECTOR_SPECS:
        tag = keys.TAG_NODE if kind == "node" else keys.TAGS_BY_KIND[kind]
        vector = {"name": name, "kind": kind, "domain_tag": tag, "input": value, "relation": relation}
        vector["expected"], vector["canonical_hex"] = kat.compute(vector)
        vectors.append(vector)
    return {"generator": "UPDATE_GOLDENS=1 uv run pytest tests/unit/test_canon.py -k kat_vectors_match", "origin": "author_supplied", "vectors": vectors}


def test_kat_vectors_match_golden(assert_golden):
    assert_golden(VECTOR_FILE, json.dumps(build_vectors(), indent=1, sort_keys=True) + "\n")


@pytest.mark.parametrize("kind", sorted(keys.HASHERS))
def test_public_hasher_is_bound_to_the_committed_vector(kind, load_vector):
    vector = next(v for v in load_vector(VECTOR_FILE)["vectors"] if v["kind"] == kind)
    assert keys.HASHERS[kind](vector["input"]) == vector["expected"]
    assert canon.encode(keys.SCHEMAS[kind], vector["input"]).hex() == vector["canonical_hex"]


def test_node_hash_is_bound_to_the_committed_vector(load_vector):
    vector = next(v for v in load_vector(VECTOR_FILE)["vectors"] if v["kind"] == "node")
    payload = canon.encode(STR, vector["input"]["payload"])
    assert keys.node_hash(vector["input"]["node_kind"], payload) == vector["expected"]


def test_kat_runner_passes_on_committed_vectors(caplog):
    caplog.set_level("INFO", logger="cairn")
    assert kat.run() == []
    names = [r.fields["name"] for r in caplog.records if r.getMessage() == "vector"]
    assert names == [spec[0] for spec in VECTOR_SPECS]


def _drifted_copy(tmp_path, mutate):
    copy = tmp_path / VECTOR_FILE
    data = json.loads(kat.DEFAULT_VECTORS.read_text())
    mutate(data)
    copy.write_text(json.dumps(data))
    return copy


def _flip_expected(data):
    v = data["vectors"][3]
    v["expected"] = ("0" if v["expected"][0] != "0" else "1") + v["expected"][1:]


def _flip_canonical(data):
    v = data["vectors"][0]
    v["canonical_hex"] = ("0" if v["canonical_hex"][0] != "0" else "1") + v["canonical_hex"][1:]


def _break_equals(data):
    data["vectors"][1]["relation"] = {"differs": "recipe_a"}


def _break_differs(data):
    data["vectors"][2]["relation"] = {"equals": "recipe_a"}


def _wrong_tag(data):
    data["vectors"][4]["domain_tag"] = keys.TAG_NODE


@pytest.mark.parametrize(
    ("mutate", "prefix"),
    [
        (_flip_expected, "hypothesis_key"),
        (_flip_canonical, "recipe_a"),
        (_break_equals, "recipe_a_permuted must differ"),
        (_break_differs, "recipe_negative_seed2 must equal"),
    ],
    ids=["expected-byte", "canonical-byte", "equals-relation", "differs-relation"],
)
def test_kat_runner_rejects_drift(tmp_path, mutate, prefix):
    failures = kat.run(_drifted_copy(tmp_path, mutate))
    assert failures and failures[0].startswith(prefix)


def test_kat_runner_refuses_a_vector_under_the_wrong_tag(tmp_path):
    with pytest.raises(CanonError, match="not the identity_bundle tag"):
        kat.run(_drifted_copy(tmp_path, _wrong_tag))


def test_kat_cli_exit_codes(tmp_path, capsys):
    assert cli.main(["kat", "canon"]) == 0
    assert capsys.readouterr().out.strip() == "PASS"
    copy = _drifted_copy(tmp_path, _break_equals)
    assert cli.main(["kat", "canon", "--vectors", str(copy)]) == 2
    assert capsys.readouterr().out.startswith("FAIL")


def test_golden_guard_rejects_a_one_byte_drift_without_update_goldens(assert_golden, tmp_path, monkeypatch):
    monkeypatch.delenv("UPDATE_GOLDENS", raising=False)
    copy = tmp_path / VECTOR_FILE
    shutil.copy(kat.DEFAULT_VECTORS, copy)
    text = copy.read_text()
    i = text.index('"canonical_hex": "') + len('"canonical_hex": "')
    drifted = text[:i] + ("0" if text[i] != "0" else "1") + text[i + 1 :]
    copy.write_text(drifted)
    with pytest.raises(AssertionError, match="golden mismatch"):
        assert_golden(copy, text)


def test_permuted_insertion_order_hashes_identically():
    assert keys.recipe_key(RECIPE_A) == keys.recipe_key(RECIPE_A_PERMUTED)


@pytest.mark.parametrize(
    ("hasher", "obj", "match"),
    [
        (keys.recipe_key, {**RECIPE_A, "bogus": 1}, "bogus"),
        (keys.recipe_key, {**RECIPE_A, "container_digest": ""}, "container_digest"),
        (keys.identity_bundle_hash, {**IDENTITY, "container_digest": ""}, "container_digest"),
        (keys.hypothesis_key, {**HYPOTHESIS, "declared_parameter_ranges": {"bits": [30, 60.0]}}, "float"),
        (keys.recipe_key, {k: v for k, v in RECIPE_A.items() if k != "salt"}, "missing"),
    ],
    ids=["undeclared-field", "empty-container-digest-recipe", "empty-container-digest-identity", "float-in-key", "missing-field"],
)
def test_key_refusals(hasher, obj, match):
    with pytest.raises(CanonError, match=match):
        hasher(obj)


@pytest.mark.parametrize(
    ("typ", "value", "match"),
    [
        (INT, True, "expected int"),
        (INT, 1.5, "float"),
        (STR, "\ud800", "not UTF-8"),
        (STR, 5, "expected str"),
        (BLOBREF, ("zz" * 32, 1), "must be hex"),
        (BLOBREF, ("11" * 31, 1), "32 bytes"),
        (BLOBREF, (None, 1), "hex str or bytes"),
        (BLOBREF, ("11" * 32, -1), "non-negative"),
        (BLOBREF, ("11" * 32,), "\\(hash, size\\)"),
        (BOOL, 1, "expected bool"),
        (Set(INT), [1, 1], "duplicate element"),
        (Map(STR, INT), {"é": 1, "é": 2}, "duplicate key"),
        (List(INT), 7, "expected list"),
    ],
    ids=["bool-as-int", "float-int", "surrogate-str", "non-str", "blobref-nonhex", "blobref-short", "blobref-none", "blobref-negative-size", "blobref-arity", "bool-type", "set-duplicate", "map-nfc-collision", "list-type"],
)
def test_leaf_type_rejections(typ, value, match):
    with pytest.raises(CanonError, match=match):
        canon.encode(typ, value)


def test_bool_and_set_and_raw_bytes_blobref_encode():
    assert canon.encode(BOOL, True) == canon.TAG_BOOL + b"\x01"
    assert canon.encode(Set(INT), [3, 1, 2]) == canon.encode(Set(INT), (1, 2, 3))
    assert canon.encode(BLOBREF, (bytes.fromhex(DIGEST_A), 7)) == canon.encode(BLOBREF, (DIGEST_A, 7))


def test_empty_domain_tag_is_refused():
    with pytest.raises(CanonError, match="domain tag"):
        canon.digest("", b"x")


def test_two_domain_tags_over_one_object_differ():
    body = canon.encode(keys.RECIPE, RECIPE_A)
    assert canon.digest(keys.TAG_RECIPE_KEY, body) != canon.digest(keys.TAG_NODE, body)


def test_struct_round_trips_through_test_decoder():
    assert decode(canon.encode(keys.RECIPE, RECIPE_A)) == {
        "skill_identity_hash": "aa" * 32,
        "inputs": {"a_input": [DIGEST_A, 7], "b_input": [DIGEST_B, 2048]},
        "seed": 1,
        "tool_versions": {"cypari2": "2.2.4", "gp": "2.17.4"},
        "container_digest": "cc" * 32,
        "salt": "",
    }
