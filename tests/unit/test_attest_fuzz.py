import json
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cairn import attest
from cairn.substrate import blob_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mutants import attest_mutants

CORPUS = Path(__file__).resolve().parent.parent / "fuzz_corpus" / "attest"
INT64 = 2**63
offsets = st.integers(min_value=-INT64, max_value=INT64)
digests = st.binary(max_size=64)


def _framed(bodies):
    return b"".join(attest.frame(body) for body in bodies)


def _write(tmp_path, data, name="attestations.log"):
    path = tmp_path / name
    path.write_bytes(data)
    return path


@st.composite
def mutated_file(draw):
    bodies = draw(st.lists(st.binary(min_size=1, max_size=48), min_size=1, max_size=3))
    data = _framed(bodies)
    how = draw(st.sampled_from(["intact", "truncate_prefix", "length_beyond_end", "zero_length", "shift_one", "tail_noise"]))
    if how == "truncate_prefix":
        data += b"\x04\x00\x00"
    elif how == "length_beyond_end":
        data += (2**32).to_bytes(8, "little") + b"abc"
    elif how == "zero_length":
        data += (0).to_bytes(8, "little")
    elif how == "shift_one":
        data = b"\x00" + data
    elif how == "tail_noise":
        data += draw(st.binary(max_size=16))
    return data, bodies, how


@given(data=st.binary(max_size=256), offset=offsets, digest=digests)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_the_matcher_never_raises_an_unhandled_exception(tmp_path_factory, data, offset, digest):
    path = _write(tmp_path_factory.mktemp("fuzz"), data)
    try:
        result = attest.attestation_record_matches(path, offset, digest)
    except attest.AttestationError:
        return
    assert result is False or (result is True and blob_hash(attest.read_record(path, offset)) == digest.hex())


@given(mutation=mutated_file(), offset=offsets, digest=digests)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_true_only_on_an_exact_offset_and_digest(tmp_path_factory, mutation, offset, digest):
    data, bodies, _ = mutation
    path = _write(tmp_path_factory.mktemp("fuzz"), data)
    if attest.attestation_record_matches(path, offset, digest):
        record = attest.read_record(path, offset)
        assert record is not None and blob_hash(record) == digest.hex()


@given(mutation=mutated_file())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_each_record_matches_at_its_own_offset_and_nowhere_else(tmp_path_factory, mutation):
    data, bodies, how = mutation
    path = _write(tmp_path_factory.mktemp("fuzz"), data)
    shift = 1 if how == "shift_one" else 0
    offset = shift
    for body in bodies:
        digest = blob_hash(body)
        assert attest.attestation_record_matches(path, offset, digest)
        for wrong in (offset - 1, offset + 1, offset + 8):
            if wrong != offset:
                assert not attest.attestation_record_matches(path, wrong, digest) or attest.read_record(path, wrong) == body
        offset += attest.LENGTH_BYTES + len(body)


@given(digest=st.binary(max_size=64))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_a_bytes_digest_matches_only_when_it_is_the_exact_raw_digest(tmp_path_factory, digest):
    body = b"body"
    path = _write(tmp_path_factory.mktemp("fuzz"), _framed([body]))
    raw = bytes.fromhex(blob_hash(body))
    assert attest.attestation_record_matches(path, 0, raw)
    assert attest.attestation_record_matches(path, 0, digest) == (digest == raw)


@pytest.mark.parametrize("wrong_type", [None, 1.5, [], {}], ids=["none", "float", "list", "dict"])
def test_a_digest_of_the_wrong_type_raises_the_typed_error(tmp_path, wrong_type):
    path = _write(tmp_path, _framed([b"body"]))
    with pytest.raises(attest.AttestationError, match="digest must be bytes or a hex str"):
        attest.attestation_record_matches(path, 0, wrong_type)


@pytest.mark.parametrize("wrong_type", [None, 1.5, "0", True], ids=["none", "float", "str", "bool"])
def test_an_offset_of_the_wrong_type_raises_the_typed_error(tmp_path, wrong_type):
    path = _write(tmp_path, _framed([b"body"]))
    with pytest.raises(attest.AttestationError, match="offset must be an int"):
        attest.attestation_record_matches(path, wrong_type, blob_hash(b"body"))


def test_an_unreadable_file_raises_the_typed_error(tmp_path):
    with pytest.raises(attest.AttestationError, match="is unreadable"):
        attest.attestation_record_matches(tmp_path / "absent.log", 0, blob_hash(b"body"))


def _corpus_case(case):
    data = bytes.fromhex(case["raw_hex"]) if "raw_hex" in case else _framed([bytes.fromhex(r) for r in case["records"]])
    digest = case["digest_hex"] if "digest_hex" in case else blob_hash(bytes.fromhex(case["records"][case["digest_of_record"]]))
    return data, case["offset"], digest


@pytest.mark.parametrize("path", sorted(CORPUS.glob("*.json")), ids=lambda p: p.stem)
def test_seed_corpus_replays(tmp_path, path):
    case = json.loads(path.read_text())
    data, offset, digest = _corpus_case(case)
    file = _write(tmp_path, data)
    assert attest.attestation_record_matches(file, offset, digest) is case["expected"], case["why"]


@pytest.mark.parametrize(
    "mutant",
    ["matches_any_record_with_digest", "matches_digest_prefix", "matches_on_length_only"],
)
def test_planted_mutants_are_killed_by_the_seed_corpus(tmp_path, mutant):
    survivors = []
    for path in sorted(CORPUS.glob("*.json")):
        case = json.loads(path.read_text())
        data, offset, digest = _corpus_case(case)
        file = _write(tmp_path, data, name=f"{case['name']}.log")
        with getattr(attest_mutants, mutant)():
            observed = attest.attestation_record_matches(file, offset, digest)
        if observed == case["expected"]:
            survivors.append(case["name"])
    assert len(survivors) < len(list(CORPUS.glob("*.json"))), f"{mutant} survived the whole corpus"
