import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import blake3

from cairn import canon, env, keys, log, pari
from cairn.canon import INT, STR, CanonError, Field, List, Map, Optional, Struct
from cairn.profile import CostProfile, Production, SizeCost, Verification

INTERFACE_VERSION = "toy_curve/1"
SEAM = "cairn.pari.ellsea"
CROSS_CHECK_AXIS = "algorithm"
INDEPENDENT_RANGE = {"bits": [0, 50]}
SEA_SEARCH_ABOVE_BITS = 50
REPLAY_GRADE = "Replayable"
DO_NOT_CACHE = False
REPO_ROOT = Path(__file__).resolve().parents[3]
IDENTITY_SOURCES = ("src/cairn/pari.py", "src/cairn/skills/toy_curve.py", "src/cairn/skills/toy_curve_corpus.json")
STATUS_OK = "OK"
STATUS_DISAGREE = "DISAGREE"
LOG_STEP = "skill.toy_curve"

COST_PROFILE = CostProfile(
    tier=0,
    production=Production(
        model="c_ln_p_tries",
        per_size={
            30: SizeCost(mean_tries=39.48, sd_tries=29.83, per_try_s=1.053e-3, mean_wall_s=0.1372),
            40: SizeCost(mean_tries=50.6, sd_tries=46.22, per_try_s=1.096e-3, mean_wall_s=0.1338),
            50: SizeCost(mean_tries=63.82, sd_tries=60.56, per_try_s=2.548e-3, mean_wall_s=0.2511),
            60: SizeCost(mean_tries=87.9, sd_tries=78.93, per_try_s=8.992e-3, mean_wall_s=0.8777),
        },
    ),
    verification=Verification(grade=REPLAY_GRADE, cost_model="same_as_production"),
    source="research/grounding/m0-stack-facts.md §6a: cairn measure toy-curve-tries --sizes 30,40,50,60 --seeds 50, 2026-08-21, seeds 1..50 per size (STRONG-EMPIRICAL on the sample)",
)

INPUTS = Struct("toy_curve_inputs", [Field("bits", INT), Field("seed", INT)])
TRANSCRIPT_BODY = Struct("order_transcript_body", [Field("call", STR), Field("curve", List(INT)), Field("result", INT)])
TRANSCRIPT = Struct("order_transcript", [Field("call", STR), Field("curve", List(INT)), Field("result", INT), Field("digest", STR)])
CROSS_CHECK = Struct("cross_check", [Field("axis", STR), Field("independent_range", Map(STR, List(INT))), Field("result", STR)])
OUTPUT = Struct(
    "toy_curve_output",
    [
        Field("bits", INT),
        Field("seed", INT),
        Field("p", INT),
        Field("a", INT),
        Field("b", INT),
        Field("n", INT),
        Field("P", List(INT)),
        Field("tries", INT),
        Field("cross_check", CROSS_CHECK),
        Field("status", STR),
        Field("transcripts", Optional(List(TRANSCRIPT))),
    ],
)
BIG_FIELDS = ("p", "a", "b", "n")


class InputError(ValueError):
    pass


class PostconditionFailed(AssertionError):
    def __init__(self, clause, detail):
        super().__init__(f"postcondition {clause} failed: {detail}")
        self.clause = clause


