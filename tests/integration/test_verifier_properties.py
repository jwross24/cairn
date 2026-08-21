import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis import strategies as st

from cairn import pari, verifier
from cairn.verifier import Instance, Verifier

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _ec  # noqa: E402
from mutants import verifier_mutants  # noqa: E402

CURVE60 = _ec.curve60()
CURVES = {"curve60": CURVE60, "GF101": _ec.CORPUS_2}
GP_EXAMPLES = 40
P_PLUS_1 = CURVE60["p"] + 1
gp_settings = settings(max_examples=GP_EXAMPLES, deadline=None)
perm_settings = settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])


def _ok(inst, x):
    result = Verifier().run(inst, x)
    assert result.accepted is True, (result.reason, x)


def _fails(inst, x, reason):
    result = Verifier().run(inst, x)
    assert (result.accepted, result.reason) == (False, reason), (result.accepted, result.reason, x)


def check_mr_s(c, x, k):
    inst, _ = _ec.pair(c, x)
    _ok(inst, x)
    _ok(_ec.instance(c, _ec.mul(c, inst.Q, k)), (k * x) % c["n"])


def check_mr_n(c, x):
    inst, _ = _ec.pair(c, x)
    _ok(inst, x)
    _ok(_ec.instance(c, _ec.neg(c, inst.Q)), c["n"] - x)


def check_mr_q_prime(c, x, Q_prime):
    inst, _ = _ec.pair(c, x)
    assert Q_prime != inst.Q
    _ok(inst, x)
    _fails(_ec.instance(c, Q_prime), x, "xP-ne-Q")


def check_mr_s_n_composite(c, x, k):
    inst, _ = _ec.pair(c, x)
    _ok(inst, x)
    kQ = _ec.mul(c, inst.Q, k)
    _ok(_ec.instance(c, _ec.neg(c, kQ)), (c["n"] - (k * x) % c["n"]) % c["n"])


def _breaks_pre_spawn_rules(fields):
    p, a, b, n, Px, Py, Qx, Qy, x = fields
    return not (x < n and p > 3 and all(0 <= v < p for v in (a, b, Px, Py, Qx, Qy)) and (n - p - 1) ** 2 <= 4 * p)


def check_mr_perm(base_fields, permuted, spy):
    assert _breaks_pre_spawn_rules(permuted)
    before = len(spy)
    result = Verifier().run_fields(permuted)
    assert (result.accepted, result.reason, result.gate_result) == (False, "bad-field", "refused"), (result.reason, permuted)
    assert len(spy) == before


@pytest.mark.parametrize("name", sorted(CURVES))
@gp_settings
@given(st.data())
def test_mr_s_scalar_multiplication(name, data):
    c = CURVES[name]
    x = data.draw(st.integers(1, c["n"] - 1), label="x")
    k = data.draw(st.integers(1, c["n"] - 1), label="k")
    check_mr_s(c, x, k)


def test_mr_s_cell_p_plus_1_on_curve60():
    assert CURVE60["p"] < P_PLUS_1 < CURVE60["n"]
    check_mr_s(CURVE60, 1, P_PLUS_1)


def test_mutant_driver_reduces_x_mod_p_is_killed_by_mr_s():
    check_mr_s(CURVE60, 1, P_PLUS_1)
    with verifier_mutants.driver_reduces_x_mod_p(), pytest.raises(AssertionError):
        check_mr_s(CURVE60, 1, P_PLUS_1)


@pytest.mark.parametrize("name", sorted(CURVES))
@gp_settings
@given(st.data())
def test_mr_n_negation(name, data):
    c = CURVES[name]
    x = data.draw(st.integers(1, c["n"] - 1), label="x")
    check_mr_n(c, x)


def test_mutant_validator_off_by_one_x_lt_n_minus_1_is_killed_by_mr_n():
    check_mr_n(CURVE60, 1)
    with verifier_mutants.validator_off_by_one_x_lt_n_minus_1(), pytest.raises(AssertionError):
        check_mr_n(CURVE60, 1)


