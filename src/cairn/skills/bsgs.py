"""Baby-step giant-step on prime-order toy curves: the ladder's refutation floor.

The skill is deterministic end to end, so its replay grade is Replayable and it
carries no witness. The seed rotates the giant-step start offset and nothing
else: x is the same under every seed, the step at which the table hit lands is
not. The table stores one u64 x-coordinate per baby step and one u32 slot per
hash bucket, and the skill reports those bytes in its output as a diagnostic;
the gate's own RSS measurement is the predicate the ladder reads.

The second opinion on x is a Pollard rho solve at CROSS_CHECK_MAX_BITS and
below, where its cost is a rounding error; at the ladder's rung sizes the
cross-check does not run and reports untested, so the rungs' resource columns
measure the table alone.
"""

import json
import math
import re
import sys
import time
from array import array
from dataclasses import dataclass
from pathlib import Path

import blake3

from cairn import canon, ec, env, keys, log, pari
from cairn.canon import INT, STR, CanonError, Field, List, Map, Optional, Struct
from cairn.profile import CostProfile, MemoryProfile, Production, SizeCost, Verification

INTERFACE_VERSION = "bsgs/1"
SEAM = "cairn.skills.rho_dp.discrete_log"
CROSS_CHECK_AXIS = "algorithm"
CROSS_CHECK_MAX_BITS = 28
INDEPENDENT_RANGE = {"bits": [0, CROSS_CHECK_MAX_BITS]}
REPLAY_GRADE = "Replayable"
DO_NOT_CACHE = False
REPO_ROOT = Path(__file__).resolve().parents[3]
IDENTITY_SOURCES = (
    "src/cairn/ec.py",
    "src/cairn/skills/bsgs.py",
    "src/cairn/skills/bsgs_corpus.json",
    "src/cairn/skills/rho_dp.py",
)
STATUS_OK = "OK"
STATUS_DISAGREE = "DISAGREE"
LOG_STEP = "skill.bsgs"
KEY_BITS = 64
KEY_TYPECODE = "Q"
SLOT_TYPECODE = "I"
KEY_BYTES = 8
SLOT_BYTES = 4
GOLDEN_RATIO_64 = 0x9E3779B97F4A7C15
MASK_64 = (1 << 64) - 1
MEMORY_MODEL = "ceil_sqrt_n_entries"
DECIMAL = re.compile(r"-?[0-9]+")

COST_PROFILE = CostProfile(
    tier=1,
    production=Production(
        model="c_sqrt_n_ops",
        per_size={
            28: SizeCost(mean_tries=19806.8, sd_tries=4305.76, per_try_s=1.4746e-6, mean_wall_s=0.0292),
            30: SizeCost(mean_tries=41226.4, sd_tries=9522.34, per_try_s=0.8459e-6, mean_wall_s=0.0349),
            40: SizeCost(mean_tries=1171748.6, sd_tries=288195.47, per_try_s=1.6077e-6, mean_wall_s=1.8838),
            50: SizeCost(mean_tries=44769554.0, sd_tries=8175063.73, per_try_s=2.085e-6, mean_wall_s=93.3451),
        },
    ),
    verification=Verification(grade=REPLAY_GRADE, cost_model="same_as_production"),
    source="research/grounding/m1-dlp-skill-costs.md §3: cairn measure dlp --skill bsgs --sizes 28,30 --seeds 10, --sizes 40 --seeds 10 and --sizes 50 --seeds 2, 2026-09-02, seeds 1..N per size (STRONG-EMPIRICAL on the sample)",
    memory=MemoryProfile(
        model=MEMORY_MODEL,
        entries="ceil(sqrt(n)) - 1 u64 keys plus a u32 slot table of the next power of two at or above 2 * ceil(sqrt(n))",
        bytes_per_entry_bounds=(16.0, 24.0),
        measured_bytes_per_entry={28: 17.548, 30: 16.918, 40: 17.516, 50: 18.278},
        measured_maxrss_bytes={28: 81412096, 30: 81510400, 40: 163397632, 50: 949764096},
    ),
)

