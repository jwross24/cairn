import json
import sys
from math import isqrt, sqrt

import formula_variants
from sweep_fast import weight, weight_chain_free

BINDING = ("statement_hash", "plan_hash", "run_id", "trial", "point", "seed", "input_blob_hash")
WITNESSES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
MAX_T = 2**36
KINDS = ("weight_le", "weight_ge", "weight_ge_counting_bound", "weight_ge_three_column_bound", "weight_within_formula")
FORMULAS = {
    "g_phase": formula_variants.g_phase,
    "g_phase_no_strip": formula_variants.g_phase_no_strip,
    "g_phase_coeff": formula_variants.g_phase_coeff,
}
SCHEDULES = {"bl2012-fitted-1": weight, "chain-free": weight_chain_free}


def is_prime(number: int) -> bool:
    if number < 2:
        return False
    for prime in WITNESSES:
        if number % prime == 0:
            return number == prime
    odd, powers = number - 1, 0
    while odd % 2 == 0:
        odd //= 2
        powers += 1
    for base in WITNESSES:
        residue = pow(base, odd, number)
        if residue in (1, number - 1):
            continue
        for _ in range(powers - 1):
            residue = residue * residue % number
            if residue == number - 1:
                break
        else:
            return False
    return True


def next_prime(start: int) -> int:
    number = start
    while not is_prime(number):
        number += 1
    return number


def counting_bound(ell: int) -> int:
    total = index = 0
    while (gap := ell - index * (index + 1) // 2) > 0:
        total += gap
        index += 1
    return total


def three_column_bound(ell: int) -> int:
    total = index = 0
    while (gap := ell - (index + 1) ** 2 // 3) > 0:
        total += gap
        index += 1
    return total


def integer_field(predicate: dict, name: str, minimum: int) -> int:
    value = predicate[name]
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def formula_function(predicate: dict):
    name = predicate["formula"]
    if type(name) is not str or name not in FORMULAS:
        raise ValueError(f"unknown formula {name!r}")
    return FORMULAS[name]


def validate_predicate(predicate: dict) -> None:
    if predicate["kind"] == "weight_within_formula":
        integer_field(predicate, "tol_num", 0)
        integer_field(predicate, "tol_den", 1)
        formula_function(predicate)


def formula_reading(predicate: dict, ell: int, total: int, n: int) -> dict:
    tol_num = integer_field(predicate, "tol_num", 0)
    tol_den = integer_field(predicate, "tol_den", 1)
    value = formula_function(predicate)(ell, n)
    return {
        "distance": tol_num / tol_den - abs(total / (ell * sqrt(ell)) - value),
        "formula_value": value,
    }


def predicate_holds(predicate: dict, ell: int, total: int, n: int) -> bool:
    kind = predicate["kind"]
    if kind == "weight_le" or kind == "weight_ge":
        num = integer_field(predicate, "num", 0)
        den = integer_field(predicate, "den", 1)
        scaled = (den * total) ** 2
        limit = num * num * ell**3
        return scaled <= limit if kind == "weight_le" else scaled >= limit
    if kind == "weight_ge_counting_bound":
        return total >= counting_bound(ell)
    if kind == "weight_ge_three_column_bound":
        return total >= three_column_bound(ell)
    if kind == "weight_within_formula":
        tol_num = integer_field(predicate, "tol_num", 0)
        tol_den = integer_field(predicate, "tol_den", 1)
        value = formula_function(predicate)(ell, n)
        return abs(total / (ell * sqrt(ell)) - value) <= tol_num / tol_den
    raise ValueError(f"unknown predicate kind {kind!r}")


def main() -> None:
    document = json.load(sys.stdin)
    if "nonce" in document:
        raise SystemExit("the executor must never see the nonce")
    t = document["point"]["t"]
    if type(t) is not int or not 3 <= t <= MAX_T:
        raise ValueError(f"t must be an integer in [3, {MAX_T}]")
    predicate = document["predicate"]
    n_milli = predicate["n_milli"]
    if type(n_milli) is not int or not 100 <= n_milli <= 2000:
        raise ValueError("n_milli must be an integer in [100, 2000]")
    if predicate["kind"] not in KINDS:
        raise ValueError(f"unknown predicate kind {predicate['kind']!r}")
    schedule = predicate["schedule"]
    if schedule not in SCHEDULES:
        raise ValueError(f"unknown schedule {schedule!r}")
    validate_predicate(predicate)
    ell = next_prime(t)
    n = (n_milli * isqrt(ell) + 500) // 1000
    total, last = SCHEDULES[schedule](ell, n)
    output = {name: document[name] for name in BINDING}
    output.update(
        status="OK",
        reading=schedule,
        n_rule=f"n = ({n_milli} * isqrt(l) + 500) // 1000",
        l=ell,
        n=n,
        weight=total,
        last_index=last,
        predicate=predicate,
        candidate=not predicate_holds(predicate, ell, total, n),
    )
    if predicate["kind"] == "weight_within_formula":
        output.update(formula_reading(predicate, ell, total, n))
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
