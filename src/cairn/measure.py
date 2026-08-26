import json
import math
import random
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass

from cairn import cli, exits, log, pari, verifier
from cairn.errors import CliError
from cairn.skills import toy_curve

TARGET_TOY_CURVE_TRIES = "toy-curve-tries"
TARGET_RHO60 = "rho60"
TARGETS = (TARGET_TOY_CURVE_TRIES, TARGET_RHO60)
DEFAULT_SIZES = "30,40,50,60"
DEFAULT_SEEDS = 50
LAUNCH_ARGV = (sys.executable, "-m", "cairn.skills.toy_curve")
LAUNCH_TIMEOUT_S = 600.0
TABLE_HEADER = "| bits | seeds | mean tries | sd tries | min | max | per-try ms | in-process mean wall s | subprocess mean wall s |"
TABLE_RULE = "|---|---|---|---|---|---|---|---|---|"

RHO40_BITS = 40
RHO60_BITS = 60
RHO_INSTANCE_SEED = 1
RHO_R = 20
RHO_THETA_BITS = 10
RHO_LOG_EVERY = 10**6
RHO_CLOCK_EVERY = 1000
RHO_MIN_RATE_OPS = 10**6
RHO40_CAP_OPS = 10**9
DEFAULT_CAP_OPS = 100_000_000
DEFAULT_CAP_MINUTES = 30.0
RHO60_ORDER = 866004985024698433
EXTRAPOLATION_TAG = "CONJECTURE"
STOP_SOLVED = "solved"
STOP_CAP_OPS = "cap-ops"
STOP_CAP_MINUTES = "cap-minutes"


class RefusedTooFewOps(ValueError):
    pass


def expected_rho_ops(order):
    return int(math.sqrt(math.pi * order / 2))


RHO60_EXPECTED_OPS = expected_rho_ops(RHO60_ORDER)


@dataclass(frozen=True)
class RateRow:
    ops: int
    elapsed_s: float
    ops_per_s: float
    expected_ops: int
    extrapolated_wall_s: float
    tag: str

    def as_dict(self):
        return {
            "ops": self.ops,
            "elapsed_s": round(self.elapsed_s, 3),
            "ops_per_s": round(self.ops_per_s, 1),
            "expected_ops": self.expected_ops,
            "extrapolated_wall_s": round(self.extrapolated_wall_s, 1),
            "tag": self.tag,
        }


def rate_report(ops, elapsed_s, expected_ops=RHO60_EXPECTED_OPS):
    if ops < RHO_MIN_RATE_OPS:
        raise RefusedTooFewOps(
            f"the walk counted {ops} group ops, fewer than 1e6 ops; raise --cap-ops to report a rate"
        )
    if elapsed_s <= 0:
        raise RefusedTooFewOps(f"the walk counted {ops} group ops in {elapsed_s}s; raise --cap-ops to report a rate")
    rate = ops / elapsed_s
    return RateRow(ops, elapsed_s, rate, expected_ops, expected_ops / rate, EXTRAPOLATION_TAG)


@dataclass(frozen=True)
class RhoRun:
    bits: int
    p: int
    a: int
    b: int
    n: int
    P: tuple
    Q: tuple
    secret: int
    x: int | None
    ops: int
    elapsed_s: float
    stop: str

    def instance(self):
        return verifier.Instance(self.p, self.a, self.b, self.n, self.P, self.Q)

    def as_dict(self):
        return {
            "bits": self.bits,
            "instance_hash": self.instance().instance_hash,
            "ops": self.ops,
            "elapsed_s": round(self.elapsed_s, 3),
            "ops_per_s": round(self.ops / self.elapsed_s, 1) if self.elapsed_s > 0 else None,
            "stop": self.stop,
            "x": self.x,
        }


def _solve(alpha_a, beta_a, alpha_b, beta_b, n):
    delta = (beta_b - beta_a) % n
    if delta == 0:
        return None
    return ((alpha_a - alpha_b) * pow(delta, -1, n)) % n


