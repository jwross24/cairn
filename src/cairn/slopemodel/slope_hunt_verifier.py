import json
import sys
from math import isqrt

from cairn.slopemodel import slopemodel_b

BINDING = ("statement_hash", "plan_hash", "run_id", "trial", "point", "seed", "input_blob_hash")


def step_size(ell: int) -> int:
    if type(ell) is not int or ell < 1:
        raise ValueError("l must be a positive integer")
    return (isqrt(ell) * 564 + 500) // 1000


def counting_bound_closed_form(ell: int) -> int:
    if type(ell) is not int or ell < 1:
        raise ValueError("l must be a positive integer")
    k = (isqrt(8 * ell + 1) - 1) // 2
    while k * (k + 1) // 2 >= ell:
        k -= 1
    while (k + 1) * (k + 2) // 2 < ell:
        k += 1
    return (k + 1) * ell - k * (k + 1) * (k + 2) // 6


def statement_fails(predicate: dict, ell: int, weight: int) -> bool:
    if type(ell) is not int or ell < 1 or type(weight) is not int or weight < 0:
        raise ValueError("l must be positive and weight nonnegative integers")
    kind = predicate["kind"]
    if kind == "weight_le":
        numerator, denominator = predicate["num"], predicate["den"]
        if type(numerator) is not int or numerator < 0 or type(denominator) is not int or denominator < 1:
            raise ValueError("num must be nonnegative and den positive integers")
        return denominator * weight > isqrt(numerator**2 * ell**3)
    if kind == "weight_ge_counting_bound":
        return weight < counting_bound_closed_form(ell)
    raise ValueError(f"unknown predicate kind {kind!r}")


def main() -> None:
    document = json.load(sys.stdin)
    if "nonce" in document:
        raise SystemExit("the verifier must never see the nonce")
    ell = slopemodel_b.next_prime(document["point"]["t"])
    n = step_size(ell)
    weight, last = slopemodel_b.weight(ell, n)
    output = {name: document[name] for name in BINDING}
    output.update(
        status="OK",
        executor_output_digest=document["executor_output_digest"],
        l=ell,
        n=n,
        weight=weight,
        last_index=last,
        counterexample_valid=statement_fails(document["predicate"], ell, weight),
    )
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
