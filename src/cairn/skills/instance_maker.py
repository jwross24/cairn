"""Gate-owned instance-maker: one DLP instance per (bits, seed), with a known answer.

The seed is derived gate-side (cairn.instances) from a nonce the worker never
sees before committing its method, so a worker cannot overfit a fixed instance
an evaluator reuses. This module is the launched half: it takes the derived
seed, draws the curve and P through the certified toy_curve skill, draws x from
the same seed and sets Q = xP. Its output is non-memoizable by declaration
(DO_NOT_CACHE), so the substrate's serve path refuses it.

The second opinion on Q = xP is a BSGS recovery of x from (P, Q) at
CROSS_CHECK_MAX_BITS and below; at the ladder's rung sizes the cross-check does
not run and reports untested.
"""

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import blake3

from cairn import canon, ec, env, keys, log, pari
from cairn.canon import INT, STR, CanonError, Field, List, Map, Optional, Struct
from cairn.profile import CostProfile, Production, SizeCost, Verification
from cairn.skills import toy_curve

INTERFACE_VERSION = "instance_maker/1"
SEAM = "cairn.skills.bsgs.discrete_log"
CROSS_CHECK_AXIS = "algorithm"
CROSS_CHECK_MAX_BITS = 28
INDEPENDENT_RANGE = {"bits": [0, CROSS_CHECK_MAX_BITS]}
REPLAY_GRADE = "Replayable"
DO_NOT_CACHE = True
REPO_ROOT = Path(__file__).resolve().parents[3]
IDENTITY_SOURCES = (
    "src/cairn/ec.py",
    "src/cairn/instances.py",
    "src/cairn/pari.py",
    "src/cairn/skills/bsgs.py",
    "src/cairn/skills/instance_maker.py",
    "src/cairn/skills/instance_maker_corpus.json",
    "src/cairn/skills/toy_curve.py",
)
STATUS_OK = "OK"
STATUS_DISAGREE = "DISAGREE"
LOG_STEP = "skill.instance_maker"
LABEL_X = b"instance-maker/x"

COST_PROFILE = CostProfile(
    tier=0,
    production=Production(
        model="c_ln_p_tries",
        per_size={
            28: SizeCost(mean_tries=49.7, sd_tries=37.67, per_try_s=988.4925e-6, mean_wall_s=0.0491),
            30: SizeCost(mean_tries=45.0, sd_tries=46.7, per_try_s=746.9944e-6, mean_wall_s=0.0336),
            40: SizeCost(mean_tries=55.5, sd_tries=38.86, per_try_s=913.9955e-6, mean_wall_s=0.0507),
            50: SizeCost(mean_tries=79.2, sd_tries=69.22, per_try_s=2239.772e-6, mean_wall_s=0.1774),
            60: SizeCost(mean_tries=93.6, sd_tries=93.9, per_try_s=8072.7288e-6, mean_wall_s=0.7556),
        },
    ),
    verification=Verification(grade=REPLAY_GRADE, cost_model="same_as_production"),
    source="research/grounding/m1-dlp-skill-costs.md §4: cairn measure dlp --skill instance-maker --sizes 28,30,40,50,60 --seeds 10, 2026-09-02, seeds 1..10 per size (STRONG-EMPIRICAL on the sample)",
)

INPUTS = Struct("instance_maker_inputs", [Field("bits", INT), Field("seed", INT)])
TRANSCRIPT_BODY = Struct("dlp_transcript_body", [Field("call", STR), Field("curve", List(INT)), Field("result", INT)])
TRANSCRIPT = Struct(
    "dlp_transcript", [Field("call", STR), Field("curve", List(INT)), Field("result", INT), Field("digest", STR)]
)
CROSS_CHECK = Struct(
    "cross_check", [Field("axis", STR), Field("independent_range", Map(STR, List(INT))), Field("result", STR)]
)
OUTPUT = Struct(
    "instance_maker_output",
    [
        Field("bits", INT),
        Field("seed", INT),
        Field("p", INT),
        Field("a", INT),
        Field("b", INT),
        Field("n", INT),
        Field("P", List(INT)),
        Field("Q", List(INT)),
        Field("x", INT),
        Field("tries", INT),
        Field("instance_hash", STR),
        Field("cross_check", CROSS_CHECK),
        Field("status", STR),
        Field("transcripts", Optional(List(TRANSCRIPT))),
    ],
)
BIG_FIELDS = ("p", "a", "b", "n", "x")
POINT_FIELDS = ("P", "Q")


class InputError(ValueError):
    pass


class PostconditionFailed(AssertionError):
    def __init__(self, clause, detail):
        super().__init__(f"postcondition {clause} failed: {detail}")
        self.clause = clause