def _log_progress(lg, bits, ops, elapsed, distinguished):
    lg.info(
        "progress",
        bits=bits,
        ops=ops,
        elapsed_s=round(elapsed, 3),
        ops_per_s=round(ops / elapsed, 1) if elapsed > 0 else None,
        distinguished=distinguished,
    )


def rho(
    bits,
    *,
    seed=RHO_INSTANCE_SEED,
    cap_ops=RHO40_CAP_OPS,
    cap_minutes=DEFAULT_CAP_MINUTES,
    theta_bits=RHO_THETA_BITS,
):
    lg = log.get("measure.rho")
    curve = toy_curve.run(bits, seed)
    p, a, b, n, P = curve.p, curve.a, curve.b, curve.n, tuple(curve.P)
    rng = random.Random(f"cairn-rho/{bits}/{seed}")  # noqa: S311
    secret = rng.randrange(1, n)
    E = pari.pari.ellinit([a, b], p)
    elladd = pari.pari.elladd
    ellmul = pari.pari.ellmul
    Pt = pari.pari.Vec(list(P))
    Qt = ellmul(E, Pt, secret)
    Q = (int(Qt[0]), int(Qt[1]))
    coeffs = [(rng.randrange(1, n), rng.randrange(1, n)) for _ in range(RHO_R)]
    steps = [elladd(E, ellmul(E, Pt, u), ellmul(E, Qt, v)) for u, v in coeffs]
    alpha, beta = rng.randrange(1, n), rng.randrange(1, n)
    cur = elladd(E, ellmul(E, Pt, alpha), ellmul(E, Qt, beta))
    mask = (1 << theta_bits) - 1
    seen = {}
    ops = 0
    x = None
    stop = STOP_CAP_OPS
    lg.info(
        "start", bits=bits, seed=seed, n=n, cap_ops=cap_ops, cap_minutes=cap_minutes, r=RHO_R, theta_bits=theta_bits
    )
    start = time.monotonic()
    cap_seconds = cap_minutes * 60.0
    while True:
        xi = int(cur[0])
        if not xi & mask:
            key = (xi, int(cur[1])) if len(cur) == 2 else (xi,)
            prev = seen.get(key)
            if prev is None:
                seen[key] = (alpha, beta)
            else:
                candidate = _solve(prev[0], prev[1], alpha, beta, n)
                if candidate is not None:
                    x = candidate
                    stop = STOP_SOLVED
                    break
        u, v = coeffs[xi % RHO_R]
        alpha = (alpha + u) % n
        beta = (beta + v) % n
        cur = elladd(E, cur, steps[xi % RHO_R])
        ops += 1
        if ops >= cap_ops:
            stop = STOP_CAP_OPS
            break
        if ops % RHO_CLOCK_EVERY == 0:
            elapsed = time.monotonic() - start
            if ops % RHO_LOG_EVERY == 0:
                _log_progress(lg, bits, ops, elapsed, len(seen))
            if elapsed >= cap_seconds:
                stop = STOP_CAP_MINUTES
                break
    elapsed = time.monotonic() - start
    _log_progress(lg, bits, ops, elapsed, len(seen))
    run = RhoRun(bits, p, a, b, n, P, Q, secret, x, ops, elapsed, stop)
    lg.info("stop", **run.as_dict())
    return run


def rho60_report(cap_ops, cap_minutes):
    run40 = rho(RHO40_BITS, cap_ops=RHO40_CAP_OPS, cap_minutes=cap_minutes)
    if run40.stop != STOP_SOLVED:
        raise CliError(
            exits.BACKEND,
            f"the {RHO40_BITS}-bit rho stopped on {run40.stop} after {run40.ops} ops without a discrete log",
            next_command="cairn doctor",
        )
    verdict = verifier.Verifier().run(run40.instance(), run40.x)
    if not verdict.accepted:
        raise CliError(
            exits.BACKEND,
            f"the {RHO40_BITS}-bit rho's x was refused by the Tier-0 verifier: {verdict.reason}",
            next_command="cairn doctor",
        )
    run60 = rho(RHO60_BITS, cap_ops=cap_ops, cap_minutes=cap_minutes)
    if run60.n != RHO60_ORDER:
        raise CliError(
            exits.BACKEND,
            f"toy_curve({RHO60_BITS}, {RHO_INSTANCE_SEED}) has order {run60.n}, not the recorded {RHO60_ORDER}",
            next_command="cairn doctor",
        )
    row = rate_report(run60.ops, run60.elapsed_s, expected_rho_ops(run60.n))
    return run40, verdict, run60, row


