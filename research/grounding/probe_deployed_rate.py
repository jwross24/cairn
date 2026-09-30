import argparse
import contextlib
import hashlib
import importlib
import json
import platform
import subprocess
import sys
import threading
import time
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

counted = importlib.import_module("research.grounding.probe_counted_process")
paired = importlib.import_module("research.grounding.probe_paired_rate")

LADDER_PLAN = ROOT / "bundle" / "ladder_plan.json"
PREREGISTERED = {
    "pairs": 15,
    "ops": 10_000,
    "trial_ops": 37_396,
    "seed": 20260930,
    "warmup_calls_per_arm": 1,
    "arms": ["reference", "batch", "trial_batch", "ipc"],
    "spread": "(max - min) / median over the per-pair ratios",
    "spread_bound": {"deployed_batch": "0.50", "deployed_trial_batch": "0.50", "deployed_ipc": "0.50"},
    "figure_rule": "median when the spread is within bound; the maximum observed ratio when it is exceeded",
}
ARMS = ("reference", "batch", "trial_batch", "ipc")
RATIO_KINDS = ("deployed_batch", "deployed_trial_batch", "deployed_ipc")
RATIO_SEMANTICS = {
    "deployed_batch": "counted-mode parent wall per group op at ops per call over reference child CPU per group op",
    "deployed_trial_batch": "counted-mode parent wall per group op at trial_ops per call over reference child CPU "
    "per group op; trial_ops is the rho_dp 30-bit mean per-trial operation count",
    "deployed_ipc": "serve-mode parent wall per group op over reference child CPU per group op; one request and "
    "one response over pipes per group op from a Python client, spawn included",
}
SERVE_TIMEOUT_S = 300


class ServeError(counted.ProbeError):
    pass


def _parse_response(line):
    fields = line.split()
    if fields == ["inf"]:
        return None
    if len(fields) != 2 or not all(field.isascii() and field.isdecimal() for field in fields):
        raise ServeError(f"serve response is not a point: {line.strip()!r}")
    point = (int(fields[0]), int(fields[1]))
    if any(coordinate >= counted.P for coordinate in point):
        raise ServeError("serve response coordinate is outside the field")
    return point


def _request(index, acc):
    if acc is None:
        raise ServeError("serve chain reached infinity")
    if index % 2 == 0:
        return f"d {acc[0]} {acc[1]}\n"
    return f"a {acc[0]} {acc[1]} {counted.GX} {counted.GY}\n"


def verify_chain(responses, ops):
    ec = counted.ec
    base = (counted.GX, counted.GY)
    if len(responses) != ops:
        raise ServeError(f"serve returned {len(responses)} responses, expected {ops}")
    acc = base
    for index, point in enumerate(responses):
        expected = ec.double(counted.P, counted.A, acc) if index % 2 == 0 else ec.add(counted.P, counted.A, acc, base)
        if point != expected:
            raise ServeError(f"serve response {index} was {point!r}, expected {expected!r}")
        acc = expected
    final = counted.expected_point(ops)
    if acc != final:
        raise ServeError(f"serve point was {acc!r}, expected {final!r}")
    return acc


def validate_serve_summary(payload, ops):
    if set(payload) != counted.PROTOCOL_KEYS:
        raise ServeError("serve summary fields do not match the closed protocol")
    if payload["mode"] != "serve":
        raise ServeError("serve summary mode does not match the request")
    if type(payload["requested_ops"]) is not int or payload["requested_ops"] != ops:
        raise ServeError("serve summary requested operation count does not match the request")
    if type(payload["count"]) is not int or payload["count"] != ops:
        raise ServeError(f"serve count was {payload['count']!r}, expected {ops}")
    if payload["point"] is not None:
        raise ServeError("serve summary must not report an arithmetic point")
    counted.validate_timing(payload, True)
    return payload


