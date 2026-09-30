import argparse
import gc
import hashlib
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

GENERIC = "kind-add"
KINDS = ("counted", "kind-add", "kind-double", "kind-inverse", "kind-identity", "kind-torsion", "kind-adjacent")
PLANTED = {
    "early-return": {"flag": "-DCAIRN_EARLY_RETURN", "cheaper": ("kind-inverse", "kind-identity", "kind-torsion")},
    "variable-inversion": {"flag": "-DCAIRN_VARIABLE_INVERSION", "cheaper": ("kind-adjacent",)},
}
PREREGISTERED = {
    "pairs": 15,
    "ops": 10_000,
    "seed": 20260930,
    "warmup_calls_per_kind": 1,
    "kinds": list(KINDS),
    "generic": GENERIC,
    "quantity": "child CPU per counted op on CLOCK_PROCESS_CPUTIME_ID inside the object, per kind, over the "
    "generic add's in the same pair; the spawn is identical across kinds and cancels",
    "spread": "(max - min) / median over the per-pair ratios",
    "spread_bound": "0.50",
    "constant_work_band": "0.90",
    "constant_work_rule": "a kind is constant work when the median of its per-pair ratio to the generic add is at "
    "least the band; a kind below the band is cheaper, and the object fails the requirement",
    "planted": {
        name: {"flag": entry["flag"], "expected_cheaper": list(entry["cheaper"])} for name, entry in PLANTED.items()
    },
}
KIND_SEMANTICS = {
    "counted": "the alternating double/add chain from the base point",
    "kind-add": "generic addition, acc + G with acc distinct from G",
    "kind-double": "doubling, acc + acc through the same step",
    "kind-inverse": "G + (-G), the inverse pair, result O",
    "kind-identity": "O + G, an infinity operand, result G",
    "kind-torsion": "(gx, 0) + (gx, 0), the y = 0 doubling, result O",
    "kind-adjacent": "(gx, gy) + (gx + 1, gy), the chord with a unit x difference and a zero y difference",
}


def expected_kind_point(kind, ops):
    ec = counted.ec
    base = (counted.GX, counted.GY)
    if kind == "counted":
        return counted.expected_point(ops)
    if kind == "kind-add":
        return ec.mul(counted.P, counted.A, base, (ops + 1) % counted.N)
    if kind == "kind-double":
        return ec.mul(counted.P, counted.A, base, pow(2, ops, counted.N))
    if kind in ("kind-inverse", "kind-torsion"):
        return None
    if kind == "kind-identity":
        return base if ops else None
    if kind == "kind-adjacent":
        if not ops:
            return None
        x3 = (0 - counted.GX - (counted.GX + 1)) % counted.P
        return (x3, (0 - counted.GY) % counted.P)
    raise counted.ProbeError(f"unknown kind {kind!r}")


def validate_kind_payload(payload, kind, ops, timed):
    if set(payload) != counted.PROTOCOL_KEYS:
        raise counted.ProbeError("kind output fields do not match the closed protocol")
    if payload["mode"] != kind:
        raise counted.ProbeError("kind output mode does not match the request")
    if type(payload["requested_ops"]) is not int or payload["requested_ops"] != ops:
        raise counted.ProbeError("kind output requested operation count does not match the request")
    if type(payload["count"]) is not int or payload["count"] != ops:
        raise counted.ProbeError(f"{kind} count was {payload['count']!r}, expected {ops}")
    expected = expected_kind_point(kind, ops)
    actual = payload["point"]
    if expected is None:
        if actual is not None:
            raise counted.ProbeError(f"{kind} point was {actual!r}, expected infinity")
    else:
        if type(actual) is not list or len(actual) != 2 or any(type(c) is not int for c in actual):
            raise counted.ProbeError(f"{kind} point must be a pair of integers")
        if tuple(actual) != expected:
            raise counted.ProbeError(f"{kind} point was {actual!r}, expected {expected!r}")
    counted.validate_timing(payload, timed)
    return payload


def rusage_ns():
    own = resource.getrusage(resource.RUSAGE_SELF)
    kids = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "self_ns": round((own.ru_utime + own.ru_stime) * 1_000_000_000),
        "children_ns": round((kids.ru_utime + kids.ru_stime) * 1_000_000_000),
    }


def run_kind(binary, kind, ops, timed=True):
    reaped = []
    collecting = gc.isenabled()
    gc.disable()
    try:
        before = rusage_ns()
        payload, wall_ns = counted.run_binary(
            binary, kind, ops, timed=timed, after_reap=lambda: reaped.append(rusage_ns()), validate=False
        )
    finally:
        if collecting:
            gc.enable()
    validate_kind_payload(payload, kind, ops, timed)
    if len(reaped) != 1:
        raise counted.ProbeError(f"{kind} call reported {len(reaped)} reaps, expected 1")
    tree = (reaped[0]["self_ns"] - before["self_ns"]) + (reaped[0]["children_ns"] - before["children_ns"])
    if tree < 0:
        raise counted.ProbeError("rusage counters went backwards")
    return {"ops": ops, "child_cpu_ns": payload["child_cpu_ns"], "parent_wall_ns": wall_ns, "tree_cpu_ns": tree}


def kind_order(seed, pair_index):
    def rank(kind):
        return hashlib.sha256(f"{seed}:{pair_index}:{kind}".encode()).digest()

    return tuple(sorted(KINDS, key=rank))


