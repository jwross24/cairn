"""Pollard rho with distinguished points on prime-order toy curves.

The ladder plan's baseline names plain rho: an r-adding walk with no negation
map, about 1.25 sqrt(n) group operations and O(1) memory. The negation-map
variant in this module is a claimant method with its own canonical parameter
(negation_map = true in the method identity), never the baseline: control (j)
of the M1 corpus measures its sqrt(2) on group operations against plain rho,
and a plan whose baseline field names the variant has no baseline left to
measure that control against. Promoting the variant is a deliberate plan
change, made in the plan and not here.

The walk definition is part of the output: the multipliers, the index function
and the distinguished-point predicate, so the witness is checkable from the
document alone. The witness stores the two colliding triples (X, a, b) and
(X, c, d) in full. Every draw comes from the input seed through BLAKE3, so two
runs on one input are byte-equal.

The second opinion on x is a BSGS solve at CROSS_CHECK_MAX_BITS and below,
where its table is a few thousand entries; at the ladder's rung sizes the
cross-check does not run and reports untested, so the rungs' memory column
measures the walk alone.
"""

import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import blake3

from cairn import canon, ec, env, keys, log, pari
from cairn.canon import BOOL, INT, STR, CanonError, Field, List, Map, Optional, Struct
from cairn.profile import CostProfile, Production, SizeCost, Verification

INTERFACE_VERSION = "rho_dp/1"
SEAM = "cairn.skills.bsgs.discrete_log"
CROSS_CHECK_AXIS = "algorithm"
CROSS_CHECK_MAX_BITS = 28
INDEPENDENT_RANGE = {"bits": [0, CROSS_CHECK_MAX_BITS]}
REPLAY_GRADE = "Verifiable"
DO_NOT_CACHE = False
REPO_ROOT = Path(__file__).resolve().parents[3]
IDENTITY_SOURCES = (
    "src/cairn/ec.py",
    "src/cairn/skills/rho_dp.py",
    "src/cairn/skills/rho_dp_corpus.json",
    "src/cairn/skills/bsgs.py",
)
STATUS_OK = "OK"
STATUS_DISAGREE = "DISAGREE"
LOG_STEP = "skill.rho_dp"
VARIANT_PLAIN = "plain"
VARIANT_NEGATION_MAP = "negation_map"
R = 32
INDEX_FUNCTION = "x mod r"
DP_PREDICATE = "x mod 2^theta_bits == 0"
CYCLE_WINDOW = 64
CAP_MULTIPLIER = 64
THETA_OFFSET = 10
COLLISION_DISTINGUISHED = "distinguished_point"
COLLISION_CYCLE_WINDOW = "cycle_window"
LABEL_MULTIPLIER_U = b"rho-dp/multiplier-u"
LABEL_MULTIPLIER_V = b"rho-dp/multiplier-v"
LABEL_START_ALPHA = b"rho-dp/start-alpha"
LABEL_START_BETA = b"rho-dp/start-beta"
PLAIN_CONSTANT = 1.2533
NEGATION_CONSTANT = 0.8862

COST_PROFILE = CostProfile(
    tier=1,
    production=Production(
        model="c_sqrt_n_ops",
        per_size={
            28: SizeCost(mean_tries=17108.2, sd_tries=10658.24, per_try_s=1.9364e-6, mean_wall_s=0.0331),
            30: SizeCost(mean_tries=37396.2, sd_tries=19210.17, per_try_s=0.7023e-6, mean_wall_s=0.0263),
            40: SizeCost(mean_tries=1130789.7, sd_tries=628392.24, per_try_s=2.0235e-6, mean_wall_s=2.2881),
            50: SizeCost(mean_tries=42652406.33, sd_tries=12984457.73, per_try_s=2.1805e-6, mean_wall_s=93.0025),
        },
    ),
    verification=Verification(grade=REPLAY_GRADE, cost_model="constant", core_s=0.005739),
    source="research/grounding/m1-dlp-skill-costs.md §1: cairn measure dlp --skill rho-dp --sizes 28,30,40 --seeds 10 and --sizes 50 --seeds 3, 2026-09-02, seeds 1..N per size, plain walk (STRONG-EMPIRICAL on the sample); the verification constant is the 50-bit witness check",
)

