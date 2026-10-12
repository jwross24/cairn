import hashlib
import math

MAX_TABLE = 1_048_575
MAX_INDEX = 1_048_575
MAX_ORDER = (1 << 62) - 1
MAX_PARTITION_BITS = 5
MAX_RESTARTS = 32
ALGORITHMS = {"rho": "seeded r-adding Floyd with bounded restarts", "bsgs": "full-point baby-step giant-step"}
LIMITATIONS = {
    "table_lookup": "tfind scans linearly and charges every scanned row to the instruction budget",
    "table_entries": MAX_TABLE,
    "counter_maximum": MAX_INDEX,
    "rho_collision": "a noninvertible denominator refuses as zero_denominator; prime-order groups are intended",
    "rho_steps": "max_steps bounds Floyd iterations per restart; each executes three counted walk additions",
    "rho_exhaustion": "bounded fruitless walks halt with no result",
    "solve": "terminal; independent xP == Q verification is required after launch",
    "performance": "bounded reference programs, without a ladder performance or calibration claim",
    "baseline_profiles": "different walks and tables from the Python skills; their cost profiles do not apply",
}


def _integer(name, value, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"{name} must be an integer in [{lower}, {upper}]")


def _inputs(n, seed):
    _integer("n", n, 1, MAX_ORDER)
    if type(seed) is not int:
        raise ValueError("seed must be an integer")


def _draw(n, seed, label, index):
    material = f"cairn-countedvm-rho/1:{seed}:{label}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(material).digest(), "big") % (n - 1) + 1


def bsgs_program(n, *, seed=0):
    _inputs(n, seed)
    m = math.isqrt(n - 1) + 1
    if m > MAX_TABLE:
        raise ValueError(f"BSGS requires {m} baby entries; MAX_TABLE is {MAX_TABLE}")
    if n == 1:
        return "setp p0 Q\nisinf i0 p0\njz i0 exhausted\nsset s0 0\nresult s0\nexhausted:\nhalt\n"
    offset = seed % n
    giant_limit = (n + m - 1) // m
    return f"""setp p0 P
setp p1 Q
setp p2 inf
sset s0 0
sset s1 1
sset s2 {offset}
sset s3 {m % n}
sset s4 0
iset i0 0
iset i1 {m}
table t0 {m}
babies:
tstore t0 i0 p2 s0 s4
addp p2 p2 p0
sadd s0 s0 s1
iadd i0 i0 1
ilt i2 i0 i1
jnz i2 babies
negp p3 p2
mulp p4 p0 s2
negp p4 p4
addp p4 p1 p4
iset i0 0
iset i1 {giant_limit}
giants:
tfind i2 t0 p4
jz i2 advance
isub i2 i2 1
tload p2 s0 s4 t0 i2
sadd s9 s2 s0
mulp p5 p0 s9
eqp i3 p5 p1
jz i3 advance
result s9
halt
advance:
iadd i0 i0 1
ilt i2 i0 i1
jz i2 exhausted
addp p4 p4 p3
sadd s2 s2 s3
jmp giants
exhausted:
halt
"""


def _step(point, alpha, beta, partition_bits):
    return [
        f"partition i4 {point} {partition_bits}",
        "tload p3 s4 s5 t0 i4",
        f"addp {point} {point} p3",
        f"sadd {alpha} {alpha} s4",
        f"sadd {beta} {beta} s5",
    ]


def rho_program(n, *, seed=0, max_steps=MAX_INDEX, restarts=8, partition_bits=5):
    _inputs(n, seed)
    _integer("n", n, 2, MAX_ORDER)
    _integer("max_steps", max_steps, 1, MAX_INDEX)
    _integer("restarts", restarts, 1, MAX_RESTARTS)
    _integer("partition_bits", partition_bits, 1, MAX_PARTITION_BITS)
    r = 1 << partition_bits
    lines = [
        "setp p6 P",
        "setp p7 Q",
        "setp p8 inf",
        "sset s8 0",
        "isinf i4 p7",
        "jnz i4 zero",
        "isinf i4 p6",
        "jnz i4 exhausted",
        f"table t0 {r}",
        f"table t1 {restarts}",
    ]
    for j in range(r):
        lines.extend(
            [
                f"iset i4 {j}",
                f"sset s4 {_draw(n, seed, 'step-a', j)}",
                f"sset s5 {_draw(n, seed, 'step-b', j)}",
                "mulp p3 p6 s4",
                "mulp p4 p7 s5",
                "addp p3 p3 p4",
                "tstore t0 i4 p3 s4 s5",
            ]
        )
    for j in range(restarts):
        lines.extend(
            [
                f"iset i4 {j}",
                f"sset s4 {_draw(n, seed, 'start-a', j)}",
                f"sset s5 {_draw(n, seed, 'start-b', j)}",
                "tstore t1 i4 p8 s4 s5",
            ]
        )
    lines.extend(
        [
            "iset i0 0",
            f"iset i1 {restarts}",
            "restart:",
            "tload p0 s0 s1 t1 i0",
            "mulp p0 p6 s0",
            "mulp p4 p7 s1",
            "addp p0 p0 p4",
            "addp p1 p0 p8",
            "sadd s2 s0 s8",
            "sadd s3 s1 s8",
            f"iset i2 {max_steps}",
            "walk:",
            *_step("p0", "s0", "s1", partition_bits),
            *_step("p1", "s2", "s3", partition_bits),
            *_step("p1", "s2", "s3", partition_bits),
            "eqp i4 p0 p1",
            "jnz i4 collision",
            "isub i2 i2 1",
            "jnz i2 walk",
            "jmp next_restart",
            "collision:",
            "seq i4 s1 s3",
            "jnz i4 next_restart",
            "solve s9 s0 s2 s1 s3",
            "result s9",
            "halt",
            "next_restart:",
            "iadd i0 i0 1",
            "ilt i4 i0 i1",
            "jnz i4 restart",
            "exhausted:",
            "halt",
            "zero:",
            "result s8",
            "halt",
        ]
    )
    return "\n".join(lines) + "\n"