INPUTS = Struct(
    "bsgs_inputs",
    [
        Field("bits", INT),
        Field("seed", INT),
        Field("p", INT),
        Field("a", INT),
        Field("b", INT),
        Field("n", INT),
        Field("P", List(INT)),
        Field("Q", List(INT)),
    ],
)
TRANSCRIPT_BODY = Struct("dlp_transcript_body", [Field("call", STR), Field("curve", List(INT)), Field("result", INT)])
TRANSCRIPT = Struct(
    "dlp_transcript", [Field("call", STR), Field("curve", List(INT)), Field("result", INT), Field("digest", STR)]
)
CROSS_CHECK = Struct(
    "cross_check", [Field("axis", STR), Field("independent_range", Map(STR, List(INT))), Field("result", STR)]
)
MEMORY = Struct(
    "bsgs_memory",
    [
        Field("model", STR),
        Field("entries", INT),
        Field("key_bytes", INT),
        Field("slot_bytes", INT),
        Field("slots", INT),
        Field("table_bytes", INT),
    ],
)
OUTPUT = Struct(
    "bsgs_output",
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
        Field("offset", INT),
        Field("giant_steps", INT),
        Field("ops", INT),
        Field("memory", MEMORY),
        Field("cross_check", CROSS_CHECK),
        Field("status", STR),
        Field("transcripts", Optional(List(TRANSCRIPT))),
    ],
)
BIG_FIELDS = ("p", "a", "b", "n", "x")
POINT_FIELDS = ("P", "Q")


class InputError(ValueError):
    pass


class NoSolution(RuntimeError):
    pass


class PostconditionFailed(AssertionError):
    def __init__(self, clause, detail):
        super().__init__(f"postcondition {clause} failed: {detail}")
        self.clause = clause


class BabyTable:
    """Open addressing over two flat arrays: u64 x-coordinates and u32 slots holding position + 1."""

    __slots__ = ("keys", "mask", "shift", "slots")

    def __init__(self, entries):
        slot_bits = max(1, (2 * entries - 1).bit_length())
        self.keys = array(KEY_TYPECODE)
        self.slots = array(SLOT_TYPECODE, bytes(SLOT_BYTES << slot_bits))
        self.mask = (1 << slot_bits) - 1
        self.shift = KEY_BITS - slot_bits

    def _home(self, key):
        return ((key * GOLDEN_RATIO_64) & MASK_64) >> self.shift

    def insert(self, key):
        self.keys.append(key)
        slots, mask = self.slots, self.mask
        h = self._home(key)
        while slots[h]:
            h = (h + 1) & mask
        slots[h] = len(self.keys)

    def lookup(self, key):
        slots, keys, mask = self.slots, self.keys, self.mask
        h = self._home(key)
        while True:
            held = slots[h]
            if not held:
                return None
            if keys[held - 1] == key:
                return held - 1
            h = (h + 1) & mask

    @property
    def entries(self):
        return len(self.keys)

    @property
    def slot_count(self):
        return len(self.slots)

    @property
    def table_bytes(self):
        return len(self.keys) * KEY_BYTES + len(self.slots) * SLOT_BYTES


@dataclass(frozen=True)
class Solution:
    x: int
    offset: int
    giant_steps: int
    ops: int
    entries: int
    slots: int
    table_bytes: int

    def memory(self):
        return {
            "model": MEMORY_MODEL,
            "entries": self.entries,
            "key_bytes": KEY_BYTES,
            "slot_bytes": SLOT_BYTES,
            "slots": self.slots,
            "table_bytes": self.table_bytes,
        }


def table_entries(n):
    return math.isqrt(n - 1) + 1