INPUTS = Struct(
    "rho_dp_inputs",
    [
        Field("bits", INT),
        Field("seed", INT),
        Field("p", INT),
        Field("a", INT),
        Field("b", INT),
        Field("n", INT),
        Field("P", List(INT)),
        Field("Q", List(INT)),
        Field("negation_map", BOOL),
    ],
)
TRANSCRIPT_BODY = Struct("dlp_transcript_body", [Field("call", STR), Field("curve", List(INT)), Field("result", INT)])
TRANSCRIPT = Struct(
    "dlp_transcript", [Field("call", STR), Field("curve", List(INT)), Field("result", INT), Field("digest", STR)]
)
CROSS_CHECK = Struct(
    "cross_check", [Field("axis", STR), Field("independent_range", Map(STR, List(INT))), Field("result", STR)]
)
WALK = Struct(
    "rho_walk",
    [
        Field("variant", STR),
        Field("r", INT),
        Field("index_function", STR),
        Field("dp_predicate", STR),
        Field("theta_bits", INT),
        Field("multipliers", List(List(INT))),
        Field("cycle_window", INT),
        Field("restarts", INT),
        Field("fruitless_escapes", INT),
        Field("lookahead_retries", INT),
    ],
)
WITNESS = Struct(
    "rho_witness",
    [Field("X", List(INT)), Field("first", List(INT)), Field("second", List(INT)), Field("collision", STR)],
)
OUTPUT = Struct(
    "rho_dp_output",
    [
        Field("bits", INT),
        Field("seed", INT),
        Field("p", INT),
        Field("a", INT),
        Field("b", INT),
        Field("n", INT),
        Field("P", List(INT)),
        Field("Q", List(INT)),
        Field("walk", WALK),
        Field("witness", WITNESS),
        Field("x", INT),
        Field("ops", INT),
        Field("setup_ops", INT),
        Field("distinguished_points", INT),
        Field("cross_check", CROSS_CHECK),
        Field("status", STR),
        Field("transcripts", Optional(List(TRANSCRIPT))),
    ],
)
BIG_FIELDS = ("p", "a", "b", "n", "x")
POINT_FIELDS = ("P", "Q")


class InputError(ValueError):
    pass


class WalkExhausted(RuntimeError):
    pass


class PostconditionFailed(AssertionError):
    def __init__(self, clause, detail):
        super().__init__(f"postcondition {clause} failed: {detail}")
        self.clause = clause


