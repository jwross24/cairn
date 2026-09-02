"""Gate-side verifier for a Pollard rho witness: two triples on one point.

A witness is graded AuditOnly when its only verifier ships in its producer's own
revision, so this module lives beside the Tier-0 verifier and outside every
skill's IDENTITY_SOURCES, and its arithmetic is libpari's rather than the
producer's pure-Python walk. The check is the one the ladder reads: aP + bQ = X
and cP + dQ = X, b != d (mod n) refused outright rather than retried, then
x = (a - c)(d - b)^-1 mod n and xP = Q.
"""

import re
import time
from dataclasses import dataclass

from cairn import keys, log, pari

BAD_FIELD = "bad-field"
P_OFF_CURVE = "P-off-curve"
Q_OFF_CURVE = "Q-off-curve"
X_OFF_CURVE = "X-off-curve"
FIRST_TRIPLE_NE_X = "first-triple-ne-X"
SECOND_TRIPLE_NE_X = "second-triple-ne-X"
B_EQ_D = "b-eq-d"
D_MINUS_B_NOT_INVERTIBLE = "d-minus-b-not-invertible"
XP_NE_Q = "xP-ne-Q"
REASONS = (
    BAD_FIELD,
    P_OFF_CURVE,
    Q_OFF_CURVE,
    X_OFF_CURVE,
    FIRST_TRIPLE_NE_X,
    SECOND_TRIPLE_NE_X,
    B_EQ_D,
    D_MINUS_B_NOT_INVERTIBLE,
    XP_NE_Q,
)
SCALAR_FIELDS = ("p", "a", "b", "n")
POINT_FIELDS = ("P", "Q", "X")
PAIR_FIELDS = ("first", "second")
LOG_STEP = "witness"
DECIMAL = re.compile(r"-?[0-9]+")


@dataclass(frozen=True)
class WitnessVerdict:
    accepted: bool
    reason: str | None
    x: int | None
    instance_hash: str | None
    wall_s: float

    def node(self):
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "x": self.x,
            "instance_hash": self.instance_hash,
            "wall_s": self.wall_s,
        }


class WitnessFieldError(ValueError):
    pass


def _int(name, value):
    if isinstance(value, bool):
        raise WitnessFieldError(f"{name} is a bool")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and DECIMAL.fullmatch(value.strip()):
        return int(value)
    raise WitnessFieldError(f"{name} is not an integer: {value!r}")


def _pair(name, value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise WitnessFieldError(f"{name} is not a pair: {value!r}")
    return _int(f"{name}[0]", value[0]), _int(f"{name}[1]", value[1])


def parse(witness):
    if not isinstance(witness, dict):
        raise WitnessFieldError(f"witness is not a mapping: {type(witness).__name__}")
    fields = {}
    for name in SCALAR_FIELDS:
        if name not in witness:
            raise WitnessFieldError(f"witness lacks {name}")
        fields[name] = _int(name, witness[name])
    for name in POINT_FIELDS + PAIR_FIELDS:
        if name not in witness:
            raise WitnessFieldError(f"witness lacks {name}")
        fields[name] = _pair(name, witness[name])
    if fields["p"] < 5 or fields["n"] < 2:
        raise WitnessFieldError(f"p = {fields['p']}, n = {fields['n']} do not describe a prime-order toy curve")
    for name in SCALAR_FIELDS[1:3]:
        if not 0 <= fields[name] < fields["p"]:
            raise WitnessFieldError(f"{name} = {fields[name]} is not reduced mod p")
    for name in POINT_FIELDS:
        if not all(0 <= c < fields["p"] for c in fields[name]):
            raise WitnessFieldError(f"{name} = {list(fields[name])} has a coordinate outside [0, p)")
    return fields


def _lift(point):
    if len(point) == 1:
        return None
    return tuple(int(c.lift()) for c in point)


def _combine(E, P, Q, pair):
    return _lift(pari.pari.elladd(E, pari.pari.ellmul(E, list(P), pair[0]), pari.pari.ellmul(E, list(Q), pair[1])))


class WitnessVerifier:
    def __init__(self):
        self._log = log.get(LOG_STEP)

    def verify(self, witness):
        start = time.monotonic()
        try:
            f = parse(witness)
        except WitnessFieldError as exc:
            return self._verdict(False, BAD_FIELD, None, None, start, detail=str(exc))
        instance_hash = keys.instance_hash(
            {"p": f["p"], "a": f["a"], "b": f["b"], "n": f["n"], "P": list(f["P"]), "Q": list(f["Q"])}
        )
        E = pari.pari.ellinit([f["a"], f["b"]], f["p"])
        for name, reason in (("P", P_OFF_CURVE), ("Q", Q_OFF_CURVE), ("X", X_OFF_CURVE)):
            if not bool(pari.pari.ellisoncurve(E, list(f[name]))):
                return self._verdict(False, reason, None, instance_hash, start)
        if _combine(E, f["P"], f["Q"], f["first"]) != f["X"]:
            return self._verdict(False, FIRST_TRIPLE_NE_X, None, instance_hash, start)
        if _combine(E, f["P"], f["Q"], f["second"]) != f["X"]:
            return self._verdict(False, SECOND_TRIPLE_NE_X, None, instance_hash, start)
        n = f["n"]
        (a, b), (c, d) = f["first"], f["second"]
        delta = (d - b) % n
        if delta == 0:
            return self._verdict(False, B_EQ_D, None, instance_hash, start)
        try:
            inverse = pow(delta, -1, n)
        except ValueError:
            return self._verdict(False, D_MINUS_B_NOT_INVERTIBLE, None, instance_hash, start)
        x = ((a - c) * inverse) % n
        if _lift(pari.pari.ellmul(E, list(f["P"]), x)) != f["Q"]:
            return self._verdict(False, XP_NE_Q, x, instance_hash, start)
        return self._verdict(True, None, x, instance_hash, start)

    def _verdict(self, accepted, reason, x, instance_hash, start, *, detail=None):
        result = WitnessVerdict(accepted, reason, x, instance_hash, round(time.monotonic() - start, 6))
        self._log.info(
            "verdict",
            instance_hash=instance_hash,
            accepted=accepted,
            reason=reason,
            detail=detail,
            wall_ms=round(result.wall_s * 1000, 3),
        )
        return result


def verify(witness):
    return WitnessVerifier().verify(witness)


def witness_from_output(document):
    """The verifier's input, projected from a rho_dp output document (wire or in-process)."""
    return {
        "p": document["p"],
        "a": document["a"],
        "b": document["b"],
        "n": document["n"],
        "P": document["P"],
        "Q": document["Q"],
        "X": document["witness"]["X"],
        "first": document["witness"]["first"],
        "second": document["witness"]["second"],
    }
