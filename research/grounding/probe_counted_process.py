import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from cairn import ec

P = 866004983247663323
A = 645824996691681933
B = 382308953708622014
N = 866004982950395713
GX = 258236120896152398
GY = 475063108841005863
DEFAULT_OPS = 10_000
DEFAULT_REPS = 7
MIN_MEASURE_OPS = 1_000
MAX_OPS = 1_000_000
MAX_U64 = (1 << 64) - 1
CC = Path("/usr/bin/clang")
CFLAGS = ("-O2", "-std=c11", "-Wall")
CHILD_TIMEOUT_S = 30
MODES = ("raw", "counted", "count-only", "zero-work")
CORRECTNESS_OPS = (0, 1, 2, 3, DEFAULT_OPS)
SOURCE = Path(__file__).resolve().with_name("counted_process.c")
ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_KEYS = {"mode", "requested_ops", "count", "point", "child_cpu_ns"}


class ProbeError(RuntimeError):
    pass


def _reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProbeError(f"duplicate output key: {key}")
        result[key] = value
    return result


def decode_output(stdout):
    try:
        result = json.loads(stdout, object_pairs_hook=_reject_duplicates)
    except ProbeError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProbeError("child output is not one JSON object") from exc
    if type(result) is not dict:
        raise ProbeError("child output is not one JSON object")
    return result


