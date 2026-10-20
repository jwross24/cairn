import argparse
import dataclasses
import hashlib
import importlib.util
import json
import os
import re
import statistics
import sys
import tempfile
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Context, Decimal
from pathlib import Path

from cairn import countedvm, runner
from cairn.skills import toy_curve

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "bundle" / "ladder_plan.json"
DOCUMENT = ROOT / "research" / "grounding" / "counted-vm-long-calibration-preregistration.md"
_spec = importlib.util.spec_from_file_location(
    "probe_counted_vm_calibration", ROOT / "research" / "grounding" / "probe_counted_vm_calibration.py"
)
assert _spec is not None and _spec.loader is not None
prior = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prior)

KINDS = prior.KINDS
ARMS = prior.ARMS
MAX_INDEX = 1_048_575
EXIT_LOAD_REFUSED = 4
SETUP = ("setp p0 P", "setp p1 P", "setp p2 inf", "negp p3 p1", "sset s0 7")
STEPS = {
    "chain": ("dblp p0 p0", "addp p0 p0 p1"),
    "add": ("addp p0 p0 p1",),
    "double": ("dblp p0 p0",),
    "identity": ("addp p0 p2 p1",),
    "inverse": ("addp p0 p1 p3",),
    "scalar_mul": ("mulp p0 p1 s0",),
}
OPS_PER_ITERATION = {
    "chain": 2,
    "add": 1,
    "double": 1,
    "identity": 1,
    "inverse": 1,
    "scalar_mul": countedvm.expected_mul_ops(7),
}
PREREGISTERED = {
    "bits": [30, 40, 50, 60],
    "pairs": 15,
    "low_ops": 10_000_000,
    "high_ops": 20_000_000,
    "inner_iterations": 500_000,
    "seed": 20261020,
    "instance_seed": 1,
    "warmups": 1,
    "statistic": "(max - min) / median of per-pair VM over native two-point cost per operation",
    "spread_bound": "0.50",
    "load_limit": "2",
    "wall_cap_s": 300,
    "instruction_budget": 200_000_000,
    "baseline_variant": "plain",
}
SPREAD_BOUND = Decimal(PREREGISTERED["spread_bound"])
LOAD_LIMIT = Decimal(PREREGISTERED["load_limit"])
CONSUMING = ("WITHIN_BOUND", "EXCEEDED_ON_IDLE_HOST")


def load_gate(readings):
    records = []
    for label, reading in readings:
        one, five, fifteen = (Decimal(str(value)) for value in reading)
        records.append({"source": label, "load_1m": str(one), "load_5m": str(five), "load_15m": str(fifteen)})
    admitted = all(Decimal(record["load_1m"]) < LOAD_LIMIT for record in records)
    return {"admitted": admitted, "limit": PREREGISTERED["load_limit"], "readings": records}


def refusal(gate):
    return {
        "kind": "counted_vm_long_calibration_refusal",
        "run_consumed": False,
        "reason": "host_load_not_below_limit",
        "gate": gate,
    }


def sample_load(reader):
    return [str(Decimal(str(value))) for value in reader()]


def two_point_cost(cpu_low, cpu_high, ops_low, ops_high):
    if type(ops_low) is not int or type(ops_high) is not int or ops_low <= 0 or ops_high <= ops_low:
        raise ValueError("two distinct positive operation counts are required")
    low, high = Decimal(str(cpu_low)), Decimal(str(cpu_high))
    cost = (high - low) / Decimal(ops_high - ops_low)
    if not cost.is_finite() or cost <= 0:
        raise ValueError("two-point difference is not positive")
    values = {"seconds_per_op": str(cost), "ops_per_second": str(1 / cost)}
    prior.validate_rate(values)
    return {**values, "startup_cpu_s": str(low - cost * ops_low)}


