import pytest

from cairn import bundle, canon, tiergate


@pytest.mark.parametrize(
    ("value", "path"),
    [
        (0.01, r"\$"),
        ([1, 2.5], r"\$\[1\]"),
        ({"f": 0.01}, r"\$\.f"),
        ({"a": {"b": [1, 1.0]}}, r"\$\.a\.b\[1\]"),
        ({1.5: "x"}, r"\$\.1\.5"),
    ],
    ids=["bare", "in-list", "in-map", "nested", "as-key"],
)
def test_a_float_anywhere_in_a_bundle_object_is_refused_and_its_location_named(value, path):
    with pytest.raises(canon.CanonError, match=rf"^{path}: floats are not canonical$"):
        bundle.canonical_bytes("auditor", value)


@pytest.mark.parametrize(
    "value", [b"raw", {1: "int-key"}, {None: "none-key"}, set()], ids=["bytes", "int-key", "none-key", "set"]
)
def test_a_type_the_bundle_encoding_does_not_admit_is_refused(value):
    with pytest.raises(canon.CanonError):
        bundle.canonical_bytes("auditor", value)


def test_two_keys_that_normalize_to_one_are_refused():
    nfc, nfd = "\u00e9", "e\u0301"
    assert nfc != nfd
    with pytest.raises(canon.CanonError, match="duplicate key"):
        bundle.canonical_bytes("auditor", {nfc: 1, nfd: 2})


@pytest.mark.parametrize(
    "value",
    [None, True, False, 0, -1, 2**300, "", "x", [], {}, [None, True, 1, "s", [], {}], {"a": [1, {"b": None}]}],
    ids=[
        "none",
        "true",
        "false",
        "zero",
        "negative",
        "big-int",
        "empty-str",
        "str",
        "empty-list",
        "empty-map",
        "mixed-list",
        "nested",
    ],
)
def test_every_admitted_shape_round_trips_through_the_decoder(value):
    assert bundle._decode(bundle.canonical_bytes("tiers", value)) == value


def test_key_order_in_the_source_does_not_move_the_canonical_bytes():
    first = bundle.canonical_bytes("tiers", {"a": 1, "b": 2})
    second = bundle.canonical_bytes("tiers", {"b": 2, "a": 1})
    assert first == second


def test_the_verifier_script_row_is_the_raw_file_bytes_not_an_encoding():
    raw = b'verify(p)=\n{\n  print("OK");\n}\n'
    assert bundle.canonical_bytes(bundle.SCRIPT_KIND, raw) == raw


@pytest.mark.parametrize("accessor", ["raw", "digest_of", "object"], ids=["raw", "digest_of", "object"])
def test_asking_a_bundle_for_a_kind_it_does_not_carry_names_the_kind(pinned_bundle, accessor):
    gate = bundle.GateBundle.open(*pinned_bundle())
    with pytest.raises(bundle.BundleError, match="no 'ladder' object"):
        getattr(gate, accessor)("ladder")


def test_a_boundary_table_whose_last_row_names_a_ceiling_still_assigns_a_tier():
    bounded = [{"tier": 0, "max_core_s": 1}, {"tier": 1, "max_core_s": 3600}]
    assert tiergate.tier_for_cost(bounded, 0.5) == 0
    assert tiergate.tier_for_cost(bounded, 3600) == 1
    assert tiergate.tier_for_cost(bounded, 10**9) == 1
