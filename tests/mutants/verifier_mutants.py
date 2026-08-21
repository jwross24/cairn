from contextlib import contextmanager

from cairn import verifier

XP_EQ_Q_CHECK = b"if(ellmul(E, P, x) != Q, "
XP_EQ_Q_LINE = b'  if(ellmul(E, P, x) != Q, print("FAIL ", ["xP-ne-Q"]); quit(1));\n'


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextmanager
def _script_variant(old, new):
    source = verifier.script_bytes()
    assert old in source
    mutated = source.replace(old, new)
    with _swap(verifier, "script_bytes", lambda: mutated):
        yield


def _rule_named(name, rule):
    return tuple((n, rule) if n == name else (n, r) for n, r in verifier.FIELD_RULES)


@contextmanager
def driver_reduces_x_mod_p():
    real = verifier.render_line

    def render(fields):
        f = tuple(fields)
        return real(f[:-1] + (f[-1] % f[0],))

    with _swap(verifier, "render_line", render):
        yield


@contextmanager
def validator_off_by_one_x_lt_n_minus_1():
    with _swap(verifier, "FIELD_RULES", _rule_named("x-lt-n", lambda p, a, b, n, Px, Py, Qx, Qy, x: x < n - 1)):
        yield


@contextmanager
def validator_skips_x_lt_n():
    with _swap(verifier, "FIELD_RULES", tuple((n, r) for n, r in verifier.FIELD_RULES if n != "x-lt-n")):
        yield


@contextmanager
def script_compares_x_coordinate_only():
    with _script_variant(XP_EQ_Q_CHECK, b"if(ellmul(E, P, x)[1] != Qx, "):
        yield


@contextmanager
def script_without_xP_eq_Q():
    with _script_variant(XP_EQ_Q_LINE, b""):
        yield


@contextmanager
def accept_rc0_only():
    with _swap(verifier.AcceptPredicate, "holds", lambda self, rc, stdout, stderr: rc == 0):
        yield


@contextmanager
def accept_if_OK_substring():
    with _swap(verifier.AcceptPredicate, "holds", lambda self, rc, stdout, stderr: isinstance(stdout, str) and "OK" in stdout):
        yield


ALL = {
    "driver_reduces_x_mod_p": driver_reduces_x_mod_p,
    "validator_off_by_one_x_lt_n_minus_1": validator_off_by_one_x_lt_n_minus_1,
    "validator_skips_x_lt_n": validator_skips_x_lt_n,
    "script_compares_x_coordinate_only": script_compares_x_coordinate_only,
    "script_without_xP_eq_Q": script_without_xP_eq_Q,
    "accept_rc0_only": accept_rc0_only,
    "accept_if_OK_substring": accept_if_OK_substring,
}
