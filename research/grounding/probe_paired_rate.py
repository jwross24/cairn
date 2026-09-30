import argparse
import hashlib
import importlib
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

counted = importlib.import_module("research.grounding.probe_counted_process")
REFERENCE_SOURCE = importlib.import_module("research.grounding.probe_clock_reference_cost").C_SOURCE

PREREGISTERED = {
    "pairs": 31,
    "ops": 10_000,
    "seed": 20260930,
    "warmup_calls_per_arm": 1,
    "spread": "(max - min) / median over the per-pair ratios",
    "spread_bound": {"cpu": "0.30", "wall": "0.50", "deployed": "0.50"},
    "null_control_pairs": 31,
    "null_median_bound_cpu": ["0.90", "1.10"],
}
RATIO_KINDS = ("cpu", "wall", "deployed")
ARMS = ("reference", "counted")
REFERENCE_KEYS = {"cpu_s", "x", "y", "inf"}
RATIO_SEMANTICS = {
    "cpu": "counted child CPU per group op over reference child CPU per group op; "
    "both on CLOCK_PROCESS_CPUTIME_ID inside the child",
    "wall": "counted parent wall per group op over reference parent wall per group op; "
    "both include one process spawn per call",
    "deployed": "counted parent wall per group op over reference child CPU per group op; "
    "the spawned counted object over the bundle's reference clock",
    "null": "second reference call over first reference call in the same pair; no counting term, expected median 1.0",
}
SYSCTL = "/usr/sbin/sysctl"
VM_STAT = "/usr/bin/vm_stat"
TOOL_TIMEOUT_S = 10


def reference_source_sha256():
    return hashlib.sha256(REFERENCE_SOURCE.encode()).hexdigest()


def build_reference(compiler, scratch):
    compiler = Path(compiler)
    scratch = Path(scratch)
    source = scratch / "ecbench.c"
    binary = scratch / "ecbench"
    source.write_text(REFERENCE_SOURCE)
    compiled = counted._run_compiler([str(compiler), *counted.CFLAGS, "-o", str(binary), str(source)])
    if compiled.returncode != 0:
        raise counted.ProbeError(f"reference build failed: {compiled.stderr.strip()}")
    if not binary.is_file():
        raise counted.ProbeError(f"compiler did not produce the reference binary: {binary}")
    return {
        "binary": binary,
        "source_sha256": reference_source_sha256(),
        "binary_sha256": counted._sha256(binary),
    }


def decode_reference_output(stdout):
    try:
        result = json.loads(stdout, object_pairs_hook=counted._reject_duplicates)
    except counted.ProbeError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise counted.ProbeError("reference output is not one JSON object") from exc
    if type(result) is not dict:
        raise counted.ProbeError("reference output is not one JSON object")
    if set(result) != REFERENCE_KEYS:
        raise counted.ProbeError("reference output fields do not match the closed protocol")
    return result


def _reference_point(payload):
    inf = payload["inf"]
    if type(inf) is not int or inf not in (0, 1):
        raise counted.ProbeError("reference inf flag must be the integer 0 or 1")
    if inf == 1:
        return None
    coordinates = (payload["x"], payload["y"])
    if any(type(coordinate) is not int for coordinate in coordinates):
        raise counted.ProbeError("reference point coordinates must be integers")
    if any(coordinate < 0 or coordinate >= counted.P for coordinate in coordinates):
        raise counted.ProbeError("reference point coordinate is outside the field")
    return coordinates


def validate_reference(payload, ops):
    actual = _reference_point(payload)
    expected = counted.expected_point(ops)
    if actual != expected:
        raise counted.ProbeError(f"reference point was {actual!r}, expected {expected!r}")
    cpu_s = payload["cpu_s"]
    if type(cpu_s) not in (int, float) or not math.isfinite(cpu_s) or cpu_s < 0:
        raise counted.ProbeError("reference cpu_s must be a finite nonnegative number")
    return round(cpu_s * 1_000_000_000)


