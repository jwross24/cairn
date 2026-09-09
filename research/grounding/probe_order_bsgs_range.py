"""Per-curve cost of the gmpy2 Hasse-interval order search, at each size, over curves the
toy_curve skill draws.

CPU time is the reported figure because the host is shared: a wall figure taken under load
measures the load. Wall and the one-minute load average are recorded beside it so a reader
can see how contended the sample was.

Exits 1 without a table if the search disagrees with the PARI-counted order on any curve.
"""

import argparse
import json
import os
import statistics
import sys
import time
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from cairn.skills import order_bsgs_gmpy2 as gm  # noqa: E402
from cairn.skills import toy_curve  # noqa: E402

DEFAULT_SIZES = (30, 40, 50, 60)
DEFAULT_CURVES = 50
PLACES = Decimal("0.000001")


def _quantize(value):
    return str(Decimal(repr(value)).quantize(PLACES))


def _one_curve(bits, seed):
    curve = toy_curve.run(bits, seed)
    point = tuple(curve.P)
    cpu_start, wall_start = time.process_time(), time.monotonic()
    found = gm.orders_in_hasse(curve.p, curve.a, curve.b, point)
    cpu = time.process_time() - cpu_start
    wall = time.monotonic() - wall_start
    return curve, found, cpu, wall


def _summarize(name, values):
    return {
        f"{name}_min": _quantize(min(values)),
        f"{name}_median": _quantize(statistics.median(values)),
        f"{name}_max": _quantize(max(values)),
        f"{name}_sd": _quantize(statistics.stdev(values) if len(values) > 1 else 0.0),
    }


def measure(sizes, curves):
    rows = {}
    disagreements = []
    for bits in sizes:
        cpu_times, wall_times, ambiguous = [], [], 0
        for seed in range(1, curves + 1):
            curve, found, cpu, wall = _one_curve(bits, seed)
            if curve.n not in found:
                disagreements.append({"bits": bits, "seed": seed, "pari": curve.n, "bsgs": [int(m) for m in found]})
                continue
            if len(found) != 1:
                ambiguous += 1
            cpu_times.append(cpu)
            wall_times.append(wall)
        rows[bits] = {
            "curves": len(cpu_times),
            "table_points": int(gm.search_width(curve.p)),
            "ambiguous": ambiguous,
            **_summarize("cpu_s_per_curve", cpu_times),
            **_summarize("wall_s_per_curve", wall_times),
        }
    return rows, disagreements


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default=",".join(str(b) for b in DEFAULT_SIZES))
    parser.add_argument("--curves", type=int, default=DEFAULT_CURVES)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)
    sizes = [int(part) for part in args.sizes.split(",")]

    load_before = os.getloadavg()
    started = time.monotonic()
    rows, disagreements = measure(sizes, args.curves)
    elapsed = time.monotonic() - started
    load_after = os.getloadavg()

    if disagreements:
        sys.stderr.write("the search disagreed with the PARI-counted order:\n")
        sys.stderr.write(json.dumps(disagreements, indent=2) + "\n")
        return 1

    report = {
        "sizes": sizes,
        "curves_per_size": args.curves,
        "cores": os.cpu_count(),
        "load_average_1m_before": round(load_before[0], 2),
        "load_average_1m_after": round(load_after[0], 2),
        "elapsed_s": round(elapsed, 1),
        "rows": rows,
    }
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"{args.curves} curves per size from cairn.skills.toy_curve.run(bits, seed) for seed 1..{args.curves}")
    print(f"every curve's order agreed with the PARI count; {os.cpu_count()} cores")
    print(f"load average 1m: {load_before[0]:.2f} before, {load_after[0]:.2f} after; elapsed {elapsed:.1f} s")
    print()
    header = f"{'bits':>5} {'curves':>7} {'table':>8} {'ambig':>6} {'cpu min':>12} {'cpu median':>12} {'cpu max':>12} {'cpu sd':>12} {'wall median':>12}"
    print(header)
    for bits in sizes:
        row = rows[bits]
        print(
            f"{bits:>5} {row['curves']:>7} {row['table_points']:>8} {row['ambiguous']:>6} "
            f"{row['cpu_s_per_curve_min']:>12} {row['cpu_s_per_curve_median']:>12} "
            f"{row['cpu_s_per_curve_max']:>12} {row['cpu_s_per_curve_sd']:>12} "
            f"{row['wall_s_per_curve_median']:>12}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
