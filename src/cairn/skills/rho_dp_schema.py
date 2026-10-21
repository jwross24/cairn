from cairn.canon import BOOL, INT, STR, Field, List, Map, Optional, Struct
from cairn.profile import CostProfile, Production, SizeCost, Verification

REPLAY_GRADE = "Verifiable"
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