def spread_summary(values):
    if any(value is None for value in values):
        return {"status": "INCONCLUSIVE", "figure": None, "reason": "invalid two-point sample"}
    summary = prior.spread_summary(values)
    exceeded = Decimal(summary["spread"]) > SPREAD_BOUND
    return {
        **summary,
        "status": "INCONCLUSIVE" if exceeded else "OBSERVED_WITHIN_SPREAD",
        "figure": None if exceeded else summary["sample_median"],
    }


def plan_inputs(path=None):
    plan = json.loads(Path(PLAN if path is None else path).read_text())
    bits = [rung["bits"] for rung in plan["rungs"]]
    variant = plan["baseline"]["method_identity"]["params"]["variant"]
    if bits != PREREGISTERED["bits"]:
        raise ValueError(f"plan rung sizes {bits} differ from the preregistered sizes")
    if variant != PREREGISTERED["baseline_variant"]:
        raise ValueError(f"baseline variant {variant!r} is not the plain program")
    return bits


def program(kind, ops, inner):
    if kind not in KINDS or type(ops) is not int or type(inner) is not int or ops <= 0:
        raise ValueError("unsupported kind, operation count or inner counter")
    iterations, remainder = divmod(ops, OPS_PER_ITERATION[kind])
    if remainder or inner < 1 or inner > MAX_INDEX or iterations % inner:
        raise ValueError("operations must fill whole iterations and whole inner loops within the index cap")
    outer = iterations // inner
    if outer > MAX_INDEX:
        raise ValueError("outer counter exceeds the index cap")
    lines = [
        *SETUP,
        f"iset i1 {outer}",
        "outer:",
        f"iset i0 {inner}",
        "loop:",
        *STEPS[kind],
        "isub i0 i0 1",
        "jnz i0 loop",
        "isub i1 i1 1",
        "jnz i1 outer",
        "halt",
    ]
    return "\n".join(lines) + "\n"


def expected_executed(kind, ops, inner):
    outer = ops // OPS_PER_ITERATION[kind] // inner
    return len(SETUP) + 1 + outer * (3 + inner * (len(STEPS[kind]) + 2)) + 1


def fixed_bounds(bits, low_ops, high_ops, inner, budget):
    programs, executed = {}, {}
    for kind in KINDS:
        for ops in (low_ops, high_ops):
            key = f"{kind}:{ops}"
            programs[key] = hashlib.sha256(program(kind, ops, inner).encode()).hexdigest()
            executed[key] = expected_executed(kind, ops, inner)
    if max(executed.values()) >= budget:
        raise ValueError("instruction budget does not cover the largest program")
    return {
        "bits": list(bits),
        "low_ops": low_ops,
        "high_ops": high_ops,
        "inner_iterations": inner,
        "instruction_budget": budget,
        "program_sha256": programs,
        "expected_executed": executed,
    }


def ordered_arms(pair):
    return sorted(ARMS, key=lambda arm: hashlib.sha256(f"{PREREGISTERED['seed']}:{pair}:{arm}".encode()).digest())


def measure_vm(binary, digest, instance, kind, ops, inner, budget, expected, scratch, attempt_id, reader):
    before = sample_load(reader)
    run = countedvm.launch(
        binary,
        digest,
        instance,
        program(kind, ops, inner),
        budget,
        attempt_id=attempt_id,
        scratch_dir=scratch,
        wall_cap_s=PREREGISTERED["wall_cap_s"],
    )
    after = sample_load(reader)
    outcome = run.outcome
    if outcome.status != countedvm.STATUS_OK or outcome.count != ops or outcome.p0 != expected:
        raise ValueError(f"VM {kind} disagrees with expected count or independent GP")
    if outcome.executed != expected_executed(kind, ops, inner):
        raise ValueError(f"VM {kind} executed {outcome.executed} instructions, unexpected")
    if not runner.scope_is_verified_complete(run.measurement_scope):
        raise ValueError("VM measurement scope is incomplete")
    cpu = Decimal(str(run.cpu_user_s)) + Decimal(str(run.cpu_sys_s))
    return {
        "counted_ops": ops,
        "cpu_s": str(cpu),
        "load_before": before,
        "load_after": after,
        "receipt": dataclasses.asdict(run),
    }