@dataclass(frozen=True)
class InstanceOutput:
    bits: int
    seed: int
    p: int
    a: int
    b: int
    n: int
    P: tuple
    Q: tuple
    x: int
    tries: int
    instance_hash: str
    cross_check: dict
    status: str
    transcripts: tuple | None = None

    def instance(self):
        return {"p": self.p, "a": self.a, "b": self.b, "n": self.n, "P": list(self.P), "Q": list(self.Q)}

    def to_dict(self):
        return {
            **self.instance(),
            "bits": self.bits,
            "seed": self.seed,
            "x": self.x,
            "tries": self.tries,
            "instance_hash": self.instance_hash,
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
            doc["x"],
            doc["tries"],
            doc["instance_hash"],
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


def to_wire(doc):
    doc = dict(doc)
    for name in BIG_FIELDS:
        doc[name] = str(doc[name])
    for name in POINT_FIELDS:
        doc[name] = [str(c) for c in doc[name]]
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
    if doc.get("transcripts") is not None:
        doc["transcripts"] = [
            {**t, "curve": [int(c) for c in t["curve"]], "result": int(t["result"])} for t in doc["transcripts"]
        ]
    return doc


def parse_inputs(text):
    if not isinstance(text, str) or not text.strip():
        raise InputError("empty stdin: expected one JSON object {bits, seed}")
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise InputError(f"stdin is not JSON: {exc}") from None
    if not isinstance(doc, dict):
        raise InputError(f"stdin is not a JSON object: {type(doc).__name__}")
    try:
        canon.encode(INPUTS, doc)
    except CanonError as exc:
        raise InputError(str(exc)) from None
    validate(doc["bits"], doc["seed"])
    return doc["bits"], doc["seed"]


def validate(bits, seed):
    try:
        toy_curve.validate(bits, seed)
    except toy_curve.InputError as exc:
        raise InputError(str(exc)) from None
    if bits < 3:
        raise InputError(f"bits must be >= 3 for a curve with a point of prime order, got {bits}")


def draw_x(seed, n):
    material = canon.length_prefix(str(seed).encode("utf-8")) + canon.length_prefix(LABEL_X)
    return int.from_bytes(blake3.blake3(material).digest(), "big") % (n - 1) + 1


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
    curve = toy_curve.ToyCurveOutput(
        out.bits, out.seed, out.p, out.a, out.b, out.n, out.P, out.tries, _cross_check("untested"), STATUS_OK
    )
    try:
        toy_curve.check_postcondition(curve)
    except toy_curve.PostconditionFailed as exc:
        raise PostconditionFailed(exc.clause, str(exc)) from None
    if not 1 <= out.x < out.n:
        raise PostconditionFailed("x-range", f"x = {out.x} is outside [1, {out.n})")
    if not ec.is_on_curve(out.p, out.a, out.b, tuple(out.Q)):
        raise PostconditionFailed("oncurve", f"Q = {out.Q} is not on the curve")
    E = pari.pari.ellinit([out.a, out.b], out.p)
    lifted = pari.pari.ellmul(E, list(out.P), out.x)
    if len(lifted) != 2 or tuple(int(c.lift()) for c in lifted) != tuple(out.Q):
        raise PostconditionFailed("ellmul", f"[{out.x}]P != Q under libpari")
    if keys.instance_hash(out.instance()) != out.instance_hash:
        raise PostconditionFailed("instance_hash", "the recorded instance hash is not the instance's")
    return out


def run(bits, seed):
    validate(bits, seed)
    lg = log.get(LOG_STEP)
    start = time.monotonic()
    curve = toy_curve.run(bits, seed)
    p, a, b, n, P = curve.p, curve.a, curve.b, curve.n, tuple(curve.P)
    x = draw_x(seed, n)
    Q = ec.mul(p, a, P, x)
    instance = {"p": p, "a": a, "b": b, "n": n, "P": list(P), "Q": list(Q)}
    out = InstanceOutput(
        bits, seed, p, a, b, n, P, Q, x, curve.tries, keys.instance_hash(instance), _cross_check("untested"), STATUS_OK
    )
    check_postcondition(out)
    if curve.status == toy_curve.STATUS_DISAGREE and curve.transcripts is not None:
        result = "disagree" if bits <= CROSS_CHECK_MAX_BITS else "untested"
        out = _with_cross_check(out, result, STATUS_DISAGREE, tuple(curve.transcripts[:2]))
    elif bits <= CROSS_CHECK_MAX_BITS:
        first = _transcript("instance_maker", (a, b, p), x)
        second = _transcript("bsgs", (a, b, p), second_opinion(p, a, b, n, P, Q, seed))
        out = _disagree(out, first, second) if second["result"] != x else _with_cross_check(out, "agree")
    wall_ms = round((time.monotonic() - start) * 1000, 3)
    lg.info(
        "run",
        bits=bits,
        seed=seed,
        tries=curve.tries,
        n_bits=n.bit_length(),
        instance_hash=out.instance_hash,
        cross_check=out.cross_check["result"],
        status=out.status,
        wall_ms=wall_ms,
    )
    if out.status == STATUS_DISAGREE and out.transcripts is not None:
        lg.info("disagree", bits=bits, seed=seed, transcript_digests=[t["digest"] for t in out.transcripts])
    return out


def _with_cross_check(out, result, status=STATUS_OK, transcripts=None):
    return InstanceOutput(
        out.bits,
        out.seed,
        out.p,
        out.a,
        out.b,
        out.n,
        out.P,
        out.Q,
        out.x,
        out.tries,
        out.instance_hash,
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


def main(stdin=None, stdout=None, stderr=None):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    log.configure(None)
    try:
        bits, seed = parse_inputs(stdin.read())
    except InputError as exc:
        stderr.write(f"error: {exc}\n")
        return 1
    out = run(bits, seed)
    stdout.write(out.to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
