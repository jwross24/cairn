from fractions import Fraction
from math import ceil, floor, sqrt

FORMULAS = ("g_phase", "g_phase_no_strip", "g_phase_coeff")


def _validate_parameters(ell, n):
    if type(ell) is not int or ell < 3 or ell % 2 == 0:
        raise ValueError("l must be an odd integer at least 3")
    if type(n) is not int or n <= 0:
        raise ValueError("n must be a positive integer")
    if not 3 * n * n <= ell <= 4 * n * n:
        raise ValueError("formula requires 3*n*n <= l <= 4*n*n")


def _band_slice(u, b, s):
    lo = max(s - u, b - u / 2)
    hi = min(u, b)
    if hi <= lo:
        return Fraction(0)
    return ((hi + u - s) ** 2 - (lo + u - s) ** 2) / 2


def _strip_integral(ell, n):
    s = Fraction(ell, 2 * n)
    r = ((ell + 1) // 2) % n
    origin = s - r
    period = Fraction(n, 2)
    first = ceil((s - n - origin) / period)
    last = floor((Fraction(3 * n, 2) - origin) / period)
    lower, upper = s / 2, Fraction(n)
    total = Fraction(0)
    for k in range(first, last + 1):
        b = origin + k * period
        boundaries = {lower, upper}
        for boundary in (b, 2 * b / 3, s - b, 2 * (s - b)):
            if lower < boundary < upper:
                boundaries.add(boundary)
        ordered = sorted(boundaries)
        for index in range(len(ordered) - 1):
            left, right = ordered[index], ordered[index + 1]
            midpoint = (left + right) / 2
            total += (right - left) * (_band_slice(left, b, s)
                                      + 4 * _band_slice(midpoint, b, s)
                                      + _band_slice(right, b, s)) / 6
    return total


def scaled_prediction(ell, n, formula="g_phase"):
    _validate_parameters(ell, n)
    if formula not in FORMULAS:
        raise ValueError(f"unknown formula {formula!r}")
    coefficient = 46 if formula == "g_phase_coeff" else 45
    strip = Fraction(0) if formula == "g_phase_no_strip" else _strip_integral(ell, n)
    return (Fraction(3 * n * ell)
            - Fraction(coefficient * n**3, 16)
            + Fraction((ell - 2 * n**2)**3, 32 * n**3)
            + Fraction((ell - 3 * n**2)**2, 4 * n)
            + 3 * strip)


def g_phase(ell, n):
    return float(scaled_prediction(ell, n, "g_phase")) / (ell * sqrt(ell))


def g_phase_no_strip(ell, n):
    return float(scaled_prediction(ell, n, "g_phase_no_strip")) / (ell * sqrt(ell))


def g_phase_coeff(ell, n):
    return float(scaled_prediction(ell, n, "g_phase_coeff")) / (ell * sqrt(ell))


def exact_statement_holds(ell, n, total, tol_num, tol_den, formula="g_phase"):
    if type(total) is not int or total < 0:
        raise ValueError("W must be a nonnegative integer")
    if type(tol_num) is not int or tol_num < 0 or type(tol_den) is not int or tol_den <= 0:
        raise ValueError("tolerance numerator must be nonnegative and denominator positive integers")
    residual = abs(total - scaled_prediction(ell, n, formula))
    return residual**2 * tol_den**2 <= tol_num**2 * ell**3