def run_reference(binary, ops, after_reap=None):
    binary = Path(binary)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise counted.ProbeError(f"binary is missing or not executable: {binary}")
    argv = [str(binary), str(counted.P), str(counted.A), str(counted.GX), str(counted.GY), str(ops)]
    started = time.perf_counter_ns()
    try:
        completed = subprocess.run(
            argv,
            cwd=counted.ROOT,
            capture_output=True,
            text=True,
            timeout=counted.CHILD_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise counted.ProbeError(
            f"reference process exceeded subprocess timeout of {counted.CHILD_TIMEOUT_S}s"
        ) from exc
    except OSError as exc:
        raise counted.ProbeError(f"could not start reference process: {binary}") from exc
    wall_ns = time.perf_counter_ns() - started
    if after_reap is not None:
        after_reap()
    if completed.returncode != 0:
        raise counted.ProbeError(f"reference process exited {completed.returncode}: {completed.stderr.strip()}")
    if completed.stderr:
        raise counted.ProbeError(f"reference process wrote to stderr: {completed.stderr.strip()}")
    payload = decode_reference_output(completed.stdout)
    return validate_reference(payload, ops), wall_ns


def pair_order(seed, pair_index):
    digest = hashlib.sha256(f"{seed}:{pair_index}".encode()).digest()
    if int.from_bytes(digest, "big") & 1:
        return ("counted", "reference")
    return ("reference", "counted")


def _ratio(numerator_ns, denominator_ns):
    if denominator_ns <= 0:
        raise counted.ProbeError("ratio denominator must be a positive nanosecond count")
    return f"{float(Fraction(numerator_ns, denominator_ns)):.9f}"


def pair_ratios(reference, counted_arm):
    return {
        "cpu": _ratio(counted_arm["child_cpu_ns"], reference["child_cpu_ns"]),
        "wall": _ratio(counted_arm["parent_wall_ns"], reference["parent_wall_ns"]),
        "deployed": _ratio(counted_arm["parent_wall_ns"], reference["child_cpu_ns"]),
    }


def _call_arm(arm, reference_binary, counted_binary, ops):
    if arm == "reference":
        child_cpu_ns, wall_ns = run_reference(reference_binary, ops)
        return {"child_cpu_ns": child_cpu_ns, "parent_wall_ns": wall_ns}
    payload, wall_ns = counted.run_binary(counted_binary, "counted", ops, timed=True)
    return {"child_cpu_ns": payload["child_cpu_ns"], "parent_wall_ns": wall_ns, "count": payload["count"]}


def run_pairs(reference_binary, counted_binary, ops, pairs, seed):
    if type(ops) is not int or ops < counted.MIN_MEASURE_OPS or ops > counted.MAX_OPS:
        raise counted.ProbeError(f"measurement requires {counted.MIN_MEASURE_OPS} through {counted.MAX_OPS} operations")
    if type(pairs) is not int or pairs < 2:
        raise counted.ProbeError("measurement requires at least 2 pairs")
    warmup = [
        {"arm": arm, "call": call, **_call_arm(arm, reference_binary, counted_binary, ops)}
        for arm in ARMS
        for call in range(1, PREREGISTERED["warmup_calls_per_arm"] + 1)
    ]
    rows = []
    for pair in range(1, pairs + 1):
        order = pair_order(seed, pair)
        results = {arm: _call_arm(arm, reference_binary, counted_binary, ops) for arm in order}
        rows.append(
            {
                "pair": pair,
                "order": list(order),
                "reference": results["reference"],
                "counted": results["counted"],
                "ratio": pair_ratios(results["reference"], results["counted"]),
            }
        )
    return {"warmup": warmup, "pairs": rows}


def run_null_pairs(reference_binary, ops, pairs):
    if type(ops) is not int or ops < counted.MIN_MEASURE_OPS or ops > counted.MAX_OPS:
        raise counted.ProbeError(f"measurement requires {counted.MIN_MEASURE_OPS} through {counted.MAX_OPS} operations")
    if type(pairs) is not int or pairs < 2:
        raise counted.ProbeError("measurement requires at least 2 pairs")
    rows = []
    for pair in range(1, pairs + 1):
        first = _call_arm("reference", reference_binary, None, ops)
        second = _call_arm("reference", reference_binary, None, ops)
        rows.append(
            {
                "pair": pair,
                "first": first,
                "second": second,
                "ratio": {
                    "cpu": _ratio(second["child_cpu_ns"], first["child_cpu_ns"]),
                    "wall": _ratio(second["parent_wall_ns"], first["parent_wall_ns"]),
                },
            }
        )
    return rows


def summarize_ratios(rows):
    summary = {}
    for kind in rows[0]["ratio"]:
        values = [float(row["ratio"][kind]) for row in rows]
        median = statistics.median(values)
        if median <= 0:
            raise counted.ProbeError(f"{kind} ratio median must be positive")
        summary[kind] = {
            "n": len(values),
            "min": f"{min(values):.9f}",
            "median": f"{median:.9f}",
            "max": f"{max(values):.9f}",
            "sd": f"{statistics.stdev(values) if len(values) > 1 else 0.0:.9f}",
            "spread": f"{(max(values) - min(values)) / median:.9f}",
        }
    return summary


def summarize_arms(rows, ops):
    return {
        arm: {
            "child_cpu_per_group_op": counted._stat([row[arm]["child_cpu_ns"] / ops for row in rows], "s/group_op"),
            "parent_wall_per_group_op": counted._stat([row[arm]["parent_wall_ns"] / ops for row in rows], "s/group_op"),
        }
        for arm in ARMS
    }


def null_verdict(null_summary, bound):
    median = Decimal(null_summary["cpu"]["median"])
    return "within_bound" if Decimal(bound[0]) <= median <= Decimal(bound[1]) else "exceeded"


def spread_verdicts(summary, bound):
    return {
        kind: "within_bound" if Decimal(summary[kind]["spread"]) <= Decimal(bound[kind]) else "exceeded"
        for kind in RATIO_KINDS
    }


def _run_text(argv):
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=TOOL_TIMEOUT_S, check=False)
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _read_text(path):
    try:
        return Path(path).read_text()
    except OSError:
        return None