def run_serve(binary, ops, after_reap=None):
    binary = Path(binary)
    if not binary.is_file():
        raise ServeError(f"binary is missing: {binary}")
    started = time.perf_counter_ns()
    try:
        process = subprocess.Popen(
            [str(binary), "serve", str(ops), "timed"],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        raise ServeError(f"could not start serve process: {binary}") from exc
    acc = (counted.GX, counted.GY)
    responses = []
    timer = threading.Timer(SERVE_TIMEOUT_S, process.kill)
    timer.start()
    try:
        for index in range(ops):
            process.stdin.write(_request(index, acc))
            line = process.stdout.readline()
            if not line:
                raise ServeError(f"serve process closed its output after {index} responses")
            acc = _parse_response(line)
            responses.append(acc)
        process.stdin.write("q\n")
        process.stdin.flush()
        process.stdin.close()
        summary_line = process.stdout.readline()
        remainder = process.stdout.read()
        stderr = process.stderr.read()
        process.wait(timeout=SERVE_TIMEOUT_S)
        if after_reap is not None:
            after_reap()
    except subprocess.TimeoutExpired as exc:
        process.kill()
        raise ServeError(f"serve process exceeded {SERVE_TIMEOUT_S}s") from exc
    except BrokenPipeError as exc:
        process.kill()
        raise ServeError("serve process closed its input") from exc
    finally:
        timer.cancel()
        timer.join()
        if process.poll() is None:
            process.kill()
            process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            with contextlib.suppress(OSError):
                stream.close()
    wall_ns = time.perf_counter_ns() - started
    if process.returncode != 0:
        raise ServeError(f"serve process exited {process.returncode}: {stderr.strip()}")
    if stderr:
        raise ServeError(f"serve process wrote to stderr: {stderr.strip()}")
    if remainder:
        raise ServeError("serve process wrote after its summary")
    payload = validate_serve_summary(counted.decode_output(summary_line), ops)
    verify_chain(responses, ops)
    return {"child_cpu_ns": payload["child_cpu_ns"], "parent_wall_ns": wall_ns, "count": payload["count"]}


def arm_order(seed, pair_index):
    def rank(arm):
        return hashlib.sha256(f"{seed}:{pair_index}:{arm}".encode()).digest()

    return tuple(sorted(ARMS, key=rank))


def _call_arm(arm, reference_binary, counted_binary, ops, trial_ops, after_reap=None):
    if arm == "reference":
        child_cpu_ns, wall_ns = paired.run_reference(reference_binary, ops, after_reap=after_reap)
        return {"ops": ops, "child_cpu_ns": child_cpu_ns, "parent_wall_ns": wall_ns}
    if arm == "ipc":
        return {"ops": ops, **run_serve(counted_binary, ops, after_reap=after_reap)}
    batch = ops if arm == "batch" else trial_ops
    payload, wall_ns = counted.run_binary(counted_binary, "counted", batch, timed=True, after_reap=after_reap)
    return {"ops": batch, "child_cpu_ns": payload["child_cpu_ns"], "parent_wall_ns": wall_ns, "count": payload["count"]}


def _per_op(result, clock):
    return Decimal(result[clock]) / Decimal(result["ops"])


def pair_ratios(results):
    reference = _per_op(results["reference"], "child_cpu_ns")
    if reference <= 0:
        raise counted.ProbeError("reference child CPU per op must be positive")
    return {
        "deployed_batch": f"{_per_op(results['batch'], 'parent_wall_ns') / reference:.9f}",
        "deployed_trial_batch": f"{_per_op(results['trial_batch'], 'parent_wall_ns') / reference:.9f}",
        "deployed_ipc": f"{_per_op(results['ipc'], 'parent_wall_ns') / reference:.9f}",
    }


def run_pairs(reference_binary, counted_binary, ops, trial_ops, pairs, seed):
    for value in (ops, trial_ops):
        if type(value) is not int or value < counted.MIN_MEASURE_OPS or value > counted.MAX_OPS:
            raise counted.ProbeError(
                f"measurement requires {counted.MIN_MEASURE_OPS} through {counted.MAX_OPS} operations"
            )
    if type(pairs) is not int or pairs < 2:
        raise counted.ProbeError("measurement requires at least 2 pairs")
    warmup = [
        {"arm": arm, "call": call, **_call_arm(arm, reference_binary, counted_binary, ops, trial_ops)}
        for arm in ARMS
        for call in range(1, PREREGISTERED["warmup_calls_per_arm"] + 1)
    ]
    rows = []
    for pair in range(1, pairs + 1):
        order = arm_order(seed, pair)
        results = {arm: _call_arm(arm, reference_binary, counted_binary, ops, trial_ops) for arm in order}
        rows.append({"pair": pair, "order": list(order), **results, "ratio": pair_ratios(results)})
    return {"warmup": warmup, "pairs": rows}


def summarize_arms(rows):
    return {
        arm: {
            "child_cpu_per_group_op": counted._stat(
                [row[arm]["child_cpu_ns"] / row[arm]["ops"] for row in rows], "s/group_op"
            ),
            "parent_wall_per_group_op": counted._stat(
                [row[arm]["parent_wall_ns"] / row[arm]["ops"] for row in rows], "s/group_op"
            ),
        }
        for arm in ARMS
    }


def spread_verdicts(summary, bound):
    return {
        kind: "within_bound" if Decimal(summary[kind]["spread"]) <= Decimal(bound[kind]) else "exceeded"
        for kind in RATIO_KINDS
    }


def figures(summary, verdicts):
    return {
        kind: {
            "rule": "median" if verdicts[kind] == "within_bound" else "max",
            "figure": summary[kind]["median"] if verdicts[kind] == "within_bound" else summary[kind]["max"],
        }
        for kind in RATIO_KINDS
    }


def clock_bound(plan_path=LADDER_PLAN):
    plan = json.loads(Path(plan_path).read_text())
    tolerance = Decimal(plan["tolerances"]["clock"])
    radius = Decimal(plan["design_radius"])
    return {
        "clock_tolerance": str(tolerance),
        "design_radius": str(radius),
        "keep_band_excess": str(2 * radius),
        "max_admissible_ratio": f"{2 * radius / tolerance:.9f}",
        "current_rate_ratio": plan["clock"]["rate_ratio"],
    }


def evaluate_bound(bound, figure_by_kind):
    tolerance = Decimal(bound["clock_tolerance"])
    excess = Decimal(bound["keep_band_excess"])
    result = {}
    for kind, entry in figure_by_kind.items():
        figure = Decimal(entry["figure"])
        product = tolerance * figure
        result[kind] = {
            "rule": entry["rule"],
            "figure": entry["figure"],
            "product": f"{product:.9f}",
            "holds": product < excess,
        }
    return result


def _arguments(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=Path, default=counted.CC)
    parser.add_argument("--pairs", type=int, default=PREREGISTERED["pairs"])
    parser.add_argument("--ops", type=counted._parse_nonnegative, default=PREREGISTERED["ops"])
    parser.add_argument("--trial-ops", type=counted._parse_nonnegative, default=PREREGISTERED["trial_ops"])
    parser.add_argument("--seed", type=int, default=PREREGISTERED["seed"])
    parser.add_argument("--arm", type=str, required=True)
    parser.add_argument("--exploratory", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not args.exploratory:
        for field in ("pairs", "ops", "trial_ops", "seed"):
            if getattr(args, field) != PREREGISTERED[field]:
                parser.error(
                    f"--{field.replace('_', '-')} differs from the pre-registered {PREREGISTERED[field]}; add --exploratory"
                )
    if min(args.ops, args.trial_ops) < counted.MIN_MEASURE_OPS:
        parser.error(f"measurement requires at least {counted.MIN_MEASURE_OPS} operations")
    if args.pairs < 2:
        parser.error("--pairs must be at least 2")
    return args


def main(argv=None):
    args = _arguments(argv)
    build = counted.build_binary(args.compiler)
    counted_binary = build["binary"]
    reference = paired.build_reference(args.compiler, build["scratch"])
    metadata = {
        **counted._metadata(build),
        "reference_source_sha256": reference["source_sha256"],
        "reference_binary": str(reference["binary"]),
        "reference_binary_sha256": reference["binary_sha256"],
        "kernel": platform.release(),
        "arm": args.arm,
    }
    before = paired.host_observations()
    correctness = counted.run_correctness(counted_binary)
    refusals = counted.verify_input_refusals(counted_binary)
    serve_correctness = [{"ops": ops, **run_serve(counted_binary, ops)} for ops in (1, 2, 3, 31)]
    timing = run_pairs(reference["binary"], counted_binary, args.ops, args.trial_ops, args.pairs, args.seed)
    after = paired.host_observations()
    summary = paired.summarize_ratios(timing["pairs"])
    verdicts = spread_verdicts(summary, PREREGISTERED["spread_bound"])
    chosen = figures(summary, verdicts)
    bound = clock_bound()
    report = {
        "kind": "deployed_rate_exploratory" if args.exploratory else "deployed_rate",
        "preregistered": not args.exploratory,
        "preregistration": PREREGISTERED,
        "settings": {"pairs": args.pairs, "ops": args.ops, "trial_ops": args.trial_ops, "seed": args.seed},
        "metadata": metadata,
        "host_observations": {"before": before, "after": after},
        "counted_correctness_checks": correctness,
        "malformed_inputs_refused": refusals,
        "serve_correctness": serve_correctness,
        "timing": timing,
        "ratio_summary": summary,
        "arm_summary": summarize_arms(timing["pairs"]),
        "spread_verdicts": verdicts,
        "figures": chosen,
        "clock_bound": {**bound, "evaluation": evaluate_bound(bound, chosen)},
        "ratio_semantics": RATIO_SEMANTICS,
        "timing_status": "DEPLOYED_PROVISIONAL",
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out is not None:
        args.out.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except counted.ProbeError as exc:
        print(f"deployed rate probe refused: {exc}", file=sys.stderr)
        sys.exit(1)