def theta_bits(bits):
    return max(0, bits // 2 - THETA_OFFSET)


def expected_ops(n, negation_map=False):
    constant = NEGATION_CONSTANT if negation_map else PLAIN_CONSTANT
    return max(8, int(constant * math.isqrt(n)))


def _draw(seed, label, counter, bound):
    material = canon.length_prefix(str(seed).encode("utf-8")) + canon.length_prefix(label) + counter.to_bytes(8, "big")
    value = int.from_bytes(blake3.blake3(material).digest(), "big")
    return value % (bound - 1) + 1


@dataclass(frozen=True)
class Walk:
    variant: str
    r: int
    theta_bits: int
    multipliers: tuple
    steps: tuple
    setup_ops: int

    def definition(self, restarts, escapes, retries):
        return {
            "variant": self.variant,
            "r": self.r,
            "index_function": INDEX_FUNCTION,
            "dp_predicate": DP_PREDICATE,
            "theta_bits": self.theta_bits,
            "multipliers": [list(pair) for pair in self.multipliers],
            "cycle_window": CYCLE_WINDOW if self.variant == VARIANT_NEGATION_MAP else 0,
            "restarts": restarts,
            "fruitless_escapes": escapes,
            "lookahead_retries": retries,
        }


def build_walk(p, a, n, P, Q, seed, bits, negation_map):
    multipliers = tuple(
        (_draw(seed, LABEL_MULTIPLIER_U, j, n), _draw(seed, LABEL_MULTIPLIER_V, j, n)) for j in range(R)
    )
    steps = []
    setup_ops = 0
    for u, v in multipliers:
        steps.append(ec.add(p, a, ec.mul(p, a, P, u), ec.mul(p, a, Q, v)))
        setup_ops += ec.mul_ops(u) + ec.mul_ops(v) + 1
    variant = VARIANT_NEGATION_MAP if negation_map else VARIANT_PLAIN
    return Walk(variant, R, theta_bits(bits), multipliers, tuple(steps), setup_ops)


@dataclass(frozen=True)
class Solution:
    x: int
    X: tuple
    first: tuple
    second: tuple
    collision: str
    ops: int
    setup_ops: int
    distinguished_points: int
    restarts: int
    fruitless_escapes: int
    lookahead_retries: int

    def witness(self):
        return {
            "X": list(self.X),
            "first": list(self.first),
            "second": list(self.second),
            "collision": self.collision,
        }


def _solve_from(prev, alpha, beta, n):
    return ((prev[0] - alpha) * pow((beta - prev[1]) % n, -1, n)) % n


def walk(p, a, n, P, Q, definition, seed):
    negation = definition.variant == VARIANT_NEGATION_MAP
    steps, multipliers = definition.steps, definition.multipliers
    mask = (1 << definition.theta_bits) - 1
    cap = CAP_MULTIPLIER * expected_ops(n, negation)
    add, canonical = ec.add, ec.canonical
    seen = {}
    ops = 0
    setup_ops = definition.setup_ops
    escapes = 0
    retries = 0
    for restart in range(CAP_MULTIPLIER):
        alpha = _draw(seed, LABEL_START_ALPHA, restart, n)
        beta = _draw(seed, LABEL_START_BETA, restart, n)
        cur = add(p, a, ec.mul(p, a, P, alpha), ec.mul(p, a, Q, beta))
        setup_ops += ec.mul_ops(alpha) + ec.mul_ops(beta) + 1
        if negation:
            cur, flipped = canonical(p, cur)
            if flipped:
                alpha, beta = (-alpha) % n, (-beta) % n
        anchor = None
        anchor_coeffs = (0, 0)
        taken = 0
        while cur is not None and taken < cap:
            x = cur[0]
            if not x & mask:
                prev = seen.get(cur)
                if prev is None:
                    seen[cur] = (alpha, beta)
                elif (beta - prev[1]) % n:
                    return Solution(
                        _solve_from(prev, alpha, beta, n),
                        cur,
                        prev,
                        (alpha, beta),
                        COLLISION_DISTINGUISHED,
                        ops,
                        setup_ops,
                        len(seen),
                        restart,
                        escapes,
                        retries,
                    )
                elif negation:
                    cur, alpha, beta = _escape(p, a, n, cur, alpha, beta)
                    ops += 1
                    escapes += 1
                    anchor = None
                    taken += 1
                    continue
                else:
                    break
            if negation:
                if taken % CYCLE_WINDOW == 0:
                    anchor, anchor_coeffs = cur, (alpha, beta)
                elif cur == anchor:
                    if (beta - anchor_coeffs[1]) % n:
                        return Solution(
                            _solve_from(anchor_coeffs, alpha, beta, n),
                            cur,
                            anchor_coeffs,
                            (alpha, beta),
                            COLLISION_CYCLE_WINDOW,
                            ops,
                            setup_ops,
                            len(seen),
                            restart,
                            escapes,
                            retries,
                        )
                    cur, alpha, beta = _escape(p, a, n, cur, alpha, beta)
                    ops += 1
                    escapes += 1
                    anchor = None
                    taken += 1
                    continue
                j = x % R
                nxt, flipped = canonical(p, add(p, a, cur, steps[j]))
                ops += 1
                if flipped and nxt is not None and nxt[0] % R == j:
                    j = (j + 1) % R
                    nxt, flipped = canonical(p, add(p, a, cur, steps[j]))
                    ops += 1
                    retries += 1
                u, v = multipliers[j]
                alpha, beta = (alpha + u) % n, (beta + v) % n
                if flipped:
                    alpha, beta = (-alpha) % n, (-beta) % n
                cur = nxt
            else:
                j = x % R
                u, v = multipliers[j]
                cur = add(p, a, cur, steps[j])
                alpha, beta = (alpha + u) % n, (beta + v) % n
                ops += 1
            taken += 1
    raise WalkExhausted(f"no collision after {CAP_MULTIPLIER} restarts of {cap} steps each")


def _escape(p, a, n, cur, alpha, beta):
    doubled, flipped = ec.canonical(p, ec.double(p, a, cur))
    alpha, beta = (2 * alpha) % n, (2 * beta) % n
    if flipped:
        alpha, beta = (-alpha) % n, (-beta) % n
    return doubled, alpha, beta


def solve(p, a, b, n, P, Q, seed, *, bits=None, negation_map=False):
    bits = p.bit_length() if bits is None else bits
    ec.require_on_curve(p, a, b, P, "P")
    ec.require_on_curve(p, a, b, Q, "Q")
    definition = build_walk(p, a, n, P, Q, seed, bits, negation_map)
    solution = walk(p, a, n, P, Q, definition, seed)
    if ec.mul(p, a, P, solution.x) != Q:
        raise PostconditionFailed("xP-eq-Q", f"the collision solved to x = {solution.x} but [x]P != Q")
    return definition, solution


def discrete_log(p, a, b, n, P, Q, seed):
    return solve(p, a, b, n, tuple(P), tuple(Q), seed)[1].x


@dataclass(frozen=True)
class RhoOutput:
    bits: int
    seed: int
    p: int
    a: int
    b: int
    n: int
    P: tuple
    Q: tuple
    walk: dict
    witness: dict
    x: int
    ops: int
    setup_ops: int
    distinguished_points: int
    cross_check: dict
    status: str
    transcripts: tuple | None = None

    def to_dict(self):
        return {
            "bits": self.bits,
            "seed": self.seed,
            "p": self.p,
            "a": self.a,
            "b": self.b,
            "n": self.n,
            "P": list(self.P),
            "Q": list(self.Q),
            "walk": {**self.walk, "multipliers": [list(pair) for pair in self.walk["multipliers"]]},
            "witness": {**self.witness, "X": list(self.witness["X"])},
            "x": self.x,
            "ops": self.ops,
            "setup_ops": self.setup_ops,
            "distinguished_points": self.distinguished_points,
            "cross_check": {
                "axis": self.cross_check["axis"],
                "independent_range": {k: list(v) for k, v in self.cross_check["independent_range"].items()},
                "result": self.cross_check["result"],
            },
            "status": self.status,
            "transcripts": None if self.transcripts is None else [dict(t) for t in self.transcripts],
        }

    def to_wire(self):
        return to_wire(self.to_dict())

    def to_json(self):
        return json.dumps(self.to_wire(), sort_keys=True, separators=(",", ":")) + "\n"

    @classmethod
    def from_dict(cls, doc):
        canon.encode(OUTPUT, doc)
        transcripts = (
            None if doc["transcripts"] is None else tuple({**t, "curve": list(t["curve"])} for t in doc["transcripts"])
        )
        return cls(
            doc["bits"],
            doc["seed"],
            doc["p"],
            doc["a"],
            doc["b"],
            doc["n"],
            tuple(doc["P"]),
            tuple(doc["Q"]),
            dict(doc["walk"]),
            dict(doc["witness"]),
            doc["x"],
            doc["ops"],
            doc["setup_ops"],
            doc["distinguished_points"],
            doc["cross_check"],
            doc["status"],
            transcripts,
        )

    @classmethod
    def from_json(cls, text):
        try:
            doc = json.loads(text)
        except ValueError as exc:
            raise InputError(f"output is not JSON: {exc}") from None
        if not isinstance(doc, dict):
            raise InputError(f"output is not a JSON object: {type(doc).__name__}")
        try:
            return cls.from_dict(from_wire(doc))
        except (KeyError, TypeError, ValueError, CanonError) as exc:
            raise InputError(f"output does not match {OUTPUT.name}: {exc}") from None

    def manifest(self):
        return canon.encode(OUTPUT, self.to_dict())

    def manifest_hash(self):
        return keys.node_hash(OUTPUT.name, self.manifest())


def _str_pairs(pairs):
    return [[str(c) for c in pair] for pair in pairs]


def _int_pairs(pairs):
    return [[int(c) for c in pair] for pair in pairs]


def to_wire(doc):
    doc = dict(doc)
    for name in BIG_FIELDS:
        doc[name] = str(doc[name])
    for name in POINT_FIELDS:
        doc[name] = [str(c) for c in doc[name]]
    doc["walk"] = {**doc["walk"], "multipliers": _str_pairs(doc["walk"]["multipliers"])}
    witness = doc["witness"]
    doc["witness"] = {
        **witness,
        "X": [str(c) for c in witness["X"]],
        "first": [str(c) for c in witness["first"]],
        "second": [str(c) for c in witness["second"]],
    }
    if doc.get("transcripts") is not None:
        doc["transcripts"] = [
            {**t, "curve": [str(c) for c in t["curve"]], "result": str(t["result"])} for t in doc["transcripts"]
        ]
    return doc


def from_wire(doc):
    doc = dict(doc)
    for name in BIG_FIELDS:
        doc[name] = int(doc[name])
    for name in POINT_FIELDS:
        doc[name] = [int(c) for c in doc[name]]
    doc["walk"] = {**doc["walk"], "multipliers": _int_pairs(doc["walk"]["multipliers"])}
    witness = doc["witness"]
    doc["witness"] = {
        **witness,
        "X": [int(c) for c in witness["X"]],
        "first": [int(c) for c in witness["first"]],
        "second": [int(c) for c in witness["second"]],
    }
    if doc.get("transcripts") is not None:
        doc["transcripts"] = [
            {**t, "curve": [int(c) for c in t["curve"]], "result": int(t["result"])} for t in doc["transcripts"]
        ]
    return doc


def parse_inputs(text):
    from cairn.skills import bsgs

    if not isinstance(text, str) or not text.strip():
        raise InputError("empty stdin: expected one JSON object {bits, seed, p, a, b, n, P, Q[, negation_map]}")
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise InputError(f"stdin is not JSON: {exc}") from None
    if not isinstance(doc, dict):
        raise InputError(f"stdin is not a JSON object: {type(doc).__name__}")
    try:
        doc = {"negation_map": False, **doc, **bsgs.instance_fields(doc)}
        canon.encode(INPUTS, doc)
    except (KeyError, CanonError, bsgs.InputError) as exc:
        raise InputError(str(exc)) from None
    validate(doc["bits"], doc["seed"], doc["p"], doc["a"], doc["b"], doc["n"], doc["P"], doc["Q"])
    return doc


def validate(bits, seed, p, a, b, n, P, Q):
    from cairn.skills import bsgs

    try:
        bsgs.validate(bits, seed, p, a, b, n, P, Q)
    except bsgs.InputError as exc:
        raise InputError(str(exc)) from None


def _transcript(call, curve, result):
    body = {"call": call, "curve": list(curve), "result": result}
    return {**body, "digest": keys.node_hash(TRANSCRIPT_BODY.name, canon.encode(TRANSCRIPT_BODY, body))}


def _cross_check(result):
    return {
        "axis": CROSS_CHECK_AXIS,
        "independent_range": {k: list(v) for k, v in INDEPENDENT_RANGE.items()},
        "result": result,
    }


def second_opinion(p, a, b, n, P, Q, seed):
    from cairn.skills import bsgs

    return int(bsgs.discrete_log(p, a, b, n, P, Q, seed))


def check_postcondition(out):
    p, a, b, n = out.p, out.a, out.b, out.n
    P, Q, X = tuple(out.P), tuple(out.Q), tuple(out.witness["X"])
    for name, point in (("P", P), ("Q", Q), ("X", X)):
        if not ec.is_on_curve(p, a, b, point):
            raise PostconditionFailed("oncurve", f"{name} = {point} is not on the curve")
    for name in ("first", "second"):
        alpha, beta = out.witness[name]
        if ec.add(p, a, ec.mul(p, a, P, alpha), ec.mul(p, a, Q, beta)) != X:
            raise PostconditionFailed("triple", f"{name} triple {alpha}, {beta} does not reach X")
    if (out.witness["second"][1] - out.witness["first"][1]) % n == 0:
        raise PostconditionFailed("b-ne-d", "the two triples share b mod n")
    if not 0 <= out.x < n:
        raise PostconditionFailed("x-range", f"x = {out.x} is outside [0, {n})")
    if ec.mul(p, a, P, out.x) != Q:
        raise PostconditionFailed("xP-eq-Q", f"[{out.x}]P != Q")
    return out


def run(bits, seed, p, a, b, n, P, Q, negation_map=False):
    P, Q = tuple(P), tuple(Q)
    validate(bits, seed, p, a, b, n, P, Q)
    lg = log.get(LOG_STEP)
    start = time.monotonic()
    definition, solution = solve(p, a, b, n, P, Q, seed, bits=bits, negation_map=bool(negation_map))
    curve = (a, b, p)
    walk_doc = definition.definition(solution.restarts, solution.fruitless_escapes, solution.lookahead_retries)
    out = RhoOutput(
        bits,
        seed,
        p,
        a,
        b,
        n,
        P,
        Q,
        walk_doc,
        solution.witness(),
        solution.x,
        solution.ops,
        solution.setup_ops,
        solution.distinguished_points,
        _cross_check("untested"),
        STATUS_OK,
    )
    check_postcondition(out)
    if bits <= CROSS_CHECK_MAX_BITS:
        first = _transcript("rho_dp", curve, solution.x)
        second = _transcript("bsgs", curve, second_opinion(p, a, b, n, P, Q, seed))
        out = _disagree(out, first, second) if second["result"] != solution.x else _with_cross_check(out, "agree")
    wall_ms = round((time.monotonic() - start) * 1000, 3)
    lg.info(
        "run",
        bits=bits,
        seed=seed,
        variant=definition.variant,
        ops=solution.ops,
        distinguished_points=solution.distinguished_points,
        restarts=solution.restarts,
        fruitless_escapes=solution.fruitless_escapes,
        collision=solution.collision,
        cross_check=out.cross_check["result"],
        status=out.status,
        wall_ms=wall_ms,
    )
    if out.status == STATUS_DISAGREE and out.transcripts is not None:
        lg.info("disagree", bits=bits, seed=seed, transcript_digests=[t["digest"] for t in out.transcripts])
    return out


def _with_cross_check(out, result, status=STATUS_OK, transcripts=None):
    return RhoOutput(
        out.bits,
        out.seed,
        out.p,
        out.a,
        out.b,
        out.n,
        out.P,
        out.Q,
        out.walk,
        out.witness,
        out.x,
        out.ops,
        out.setup_ops,
        out.distinguished_points,
        _cross_check(result),
        status,
        transcripts,
    )


def _disagree(out, first, second):
    return _with_cross_check(out, "disagree", STATUS_DISAGREE, (first, second))


def implementation_revision(root=REPO_ROOT):
    hasher = blake3.blake3()
    for rel in sorted(IDENTITY_SOURCES):
        path = Path(root) / rel
        data = path.read_bytes() if path.is_file() else b""
        hasher.update(canon.length_prefix(rel.encode("utf-8")) + canon.length_prefix(data))
    return hasher.hexdigest()


def identity_bundle(root=REPO_ROOT):
    versions = pari.pari_versions()
    return {
        "interface_version": INTERFACE_VERSION,
        "implementation_revision": implementation_revision(root),
        "tool_digests": {
            "gp_binary_sha256": env.gp_binary_sha256(),
            "cypari2": versions["cypari2"],
            "libpari": versions["libpari"],
        },
        "container_digest": keys.env_manifest_digest(env.manifest()),
        "numeric_profile": None,
    }


def skill_identity_hash(root=REPO_ROOT):
    return keys.identity_bundle_hash(identity_bundle(root))


def method_params(negation_map):
    return {"variant": VARIANT_NEGATION_MAP if negation_map else VARIANT_PLAIN, "r": str(R)}


def main(stdin=None, stdout=None, stderr=None):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    log.configure(None)
    try:
        doc = parse_inputs(stdin.read())
    except InputError as exc:
        stderr.write(f"error: {exc}\n")
        return 1
    out = run(doc["bits"], doc["seed"], doc["p"], doc["a"], doc["b"], doc["n"], doc["P"], doc["Q"], doc["negation_map"])
    stdout.write(out.to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
