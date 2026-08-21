import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

import pytest

from cairn import canon, kat, keys
from cairn.canon import CanonError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _canon_decoder import decode, decode_int  # noqa: E402

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


def build_vectors():
    specs = [
        ("recipe_a", "recipe", keys.TAG_RECIPE_KEY, RECIPE_A, None),
        ("recipe_a_permuted", "recipe", keys.TAG_RECIPE_KEY, RECIPE_A_PERMUTED, {"equals": "recipe_a"}),
        ("recipe_negative_seed2", "recipe", keys.TAG_RECIPE_KEY, RECIPE_NEGATIVE, {"differs": "recipe_a"}),
        ("hypothesis_key", "hypothesis_object", keys.TAG_HYPOTHESIS_KEY, HYPOTHESIS, None),
        ("identity_bundle", "identity_bundle", keys.TAG_IDENTITY_BUNDLE, IDENTITY, None),
        ("env_manifest", "env_manifest", keys.TAG_ENV_MANIFEST, ENV, None),
        ("instance", "instance", keys.TAG_INSTANCE, INSTANCE, None),
        ("node", "node", keys.TAG_NODE, {"node_kind": "test", "payload": "payload"}, None),
    ]
    vectors = []
    for name, kind, tag, value, relation in specs:
        vector = {"name": name, "kind": kind, "domain_tag": tag, "input": value, "relation": relation}
        expected, canonical_hex = kat.compute(vector)
        vector["expected"] = expected
        vector["canonical_hex"] = canonical_hex
        vectors.append(vector)
    return {"generator": "UPDATE_GOLDENS=1 uv run pytest tests/unit/test_canon.py -k kat", "origin": "author_supplied", "blake3": importlib.metadata.version("blake3"), "vectors": vectors}


def test_kat_vectors_match_golden(assert_golden):
    text = json.dumps(build_vectors(), indent=1, sort_keys=True) + "\n"
    assert_golden(VECTOR_FILE, text)


def test_kat_runner_passes_on_committed_vectors(caplog):
    caplog.set_level("INFO", logger="cairn")
    assert kat.run() == []
    names = [r.fields["name"] for r in caplog.records if r.getMessage() == "vector"]
    assert len(names) == 8


def test_kat_guard_rejects_drift(tmp_path):
    copy = tmp_path / VECTOR_FILE
    data = json.loads(kat.DEFAULT_VECTORS.read_text())
    first = data["vectors"][0]
    first["expected"] = ("0" if first["expected"][0] != "0" else "1") + first["expected"][1:]
    copy.write_text(json.dumps(data))
    failures = kat.run(copy)
    assert failures and failures[0].startswith(first["name"])


def test_kat_negative_vector_differs_from_its_base():
    vectors = {v["name"]: v for v in build_vectors()["vectors"]}
    assert vectors["recipe_negative_seed2"]["expected"] != vectors["recipe_a"]["expected"]
    assert vectors["recipe_a_permuted"]["expected"] == vectors["recipe_a"]["expected"]


def test_permuted_insertion_order_hashes_identically():
    assert keys.recipe_key(RECIPE_A) == keys.recipe_key(RECIPE_A_PERMUTED)


def test_undeclared_field_is_refused():
    with pytest.raises(CanonError, match="bogus"):
        keys.recipe_key({**RECIPE_A, "bogus": 1})


def test_empty_container_digest_is_refused():
    with pytest.raises(CanonError, match="container_digest"):
        keys.recipe_key({**RECIPE_A, "container_digest": ""})
    with pytest.raises(CanonError, match="container_digest"):
        keys.identity_bundle_hash({**IDENTITY, "container_digest": ""})


def test_float_anywhere_is_refused():
    with pytest.raises(CanonError, match="float"):
        keys.hypothesis_key({**HYPOTHESIS, "declared_parameter_ranges": {"bits": [30, 60.0]}})


def test_two_domain_tags_over_one_object_differ():
    body = canon.encode(keys.RECIPE, RECIPE_A)
    assert canon.digest(keys.TAG_RECIPE_KEY, body) != canon.digest(keys.TAG_NODE, body)


@pytest.mark.parametrize("value", [0, 1, -1, 255, 256, -256, 2**64, -(2**64), 2**300 - 1, -(2**300)])
def test_int_round_trip_through_test_decoder(value):
    assert decode_int(canon.encode_int_body(value)) == value


def test_struct_round_trips_through_test_decoder():
    assert decode(canon.encode(keys.RECIPE, RECIPE_A)) == {
        "skill_identity_hash": "aa" * 32,
        "inputs": {"a_input": [DIGEST_A, 7], "b_input": [DIGEST_B, 2048]},
        "seed": 1,
        "tool_versions": {"cypari2": "2.2.4", "gp": "2.17.4"},
        "container_digest": "cc" * 32,
        "salt": "",
    }


def test_kat_cli_prints_pass(capsys):
    from cairn import cli

    assert cli.main(["kat", "canon"]) == 0
    assert capsys.readouterr().out.strip() == "PASS"


def test_kat_cli_fails_on_drifted_copy(tmp_path, capsys):
    from cairn import cli

    copy = tmp_path / VECTOR_FILE
    shutil.copy(kat.DEFAULT_VECTORS, copy)
    data = json.loads(copy.read_text())
    data["vectors"][1]["relation"] = {"differs": "recipe_a"}
    copy.write_text(json.dumps(data))
    assert cli.main(["kat", "canon", "--vectors", str(copy)]) == 1
    assert capsys.readouterr().out.startswith("FAIL")