def pair_ratios(results):
    generic = Decimal(results[GENERIC]["child_cpu_ns"]) / Decimal(results[GENERIC]["ops"])
    if generic <= 0:
        raise counted.ProbeError("generic add child CPU per op must be positive")
    return {
        kind: f"{(Decimal(results[kind]['child_cpu_ns']) / Decimal(results[kind]['ops'])) / generic:.9f}"
        for kind in KINDS
        if kind != GENERIC
    }


def run_pairs(binary, ops, pairs, seed):
    if type(ops) is not int or ops < counted.MIN_MEASURE_OPS or ops > counted.MAX_OPS:
        raise counted.ProbeError(f"measurement requires {counted.MIN_MEASURE_OPS} through {counted.MAX_OPS} operations")
    if type(pairs) is not int or pairs < 2:
        raise counted.ProbeError("measurement requires at least 2 pairs")
    warmup = [
        {"kind": kind, "call": call, **run_kind(binary, kind, ops)}
        for kind in KINDS
        for call in range(1, PREREGISTERED["warmup_calls_per_kind"] + 1)
    ]
    rows = []
    for pair in range(1, pairs + 1):
        order = kind_order(seed, pair)
        results = {kind: run_kind(binary, kind, ops) for kind in order}
        rows.append({"pair": pair, "order": list(order), **results, "ratio": pair_ratios(results)})
    return {"warmup": warmup, "pairs": rows}


def summarize_kinds(rows):
    return {
        kind: {
            "child_cpu_per_group_op": counted._stat(
                [row[kind]["child_cpu_ns"] / row[kind]["ops"] for row in rows], "s/group_op"
            ),
            "tree_cpu_per_group_op": counted._stat(
                [row[kind]["tree_cpu_ns"] / row[kind]["ops"] for row in rows], "s/group_op"
            ),
        }
        for kind in KINDS
    }


def verdicts(summary, band, spread_bound):
    result = {}
    for kind, entry in summary.items():
        result[kind] = {
            "constant_work": "constant_work" if Decimal(entry["median"]) >= Decimal(band) else "cheaper",
            "spread": "within_bound" if Decimal(entry["spread"]) <= Decimal(spread_bound) else "exceeded",
        }
    return result


def requirement_holds(kind_verdicts):
    return all(
        entry["constant_work"] == "constant_work" and entry["spread"] == "within_bound"
        for entry in kind_verdicts.values()
    )


def planted_outcome(name, kind_verdicts):
    expected = set(PLANTED[name]["cheaper"])
    cheaper = {kind for kind, entry in kind_verdicts.items() if entry["constant_work"] == "cheaper"}
    return {
        "planted": name,
        "expected_cheaper": sorted(expected),
        "observed_cheaper": sorted(cheaper),
        "fails_for_the_stated_reason": expected <= cheaper,
    }


def _arguments(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=Path, default=counted.CC)
    parser.add_argument("--pairs", type=int, default=PREREGISTERED["pairs"])
    parser.add_argument("--ops", type=counted._parse_nonnegative, default=PREREGISTERED["ops"])
    parser.add_argument("--seed", type=int, default=PREREGISTERED["seed"])
    parser.add_argument("--arm", type=str, required=True)
    parser.add_argument("--planted", choices=sorted(PLANTED))
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
    extra = () if args.planted is None else (PLANTED[args.planted]["flag"],)
    build = counted.build_binary(args.compiler, extra_cflags=extra)
    binary = build["binary"]
    metadata = {**counted._metadata(build), "kernel": platform.release(), "arm": args.arm, "planted": args.planted}
    before = paired.host_observations()
    correctness = counted.run_correctness(binary)
    refusals = counted.verify_input_refusals(binary)
    kind_correctness = [
        {"kind": kind, "ops": ops, **run_kind(binary, kind, ops, timed=False)} for kind in KINDS for ops in (1, 2, 3)
    ]
    timing = run_pairs(binary, args.ops, args.pairs, args.seed)
    after = paired.host_observations()
    summary = paired.summarize_ratios(timing["pairs"])
    kind_verdicts = verdicts(summary, PREREGISTERED["constant_work_band"], PREREGISTERED["spread_bound"])
    report = {
        "kind": "constant_work_exploratory" if args.exploratory else "constant_work",
        "preregistered": not args.exploratory,
        "preregistration": PREREGISTERED,
        "settings": {"pairs": args.pairs, "ops": args.ops, "seed": args.seed, "planted": args.planted},
        "metadata": metadata,
        "host_observations": {"before": before, "after": after},
        "counted_correctness_checks": correctness,
        "malformed_inputs_refused": refusals,
        "kind_correctness": kind_correctness,
        "timing": timing,
        "ratio_summary": summary,
        "kind_summary": summarize_kinds(timing["pairs"]),
        "verdicts": kind_verdicts,
        "requirement_holds": requirement_holds(kind_verdicts),
        "kind_semantics": KIND_SEMANTICS,
        "timing_status": "CONSTANT_WORK_PROVISIONAL",
    }
    if args.planted is not None:
        report["planted_outcome"] = planted_outcome(args.planted, kind_verdicts)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out is not None:
        args.out.write_text(text + "\n")
    if args.planted is not None and not report["planted_outcome"]["fails_for_the_stated_reason"]:
        print(f"planted negative {args.planted} did not fail for the stated reason", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except counted.ProbeError as exc:
        print(f"constant work probe refused: {exc}", file=sys.stderr)
        sys.exit(1)
