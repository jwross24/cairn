from contextlib import contextmanager

from cairn import tiergate


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextmanager
def short_circuit_gate():
    real = tiergate.predicate_reasons

    def first_only(**facts):
        reasons = real(**facts)
        return reasons[:1]

    with _swap(tiergate, "predicate_reasons", first_only):
        yield


@contextmanager
def reasons_unordered():
    real = tiergate.predicate_reasons

    def reversed_order(**facts):
        return tuple(reversed(real(**facts)))

    with _swap(tiergate, "predicate_reasons", reversed_order):
        yield
