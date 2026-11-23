from contextlib import contextmanager

from cairn import canon, claims, claims_schema


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


def _informal_only(stmt):
    return canon.encode(canon.STR, stmt.informal)


@contextmanager
def statement_hash_skips_scope():
    with (
        _swap(claims_schema, "claim_statement_canonical", _informal_only),
        _swap(claims, "claim_statement_canonical", _informal_only),
    ):
        yield


ALL = {"statement_hash_skips_scope": statement_hash_skips_scope}
