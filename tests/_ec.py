import json
from pathlib import Path

from cairn import pari
from cairn.verifier import Instance

VECTORS = Path(__file__).resolve().parent / "vectors"
CORPUS_1 = {"name": "F5", "p": 5, "a": -3, "b": 1, "n": 7, "P": (0, 1), "Q": (3, 3), "x": 3}
CORPUS_2 = {"name": "GF101", "p": 101, "a": 90, "b": 44, "n": 89, "P": (2, 38), "x": 2}


def curve60():
    v = json.loads((VECTORS / "curve60_seed1.json").read_text())
    return {
        "name": "curve60",
        "p": int(v["p"]),
        "a": int(v["a"]),
        "b": int(v["b"]),
        "n": int(v["n"]),
        "P": tuple(int(c) for c in v["P"]),
    }


# first (a, b) in row-major order over 1..399 with prime order and negative trace on nextprime(10**18)
def curve60_neg_trace():
    return {
        "name": "curve60_neg_trace",
        "p": 1000000000000000003,
        "a": 1,
        "b": 79,
        "n": 1000000001592367331,
        "P": (942394188664611951, 885954806630732808),
    }


def _curve(c):
    return pari.pari.ellinit([c["a"], c["b"]], c["p"])


def _lift(point):
    if len(point) == 1:
        return None
    return tuple(int(c.lift()) for c in point)


def mul(c, point, k):
    return _lift(pari.pari.ellmul(_curve(c), list(point), k))


def neg(c, point):
    return (point[0], (-point[1]) % c["p"])


def on_curve(c, point):
    return bool(pari.pari.ellisoncurve(_curve(c), list(point)))


def instance(c, Q):
    return Instance(c["p"], c["a"], c["b"], c["n"], tuple(c["P"]), tuple(Q))


def pair(c, x):
    return instance(c, mul(c, c["P"], x)), x


def breaks_pre_spawn_rules(fields):
    p, a, b, n, Px, Py, Qx, Qy, x = fields
    return not (x < n and p > 3 and all(0 <= v < p for v in (a, b, Px, Py, Qx, Qy)) and (n - p - 1) ** 2 <= 4 * p)
