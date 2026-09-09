"""Per-group-operation cost of four elliptic-curve arithmetic implementations.

Operator decision 12 (PLAN section 16) asks for the fastest arithmetic a method could
carry, so the ladder's clock check can bound uncounted work. The number the gate bundle
stores is a COST in seconds per group operation, never a throughput: `ladderplan` divides
by it, so a reciprocal stored here inverts the bound the plan validates.

The curve is `tests/vectors/curve60_seed1.json`, a 60-bit prime-order toy curve, inlined
here so the probe stands alone. Every arm walks the same deterministic chain of group
operations and must land on the same point; an arm that disagrees is not measuring the
same work and the probe refuses.

The compiler is invoked by absolute path because an interactive shell on this machine can
alias `cc` to something that is not a compiler.
"""

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

P = 866004983247663323
A = 645824996691681933
B = 382308953708622014
N = 866004982950395713
GX = 258236120896152398
GY = 475063108841005863

DEFAULT_OPS = 10_000
DEFAULT_REPS = 7
CC = "/usr/bin/clang"
CFLAGS = ("-O2", "-std=c11", "-Wall")

C_SOURCE = r"""
#include <stdint.h>
#include <stdio.h>
#include <time.h>

typedef unsigned __int128 u128;
typedef uint64_t u64;

static u64 p, a_coeff;

static u64 mulmod(u64 x, u64 y) { return (u64)(((u128)x * (u128)y) % (u128)p); }
static u64 addmod(u64 x, u64 y) { u64 s = x + y; return s >= p ? s - p : s; }
static u64 submod(u64 x, u64 y) { return x >= y ? x - y : x + p - y; }

static u64 invmod(u64 x) {
    int64_t t = 0, newt = 1;
    int64_t r = (int64_t)p, newr = (int64_t)x;
    while (newr != 0) {
        int64_t q = r / newr;
        int64_t tmp = t - q * newt; t = newt; newt = tmp;
        tmp = r - q * newr; r = newr; newr = tmp;
    }
    if (t < 0) t += (int64_t)p;
    return (u64)t;
}

typedef struct { u64 x, y; int inf; } pt;

static pt ec_double(pt v) {
    pt out; out.inf = 0; out.x = 0; out.y = 0;
    if (v.inf || v.y == 0) { out.inf = 1; return out; }
    u64 num = addmod(mulmod(3, mulmod(v.x, v.x)), a_coeff);
    u64 lam = mulmod(num, invmod(addmod(v.y, v.y)));
    u64 x3 = submod(mulmod(lam, lam), addmod(v.x, v.x));
    out.x = x3;
    out.y = submod(mulmod(lam, submod(v.x, x3)), v.y);
    return out;
}

static pt ec_add(pt l, pt r) {
    if (l.inf) return r;
    if (r.inf) return l;
    if (l.x == r.x) {
        if (addmod(l.y, r.y) == 0) { pt out; out.inf = 1; out.x = 0; out.y = 0; return out; }
        return ec_double(l);
    }
    u64 lam = mulmod(submod(r.y, l.y), invmod(submod(r.x, l.x)));
    u64 x3 = submod(submod(mulmod(lam, lam), l.x), r.x);
    pt out; out.inf = 0; out.x = x3;
    out.y = submod(mulmod(lam, submod(l.x, x3)), l.y);
    return out;
}

int main(int argc, char **argv) {
    unsigned long long ops;
    unsigned long long gx, gy;
    sscanf(argv[1], "%llu", (unsigned long long *)&p);
    sscanf(argv[2], "%llu", (unsigned long long *)&a_coeff);
    sscanf(argv[3], "%llu", &gx);
    sscanf(argv[4], "%llu", &gy);
    sscanf(argv[5], "%llu", &ops);

    pt base; base.x = (u64)gx; base.y = (u64)gy; base.inf = 0;
    pt acc = base;
    struct timespec t0, t1;
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &t0);
    for (unsigned long long i = 0; i < ops; i++) {
        acc = (i % 2 == 0) ? ec_double(acc) : ec_add(acc, base);
    }
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &t1);
    double cpu = (double)(t1.tv_sec - t0.tv_sec) + 1e-9 * (double)(t1.tv_nsec - t0.tv_nsec);
    printf("{\"cpu_s\": %.9f, \"x\": %llu, \"y\": %llu, \"inf\": %d}\n",
           cpu, (unsigned long long)acc.x, (unsigned long long)acc.y, acc.inf);
    return 0;
}
"""


def _chain(double_fn, add_fn, base, ops):
    acc = base
    for i in range(ops):
        acc = double_fn(acc) if i % 2 == 0 else add_fn(acc, base)
    return acc


def _python_int(ops):
    from cairn import ec

    base = (GX, GY)
    start = time.process_time()
    acc = _chain(lambda v: ec.double(P, A, v), lambda left, right: ec.add(P, A, left, right), base, ops)
    return time.process_time() - start, acc