def measure_native(binary, instance, ops, expected, scratch, reader):
    scratch.mkdir(parents=True)
    out, err = scratch / "stdout", scratch / "stderr"
    before = sample_load(reader)
    run = runner.spawn_and_wait(
        [str(binary), str(instance.p), str(instance.a), *(str(c) for c in instance.P), str(ops)],
        out,
        err,
        wall_cap_s=PREREGISTERED["wall_cap_s"],
        env=runner.child_env(),
    )
    after = sample_load(reader)
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
    if (None if payload["inf"] else (payload["x"], payload["y"])) != expected:
        raise ValueError("native result disagrees with independent GP")
    return {
        "counted_ops": ops,
        "cpu_s": str(Decimal(str(payload["cpu_s"]))),
        "load_before": before,
        "load_after": after,
        "receipt": dataclasses.asdict(run),
    }


def pair_costs(samples):
    try:
        return two_point_cost(
            samples["low"]["cpu_s"],
            samples["high"]["cpu_s"],
            samples["low"]["counted_ops"],
            samples["high"]["counted_ops"],
        )
    except ValueError as error:
        return {"invalid": str(error)}


def pair_ratios(costs):
    c_f = costs["native"].get("seconds_per_op")
    return {
        kind: None
        if c_f is None or "invalid" in costs[kind]
        else str(Decimal(costs[kind]["seconds_per_op"]) / Decimal(c_f))
        for kind in KINDS
    }


def cell_summaries(rows):
    ratios = [pair_ratios(row["costs"]) for row in rows]
    return {kind: spread_summary([pair[kind] for pair in ratios]) for kind in KINDS}


def measure_rung(bits, bounds, pairs, binaries, scratch, reader):
    vm, native, digest = binaries
    low, high, inner, budget = (
        bounds[key] for key in ("low_ops", "high_ops", "inner_iterations", "instruction_budget")
    )
    generated = toy_curve.run(bits, PREREGISTERED["instance_seed"])
    if generated.status != toy_curve.STATUS_OK or generated.p.bit_length() != bits:
        raise ValueError("instance generator produced the wrong field size")
    instance = countedvm.Instance(
        generated.p, generated.a, generated.b, generated.n, tuple(generated.P), tuple(generated.P)
    )
    expected = {}
    oracles = []
    for ops in (low, high):
        expected[ops], oracle = prior.gp_points(instance, ops)
        oracles.append(oracle)

    def call(arm, ops, label):
        directory = scratch / label / f"{arm}-{ops}"
        directory.parent.mkdir(parents=True, exist_ok=True)
        if arm == "native":
            return measure_native(native, instance, ops, expected[ops]["chain"], directory, reader)
        return measure_vm(
            vm,
            digest,
            instance,
            arm,
            ops,
            inner,
            budget,
            expected[ops][arm],
            directory,
            f"{bits}:{label}:{arm}:{ops}",
            reader,
        )

    warmups = {arm: call(arm, low, "warmup") for arm in ordered_arms(0)}
    rows = []
    for pair in range(pairs):
        order = ordered_arms(pair + 1)
        samples = {
            arm: {"low": call(arm, low, f"pair-{pair}"), "high": call(arm, high, f"pair-{pair}")} for arm in order
        }
        costs = {arm: pair_costs(samples[arm]) for arm in order}
        rows.append({"pair": pair + 1, "order": order, "samples": samples, "costs": costs})
    return {
        "bits": bits,
        "instance": dataclasses.asdict(instance),
        "instance_hash": countedvm.instance_hash(instance),
        "gp_checks": oracles,
        "warmups": warmups,
        "pairs": rows,
        "kind_ratio_summaries": cell_summaries(rows),
    }


def loads_of(rungs):
    for rung in rungs:
        samples = list(rung["warmups"].values())
        for row in rung["pairs"]:
            for arm in row["samples"].values():
                samples.extend(arm.values())
        for sample in samples:
            yield from (Decimal(sample[key][0]) for key in ("load_before", "load_after"))


