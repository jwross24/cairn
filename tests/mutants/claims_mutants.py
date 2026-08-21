from contextlib import contextmanager

from cairn import canon, claims


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextmanager
def statement_hash_skips_scope():
    with _swap(claims, "claim_statement_canonical", lambda stmt: canon.encode(canon.STR, stmt.informal)):
        yield


ALL = {"statement_hash_skips_scope": statement_hash_skips_scope}
