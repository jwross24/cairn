from contextlib import contextmanager

from cairn import pari
from cairn.skills import toy_curve


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextmanager
def composite_n_skill():
    with _swap(toy_curve, "_order_is_prime", lambda n: True):
        yield


@contextmanager
def unpinned_sequence_skill():
    def settle(bits, E, curve):
        P = toy_curve._draw_point(E)
        confirm = toy_curve._confirm_order(bits, E, curve)
        return confirm, P

    with _swap(toy_curve, "_settle", settle):
        yield


@contextmanager
def cross_check_in_loop_skill():
    real = toy_curve._count_order

    def count_order(bits, E):
        m, call = real(bits, E)
        pari.ellsea(E)
        return m, call

    with _swap(toy_curve, "_count_order", count_order):
        yield


ALL = {
    "composite_n_skill": composite_n_skill,
    "unpinned_sequence_skill": unpinned_sequence_skill,
    "cross_check_in_loop_skill": cross_check_in_loop_skill,
}