@pytest.mark.parametrize("name", sorted(CURVES))
@gp_settings
@given(st.data())
def test_mr_q_prime_point_perturbation(name, data):
    c = CURVES[name]
    x = data.draw(st.integers(1, c["n"] - 1), label="x")
    j = data.draw(st.integers(1, c["n"] - 1).filter(lambda j: j != x), label="j")
    check_mr_q_prime(c, x, _ec.mul(c, c["P"], j))


@pytest.mark.parametrize("name", sorted(CURVES))
def test_mr_q_prime_example_negated_q(name):
    c = CURVES[name]
    inst, x = _ec.pair(c, 2)
    minus_q = _ec.neg(c, inst.Q)
    assert minus_q != inst.Q
    check_mr_q_prime(c, x, minus_q)


def test_mutant_script_compares_x_coordinate_only_is_killed_by_mr_q_prime():
    inst, x = _ec.pair(CURVE60, 2)
    minus_q = _ec.neg(CURVE60, inst.Q)
    check_mr_q_prime(CURVE60, x, minus_q)
    with verifier_mutants.script_compares_x_coordinate_only(), pytest.raises(AssertionError):
        check_mr_q_prime(CURVE60, x, minus_q)


def test_mutant_script_without_xP_eq_Q_is_killed_by_mr_q_prime():
    other = _ec.mul(CURVE60, CURVE60["P"], 7)
    check_mr_q_prime(CURVE60, 2, other)
    with verifier_mutants.script_without_xP_eq_Q(), pytest.raises(AssertionError):
        check_mr_q_prime(CURVE60, 2, other)


@pytest.mark.parametrize("name", sorted(CURVES))
@gp_settings
@given(st.data())
def test_mr_s_n_composite(name, data):
    c = CURVES[name]
    x = data.draw(st.integers(1, c["n"] - 1), label="x")
    k = data.draw(st.integers(1, c["n"] - 1), label="k")
    check_mr_s_n_composite(c, x, k)


@st.composite
def distinguishable_permutations(draw):
    x = draw(st.integers(1, CURVE60["n"] - 1))
    inst, _ = _ec.pair(CURVE60, x)
    base = inst.fields(x)
    order = draw(st.permutations(range(verifier.ARITY)))
    assume(list(order) != list(range(verifier.ARITY)))
    permuted = tuple(base[i] for i in order)
    assume(_breaks_pre_spawn_rules(permuted))
    return base, permuted


def _n_x_swap_example():
    inst, _ = _ec.pair(CURVE60, P_PLUS_1)
    base = inst.fields(P_PLUS_1)
    swapped = base[:3] + (base[8],) + base[4:8] + (base[3],)
    return base, swapped


@perm_settings
@given(distinguishable_permutations())
@example(_n_x_swap_example())
def test_mr_perm_field_permutation_is_refused_pre_spawn(run_gp_spy, case):
    base, permuted = case
    check_mr_perm(base, permuted, run_gp_spy)


def test_n_x_swap_example_is_refused_only_by_x_lt_n():
    base, swapped = _n_x_swap_example()
    p, a, b, n, Px, Py, Qx, Qy, x = swapped
    assert (n, x) == (P_PLUS_1, CURVE60["n"])
    assert p > 3 and all(0 <= v < p for v in (a, b, Px, Py, Qx, Qy)) and (n - p - 1) ** 2 <= 4 * p
    assert not x < n


def test_mutant_validator_skips_x_lt_n_is_killed_by_mr_perm(run_gp_spy):
    base, swapped = _n_x_swap_example()
    check_mr_perm(base, swapped, run_gp_spy)
    with verifier_mutants.validator_skips_x_lt_n(), pytest.raises(AssertionError):
        check_mr_perm(base, swapped, run_gp_spy)
    assert run_gp_spy and run_gp_spy[-1]["args"][0].endswith("/verify.gp")
    assert run_gp_spy[-1]["stdin"] == verifier.render_line(swapped)


def test_every_named_mutant_is_listed():
    assert set(verifier_mutants.ALL) >= {
        "driver_reduces_x_mod_p",
        "validator_off_by_one_x_lt_n_minus_1",
        "script_compares_x_coordinate_only",
        "script_without_xP_eq_Q",
        "validator_skips_x_lt_n",
    }
    assert pari.GP_BIN == Verifier().config.backend_path