def require_complete(rungs):
    if [rung["bits"] for rung in rungs] != PREREGISTERED["bits"]:
        raise ValueError("every preregistered rung is required")
    if any(not rung["pairs"] or any(set(row["costs"]) != set(ARMS) for row in rung["pairs"]) for rung in rungs):
        raise ValueError("every rung needs pairs with the native arm and six kinds")


def classify(rungs):
    require_complete(rungs)
    if not all(value < LOAD_LIMIT for value in loads_of(rungs)):
        return "LOAD_NOT_CLEAN", False
    cells = [cell for rung in rungs for cell in cell_summaries(rung["pairs"]).values()]
    if any("spread" in cell and cell["status"] == "INCONCLUSIVE" for cell in cells):
        return "EXCEEDED_ON_IDLE_HOST", True
    if any(cell["status"] == "INCONCLUSIVE" for cell in cells):
        return "INVALID_SAMPLE", True
    return "WITHIN_BOUND", True


def rate_ratio_candidate(rungs):
    status, _ = classify(rungs)
    if status != "WITHIN_BOUND":
        return {"candidate": None, "reason": f"status {status}: no figure is converted"}

    def median(rung, arm):
        return statistics.median([Decimal(row["costs"][arm]["seconds_per_op"]) for row in rung["pairs"]])

    reference = min(median(rung, "native") for rung in rungs)
    slowest = max(median(rung, kind) for rung in rungs for kind in KINDS)
    ratio = slowest / reference
    candidate = Context(prec=3, rounding=ROUND_CEILING).plus(ratio)
    plan = json.loads(PLAN.read_text())
    tolerance, radius = Decimal(plan["tolerances"]["clock"]), Decimal(plan["design_radius"])
    return {
        "candidate": str(candidate) if ratio >= 1 else None,
        "reference_cost_s_per_group_op": str(reference),
        "slowest_vm_cost_s_per_op": str(slowest),
        "unrounded_ratio": str(ratio),
        "rounding": "up, 3 significant digits",
        "clock_tolerance": str(tolerance),
        "product": str(tolerance * candidate),
        "keep_band_excess": str(2 * radius),
        "plan_inequality_holds": ratio >= 1 and tolerance * candidate < 2 * radius,
    }


def check_preregistration(sha, source_sha256, document_sha256):
    for value, pattern, name in (
        (sha, r"[0-9a-f]{40}", "a full committed preregistration SHA"),
        (source_sha256, r"[0-9a-f]{64}", "the operator-supplied committed source SHA256"),
        (document_sha256, r"[0-9a-f]{64}", "the operator-supplied committed document SHA256"),
    ):
        if not value or re.fullmatch(pattern, value) is None:
            raise ValueError(f"{name} is required")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != source_sha256:
        raise ValueError("source differs from the supplied preregistration digest")
    if hashlib.sha256(DOCUMENT.read_bytes()).hexdigest() != document_sha256:
        raise ValueError("document differs from the supplied preregistration digest")


def parse_reading(text):
    values = tuple(float(part) for part in text.split(","))
    if len(values) != 3 or min(values) < 0:
        raise argparse.ArgumentTypeError("expected 1m,5m,15m")
    return values