def launch(bits, seed):
    argv = list(LAUNCH_ARGV)
    start = time.monotonic()
    proc = subprocess.run(
        argv, input=json.dumps({"bits": bits, "seed": seed}), capture_output=True, text=True, timeout=LAUNCH_TIMEOUT_S
    )
    wall = time.monotonic() - start
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()[-1:] or [""]
        raise CliError(
            exits.BACKEND,
            f"launch {' '.join(argv)} for bits={bits} seed={seed} exited {proc.returncode}: {tail[0]}",
            next_command="cairn doctor",
        )
    try:
        out = toy_curve.ToyCurveOutput.from_json(proc.stdout)
    except toy_curve.InputError as exc:
        raise CliError(
            exits.BACKEND,
            f"launch {' '.join(argv)} for bits={bits} seed={seed} wrote malformed output: {exc}",
            next_command="cairn doctor",
        ) from None
    return wall, out


def _row(bits, tries, walls, launch_walls):
    total_tries = sum(tries)
    return {
        "bits": bits,
        "seeds": len(tries),
        "mean_tries": round(statistics.fmean(tries), 2),
        "sd_tries": round(statistics.stdev(tries), 2) if len(tries) > 1 else 0.0,
        "min_tries": min(tries),
        "max_tries": max(tries),
        "per_try_ms": round(sum(walls) / total_tries * 1000, 3),
        "in_process_mean_wall_s": round(statistics.fmean(walls), 4),
        "mean_wall_s": round(statistics.fmean(launch_walls), 4),
    }


def toy_curve_tries(sizes, seeds):
    lg = log.get("measure.toy_curve_tries")
    rows = []
    for bits in sizes:
        tries, walls, launch_walls = [], [], []
        for seed in range(1, seeds + 1):
            start = time.monotonic()
            out = toy_curve.run(bits, seed)
            walls.append(time.monotonic() - start)
            tries.append(out.tries)
            launch_wall, sub = launch(bits, seed)
            if (sub.p, sub.a, sub.b, sub.n, sub.P, sub.tries, sub.status) != (
                out.p,
                out.a,
                out.b,
                out.n,
                out.P,
                out.tries,
                out.status,
            ):
                raise CliError(
                    exits.BACKEND,
                    f"subprocess output for bits={bits} seed={seed} differs from the in-process run",
                    next_command="cairn doctor",
                )
            launch_walls.append(launch_wall)
            lg.debug(
                "seed",
                bits=bits,
                seed=seed,
                tries=out.tries,
                wall_s=round(walls[-1], 4),
                launch_wall_s=round(launch_wall, 4),
            )
        if tries:
            row = _row(bits, tries, walls, launch_walls)
            lg.info("size", **row)
            rows.append(row)
    return rows


def table_lines(rows):
    return [
        TABLE_HEADER,
        TABLE_RULE,
        *(
            f"| {r['bits']} | {r['seeds']} | {r['mean_tries']:.2f} | {r['sd_tries']:.2f} | {r['min_tries']} | {r['max_tries']} | {r['per_try_ms']:.3f} | {r['in_process_mean_wall_s']:.4f} | {r['mean_wall_s']:.4f} |"
            for r in rows
        ),
    ]


def parse_sizes(text):
    try:
        return [int(part) for part in text.split(",") if part.strip()]
    except ValueError:
        raise CliError(
            exits.USER_INPUT,
            f"--sizes must be comma-separated integers, got {text!r}",
            next_command="cairn measure --help",
        ) from None


