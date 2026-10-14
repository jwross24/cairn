import json
import sys
from math import isqrt

from fast_weight import weight, weight_chain_free

BINDING = ("statement_hash", "plan_hash", "run_id", "trial", "point", "seed", "input_blob_hash")
MR_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
MAX_T = 2**36


def is_prime(number):
    if number < 2:
        return False
    for divisor in MR_BASES:
        if number % divisor == 0:
            return number == divisor
    odd = number - 1
    powers = 0
    while odd % 2 == 0:
        odd //= 2
        powers += 1
    for base in MR_BASES:
        value = pow(base, odd, number)
        if value == 1 or value == number - 1:
            continue
        for _ in range(powers - 1):
            value = value * value % number
            if value == number - 1:
                break
        else:
            return False
    return True


def next_prime(t):
    if type(t) is not int or not 3 <= t <= MAX_T:
        raise ValueError(f"t must be an integer in [3, {MAX_T}]")
    candidate = t if t % 2 else t + 1
    while not is_prime(candidate):
        candidate += 2
    return candidate


def step_size(ell, n_milli):
    if type(ell) is not int or ell < 3:
        raise ValueError("l must be an integer at least 3")
    if type(n_milli) is not int or not 100 <= n_milli <= 2000:
        raise ValueError("n_milli must be an integer in [100, 2000]")
    return (n_milli * isqrt(ell) + 500) // 1000


def counting_bound_closed_form(ell):
    if type(ell) is not int or ell < 1:
        raise ValueError("l must be a positive integer")
    k = (isqrt(8 * ell - 7) - 1) // 2
    return (k + 1) * ell - k * (k + 1) * (k + 2) // 6


def three_column_bound_closed_form(ell):
    if type(ell) is not int or ell < 1:
        raise ValueError("l must be a positive integer")
    m = isqrt(3 * ell - 1)
    squares = m * (m + 1) * (2 * m + 1) // 6
    nonmultiples = m - m // 3
    return m * ell - (squares - nonmultiples) // 3


def three_column_bound_loop(ell):
    if type(ell) is not int or ell < 1:
        raise ValueError("l must be a positive integer")
    total = 0
    j = 1
    while True:
        term = ell - j * j // 3
        if term <= 0:
            return total
        total += term
        j += 1


def statement_fails(predicate, ell, total):
    if type(ell) is not int or ell < 1 or type(total) is not int or total < 0:
        raise ValueError("l must be positive and weight nonnegative integers")
    kind = predicate["kind"]
    if kind == "weight_ge_counting_bound":
        return total < counting_bound_closed_form(ell)
    if kind == "weight_ge_three_column_bound":
        return total < three_column_bound_closed_form(ell)
    if kind not in ("weight_le", "weight_ge"):
        raise ValueError(f"unknown predicate kind {kind!r}")
    numerator = predicate["num"]
    denominator = predicate["den"]
    if type(numerator) is not int or numerator < 0 or type(denominator) is not int or denominator < 1:
        raise ValueError("num must be nonnegative and den positive integers")
    scaled_weight = (denominator * total) ** 2
    threshold = numerator**2 * ell**3
    if kind == "weight_le":
        return scaled_weight > threshold
    return scaled_weight < threshold


def verify_document(document):
    if "nonce" in document:
        raise SystemExit("the verifier must never see the nonce")
    predicate = document["predicate"]
    schedule = predicate["schedule"]
    if schedule == "bl2012-fitted-1":
        evaluator = weight
    elif schedule == "chain-free":
        evaluator = weight_chain_free
    else:
        raise ValueError(f"unknown schedule {schedule!r}")
    ell = next_prime(document["point"]["t"])
    n = step_size(ell, predicate["n_milli"])
    total, last = evaluator(ell, n)
    output = {name: document[name] for name in BINDING}
    output.update(
        status="OK",
        executor_output_digest=document["executor_output_digest"],
        l=ell,
        n=n,
        weight=total,
        last_index=last,
        counterexample_valid=statement_fails(predicate, ell, total),
    )
    return output


def main():
    print(json.dumps(verify_document(json.load(sys.stdin)), sort_keys=True))


if __name__ == "__main__":
    main()