def solve(p, a, b, n, P, Q, seed):
    ec.require_on_curve(p, a, b, P, "P")
    ec.require_on_curve(p, a, b, Q, "Q")
    m = table_entries(n)
    offset = seed % m
    table = BabyTable(m)
    add = ec.add
    ops = 0
    cur = P
    for _ in range(1, m):
        table.insert(cur[0])
        cur = add(p, a, cur, P)
        ops += 1
    stride = ec.neg(p, cur)
    remainder = ec.sub(p, a, Q, ec.mul(p, a, P, offset))
    ops += ec.mul_ops(offset) + 1
    giant_limit = n // m + 2
    for i in range(giant_limit):
        base = offset + i * m
        if remainder is None:
            return _solution(base % n, offset, i, ops, table)
        position = table.lookup(remainder[0])
        if position is not None:
            j = position + 1
            for candidate in ((base + j) % n, (base - j) % n):
                ops += ec.mul_ops(candidate)
                if ec.mul(p, a, P, candidate) == Q:
                    return _solution(candidate, offset, i, ops, table)
        remainder = add(p, a, remainder, stride)
        ops += 1
    raise NoSolution(f"no x in [0, {n}) with xP = Q after {giant_limit} giant steps")


def _solution(x, offset, giant_steps, ops, table):
    return Solution(x, offset, giant_steps, ops, table.entries, table.slot_count, table.table_bytes)


def discrete_log(p, a, b, n, P, Q, seed):
    return solve(p, a, b, n, P, Q, seed).x


@dataclass(frozen=True)
class BsgsOutput:
    bits: int
    seed: int
    p: int
    a: int
    b: int
    n: int
    P: tuple
    Q: tuple
    x: int
    offset: int
    giant_steps: int
    ops: int
    memory: dict
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
            "x": self.x,
            "offset": self.offset,
            "giant_steps": self.giant_steps,
            "ops": self.ops,
            "memory": dict(self.memory),
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
            doc["offset"],
            doc["giant_steps"],
            doc["ops"],
            dict(doc["memory"]),
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


def big_int(name, value):
    if isinstance(value, bool):
        raise InputError(f"{name} must be an int or a decimal string, got bool")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and DECIMAL.fullmatch(value.strip()):
        return int(value)
    raise InputError(f"{name} must be an int or a decimal string, got {value!r}")


