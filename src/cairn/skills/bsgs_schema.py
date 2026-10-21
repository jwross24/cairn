from cairn.canon import INT, STR, Field, List, Map, Optional, Struct

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