def _gmpy2(ops):
    import gmpy2

    p = gmpy2.mpz(P)
    a = gmpy2.mpz(A)
    three = gmpy2.mpz(3)
    two = gmpy2.mpz(2)

    def double(v):
        if v is None:
            return None
        x, y = v
        if y == 0:
            return None
        lam = (three * x * x + a) * gmpy2.invert(two * y, p) % p
        x3 = (lam * lam - two * x) % p
        return x3, (lam * (x - x3) - y) % p

    def add(left, right):
        if left is None:
            return right
        if right is None:
            return left
        x1, y1 = left
        x2, y2 = right
        if x1 == x2:
            if (y1 + y2) % p == 0:
                return None
            return double(left)
        lam = (y2 - y1) * gmpy2.invert(x2 - x1, p) % p
        x3 = (lam * lam - x1 - x2) % p
        return x3, (lam * (x1 - x3) - y1) % p

    base = (gmpy2.mpz(GX), gmpy2.mpz(GY))
    start = time.process_time()
    acc = _chain(double, add, base, ops)
    return time.process_time() - start, None if acc is None else (int(acc[0]), int(acc[1]))


def _cypari2(ops):
    from cairn.pari import pari

    curve = pari.ellinit([0, 0, 0, A, B], P)
    base = pari([GX, GY])
    start = time.process_time()
    acc = _chain(lambda v: pari.elladd(curve, v, v), lambda left, right: pari.elladd(curve, left, right), base, ops)
    spent = time.process_time() - start
    if len(acc) == 1:
        return spent, None
    return spent, (int(acc[0]), int(acc[1]))


def _build_c(scratch):
    source = Path(scratch) / "ecbench.c"
    binary = Path(scratch) / "ecbench"
    source.write_text(C_SOURCE)
    subprocess.run([CC, *CFLAGS, "-o", str(binary), str(source)], check=True, capture_output=True)
    return binary


def _c_reference(binary, ops):
    out = subprocess.run(
        [str(binary), str(P), str(A), str(GX), str(GY), str(ops)], check=True, capture_output=True, text=True
    )
    parsed = json.loads(out.stdout)
    point = None if parsed["inf"] else (parsed["x"], parsed["y"])
    return parsed["cpu_s"], point


def _summarize(name, costs, point):
    per_op = sorted(costs)
    return {
        "arm": name,
        "reps": len(costs),
        "final_point": None if point is None else [str(point[0]), str(point[1])],
        "cost_s_per_group_op_min": f"{per_op[0]:.12f}",
        "cost_s_per_group_op_median": f"{statistics.median(per_op):.12f}",
        "cost_s_per_group_op_max": f"{per_op[-1]:.12f}",
        "cost_s_per_group_op_sd": f"{(statistics.stdev(per_op) if len(per_op) > 1 else 0.0):.12f}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", type=int, default=DEFAULT_OPS)
    ap.add_argument("--reps", type=int, default=DEFAULT_REPS)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args()
    if ns.ops < 1000:
        print(f"decision 12 asks for at least 1000 operations per arm, got {ns.ops}", file=sys.stderr)
        return 2

    scratch = tempfile.mkdtemp(prefix="cairn-clock-ref-")
    binary = _build_c(scratch)
    compiler = subprocess.run([CC, "--version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]

    arms = {
        "python_int": lambda: _python_int(ns.ops),
        "gmpy2": lambda: _gmpy2(ns.ops),
        "cypari2": lambda: _cypari2(ns.ops),
        "c_reference": lambda: _c_reference(binary, ns.ops),
    }

    records = []
    points = {}
    for name, run in arms.items():
        costs = []
        point = None
        for _ in range(ns.reps):
            spent, point = run()
            costs.append(spent / ns.ops)
        points[name] = point
        records.append(_summarize(name, costs, point))

    distinct = {json.dumps(p) for p in points.values()}
    if len(distinct) != 1:
        print(f"arms walked to different points, so they are not measuring the same work: {points}", file=sys.stderr)
        return 1

    fastest = min(records, key=lambda r: float(r["cost_s_per_group_op_median"]))
    report = {
        "curve": {"bits": 60, "p": str(P), "a": str(A), "b": str(B), "n": str(N)},
        "ops_per_arm_per_rep": ns.ops,
        "reps": ns.reps,
        "compiler": compiler,
        "cflags": list(CFLAGS),
        "scratch": scratch,
        "agreed_final_point": records[0]["final_point"],
        "arms": records,
        "fastest": {
            "arm": fastest["arm"],
            "cost_s_per_group_op": fastest["cost_s_per_group_op_median"],
        },
    }

    if ns.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print(f"curve 60-bit p={P}")
    print(f"{ns.ops} group operations per arm per rep, {ns.reps} reps")
    print(f"compiler {compiler} {' '.join(CFLAGS)}")
    print(f"all arms agree on {records[0]['final_point']}")
    print()
    print(f"{'arm':<14}{'min':>18}{'median':>18}{'max':>18}{'sd':>18}")
    for r in records:
        print(
            f"{r['arm']:<14}"
            f"{r['cost_s_per_group_op_min']:>18}"
            f"{r['cost_s_per_group_op_median']:>18}"
            f"{r['cost_s_per_group_op_max']:>18}"
            f"{r['cost_s_per_group_op_sd']:>18}"
        )
    print()
    print(f"fastest: {fastest['arm']} at {fastest['cost_s_per_group_op_median']} seconds per group operation")
    print(f"scratch build dir: {scratch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
