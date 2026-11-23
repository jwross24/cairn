from contextlib import contextmanager

from cairn import justify, justify_lattice

OWNERS = (justify, justify_lattice)


@contextmanager
def _swap(name, replacement):
    originals = [(owner, getattr(owner, name)) for owner in OWNERS]
    for owner, _ in originals:
        setattr(owner, name, replacement)
    try:
        yield
    finally:
        for owner, original in originals:
            setattr(owner, name, original)


@contextmanager
def comparator_strict_containment():
    def contains(outer, inner):
        wide, narrow = justify._interval(outer), justify._interval(inner)
        if wide is None or narrow is None or wide[0] > wide[1] or narrow[0] > narrow[1]:
            return False
        return wide[0] < narrow[0] and wide[1] > narrow[1]

    with _swap("contains", contains):
        yield


@contextmanager
def comparator_checks_lo_only():
    def contains(outer, inner):
        wide, narrow = justify._interval(outer), justify._interval(inner)
        if wide is None or narrow is None or wide[0] > wide[1] or narrow[0] > narrow[1]:
            return False
        return wide[0] <= narrow[0]

    with _swap("contains", contains):
        yield


@contextmanager
def comparator_assumptions_superset():
    def subset(inner, outer):
        small, big = justify._as_set(inner), justify._as_set(outer)
        if small is None or big is None:
            return False
        return small >= big

    with _swap("subset", subset):
        yield


@contextmanager
def derive_takes_last_node():
    def strongest(results):
        return next(
            (pair for pair in reversed(list(results)) if isinstance(pair[1], justify.Justification)),
            None,
        )

    with _swap("strongest", strongest):
        yield


@contextmanager
def kind_table_off_by_one():
    table = {**justify.KIND_MAX_CLASS, "statistical": justify.PROVEN}
    with _swap("KIND_MAX_CLASS", table):
        yield


@contextmanager
def producer_rule_ignores_range():
    def cross_check_covers(cross_check, inputs):
        return justify.CrossCheckCoverage(isinstance(cross_check, (dict, list, tuple)), {}, {})

    with _swap("cross_check_covers", cross_check_covers):
        yield


ALL = {
    "comparator_strict_containment": comparator_strict_containment,
    "comparator_checks_lo_only": comparator_checks_lo_only,
    "comparator_assumptions_superset": comparator_assumptions_superset,
    "derive_takes_last_node": derive_takes_last_node,
    "kind_table_off_by_one": kind_table_off_by_one,
    "producer_rule_ignores_range": producer_rule_ignores_range,
}
