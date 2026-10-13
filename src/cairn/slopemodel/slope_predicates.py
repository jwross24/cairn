from math import isqrt

N_RULE = "n = (564 * isqrt(l) + 500) // 1000"


def step_size(ell: int) -> int:
    if type(ell) is not int or ell <= 0:
        raise ValueError("l must be a positive integer")
    return (564 * isqrt(ell) + 500) // 1000


def counting_bound(ell: int) -> int:
    if type(ell) is not int or ell <= 0:
        raise ValueError("l must be a positive integer")
    total = index = 0
    while (gap := ell - index * (index + 1) // 2) > 0:
        total += gap
        index += 1
    return total


def holds(predicate: dict, ell: int, weight: int) -> bool:
    if type(ell) is not int or ell <= 0 or type(weight) is not int or weight < 0:
        raise ValueError("l must be positive and weight nonnegative integers")
    kind = predicate["kind"]
    if kind == "weight_le":
        num, den = predicate["num"], predicate["den"]
        if type(num) is not int or num < 0 or type(den) is not int or den <= 0:
            raise ValueError("num must be nonnegative and den positive integers")
        return (den * weight) ** 2 <= num * num * ell**3
    if kind == "weight_ge_counting_bound":
        return weight >= counting_bound(ell)
    raise ValueError(f"unknown predicate kind {kind!r}")