@dataclass(frozen=True)
class ToyCurveOutput:
    bits: int
    seed: int
    p: int
    a: int
    b: int
    n: int
    P: tuple
    tries: int
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
            "tries": self.tries,
            "cross_check": {"axis": self.cross_check["axis"], "independent_range": {k: list(v) for k, v in self.cross_check["independent_range"].items()}, "result": self.cross_check["result"]},
            "status": self.status,
            "transcripts": None if self.transcripts is None else [dict(t) for t in self.transcripts],
        }

    def to_wire(self):
        doc = self.to_dict()
        for name in BIG_FIELDS:
            doc[name] = str(doc[name])
        doc["P"] = [str(c) for c in doc["P"]]
        if doc["transcripts"] is not None:
            doc["transcripts"] = [{**t, "curve": [str(c) for c in t["curve"]], "result": str(t["result"])} for t in doc["transcripts"]]
        return doc

    def to_json(self):
        return json.dumps(self.to_wire(), sort_keys=True, separators=(",", ":")) + "\n"

    @classmethod
    def from_dict(cls, doc):
        canon.encode(OUTPUT, doc)
        transcripts = None if doc["transcripts"] is None else tuple({**t, "curve": list(t["curve"])} for t in doc["transcripts"])
        return cls(doc["bits"], doc["seed"], doc["p"], doc["a"], doc["b"], doc["n"], tuple(doc["P"]), doc["tries"], doc["cross_check"], doc["status"], transcripts)

    @classmethod
    def from_json(cls, text):
        try:
            doc = json.loads(text)
        except ValueError as exc:
            raise InputError(f"output is not JSON: {exc}") from None
        if not isinstance(doc, dict):
            raise InputError(f"output is not a JSON object: {type(doc).__name__}")
        try:
            for name in BIG_FIELDS:
                doc[name] = int(doc[name])
            doc["P"] = [int(c) for c in doc["P"]]
            if doc.get("transcripts") is not None:
                doc["transcripts"] = [{**t, "curve": [int(c) for c in t["curve"]], "result": int(t["result"])} for t in doc["transcripts"]]
            return cls.from_dict(doc)
        except (KeyError, TypeError, ValueError, CanonError) as exc:
            raise InputError(f"output does not match {OUTPUT.name}: {exc}") from None

    def manifest(self):
        return canon.encode(OUTPUT, self.to_dict())

    def manifest_hash(self):
        return keys.node_hash(OUTPUT.name, self.manifest())


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
    for name, value in (("bits", bits), ("seed", seed)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise InputError(f"{name} must be an int, got {type(value).__name__}")
        if value < 1:
            raise InputError(f"{name} must be >= 1, got {value}")


def _singular(a, b, p):
    return (4 * a * a * a + 27 * b * b) % p == 0


def _draw_pair(p):
    return int(pari.pari.random(p)), int(pari.pari.random(p))


def _order_is_prime(n):
    return bool(pari.pari.isprime(n))


def _count_order(bits, E):
    if bits <= SEA_SEARCH_ABOVE_BITS:
        return int(pari.ellcard(E)), "ellcard"
    return int(pari.ellsea(E, 1)), "ellsea_early_abort"


def _search(bits, p):
    tries = 0
    while True:
        a, b = _draw_pair(p)
        if _singular(a, b, p):
            continue
        tries += 1
        E = pari.pari.ellinit([a, b], p)
        m, call = _count_order(bits, E)
        if m != 0 and _order_is_prime(m):
            return a, b, m, tries, E, call


def _confirm_order(bits, E, curve):
    if bits <= SEA_SEARCH_ABOVE_BITS:
        return None
    return _transcript("ellcard", curve, int(pari.ellcard(E)))


def _draw_point(E):
    while True:
        point = pari.pari.random(E)
        if len(point) == 2:
            return int(point[0].lift()), int(point[1].lift())


def _settle(bits, E, curve):
    confirm = _confirm_order(bits, E, curve)
    P = _draw_point(E)
    return confirm, P


def _transcript(call, curve, result):
    body = {"call": call, "curve": list(curve), "result": result}
    return {**body, "digest": keys.node_hash(TRANSCRIPT_BODY.name, canon.encode(TRANSCRIPT_BODY, body))}


def _cross_check(result):
    return {"axis": CROSS_CHECK_AXIS, "independent_range": {k: list(v) for k, v in INDEPENDENT_RANGE.items()}, "result": result}


def check_postcondition(out):
    E = pari.pari.ellinit([out.a, out.b], out.p)
    if not bool(pari.pari.isprime(out.n)):
        raise PostconditionFailed("isprime", f"n = {out.n} is not prime")
    if (out.n - (out.p + 1)) ** 2 > 4 * out.p:
        raise PostconditionFailed("hasse", f"n = {out.n} is outside [p+1-2sqrt(p), p+1+2sqrt(p)] for p = {out.p}")
    if not bool(pari.pari.ellisoncurve(E, list(out.P))):
        raise PostconditionFailed("ellisoncurve", f"P = {out.P} is not on the curve")
    if len(pari.pari.ellmul(E, list(out.P), out.n)) != 1:
        raise PostconditionFailed("ellmul", f"[n]P is not the identity for n = {out.n}")
    return out


def run(bits, seed):
    validate(bits, seed)
    lg = log.get(LOG_STEP)
    start = time.monotonic()
    pari.pari.setrand(seed)
    p = int(pari.pari.randomprime([2 ** (bits - 1), 2**bits]))
    a, b, n, tries, E, search_call = _search(bits, p)
    curve = (a, b, p)
    confirm, P = _settle(bits, E, curve)
    out = ToyCurveOutput(bits, seed, p, a, b, n, P, tries, _cross_check("untested"), STATUS_OK)
    check_postcondition(out)
    if confirm is not None and confirm["result"] != n:
        out = _disagree(out, _transcript(search_call, curve, n), confirm)
    elif bits <= SEA_SEARCH_ABOVE_BITS:
        sea = _transcript("ellsea", curve, int(pari.ellsea(E)))
        card = _transcript("ellcard", curve, n)
        out = _disagree(out, card, sea) if sea["result"] != n else ToyCurveOutput(bits, seed, p, a, b, n, P, tries, _cross_check("agree"), STATUS_OK)
    wall_ms = round((time.monotonic() - start) * 1000, 3)
    lg.info("run", bits=bits, seed=seed, tries=tries, n_bits=n.bit_length(), cross_check=out.cross_check["result"], status=out.status, wall_ms=wall_ms)
    if out.status == STATUS_DISAGREE:
        lg.info("disagree", bits=bits, seed=seed, transcript_digests=[t["digest"] for t in out.transcripts])
    return out


def _disagree(out, first, second):
    return ToyCurveOutput(out.bits, out.seed, out.p, out.a, out.b, out.n, out.P, out.tries, _cross_check("disagree"), STATUS_DISAGREE, (first, second))


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
        "tool_digests": {"gp_binary_sha256": env.gp_binary_sha256(), "cypari2": versions["cypari2"], "libpari": versions["libpari"]},
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
