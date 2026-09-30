import argparse
import gc
import importlib
import json
import platform
import resource
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

counted = importlib.import_module("research.grounding.probe_counted_process")
paired = importlib.import_module("research.grounding.probe_paired_rate")
deployed = importlib.import_module("research.grounding.probe_deployed_rate")

RATIO_KINDS = ("cpu_deployed_batch", "cpu_deployed_trial_batch", "cpu_deployed_ipc")
PREREGISTERED = {
    "pairs": deployed.PREREGISTERED["pairs"],
    "ops": deployed.PREREGISTERED["ops"],
    "trial_ops": deployed.PREREGISTERED["trial_ops"],
    "seed": deployed.PREREGISTERED["seed"],
    "warmup_calls_per_arm": deployed.PREREGISTERED["warmup_calls_per_arm"],
    "arms": list(deployed.ARMS),
    "quantity": "process-tree CPU per counted op: the parent's RUSAGE_SELF user plus system delta and the "
    "RUSAGE_CHILDREN user plus system delta from before the spawn to the reap, ahead of any validation, "
    "with the garbage collector held off, over the reference child CPU per op",
    "spread": deployed.PREREGISTERED["spread"],
    "spread_bound": dict.fromkeys(RATIO_KINDS, "0.50"),
    "figure_rule": deployed.PREREGISTERED["figure_rule"],
}
RATIO_SEMANTICS = {
    "cpu_deployed_batch": "process-tree CPU per group op of counted-mode calls at ops per call over reference child "
    "CPU per group op",
    "cpu_deployed_trial_batch": "process-tree CPU per group op of counted-mode calls at trial_ops per call over "
    "reference child CPU per group op",
    "cpu_deployed_ipc": "process-tree CPU per group op of a serve session with one round trip per op from a Python "
    "client over reference child CPU per group op",
}


def rusage_ns():
    own = resource.getrusage(resource.RUSAGE_SELF)
    kids = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "self_ns": round((own.ru_utime + own.ru_stime) * 1_000_000_000),
        "children_ns": round((kids.ru_utime + kids.ru_stime) * 1_000_000_000),
    }


def cpu_delta(before, after):
    self_ns = after["self_ns"] - before["self_ns"]
    children_ns = after["children_ns"] - before["children_ns"]
    if self_ns < 0 or children_ns < 0:
        raise counted.ProbeError("rusage counters went backwards")
    return {"parent_cpu_ns": self_ns, "children_cpu_ns": children_ns, "tree_cpu_ns": self_ns + children_ns}


def call_with_cpu(arm, reference_binary, counted_binary, ops, trial_ops):
    reaped = []
    collecting = gc.isenabled()
    gc.disable()
    try:
        before = rusage_ns()
        result = deployed._call_arm(
            arm, reference_binary, counted_binary, ops, trial_ops, after_reap=lambda: reaped.append(rusage_ns())
        )
    finally:
        if collecting:
            gc.enable()
    if len(reaped) != 1:
        raise counted.ProbeError(f"{arm} call reported {len(reaped)} reaps, expected 1")
    return {**result, **cpu_delta(before, reaped[0])}


def _per_op(result, clock):
    return Decimal(result[clock]) / Decimal(result["ops"])


def pair_ratios(results):
    reference = _per_op(results["reference"], "child_cpu_ns")
    if reference <= 0:
        raise counted.ProbeError("reference child CPU per op must be positive")
    return {
        "cpu_deployed_batch": f"{_per_op(results['batch'], 'tree_cpu_ns') / reference:.9f}",
        "cpu_deployed_trial_batch": f"{_per_op(results['trial_batch'], 'tree_cpu_ns') / reference:.9f}",
        "cpu_deployed_ipc": f"{_per_op(results['ipc'], 'tree_cpu_ns') / reference:.9f}",
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
        {"arm": arm, "call": call, **call_with_cpu(arm, reference_binary, counted_binary, ops, trial_ops)}
        for arm in deployed.ARMS
        for call in range(1, PREREGISTERED["warmup_calls_per_arm"] + 1)
    ]
    rows = []
    for pair in range(1, pairs + 1):
        order = deployed.arm_order(seed, pair)
        results = {arm: call_with_cpu(arm, reference_binary, counted_binary, ops, trial_ops) for arm in order}
        rows.append({"pair": pair, "order": list(order), **results, "ratio": pair_ratios(results)})
    return {"warmup": warmup, "pairs": rows}


def summarize_arms(rows):
    clocks = ("child_cpu_ns", "parent_cpu_ns", "children_cpu_ns", "tree_cpu_ns", "parent_wall_ns")
    return {
        arm: {
            clock.replace("_ns", "_per_group_op"): counted._stat(
                [row[arm][clock] / row[arm]["ops"] for row in rows], "s/group_op"
            )
            for clock in clocks
        }
        for arm in deployed.ARMS
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
        "rusage_resolution_s": "0.000001",
    }
    before = paired.host_observations()
    correctness = counted.run_correctness(counted_binary)
    refusals = counted.verify_input_refusals(counted_binary)
    serve_correctness = [{"ops": ops, **deployed.run_serve(counted_binary, ops)} for ops in (1, 2, 3, 31)]
    timing = run_pairs(reference["binary"], counted_binary, args.ops, args.trial_ops, args.pairs, args.seed)
    after = paired.host_observations()
    summary = paired.summarize_ratios(timing["pairs"])
    verdicts = spread_verdicts(summary, PREREGISTERED["spread_bound"])
    chosen = figures(summary, verdicts)
    bound = deployed.clock_bound()
    report = {
        "kind": "deployed_cpu_rate_exploratory" if args.exploratory else "deployed_cpu_rate",
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
        "clock_bound": {**bound, "evaluation": deployed.evaluate_bound(bound, chosen)},
        "ratio_semantics": RATIO_SEMANTICS,
        "timing_status": "DEPLOYED_CPU_PROVISIONAL",
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
        print(f"deployed cpu probe refused: {exc}", file=sys.stderr)
        sys.exit(1)