def expected_point(ops):
    base = (GX, GY)
    if not ec.is_on_curve(P, A, B, base):
        raise ProbeError("fixed base point is not on the fixed curve")
    pairs = pow(2, ops // 2 + 1, N)
    scalar = (pairs - 1) % N
    if ops % 2:
        scalar = 2 * scalar % N
    return ec.mul(P, A, base, scalar)


def validate_count(payload, mode, ops):
    expected = {
        "raw": None,
        "counted": ops,
        "count-only": ops,
        "zero-work": 0,
    }[mode]
    actual = payload["count"]
    if expected is None:
        if actual is not None:
            raise ProbeError("raw arithmetic must not report a counted-call value")
        return
    if type(actual) is not int or actual != expected:
        raise ProbeError(f"{mode} count was {actual!r}, expected {expected}")


def validate_point(payload, mode, ops):
    actual = payload["point"]
    if mode in ("count-only", "zero-work"):
        if actual is not None:
            raise ProbeError(f"{mode} must not report an arithmetic point")
        return
    expected = expected_point(ops)
    if expected is None:
        if actual is not None:
            raise ProbeError(f"point was {actual!r}, expected infinity")
        return
    if type(actual) is not list or len(actual) != 2:
        raise ProbeError("point must be null or a pair of coordinates")
    if any(type(coordinate) is not int for coordinate in actual):
        raise ProbeError("point coordinates must be integers")
    if any(coordinate < 0 or coordinate >= P for coordinate in actual):
        raise ProbeError("point coordinate is outside the field")
    if tuple(actual) != expected:
        raise ProbeError(f"point was {actual!r}, expected {expected!r}")


def validate_timing(payload, timed):
    actual = payload["child_cpu_ns"]
    if not timed:
        if actual is not None:
            raise ProbeError("untimed process returned timing evidence")
        return
    if type(actual) is not int or not 0 <= actual <= MAX_U64:
        raise ProbeError("child CPU time must be a nonnegative integer nanosecond count")


def validate_payload(payload, mode, ops, timed):
    if mode not in MODES or type(ops) is not int or not 0 <= ops <= MAX_OPS:
        raise ProbeError("invalid expected mode or operation count")
    if set(payload) != PROTOCOL_KEYS:
        raise ProbeError("child output fields do not match the closed protocol")
    if payload["mode"] != mode:
        raise ProbeError("child mode does not match the request")
    if type(payload["requested_ops"]) is not int or payload["requested_ops"] != ops:
        raise ProbeError("child requested operation count does not match the request")
    validate_count(payload, mode, ops)
    validate_point(payload, mode, ops)
    validate_timing(payload, timed)
    return payload


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _run_compiler(command):
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=CHILD_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError(f"compiler command failed: {command[0]}") from exc


def build_binary(compiler=CC):
    compiler = Path(compiler)
    if not compiler.is_file() or not os.access(compiler, os.X_OK):
        raise ProbeError(f"compiler is missing or not executable: {compiler}")
    if not SOURCE.is_file():
        raise ProbeError(f"C source is missing: {SOURCE}")
    temp_root = Path(tempfile.gettempdir()).resolve()
    if temp_root == ROOT or ROOT in temp_root.parents:
        raise ProbeError("temporary directory must be outside the checkout")
    scratch = Path(tempfile.mkdtemp(prefix="cairn-counted-process-"))
    binary = scratch / "counted_process"
    version = _run_compiler([str(compiler), "--version"])
    if version.returncode != 0 or not version.stdout.strip():
        raise ProbeError(f"could not identify compiler: {version.stderr.strip()}")
    compiled = _run_compiler([str(compiler), *CFLAGS, "-o", str(binary), str(SOURCE)])
    if compiled.returncode != 0:
        raise ProbeError(f"C build failed: {compiled.stderr.strip()}")
    if not binary.is_file():
        raise ProbeError(f"compiler did not produce the binary: {binary}")
    return {
        "binary": binary,
        "scratch": str(scratch),
        "compiler": str(compiler),
        "compiler_version": version.stdout.splitlines()[0],
        "cflags": list(CFLAGS),
        "source_sha256": _sha256(SOURCE),
        "binary_sha256": _sha256(binary),
    }


def run_binary(binary, mode, ops, timed=False, after_reap=None):
    binary = Path(binary)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ProbeError(f"binary is missing or not executable: {binary}")
    argv = [str(binary), mode, str(ops), "timed" if timed else "untimed"]
    started = time.perf_counter_ns() if timed else None
    try:
        completed = subprocess.run(
            argv,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=CHILD_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError(f"counted process exceeded subprocess timeout of {CHILD_TIMEOUT_S}s") from exc
    except OSError as exc:
        raise ProbeError(f"could not start counted process: {binary}") from exc
    wall_ns = time.perf_counter_ns() - started if timed else None
    if after_reap is not None:
        after_reap()
    if completed.returncode != 0:
        raise ProbeError(f"counted process exited {completed.returncode}: {completed.stderr.strip()}")
    if completed.stderr:
        raise ProbeError(f"counted process wrote to stderr: {completed.stderr.strip()}")
    payload = decode_output(completed.stdout)
    validate_payload(payload, mode, ops, timed)
    return payload, wall_ns


def verify_input_refusals(binary):
    rejected = ("-1", "3junk", "1000001", "18446744073709551616")
    for value in rejected:
        try:
            completed = subprocess.run(
                [str(binary), "counted", value, "untimed"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=CHILD_TIMEOUT_S,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProbeError(f"malformed-input check could not run for {value!r}") from exc
        if completed.returncode == 0 or completed.stdout:
            raise ProbeError(f"counted process accepted malformed operation count {value!r}")
    return list(rejected)


def _host_load():
    try:
        return os.getloadavg()[0]
    except AttributeError:
        return None
    except OSError:
        return None


def _source_metadata(build, source=None):
    if source is not None:
        source_path = Path(source)
        if not source_path.is_file():
            raise ProbeError(f"C source is missing: {source_path}")
        provenance = "supplied_source_unverified"
    elif build.get("compiler") is not None:
        source_path = SOURCE
        if not source_path.is_file():
            raise ProbeError(f"C source is missing: {source_path}")
        provenance = "probe_build_input"
    else:
        return {"source": None, "source_sha256": None, "source_provenance": "unknown_external_binary"}
    return {
        "source": str(source_path),
        "source_sha256": _sha256(source_path),
        "source_provenance": provenance,
    }


def _metadata(build, source=None):
    binary = Path(build["binary"])
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ProbeError(f"binary is missing or not executable: {binary}")
    return {
        "curve": {"bits": 60, "p": str(P), "a": str(A), "b": str(B), "n": str(N)},
        **_source_metadata(build, source),
        "binary": str(binary),
        "binary_sha256": _sha256(binary),
        "compiler": build.get("compiler"),
        "compiler_version": build.get("compiler_version"),
        "cflags": build.get("cflags"),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.splitlines()[0],
        "host_1m_load_average": _host_load(),
        "scratch": build.get("scratch"),
    }


def run_correctness(binary, extra_ops=()):
    ops_values = list(dict.fromkeys((*CORRECTNESS_OPS, *extra_ops)))
    checks = []
    for ops in ops_values:
        for mode in MODES:
            payload, _ = run_binary(binary, mode, ops, timed=False)
            checks.append({"mode": mode, "ops_per_process_call": ops, "result": payload})
    return checks


def _stat(values, unit):
    seconds = [value / 1_000_000_000 for value in values]
    return {
        "unit": unit,
        "min": f"{min(seconds):.12f}",
        "median": f"{statistics.median(seconds):.12f}",
        "max": f"{max(seconds):.12f}",
        "sd": f"{statistics.stdev(seconds) if len(seconds) > 1 else 0.0:.12f}",
    }


def run_measurement(binary, ops=DEFAULT_OPS, reps=DEFAULT_REPS):
    if type(ops) is not int or ops < MIN_MEASURE_OPS or ops > MAX_OPS:
        raise ProbeError(f"measurement requires {MIN_MEASURE_OPS} through {MAX_OPS} operations")
    if type(reps) is not int or reps < 2:
        raise ProbeError("measurement requires at least 2 repetitions")
    rows = []
    for mode in MODES:
        for rep in range(1, reps + 1):
            payload, wall_ns = run_binary(binary, mode, ops, timed=True)
            rows.append(
                {
                    "mode": mode,
                    "rep": rep,
                    "process_calls": 1,
                    "ops_per_process_call": ops,
                    "count": payload["count"],
                    "child_cpu_ns": payload["child_cpu_ns"],
                    "parent_wall_ns": wall_ns,
                }
            )
    summaries = {}
    for mode in MODES:
        mode_rows = [row for row in rows if row["mode"] == mode]
        parent = [row["parent_wall_ns"] for row in mode_rows]
        if mode == "zero-work":
            summaries[mode] = {
                "parent_wall_per_process_call": _stat(parent, "s/call"),
                "parent_wall_amortized_per_requested_op_slot": _stat(
                    [value / ops for value in parent], "s/requested_op_slot"
                ),
                "child_cpu_per_process_call": _stat([row["child_cpu_ns"] for row in mode_rows], "s/call"),
            }
        elif mode == "count-only":
            summaries[mode] = {
                "child_cpu_per_counter_increment": _stat(
                    [row["child_cpu_ns"] / ops for row in mode_rows], "s/increment"
                ),
                "parent_wall_per_counter_increment": _stat([value / ops for value in parent], "s/increment"),
            }
        else:
            summaries[mode] = {
                "child_cpu_per_group_op": _stat([row["child_cpu_ns"] / ops for row in mode_rows], "s/group_op"),
                "parent_wall_per_group_op": _stat([value / ops for value in parent], "s/group_op"),
            }
    return {"ops_per_process_call": ops, "reps": reps, "samples": rows, "summaries": summaries}


def _parse_nonnegative(text):
    if not text or not text.isascii() or not text.isdecimal():
        raise argparse.ArgumentTypeError("must be decimal digits")
    value = int(text)
    if value > MAX_OPS:
        raise argparse.ArgumentTypeError(f"must not exceed {MAX_OPS}")
    return value


def _arguments(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--ops", type=_parse_nonnegative, default=DEFAULT_OPS)
    parser.add_argument("--reps", type=int, default=DEFAULT_REPS)
    parser.add_argument("--correctness-only", action="store_true")
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args(argv)
    if args.reps < 2:
        parser.error("--reps must be at least 2")
    if args.binary is not None and not args.correctness_only:
        parser.error("--binary is available only with --correctness-only")
    if args.source is not None and args.binary is None:
        parser.error("--source requires --binary")
    if not args.correctness_only and args.ops < MIN_MEASURE_OPS:
        parser.error(f"measurement requires at least {MIN_MEASURE_OPS} operations")
    return args


def main(argv=None):
    args = _arguments(argv)
    build = build_binary() if args.binary is None else {"binary": args.binary}
    metadata = _metadata(build, args.source)
    if args.correctness_only:
        checks = run_correctness(args.binary or build["binary"], (args.ops,))
        refusals = verify_input_refusals(args.binary or build["binary"])
        report = {
            "kind": "correctness_only",
            "timing_status": "NOT_TAKEN",
            "metadata": metadata,
            "correctness_checks": checks,
            "malformed_inputs_refused": refusals,
        }
    else:
        checks = run_correctness(build["binary"])
        refusals = verify_input_refusals(build["binary"])
        timing = run_measurement(build["binary"], args.ops, args.reps)
        report = {
            "kind": "timing",
            "timing_status": "PROVISIONAL",
            "metadata": metadata,
            "correctness_checks": checks,
            "malformed_inputs_refused": refusals,
            "timing": timing,
            "count_semantic": "one requested primitive group-operation wrapper call; no field-operation count",
            "counting_cost_inference": "not derived by subtracting raw and counted timings",
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProbeError as exc:
        print(f"counted process probe refused: {exc}", file=sys.stderr)
        sys.exit(1)
