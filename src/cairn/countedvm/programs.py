import hashlib
import math

from cairn.countedvm import expected_mul_ops

MAX_TABLE = 1_048_575
MAX_INDEX = 1_048_575
MAX_ORDER = (1 << 62) - 1
MAX_PARTITION_BITS = 5
MAX_RESTARTS = 32
MAX_DP_PARTITION_BITS = 7
MAX_THETA_BITS = 20
INNER_DEFAULT = 65_536
ALGORITHMS = {
    "rho": "seeded r-adding Floyd with bounded restarts",
    "bsgs": "full-point baby-step giant-step",
    "dp_rho": "seeded r-adding distinguished-point rho with bounded steps",
}
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
    "dp_table_entries": MAX_TABLE - 1,
    "dp_collision": "equal second coefficients halt with no result and i0 equal to MAX_INDEX",
    "dp_full_table": "a full distinguished-point table halts with no result",
    "dp_steps": "max_outer times max_inner bounds walk additions; exhaustion halts with no result",
    "dp_count": "setup_ops plus one counted addition per walk step; table scans consume instructions only",
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


def default_theta(bits):
    _integer("bits", bits, 1, MAX_ORDER.bit_length())
    return max(1, min(MAX_THETA_BITS, bits // 2 - 8))


def default_table_rows(n, theta_bits):
    _integer("n", n, 2, MAX_ORDER)
    _integer("theta_bits", theta_bits, 1, MAX_THETA_BITS)
    return 8 * (math.isqrt(n) >> theta_bits) + 64


def default_caps(n):
    _integer("n", n, 2, MAX_ORDER)
    steps = 8 * (math.isqrt(n) + 1)
    outer = (steps + INNER_DEFAULT - 1) // INNER_DEFAULT
    _integer("max_outer", outer, 0, MAX_INDEX)
    return outer, INNER_DEFAULT


def setup_ops(n, seed, partition_bits=5):
    _inputs(n, seed)
    _integer("n", n, 2, MAX_ORDER)
    _integer("partition_bits", partition_bits, 1, MAX_DP_PARTITION_BITS)
    total = sum(
        expected_mul_ops(_draw(n, seed, "step-a", j)) + expected_mul_ops(_draw(n, seed, "step-b", j)) + 1
        for j in range(1 << partition_bits)
    )
    return total + expected_mul_ops(_draw(n, seed, "start-a", 0)) + expected_mul_ops(_draw(n, seed, "start-b", 0)) + 1


def dp_rho_program(n, *, seed, theta_bits, partition_bits=5, max_outer, max_inner, table_rows=None):
    _inputs(n, seed)
    _integer("n", n, 2, MAX_ORDER)
    _integer("theta_bits", theta_bits, 1, MAX_THETA_BITS)
    _integer("partition_bits", partition_bits, 1, MAX_DP_PARTITION_BITS)
    _integer("max_outer", max_outer, 0, MAX_INDEX)
    _integer("max_inner", max_inner, 1, MAX_INDEX)
    rows = default_table_rows(n, theta_bits) if table_rows is None else table_rows
    _integer("table_rows", rows, 1, MAX_TABLE - 1)
    lines = [
        "setp p6 P",
        "setp p7 Q",
        "sset s8 0",
        "isinf i4 p7",
        "jnz i4 zero",
        "isinf i4 p6",
        "jnz i4 exhausted",
        f"table t0 {1 << partition_bits}",
        f"table t1 {rows}",
    ]
    for j in range(1 << partition_bits):
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
    lines.extend(
        [
            f"sset s0 {_draw(n, seed, 'start-a', 0)}",
            f"sset s1 {_draw(n, seed, 'start-b', 0)}",
            "mulp p0 p6 s0",
            "mulp p4 p7 s1",
            "addp p0 p0 p4",
            "iset i0 0",
            f"iset i7 {rows}",
            f"iset i1 {max_outer}",
            "jz i1 exhausted",
            "outer:",
            f"iset i2 {max_inner}",
            "inner:",
            *_step("p0", "s0", "s1", partition_bits),
            f"partition i5 p0 {theta_bits}",
            "jz i5 dp",
            "tail:",
            "isub i2 i2 1",
            "jnz i2 inner",
            "isub i1 i1 1",
            "jnz i1 outer",
            "exhausted:",
            "halt",
            "dp:",
            "tfind i3 t1 p0",
            "jnz i3 found",
            "ilt i6 i0 i7",
            "jz i6 full",
            "tstore t1 i0 p0 s0 s1",
            "iadd i0 i0 1",
            "jmp tail",
            "found:",
            "isub i3 i3 1",
            "tload p4 s2 s3 t1 i3",
            "seq i6 s1 s3",
            "jnz i6 useless",
            "solve s9 s0 s2 s1 s3",
            "result s9",
            "halt",
            "useless:",
            f"iset i0 {MAX_INDEX}",
            "halt",
            "full:",
            "halt",
            "zero:",
            "result s8",
            "halt",
        ]
    )
    if len(lines) >= 4000:
        raise ValueError(f"program has {len(lines)} lines; fewer than 4000 required, VM allows 4096")
    return "\n".join(lines) + "\n"
