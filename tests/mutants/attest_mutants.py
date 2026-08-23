from contextlib import contextmanager

from cairn import attest
from cairn.substrate import blob_hash


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextmanager
def matches_any_record_with_digest():
    def scan(path, offset, digest):
        wanted = attest._normalize_digest(digest)
        return any(blob_hash(body) == wanted for _, body in attest.records(path))

    with _swap(attest, "attestation_record_matches", scan):
        yield


@contextmanager
def matches_digest_prefix():
    real = attest.read_record

    def prefix(path, offset, digest):
        wanted = attest._normalize_digest(digest)
        record = real(path, offset)
        return record is not None and bool(wanted) and blob_hash(record).startswith(wanted[:8])

    with _swap(attest, "attestation_record_matches", prefix):
        yield


@contextmanager
def matches_on_length_only():
    real = attest.read_record

    def by_length(path, offset, digest):
        wanted = attest._normalize_digest(digest)
        record = real(path, offset)
        if record is None:
            return False
        return any(len(body) == len(record) and blob_hash(body) == wanted for _, body in attest.records(path))

    with _swap(attest, "attestation_record_matches", by_length):
        yield
