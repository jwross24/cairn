from contextlib import contextmanager

from cairn import selftest


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextmanager
def schema_checks_first_case_only():
    with _swap(selftest, "_cases_to_check", lambda cases: list(enumerate(cases))[:1]):
        yield


@contextmanager
def floor_not_validated():
    with _swap(selftest, "_check_floor", lambda floor, count: None):
        yield


ALL = {
    "schema_checks_first_case_only": schema_checks_first_case_only,
    "floor_not_validated": floor_not_validated,
}