def _first_int(pattern, text):
    if text is None:
        return None
    match = re.search(pattern, text)
    if match is None:
        return None
    return int(match.group(1))


def _int_list(text, length):
    if text is None:
        return None
    fields = text.split()
    if len(fields) < length or not all(field.isdecimal() for field in fields[:length]):
        return None
    return [int(field) for field in fields[:length]]


def host_observations():
    observed = {
        "load_1m": counted._host_load(),
        "free_pages_16k": None,
        "kern_num_files": None,
        "meminfo_free_kb": None,
        "file_nr": None,
        "loadavg_line": None,
    }
    system = platform.system()
    if system == "Darwin":
        observed["kern_num_files"] = _first_int(r"(\d+)", _run_text([SYSCTL, "-n", "kern.num_files"]))
        observed["free_pages_16k"] = _first_int(r"Pages free:\s+(\d+)\.", _run_text([VM_STAT]))
    elif system == "Linux":
        loadavg = _read_text("/proc/loadavg")
        observed["loadavg_line"] = None if loadavg is None else loadavg.strip()
        observed["meminfo_free_kb"] = _first_int(r"MemFree:\s+(\d+)\s+kB", _read_text("/proc/meminfo"))
        observed["file_nr"] = _int_list(_read_text("/proc/sys/fs/file-nr"), 3)
    observed["taken_at"] = datetime.now(UTC).isoformat()
    return observed


def _arguments(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=Path, default=counted.CC)
    parser.add_argument("--pairs", type=int, default=PREREGISTERED["pairs"])
    parser.add_argument("--ops", type=counted._parse_nonnegative, default=PREREGISTERED["ops"])
    parser.add_argument("--seed", type=int, default=PREREGISTERED["seed"])
    parser.add_argument("--arm", type=str, required=True)
    parser.add_argument("--exploratory", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not args.exploratory:
        for field in ("pairs", "ops", "seed"):
            if getattr(args, field) != PREREGISTERED[field]:
                parser.error(f"--{field} differs from the pre-registered {PREREGISTERED[field]}; add --exploratory")
    if args.ops < counted.MIN_MEASURE_OPS:
        parser.error(f"measurement requires at least {counted.MIN_MEASURE_OPS} operations")
    if args.pairs < 2:
        parser.error("--pairs must be at least 2")
    return args


def main(argv=None):
    args = _arguments(argv)
    build = counted.build_binary(args.compiler)
    counted_binary = build["binary"]
    reference = build_reference(args.compiler, build["scratch"])
    metadata = {
        **counted._metadata(build),
        "reference_source_sha256": reference["source_sha256"],
        "reference_binary": str(reference["binary"]),
        "reference_binary_sha256": reference["binary_sha256"],
        "kernel": platform.release(),
        "arm": args.arm,
    }
    before = host_observations()
    correctness = counted.run_correctness(counted_binary)
    refusals = counted.verify_input_refusals(counted_binary)
    reference_correctness = []
    for ops in counted.CORRECTNESS_OPS:
        child_cpu_ns, _ = run_reference(reference["binary"], ops)
        reference_correctness.append({"ops": ops, "child_cpu_ns": child_cpu_ns})
    timing = run_pairs(reference["binary"], counted_binary, args.ops, args.pairs, args.seed)
    null_rows = run_null_pairs(
        reference["binary"],
        args.ops,
        args.pairs if args.exploratory else PREREGISTERED["null_control_pairs"],
    )
    after = host_observations()
    null_summary = summarize_ratios(null_rows)
    ratio_summary = summarize_ratios(timing["pairs"])
    report = {
        "kind": "paired_rate_exploratory" if args.exploratory else "paired_rate",
        "preregistered": not args.exploratory,
        "preregistration": PREREGISTERED,
        "settings": {"pairs": args.pairs, "ops": args.ops, "seed": args.seed},
        "metadata": metadata,
        "host_observations": {"before": before, "after": after},
        "counted_correctness_checks": correctness,
        "malformed_inputs_refused": refusals,
        "reference_correctness": reference_correctness,
        "timing": timing,
        "ratio_summary": ratio_summary,
        "arm_summary": summarize_arms(timing["pairs"], args.ops),
        "spread_verdicts": spread_verdicts(ratio_summary, PREREGISTERED["spread_bound"]),
        "null_control": {
            "pairs": null_rows,
            "ratio_summary": null_summary,
            "median_bound_cpu": PREREGISTERED["null_median_bound_cpu"],
            "verdict": null_verdict(null_summary, PREREGISTERED["null_median_bound_cpu"]),
        },
        "ratio_semantics": RATIO_SEMANTICS,
        "timing_status": "PAIRED_PROVISIONAL",
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
        print(f"paired rate probe refused: {exc}", file=sys.stderr)
        sys.exit(1)
