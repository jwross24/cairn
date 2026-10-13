from cairn.countedvm.programs import (
    MAX_DP_PARTITION_BITS,
    MAX_INDEX,
    MAX_ORDER,
    MAX_TABLE,
    MAX_THETA_BITS,
    _draw,
    _inputs,
    _integer,
    default_caps,
    default_table_rows,
    default_theta,
    setup_ops,
)

INSTRUCTION_SET = "signed/1"
__all__ = ["INSTRUCTION_SET", "default_caps", "default_theta", "negation_dp_rho_program", "setup_ops"]


def negation_dp_rho_program(n, *, seed, theta_bits, partition_bits=5, max_outer, max_inner, table_rows=None):
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
            "canonicalp p0 p0 i4",
            "jz i4 start",
            "sneg s0 s0",
            "sneg s1 s1",
            "start:",
            "canonicalp p1 p0 i15",
            "canonicalp p5 p0 i15",
            "iset i0 0",
            "iset i9 0",
            "iset i10 32",
            "iset i12 0",
            f"iset i13 {1 << partition_bits}",
            f"iset i7 {rows}",
            f"iset i1 {max_outer}",
            "jz i1 exhausted",
            "outer:",
            f"iset i2 {max_inner}",
            "inner:",
            "canonicalp p2 p1 i15",
            "canonicalp p1 p0 i15",
            "jnz i9 escape",
            f"partition i4 p0 {partition_bits}",
            "tload p3 s4 s5 t0 i4",
            "addp p0 p0 p3",
            "sadd s0 s0 s4",
            "sadd s1 s1 s5",
            "jmp normalize",
            "escape:",
            "tload p3 s4 s5 t0 i12",
            "addp p0 p0 p3",
            "sadd s0 s0 s4",
            "sadd s1 s1 s5",
            "iadd i12 i12 1",
            "ilt i4 i12 i13",
            "jnz i4 escaped",
            "iset i12 0",
            "escaped:",
            "iset i9 0",
            "normalize:",
            "canonicalp p0 p0 i4",
            "jz i4 cycle",
            "sneg s0 s0",
            "sneg s1 s1",
            "cycle:",
            "eqp i9 p0 p2",
            "eqp i4 p0 p5",
            "jz i4 checkpoint",
            "iset i9 1",
            "checkpoint:",
            "isub i10 i10 1",
            "jnz i10 distinguish",
            "canonicalp p5 p0 i15",
            "iset i10 32",
            "distinguish:",
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
            "jz i6 exhausted",
            "tstore t1 i0 p0 s0 s1",
            "iadd i0 i0 1",
            "jmp tail",
            "found:",
            "isub i3 i3 1",
            "tload p4 s2 s3 t1 i3",
            "seq i6 s1 s3",
            "jnz i6 useless",
            "solve s10 s0 s2 s1 s3",
            "result s10",
            "halt",
            "useless:",
            "iset i9 1",
            "jmp tail",
            "zero:",
            "result s8",
            "halt",
        ]
    )
    if len(lines) >= 4000:
        raise ValueError(f"program has {len(lines)} lines; fewer than 4000 required, VM allows 4096")
    return "\n".join(lines) + "\n"