def point_field(name, value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise InputError(f"{name} must be a pair of coordinates, got {value!r}")
    return [big_int(f"{name}[{i}]", c) for i, c in enumerate(value)]


def instance_fields(doc):
    fields = {name: big_int(name, doc[name]) for name in ("p", "a", "b", "n") if name in doc}
    for name in POINT_FIELDS:
        if name in doc:
            fields[name] = point_field(name, doc[name])
    return fields


def parse_inputs(text):
    if not isinstance(text, str) or not text.strip():
        raise InputError("empty stdin: expected one JSON object {bits, seed, p, a, b, n, P, Q}")
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise InputError(f"stdin is not JSON: {exc}") from None
    if not isinstance(doc, dict):
        raise InputError(f"stdin is not a JSON object: {type(doc).__name__}")
    try:
        doc = {**doc, **instance_fields(doc)}
        canon.encode(INPUTS, doc)
    except (KeyError, CanonError) as exc:
        raise InputError(str(exc)) from None
    validate(doc["bits"], doc["seed"], doc["p"], doc["a"], doc["b"], doc["n"], doc["P"], doc["Q"])
    return doc


def validate(bits, seed, p, a, b, n, P, Q):
    for name, value in (("bits", bits), ("seed", seed), ("p", p), ("n", n)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise InputError(f"{name} must be an int, got {type(value).__name__}")
        if value < 1:
            raise InputError(f"{name} must be >= 1, got {value}")
    if p < 5 or not bool(pari.pari.isprime(p)):
        raise InputError(f"p = {p} is not a prime above 3")
    if p.bit_length() != bits:
        raise InputError(f"bits = {bits} but p has {p.bit_length()} bits")
    if p.bit_length() > KEY_BITS:
        raise InputError(f"p has {p.bit_length()} bits; the table keys hold {KEY_BITS}")
    if not (0 <= a < p and 0 <= b < p):
        raise InputError(f"a = {a}, b = {b} are not reduced coordinates mod p = {p}")
    if (4 * a * a * a + 27 * b * b) % p == 0:
        raise InputError(f"y^2 = x^3 + {a}x + {b} is singular over F_{p}")
    if n < 2 or not bool(pari.pari.isprime(n)):
        raise InputError(f"n = {n} is not prime; the skill is defined on prime-order curves")
    if (n - p - 1) ** 2 > 4 * p:
        raise InputError(f"n = {n} is outside the Hasse interval of p = {p}")
    for name, point in (("P", P), ("Q", Q)):
        if len(point) != 2 or not all(isinstance(c, int) and not isinstance(c, bool) for c in point):
            raise InputError(f"{name} must be a pair of ints, got {point!r}")
        if not ec.is_on_curve(p, a, b, tuple(point)):
            raise InputError(f"{name} = {list(point)} is not on the curve")
        if ec.mul(p, a, tuple(point), n) is not None:
            raise InputError(f"[n]{name} is not the identity for n = {n}")


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
    from cairn.skills import rho_dp

    return int(rho_dp.discrete_log(p, a, b, n, P, Q, seed))


def check_postcondition(out):
    if not ec.is_on_curve(out.p, out.a, out.b, tuple(out.P)):
        raise PostconditionFailed("oncurve", f"P = {out.P} is not on the curve")
    if not ec.is_on_curve(out.p, out.a, out.b, tuple(out.Q)):
        raise PostconditionFailed("oncurve", f"Q = {out.Q} is not on the curve")
    if not 0 <= out.x < out.n:
        raise PostconditionFailed("x-range", f"x = {out.x} is outside [0, {out.n})")
    if ec.mul(out.p, out.a, tuple(out.P), out.x) != tuple(out.Q):
        raise PostconditionFailed("xP-eq-Q", f"[{out.x}]P != Q")
    if out.memory["entries"] != table_entries(out.n) - 1:
        raise PostconditionFailed("table", f"{out.memory['entries']} entries for n = {out.n}")
    return out


def run(bits, seed, p, a, b, n, P, Q):
    P, Q = tuple(P), tuple(Q)
    validate(bits, seed, p, a, b, n, P, Q)
    lg = log.get(LOG_STEP)
    start = time.monotonic()
    solution = solve(p, a, b, n, P, Q, seed)
    curve = (a, b, p)
    out = BsgsOutput(
        bits,
        seed,
        p,
        a,
        b,
        n,
        P,
        Q,
        solution.x,
        solution.offset,
        solution.giant_steps,
        solution.ops,
        solution.memory(),
        _cross_check("untested"),
        STATUS_OK,
    )
    check_postcondition(out)
    if bits <= CROSS_CHECK_MAX_BITS:
        first = _transcript("bsgs", curve, solution.x)
        second = _transcript("rho_dp", curve, second_opinion(p, a, b, n, P, Q, seed))
        if second["result"] != solution.x:
            out = _disagree(out, first, second)
        else:
            out = BsgsOutput(
                bits,
                seed,
                p,
                a,
                b,
                n,
                P,
                Q,
                solution.x,
                solution.offset,
                solution.giant_steps,
                solution.ops,
                solution.memory(),
                _cross_check("agree"),
                STATUS_OK,
            )
    wall_ms = round((time.monotonic() - start) * 1000, 3)
    lg.info(
        "run",
        bits=bits,
        seed=seed,
        ops=solution.ops,
        entries=solution.entries,
        table_bytes=solution.table_bytes,
        giant_steps=solution.giant_steps,
        cross_check=out.cross_check["result"],
        status=out.status,
        wall_ms=wall_ms,
    )
    if out.status == STATUS_DISAGREE and out.transcripts is not None:
        lg.info("disagree", bits=bits, seed=seed, transcript_digests=[t["digest"] for t in out.transcripts])
    return out


def _disagree(out, first, second):
    return BsgsOutput(
        out.bits,
        out.seed,
        out.p,
        out.a,
        out.b,
        out.n,
        out.P,
        out.Q,
        out.x,
        out.offset,
        out.giant_steps,
        out.ops,
        out.memory,
        _cross_check("disagree"),
        STATUS_DISAGREE,
        (first, second),
    )


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
        doc = parse_inputs(stdin.read())
    except InputError as exc:
        stderr.write(f"error: {exc}\n")
        return 1
    out = run(doc["bits"], doc["seed"], doc["p"], doc["a"], doc["b"], doc["n"], doc["P"], doc["Q"])
    stdout.write(out.to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
