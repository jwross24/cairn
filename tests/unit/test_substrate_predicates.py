import blake3
import pytest
from hypothesis import given
from hypothesis import strategies as st

from cairn import substrate

hexdigest = st.binary(min_size=32, max_size=32).map(bytes.hex)


@pytest.mark.parametrize(
    ("from_grade", "to_grade", "weaker"),
    [
        ("Replayable", "Verifiable", True),
        ("Replayable", "AuditOnly", True),
        ("Verifiable", "AuditOnly", True),
        ("Verifiable", "Replayable", False),
        ("AuditOnly", "Verifiable", False),
        ("AuditOnly", "Replayable", False),
        ("Replayable", "Replayable", False),
        ("Verifiable", "Verifiable", False),
        ("AuditOnly", "AuditOnly", False),
    ],
)
def test_grade_weaker_follows_the_order(from_grade, to_grade, weaker):
    assert substrate.grade_weaker(from_grade, to_grade) is weaker


@pytest.mark.parametrize(
    ("status", "disowned_at", "inadmissible", "do_not_cache", "blobs_present", "reason"),
    [
        ("OK", None, 0, 0, True, None),
        ("OK", None, 0, 1, True, "do_not_cache"),
        ("FAIL", None, 0, 0, True, "status=FAIL"),
        ("RUNNING", None, 0, 0, True, "status=RUNNING"),
        ("OK", "2026-08-21", 0, 0, True, "disowned"),
        ("OK", None, 1, 0, True, "inadmissible"),
        ("OK", None, 0, 0, False, "missing_blob"),
    ],
)
def test_attempt_eligible_names_the_first_failing_predicate(
    status, disowned_at, inadmissible, do_not_cache, blobs_present, reason
):
    assert substrate.attempt_eligible(status, disowned_at, inadmissible, do_not_cache, blobs_present) == reason


@given(st.dictionaries(st.text(max_size=8), st.tuples(hexdigest, st.integers(0, 2**40)), max_size=4), st.data())
def test_output_manifest_hash_is_order_and_hex_bytes_invariant(artifacts, data):
    order = data.draw(st.permutations(list(artifacts)))
    permuted = {k: artifacts[k] for k in order}
    raw = {k: (bytes.fromhex(h), n) for k, (h, n) in artifacts.items()}
    assert (
        substrate.output_manifest_hash(permuted)
        == substrate.output_manifest_hash(artifacts)
        == substrate.output_manifest_hash(raw)
    )


def test_receipt_canonical_requires_every_field_and_fixes_float_spelling():
    receipt = {name: ("aa" * 32 if name.endswith(("hash", "digest")) else 1) for name in substrate.RECEIPT_FIELDS}
    assert substrate.receipt_hash(receipt) == substrate.receipt_hash({**receipt, "wall_s": 1.0})
    assert substrate.receipt_hash(receipt) != substrate.receipt_hash({**receipt, "wall_s": 1.5})
    with pytest.raises(substrate.SubstrateError, match="missing field"):
        substrate.receipt_canonical({k: v for k, v in receipt.items() if k != "exit_status"})


def test_blob_hash_is_plain_blake3():
    assert substrate.blob_hash(b"abc") == blake3.blake3(b"abc").hexdigest()
    assert substrate.blob_hash(bytearray(b"abc")) == substrate.blob_hash(b"abc")
