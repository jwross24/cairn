import argparse
import dataclasses
import hashlib
import importlib
import json
import platform
import re
import statistics
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from cairn import countedvm, pari, runner
from cairn.skills import toy_curve

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
REFERENCE_SOURCE = importlib.import_module("research.grounding.probe_clock_reference_cost").C_SOURCE
SOURCE_PATHS = (
    "research/grounding/probe_counted_vm_calibration.py",
    "research/grounding/probe_clock_reference_cost.py",
    "src/cairn/countedvm/__init__.py",
    "src/cairn/countedvm/vm.c",
    "src/cairn/runner.py",
    "src/cairn/pari.py",
    "src/cairn/ec.py",
    "src/cairn/skills/toy_curve.py",
    "src/cairn/skills/order_bsgs_gmpy2.py",
)
KINDS = ("chain", "add", "double", "identity", "inverse", "scalar_mul")
ARMS = ("native", *KINDS)
PREREGISTERED: dict[str, Any] = {
    "bits": [30, 40, 50, 60],
    "pairs": 15,
    "ops": 10_000,
    "seed": 20261012,
    "instance_seed": 1,
    "warmups": 1,
    "spread": "(max - min) / median of paired VM-total-CPU/native-inner-CPU costs per counted operation",
    "spread_bound": "0.50",
    "wall_cap_s": 30,
    "instruction_budget": 1_000_000,
    "scalar": 7,
    "c_floor_s_per_op": "0",
    "c_floor_basis": "nonnegative CPU time; no positive universal lower bound established",
}
HOLDS = {
    "S_ref": "startup control is an observation, not an established startup decomposition",
    "S_clm": "startup control is an observation, not an established claimant startup decomposition",
    "S_ref_share": "reference startup allocation to trial N is unsupported",
    "measurement_margin": "no justified one-sided measurement margin",
    "aa_radius": "no same-rung independently seeded rho A/A distribution measured",
    "emulation_floor": "no bound on the cheapest scalar/multiword VM-emulated group operation",
    "B2_B3_sufficiency": "not evaluated; these measurements are partial S3 progress",
}


def rate_values(cpu_s, ops):
    cpu, count = Decimal(str(cpu_s)), Decimal(ops)
    if not cpu.is_finite() or cpu <= 0 or count <= 0:
        raise ValueError("positive CPU seconds and operation count required")
    cost = cpu / count
    result = {"seconds_per_op": str(cost), "ops_per_second": str(1 / cost)}
    validate_rate(result)
    return result


def validate_rate(values):
    if set(values) != {"seconds_per_op", "ops_per_second"}:
        raise ValueError("explicit seconds_per_op and ops_per_second units required")
    cost, rate = (Decimal(values[key]) for key in ("seconds_per_op", "ops_per_second"))
    if not all(value.is_finite() and value > 0 for value in (cost, rate)):
        raise ValueError("rate and cost must be finite and positive")
    if abs(cost * rate - 1) > Decimal("1e-24"):
        raise ValueError("rate is not the reciprocal of cost")


def spread_summary(values):
    sample = [Decimal(str(value)) for value in values]
    if len(sample) < 2 or any(not value.is_finite() or value <= 0 for value in sample):
        raise ValueError("spread requires at least two positive finite observations")
    median = statistics.median(sample)
    spread = (max(sample) - min(sample)) / median
    exceeded = spread > Decimal(PREREGISTERED["spread_bound"])
    return {
        "sample_min": str(min(sample)),
        "sample_median": str(median),
        "sample_max": str(max(sample)),
        "spread": str(spread),
        "status": "INCONCLUSIVE" if exceeded else "OBSERVED_WITHIN_SPREAD",
        "figure": None if exceeded else str(median),
    }


def check_preregistration(sha, source_sha256):
    if not sha or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise ValueError("a full committed preregistration SHA is required")
    if not source_sha256 or re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None:
        raise ValueError("the operator-supplied committed source SHA256 is required")
    actual = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if actual != source_sha256:
        raise ValueError("source differs from operator-supplied committed preregistration digest")


