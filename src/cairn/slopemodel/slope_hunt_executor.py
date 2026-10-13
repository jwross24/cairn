import json
import sys

from cairn.pari import pari
from cairn.slopemodel import slope_predicates, slopemodel_a

BINDING = ("statement_hash", "plan_hash", "run_id", "trial", "point", "seed", "input_blob_hash")


def main() -> None:
    document = json.load(sys.stdin)
    if "nonce" in document:
        raise SystemExit("the executor must never see the nonce")
    t = document["point"]["t"]
    if type(t) is not int or not 3 <= t <= slopemodel_a.MAX_L:
        raise ValueError(f"t must be an integer in [3, {slopemodel_a.MAX_L}]")
    ell = int(pari.nextprime(t))
    n = slope_predicates.step_size(ell)
    weight, last = slopemodel_a.weight(ell, n)
    output = {name: document[name] for name in BINDING}
    output.update(
        status="OK",
        reading=slopemodel_a.READING,
        n_rule=slope_predicates.N_RULE,
        l=ell,
        n=n,
        weight=weight,
        last_index=last,
        predicate=document["predicate"],
        candidate=not slope_predicates.holds(document["predicate"], ell, weight),
    )
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