def main(argv=None, load_reader=os.getloadavg):
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("dev-macos", "gold-linux-container"), required=True)
    parser.add_argument(
        "--compiler", type=Path, default=Path("/usr/bin/clang" if sys.platform == "darwin" else "/usr/bin/cc")
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--exploratory", action="store_true")
    parser.add_argument("--low-ops", type=int, default=PREREGISTERED["low_ops"])
    parser.add_argument("--high-ops", type=int, default=PREREGISTERED["high_ops"])
    parser.add_argument("--inner", type=int, default=PREREGISTERED["inner_iterations"])
    parser.add_argument("--pairs", type=int, default=PREREGISTERED["pairs"])
    parser.add_argument("--injected-load", type=parse_reading)
    parser.add_argument("--preregistration-sha")
    parser.add_argument("--preregistration-source-sha256")
    parser.add_argument("--preregistration-document-sha256")
    args = parser.parse_args(argv)
    settings = (args.low_ops, args.high_ops, args.inner, args.pairs)
    fixed = (
        PREREGISTERED["low_ops"],
        PREREGISTERED["high_ops"],
        PREREGISTERED["inner_iterations"],
        PREREGISTERED["pairs"],
    )
    if not args.exploratory and settings != fixed:
        parser.error("confirmatory settings must match preregistration")
    if not args.exploratory and args.injected_load:
        parser.error("an injected load reading is exploratory only")
    if args.pairs < 2 or args.pairs > PREREGISTERED["pairs"]:
        parser.error("pairs must be within the preregistered limits")
    if not args.exploratory and args.arm != "dev-macos":
        parser.error("this preregistration covers the dev-macos arm only")
    if (args.arm == "dev-macos") != (sys.platform == "darwin"):
        parser.error("arm does not match the execution platform")
    if args.out.resolve().is_relative_to(ROOT) or args.out.exists():
        parser.error("output must be a new path outside the checkout")
    if not args.exploratory:
        try:
            check_preregistration(
                args.preregistration_sha, args.preregistration_source_sha256, args.preregistration_document_sha256
            )
        except ValueError as error:
            parser.error(str(error))
    reader = (lambda: args.injected_load) if args.injected_load else load_reader
    gate = load_gate([("local" if args.injected_load is None else "injected", tuple(reader()))])
    if not gate["admitted"]:
        text = json.dumps(refusal(gate), sort_keys=True)
        args.out.write_text(text + "\n")
        print(text)
        return EXIT_LOAD_REFUSED
    bits = plan_inputs()
    bounds = fixed_bounds(bits, args.low_ops, args.high_ops, args.inner, PREREGISTERED["instruction_budget"])
    sources = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in (
            "research/grounding/probe_counted_vm_long_calibration.py",
            "research/grounding/probe_counted_vm_calibration.py",
            "bundle/ladder_plan.json",
            "src/cairn/countedvm/__init__.py",
            "src/cairn/runner.py",
            "src/cairn/skills/toy_curve.py",
        )
    }
    scratch = Path(tempfile.mkdtemp(prefix="cairn-vm-long-calibration-"))
    vm, native, build = prior.build_binaries(args.compiler, scratch / "build")
    binaries = (vm, native, build["vm_binary_digest"])
    rungs = [measure_rung(b, bounds, args.pairs, binaries, scratch / str(b), reader) for b in bits]
    status, load_clean = classify(rungs)
    report = {
        "kind": "counted_vm_long_calibration_exploratory" if args.exploratory else "counted_vm_long_calibration",
        "preregistered": not args.exploratory,
        "run_consumed": not args.exploratory and status in CONSUMING,
        "rate_ratio": {"candidate": None, "reason": "exploratory run"}
        if args.exploratory
        else rate_ratio_candidate(rungs),
        "preregistration_sha": None if args.exploratory else args.preregistration_sha,
        "preregistration_source_sha256": None if args.exploratory else args.preregistration_source_sha256,
        "preregistration_document_sha256": None if args.exploratory else args.preregistration_document_sha256,
        "preregistration": PREREGISTERED,
        "settings": {"low_ops": args.low_ops, "high_ops": args.high_ops, "inner": args.inner, "pairs": args.pairs},
        "load_gate": gate,
        "load_clean_throughout": load_clean,
        "bounds_fixed_before_any_curve": bounds,
        "arm": args.arm,
        "completed_utc": datetime.now(UTC).isoformat(),
        "source_sha256": sources,
        "build": build,
        "scratch": str(scratch),
        "rungs": rungs,
        "status": status,
        "no_claim": "No KEEP, B2/B3 sufficiency, emulation floor or pin.",
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"out": str(args.out), "kind": report["kind"], "status": status, "load_clean": load_clean}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