def ordered_arms(pair):
    return sorted(ARMS, key=lambda arm: hashlib.sha256(f"{PREREGISTERED['seed']}:{pair}:{arm}".encode()).digest())


def vm_program(kind, ops):
    if kind not in KINDS or type(ops) is not int or ops < 0:
        raise ValueError("unsupported kind or operation count")
    setup = ["setp p0 P", "setp p1 P", "setp p2 inf", "negp p3 p1", "sset s0 7"]
    steps = {
        "chain": ["dblp p0 p0", "addp p0 p0 p1"],
        "add": ["addp p0 p0 p1"],
        "double": ["dblp p0 p0"],
        "identity": ["addp p0 p2 p1"],
        "inverse": ["addp p0 p1 p3"],
        "scalar_mul": ["mulp p0 p1 s0"],
    }
    iterations = ops // 2 if kind == "chain" else ops
    lines = [
        *setup,
        f"iset i0 {iterations}",
        "jz i0 done",
        "loop:",
        *steps[kind],
        "isub i0 i0 1",
        "jnz i0 loop",
        "done:",
    ]
    if kind == "chain" and ops % 2:
        lines.append("dblp p0 p0")
    lines.append("halt")
    return "\n".join(lines) + "\n"


def expected_count(kind, ops):
    return ops * countedvm.expected_mul_ops(PREREGISTERED["scalar"]) if kind == "scalar_mul" else ops


def expected_scalar(kind, ops, n):
    if ops == 0:
        return 1
    if kind == "chain":
        value = 1
        for step in range(ops):
            value = (2 * value if step % 2 == 0 else value + 1) % n
        return value
    return {
        "add": (ops + 1) % n,
        "double": pow(2, ops, n),
        "identity": 1,
        "inverse": 0,
        "scalar_mul": PREREGISTERED["scalar"],
    }[kind]


def gp_points(instance, ops):
    scalars = [expected_scalar(kind, ops, instance.n) for kind in KINDS]
    script = (
        f"E=ellinit([{instance.a},{instance.b}],{instance.p});P={list(instance.P)};"
        f"if(!isprime({instance.p})||!isprime({instance.n})||ellcard(E)!={instance.n},quit(1));"
        f"if(!ellisoncurve(E,P)||ellmul(E,P,{instance.n})!=[0],quit(1));"
        f"print(vector({len(scalars)},i,lift(ellmul(E,P,{scalars}[i]))));quit(0)\n"
    )
    rc, out, err = pari.run_gp([], script)
    if rc != 0 or err:
        raise ValueError(f"independent GP check failed: {rc}, {out}, {err}")
    points = json.loads(out)
    if len(points) != len(KINDS):
        raise ValueError("GP returned the wrong number of points")
    return dict(zip(KINDS, (None if point == [0] else tuple(point) for point in points), strict=True)), {
        "script": script,
        "rc": rc,
        "stdout": out,
        "stderr": err,
    }


def build_binaries(compiler, scratch):
    scratch.mkdir()
    vm = countedvm.build(compiler, scratch)
    source, native = scratch / "native.c", scratch / "native"
    source.write_text(REFERENCE_SOURCE)
    subprocess.run(
        [str(compiler), *countedvm.CFLAGS, "-o", str(native), str(source)],
        capture_output=True,
        timeout=30,
        check=True,
    )
    version = subprocess.run([str(compiler), "--version"], capture_output=True, text=True, timeout=10, check=True)
    return (
        vm,
        native,
        {
            "compiler": str(compiler),
            "compiler_version": version.stdout,
            "compiler_sha256": hashlib.sha256(compiler.read_bytes()).hexdigest(),
            "flags": list(countedvm.CFLAGS),
            "vm_source_sha256": countedvm.source_sha256(),
            "native_source_sha256": hashlib.sha256(REFERENCE_SOURCE.encode()).hexdigest(),
            "vm_binary_digest": countedvm.file_digest(vm),
            "native_binary_digest": countedvm.file_digest(native),
        },
    )