def _configure(parser):
    parser.add_argument("target", nargs="?", default=TARGET_TOY_CURVE_TRIES, choices=TARGETS, help="what to measure")
    parser.add_argument("--sizes", default=DEFAULT_SIZES, metavar="BITS,BITS,...", help="bit sizes to measure")
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEEDS, metavar="N", help="seeds 1..N per size")
    parser.add_argument(
        "--cap-ops",
        type=int,
        default=DEFAULT_CAP_OPS,
        metavar="N",
        help="rho60: stop the 60-bit walk after N group ops",
    )
    parser.add_argument(
        "--cap-minutes",
        type=float,
        default=DEFAULT_CAP_MINUTES,
        metavar="M",
        help="rho60: stop the 60-bit walk after M minutes",
    )


def _rho60(ns):
    if ns.cap_ops < 1:
        raise CliError(
            exits.USER_INPUT, f"--cap-ops must be >= 1, got {ns.cap_ops}", next_command="cairn measure --help"
        )
    if ns.cap_minutes <= 0:
        raise CliError(
            exits.USER_INPUT, f"--cap-minutes must be > 0, got {ns.cap_minutes}", next_command="cairn measure --help"
        )
    try:
        run40, verdict, run60, row = rho60_report(ns.cap_ops, ns.cap_minutes)
    except RefusedTooFewOps as exc:
        raise CliError(exits.USER_INPUT, str(exc), next_command="cairn measure rho60 --cap-ops 100000000") from None
    if ns.json:
        cli.emit_json(
            "measure",
            {
                "target": TARGET_RHO60,
                "bits": run60.bits,
                "instance_hash": run60.instance().instance_hash,
                "stop": run60.stop,
                **row.as_dict(),
                "verified_x": run40.x,
                "rho40": {**run40.as_dict(), "accepted": verdict.accepted, "verifier_wall_s": verdict.wall_s},
                "versions": pari.pari_versions(),
            },
        )
    else:
        for line in rho_table_lines(run40, verdict, run60, row):
            print(line)
    return exits.OK


RHO_TABLE_HEADER = "| bits | ops | elapsed s | ops/s | expected ops | extrapolated wall s | stop | tag |"
RHO_TABLE_RULE = "|---|---|---|---|---|---|---|---|"


def rho_table_lines(run40, verdict, run60, row):
    return [
        RHO_TABLE_HEADER,
        RHO_TABLE_RULE,
        f"| {run40.bits} | {run40.ops} | {run40.elapsed_s:.3f} | {run40.ops / run40.elapsed_s:.1f} | "
        f"{expected_rho_ops(run40.n)} | — | {run40.stop} | STRONG-EMPIRICAL |",
        f"| {run60.bits} | {row.ops} | {row.elapsed_s:.3f} | {row.ops_per_s:.1f} | {row.expected_ops} | "
        f"{row.extrapolated_wall_s:.1f} | {run60.stop} | {row.tag} |",
        f"verified_x={run40.x} accepted={verdict.accepted} reason={verdict.reason}",
    ]


def _run(ns):
    if ns.target == TARGET_RHO60:
        return _rho60(ns)
    sizes = parse_sizes(ns.sizes)
    if ns.seeds < 0:
        raise CliError(exits.USER_INPUT, f"--seeds must be >= 0, got {ns.seeds}", next_command="cairn measure --help")
    rows = toy_curve_tries(sizes, ns.seeds)
    if ns.json:
        cli.emit_json(
            "measure",
            {
                "target": ns.target,
                "seeds": ns.seeds,
                "sizes": sizes,
                "launch_argv": list(LAUNCH_ARGV),
                "versions": pari.pari_versions(),
                "rows": rows,
            },
        )
    else:
        for line in table_lines(rows):
            print(line)
    return exits.OK


cli.register(
    "measure",
    _configure,
    _run,
    summary="measure a skill's cost constant (toy-curve-tries: tries and subprocess wall over seeds 1..N per size; rho60: interpreted Pollard rho rate at 60 bits with a completed 40-bit rho)",
    read_only=True,
    json=True,
)
