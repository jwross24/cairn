import json
import statistics
import subprocess
import sys
import time

from cairn import cli, exits, log, pari
from cairn.errors import CliError
from cairn.skills import toy_curve

TARGET_TOY_CURVE_TRIES = "toy-curve-tries"
TARGETS = (TARGET_TOY_CURVE_TRIES,)
DEFAULT_SIZES = "30,40,50,60"
DEFAULT_SEEDS = 50
LAUNCH_ARGV = (sys.executable, "-m", "cairn.skills.toy_curve")
LAUNCH_TIMEOUT_S = 600.0
TABLE_HEADER = "| bits | seeds | mean tries | sd tries | min | max | per-try ms | in-process mean wall s | subprocess mean wall s |"
TABLE_RULE = "|---|---|---|---|---|---|---|---|---|"


def launch(bits, seed):
    argv = list(LAUNCH_ARGV)
    start = time.monotonic()
    proc = subprocess.run(argv, input=json.dumps({"bits": bits, "seed": seed}), capture_output=True, text=True, timeout=LAUNCH_TIMEOUT_S)
    wall = time.monotonic() - start
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()[-1:] or [""]
        raise CliError(exits.BACKEND, f"launch {' '.join(argv)} for bits={bits} seed={seed} exited {proc.returncode}: {tail[0]}", next_command="cairn doctor")
    try:
        out = toy_curve.ToyCurveOutput.from_json(proc.stdout)
    except toy_curve.InputError as exc:
        raise CliError(exits.BACKEND, f"launch {' '.join(argv)} for bits={bits} seed={seed} wrote malformed output: {exc}", next_command="cairn doctor") from None
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
            if (sub.p, sub.a, sub.b, sub.n, sub.P, sub.tries, sub.status) != (out.p, out.a, out.b, out.n, out.P, out.tries, out.status):
                raise CliError(exits.BACKEND, f"subprocess output for bits={bits} seed={seed} differs from the in-process run", next_command="cairn doctor")
            launch_walls.append(launch_wall)
            lg.debug("seed", bits=bits, seed=seed, tries=out.tries, wall_s=round(walls[-1], 4), launch_wall_s=round(launch_wall, 4))
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
        raise CliError(exits.USER_INPUT, f"--sizes must be comma-separated integers, got {text!r}", next_command="cairn measure --help") from None


def _configure(parser):
    parser.add_argument("target", nargs="?", default=TARGET_TOY_CURVE_TRIES, choices=TARGETS, help="what to measure")
    parser.add_argument("--sizes", default=DEFAULT_SIZES, metavar="BITS,BITS,...", help="bit sizes to measure")
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEEDS, metavar="N", help="seeds 1..N per size")


def _run(ns):
    sizes = parse_sizes(ns.sizes)
    if ns.seeds < 0:
        raise CliError(exits.USER_INPUT, f"--seeds must be >= 0, got {ns.seeds}", next_command="cairn measure --help")
    rows = toy_curve_tries(sizes, ns.seeds)
    if ns.json:
        cli.emit_json("measure", {"target": ns.target, "seeds": ns.seeds, "sizes": sizes, "launch_argv": list(LAUNCH_ARGV), "versions": pari.pari_versions(), "rows": rows})
    else:
        for line in table_lines(rows):
            print(line)
    return exits.OK


cli.register("measure", _configure, _run, summary="measure a skill's cost constant (toy-curve-tries: tries and subprocess wall over seeds 1..N per size)", read_only=True, json=True)