def measure_native(binary, instance, ops, expected, scratch):
    scratch.mkdir()
    out, err = scratch / "stdout", scratch / "stderr"
    run = runner.spawn_and_wait(
        [str(binary), str(instance.p), str(instance.a), *(str(c) for c in instance.P), str(ops)],
        out,
        err,
        wall_cap_s=PREREGISTERED["wall_cap_s"],
        env=runner.child_env(),
    )
    if (
        run.exit_status != 0
        or run.timed_out
        or err.read_bytes()
        or not runner.scope_is_verified_complete(run.measurement_scope)
    ):
        raise ValueError("native measurement refused")
    payload = json.loads(out.read_text())
    if set(payload) != {"cpu_s", "x", "y", "inf"} or payload["inf"] not in (0, 1):
        raise ValueError("native output is not the reference protocol")
    point = None if payload["inf"] else (payload["x"], payload["y"])
    if point != expected:
        raise ValueError("native result disagrees with independent GP")
    cpu = Decimal(str(payload["cpu_s"]))
    if not cpu.is_finite() or cpu < 0:
        raise ValueError("native inner CPU is invalid")
    rates = {} if ops == 0 else rate_values(cpu, ops)
    return {
        "counted_ops": ops,
        "inner_cpu_s": str(cpu),
        "rates": rates,
        "output": payload,
        "receipt": dataclasses.asdict(run),
    }


def measure_vm(binary, digest, instance, kind, ops, expected, scratch, attempt_id):
    run = countedvm.launch(
        binary,
        digest,
        instance,
        vm_program(kind, ops),
        PREREGISTERED["instruction_budget"],
        attempt_id=attempt_id,
        scratch_dir=scratch,
        wall_cap_s=PREREGISTERED["wall_cap_s"],
    )
    count = expected_count(kind, ops)
    if run.outcome.status != countedvm.STATUS_OK or run.outcome.count != count or run.outcome.p0 != expected:
        raise ValueError(f"VM {kind} disagrees with expected count or independent GP")
    if not runner.scope_is_verified_complete(run.measurement_scope):
        raise ValueError("VM measurement scope is incomplete")
    rates = {} if count == 0 else rate_values(run.cpu_user_s + run.cpu_sys_s, count)
    return {
        "iterations": ops,
        "setup_counted_ops": 0,
        "counted_ops": count,
        "rates": rates,
        "receipt": dataclasses.asdict(run),
    }


