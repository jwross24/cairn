from math import sqrt

import formula


def g_phase(ell: int, n: int) -> float:
    return formula.g_phase_for(ell, n)


def g_phase_no_strip(ell: int, n: int) -> float:
    a = n / sqrt(ell)
    formula.check_range(a)
    return formula.g_without_strip(a)


def g_phase_coeff(ell: int, n: int) -> float:
    a = n / sqrt(ell)
    return g_phase(ell, n) - a**3 / 16
