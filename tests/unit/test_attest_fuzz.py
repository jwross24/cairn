import fcntl
import json
import os
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


@given(bodies=st.lists(st.binary(max_size=16384), min_size=2, max_size=4, unique=True))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_appended_records_match_only_their_own_frame_offsets(tmp_path_factory, bodies):
    path = tmp_path_factory.mktemp("append") / "attestations.log"
    offsets = [attest.append_record(path, body) for body in bodies]
    assert list(attest.records(path)) == list(zip(offsets, bodies, strict=True))
    assert path.read_bytes() == _framed(bodies)
    for index, body in enumerate(bodies):
        for other, offset in enumerate(offsets):
            assert attest.attestation_record_matches(path, offset, blob_hash(body)) == (index == other)


@pytest.mark.parametrize("failure", [None, "write", "flush", "no_progress"])
def test_append_holds_lock_through_short_writes_and_flush_and_releases_on_failure(
    tmp_path, monkeypatch, caplog, failure
):
    path = _write(tmp_path, b"")
    original_open = Path.open
    opened_files = []
    events = []

    class ShortWriteFile:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.file.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self.file, name)

        def assert_locked(self):
            with original_open(path, "ab", buffering=0) as contender, pytest.raises(BlockingIOError):
                fcntl.flock(contender.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        def seek(self, *args):
            self.assert_locked()
            events.append("seek")
            return self.file.seek(*args)

        def tell(self):
            self.assert_locked()
            events.append("tell")
            return self.file.tell()

        def write(self, data):
            self.assert_locked()
            events.append("write")
            if failure == "write":
                raise OSError("injected write failure")
            if failure == "no_progress":
                return 0
            return self.file.write(data[:3])

        def flush(self):
            self.assert_locked()
            events.append("flush")
            if failure == "flush":
                raise OSError("injected flush failure")
            return self.file.flush()

    def opened(self, *args, **kwargs):
        file = original_open(self, *args, **kwargs)
        if self == path and args and args[0] == "ab":
            assert kwargs["buffering"] == 0
            opened_files.append(file)
            return ShortWriteFile(file)
        return file

    monkeypatch.setattr(Path, "open", opened)
    if failure:
        message = "made no progress" if failure == "no_progress" else f"injected {failure} failure"
        with pytest.raises(OSError, match=message):
            attest.append_record(path, b"body")
        assert not any(record.getMessage() == "append" for record in caplog.records)
    else:
        assert attest.append_record(path, b"body") == 0
        assert events == ["seek", "tell", "write", "write", "write", "write", "flush"]
        assert path.read_bytes() == attest.frame(b"body")
    assert opened_files[0].closed
    with original_open(path, "ab") as contender:
        fcntl.flock(contender.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(contender.fileno(), fcntl.LOCK_UN)


def test_lock_acquisition_failure_closes_file_without_appending_or_reporting_success(tmp_path, monkeypatch, caplog):
    path = _write(tmp_path, b"")
    descriptors = []

    def refused(fd, operation):
        assert operation == fcntl.LOCK_EX
        descriptors.append(fd)
        raise OSError("injected lock failure")

    monkeypatch.setattr(attest.fcntl, "flock", refused)
    with pytest.raises(OSError, match="injected lock failure"):
        attest.append_record(path, b"body")
    assert path.read_bytes() == b""
    assert not any(record.getMessage() == "append" for record in caplog.records)
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(descriptors[0])


@st.composite
def mutated_file(draw):
    bodies = draw(st.lists(st.binary(min_size=1, max_size=48), min_size=1, max_size=3))
    data = _framed(bodies)
    how = draw(
        st.sampled_from(["intact", "truncate_prefix", "length_beyond_end", "zero_length", "shift_one", "tail_noise"])
    )
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
                assert (
                    not attest.attestation_record_matches(path, wrong, digest)
                    or attest.read_record(path, wrong) == body
                )
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
    digest = (
        case["digest_hex"]
        if "digest_hex" in case
        else blob_hash(bytes.fromhex(case["records"][case["digest_of_record"]]))
    )
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