def measure_rung(bits, ops, pairs, vm, native, digest, scratch):
    generated = toy_curve.run(bits, PREREGISTERED["instance_seed"])
    if generated.status != toy_curve.STATUS_OK or generated.p.bit_length() != bits:
        raise ValueError("instance generator disagreed or produced the wrong field size")
    instance = countedvm.Instance(
        generated.p, generated.a, generated.b, generated.n, tuple(generated.P), tuple(generated.P)
    )
    expected, oracle = gp_points(instance, ops)
    zero_expected, zero_oracle = gp_points(instance, 0)

    def call(arm, count, points, label):
        directory = scratch / label / arm
        directory.parent.mkdir(parents=True, exist_ok=True)
        if arm == "native":
            return measure_native(native, instance, count, points["chain"], directory)
        return measure_vm(vm, digest, instance, arm, count, points[arm], directory, f"{bits}:{label}:{arm}")

    controls = {arm: call(arm, 0, zero_expected, "startup-control") for arm in ARMS}
    warmups = {arm: call(arm, ops, expected, "warmup") for arm in ordered_arms(0)}
    rows: list[dict[str, Any]] = []
    for pair in range(pairs):
        order = ordered_arms(pair + 1)
        measurements = {arm: call(arm, ops, expected, f"pair-{pair}") for arm in order}
        c_f = Decimal(measurements["native"]["rates"]["seconds_per_op"])
        ratios = {kind: str(Decimal(measurements[kind]["rates"]["seconds_per_op"]) / c_f) for kind in KINDS}
        rows.append({"pair": pair + 1, "order": order, "measurements": measurements, "ratios": ratios})
    summaries = {kind: spread_summary([row["ratios"][kind] for row in rows]) for kind in KINDS}
    return {
        "bits": bits,
        "instance": dataclasses.asdict(instance),
        "instance_hash": countedvm.instance_hash(instance),
        "generator_seed": PREREGISTERED["instance_seed"],
        "gp_checks": [oracle, zero_oracle],
        "startup_controls": controls,
        "startup_control_scope": "zero-operation programs; not a decomposition of measured work",
        "warmups": warmups,
        "pairs": rows,
        "c_f_native_reference_sample": spread_summary(
            [row["measurements"]["native"]["rates"]["seconds_per_op"] for row in rows]
        ),
        "c_f_scope": "this native reference, field size, operation mix, machine and session; not universally fastest",
        "kind_ratio_summaries": summaries,
        "status": "INCONCLUSIVE",
        "holds": HOLDS,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("dev-macos", "gold-linux-container"), required=True)
    parser.add_argument(
        "--compiler", type=Path, default=Path("/usr/bin/clang" if sys.platform == "darwin" else "/usr/bin/cc")
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--exploratory", action="store_true")
    parser.add_argument("--ops", type=int, default=PREREGISTERED["ops"])
    parser.add_argument("--pairs", type=int, default=PREREGISTERED["pairs"])
    parser.add_argument("--preregistration-sha")
    parser.add_argument("--preregistration-source-sha256")
    parser.add_argument("--image-digest")
    args = parser.parse_args(argv)
    if args.ops < 2 or args.ops > PREREGISTERED["ops"] or args.pairs < 2 or args.pairs > PREREGISTERED["pairs"]:
        parser.error("ops and pairs must be within the preregistered limits")
    if (args.arm == "dev-macos") != (sys.platform == "darwin"):
        parser.error("arm does not match the execution platform")
    if args.out.resolve().is_relative_to(ROOT):
        parser.error("output must be outside the checkout")
    if (
        args.arm == "gold-linux-container"
        and not args.exploratory
        and (not args.image_digest or re.fullmatch(r"sha256:[0-9a-f]{64}", args.image_digest) is None)
    ):
        parser.error("confirmatory Linux measurements require the container image digest")
    if not args.exploratory and (args.ops != PREREGISTERED["ops"] or args.pairs != PREREGISTERED["pairs"]):
        parser.error("confirmatory settings must match preregistration")
    if not args.exploratory:
        check_preregistration(args.preregistration_sha, args.preregistration_source_sha256)
    sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_PATHS}
    scratch = Path(tempfile.mkdtemp(prefix="cairn-vm-calibration-"))
    started = datetime.now(UTC).isoformat()
    vm, native, build = build_binaries(args.compiler, scratch / "build")
    rungs = [
        measure_rung(bits, args.ops, args.pairs, vm, native, build["vm_binary_digest"], scratch / str(bits))
        for bits in PREREGISTERED["bits"]
    ]
    report = {
        "kind": "counted_vm_calibration_exploratory" if args.exploratory else "counted_vm_calibration_preregistered",
        "preregistered": not args.exploratory,
        "preregistration_sha": None if args.exploratory else args.preregistration_sha,
        "preregistration_source_sha256": None if args.exploratory else args.preregistration_source_sha256,
        "preregistration_provenance": "operator supplies git-show SHA and digest and verifies the archived source; inputs alone are not proof",
        "preregistration": PREREGISTERED,
        "settings": {"ops": args.ops, "pairs": args.pairs},
        "arm": args.arm,
        "platform": platform.platform(),
        "image_digest": args.image_digest,
        "started_utc": started,
        "completed_utc": datetime.now(UTC).isoformat(),
        "source_sha256": sources,
        "build": build,
        "scratch": str(scratch),
        "rungs": rungs,
        "status": "INCONCLUSIVE",
        "holds": HOLDS,
        "no_claim": "No KEEP, B2/B3 sufficiency, universal emulation floor or ladder integration. The 254-bit ECDLP almost certainly stands.",
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"out": str(args.out), "kind": report["kind"], "status": report["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
