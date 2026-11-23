import json
from dataclasses import dataclass
from itertools import combinations
from math import prod

from cairn import claims, log, repro

lg = log.get("justify")

CLASSES = claims.TAGS
SPECULATION, CONJECTURE, STRONG_EMPIRICAL, PROVEN = CLASSES

KIND_MAX_CLASS = {
    "lean_artifact": PROVEN,
    "ladder_table": STRONG_EMPIRICAL,
    "repro_node": STRONG_EMPIRICAL,
    "statistical": STRONG_EMPIRICAL,
    "counterexample_hunt_record": CONJECTURE,
    "model_proof": CONJECTURE,
}

AUDIT_ONLY = "AuditOnly"
AUTHOR_SUPPLIED = "author_supplied"
ACTOR = "gate:justify"
REASON_HUMAN_REVIEW = "human_review"
REASON_HUNT_KILLED = "hunt-killed"
REASON_REPRO_DEFERRED = "repro-deferred"
REASON_INADMISSIBLE = "attempt-inadmissible"
REASON_AUDIT_ONLY = "audit-only-inadmissible"
REASON_PREMISE_CEILING = "premise-ceiling"


@dataclass(frozen=True)
class CrossCheckCoverage:
    covered: bool
    dimensions: dict[str, bool]
    contributions: dict[str, dict[str, list[int]]]

    def __bool__(self):
        raise TypeError("use coverage.covered")

    def record(self):
        return {
            "covered": self.covered,
            "dimensions": self.dimensions,
            "contributions": self.contributions,
        }


@dataclass(frozen=True)
class Justification:
    cls: str
    kind: str
    evidence_hash: str
    reason: str
    gate_run_hash: str | None = None
    review_verdict_hash: str | None = None
    record_digest: str | None = None
    file_offset: int | None = None
    cross_check_coverage: CrossCheckCoverage | None = None


@dataclass(frozen=True)
class CoverageViolation:
    field: str
    evidence_hash: str


@dataclass(frozen=True)
class LatticeViolation:
    reason: str
    evidence_hash: str


@dataclass(frozen=True)
class Absent:
    reason: str
    evidence_hash: str


@dataclass(frozen=True)
class Pending:
    reason: str
    evidence_hash: str


@dataclass(frozen=True)
class Refutation:
    evidence_hash: str


@dataclass(frozen=True)
class Context:
    grade: str = "Replayable"
    repro_passed: bool | None = None
    has_cost_model: bool = False
    approved: bool = False
    disowned: bool = False
    statement_status: str = "open"
    producer_summary: dict | None = None
    attempt_inputs: dict | None = None
    offered_class: str | None = None
    tier: int = 0
    inadmissible: bool = False
    formalization_reason: str | None = "lean-gate-absent"
    gate_run_hash: str | None = None
    review_verdict_hash: str | None = None
    record_digest: str | None = None
    file_offset: int | None = None


@dataclass(frozen=True)
class Derivation:
    statement_hash: str
    tag: str
    justified_by: str | None
    results: tuple
    appended: bool
    refuted_by: str | None
    deferred: tuple = ()
    premise_cap: tuple | None = None


def rank(cls):
    return CLASSES.index(cls)


def weakest(a, b):
    return a if rank(a) <= rank(b) else b


def _load(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return value


def _interval(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return (value, value)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        lo, hi = value
        if isinstance(lo, bool) or isinstance(hi, bool):
            return None
        if not isinstance(lo, int) or not isinstance(hi, int):
            return None
        return (lo, hi)
    return None


def contains(outer, inner):
    wide = _interval(outer)
    narrow = _interval(inner)
    if wide is None or narrow is None:
        return False
    if wide[0] > wide[1] or narrow[0] > narrow[1]:
        return False
    return wide[0] <= narrow[0] and wide[1] >= narrow[1]


def _as_set(value):
    if value is None:
        return frozenset()
    if isinstance(value, (str, bytes)):
        return None
    if isinstance(value, (set, frozenset, list, tuple)):
        try:
            return frozenset(value)
        except TypeError:
            return None
    return None


def subset(inner, outer):
    small = _as_set(inner)
    big = _as_set(outer)
    if small is None or big is None:
        return False
    return small <= big


def coverage_violation(population, scope):
    if not isinstance(population, dict) or not isinstance(scope, dict):
        return "population"
    if population.get("target_family") != scope.get("target_family"):
        return "target_family"
    if not contains(population.get("size_interval"), scope.get("size_interval")):
        return "size_interval"
    wide = population.get("param_ranges")
    narrow = scope.get("param_ranges")
    if narrow is None:
        narrow = {}
    if not isinstance(wide, dict) or not isinstance(narrow, dict):
        return "param_ranges"
    for axis, wanted in narrow.items():
        if not contains(wide.get(axis), wanted):
            return "param_ranges"
    if not subset(population.get("assumption_set"), scope.get("assumption_set")):
        return "assumptions"
    return None


def counterexample_coverage_violation(population, scope):
    if not isinstance(population, dict) or not isinstance(scope, dict):
        return "population"
    if population.get("target_family") != scope.get("target_family"):
        return "target_family"
    if not contains(scope.get("size_interval"), population.get("size_interval")):
        return "size_interval"
    point_ranges = population.get("param_ranges")
    scope_ranges = scope.get("param_ranges", {})
    if not isinstance(point_ranges, dict) or not isinstance(scope_ranges, dict):
        return "param_ranges"
    for axis, bounds in scope_ranges.items():
        if not contains(bounds, point_ranges.get(axis)):
            return "param_ranges"
    if not subset(scope.get("assumption_set"), population.get("assumption_set")):
        return "assumptions"
    return None


def _origin_values(origins):
    if isinstance(origins, dict):
        values = []
        for entry in origins.values():
            values.extend(entry.values() if isinstance(entry, dict) else [entry])
        return values
    if isinstance(origins, (list, tuple)):
        return list(origins)
    return []


def _cross_check_records(cross_check):
    singular = isinstance(cross_check, dict)
    records = [cross_check] if singular else cross_check
    if not isinstance(records, (list, tuple)) or not records:
        return None
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            return None
        ranges = record.get("independent_range")
        if not isinstance(ranges, dict) or not ranges:
            return None
        if not singular:
            axis = record.get("axis")
            if axis not in ("algorithm", "implementation") or axis in seen:
                return None
            seen.add(axis)
            for bounds in ranges.values():
                interval = _interval(bounds)
                if interval is None or interval[0] > interval[1]:
                    return None
    return records


def _clip_box(ranges, requested):
    clipped = {}
    for dimension, (low, high) in requested.items():
        bounds = _interval(ranges.get(dimension))
        if bounds is None or bounds[0] > bounds[1]:
            return None
        start, end = max(low, bounds[0]), min(high, bounds[1])
        if start > end:
            return None
        clipped[dimension] = (start, end)
    return clipped


def _box_volume(box):
    return prod(high - low + 1 for low, high in box.values())


def _box_union_volume(boxes):
    volume = 0
    for count in range(1, len(boxes) + 1):
        for selected in combinations(boxes, count):
            intersection = selected[0]
            for box in selected[1:]:
                intersection = _clip_box(box, intersection)
                if intersection is None:
                    break
            if intersection is not None:
                volume += (1 if count % 2 else -1) * _box_volume(intersection)
    return volume


def cross_check_covers(cross_check, inputs):
    if not isinstance(inputs, dict) or not inputs:
        return CrossCheckCoverage(False, {}, {})
    records = _cross_check_records(cross_check)
    if records is None:
        return CrossCheckCoverage(False, dict.fromkeys(inputs, False), {})
    requested = {}
    for dimension, wanted in inputs.items():
        interval = _interval(wanted)
        if interval is None or interval[0] > interval[1]:
            return CrossCheckCoverage(False, dict.fromkeys(inputs, False), {dimension: {} for dimension in inputs})
        requested[dimension] = interval
    clipped = []
    for record in records:
        box = _clip_box(record["independent_range"], requested)
        if box is not None:
            clipped.append((record.get("axis"), box))
    dimensions = {
        dimension: _box_union_volume([{dimension: box[dimension]} for _, box in clipped]) == high - low + 1
        for dimension, (low, high) in requested.items()
    }
    contributions = {
        dimension: {axis: list(box[dimension]) for axis, box in clipped if isinstance(axis, str)}
        for dimension in requested
    }
    covered = _box_union_volume([box for _, box in clipped]) == _box_volume(requested)
    return CrossCheckCoverage(covered, dimensions, contributions)


def producer_capped(summary, inputs, *, coverage=None):
    if not isinstance(summary, dict):
        return False
    if not all(value == AUTHOR_SUPPLIED for value in _origin_values(summary.get("corpus_origins"))):
        return False
    if summary.get("randomized_arm"):
        return False
    coverage = cross_check_covers(summary.get("cross_check"), inputs) if coverage is None else coverage
    return not coverage.covered


def kind_class(
    kind,
    verdict,
    *,
    repro_passed=None,
    in_sample_ok=False,
    has_cost_model=False,
    approved=False,
):
    if kind == "lean_artifact":
        return (PROVEN, "lean-artifact-approved") if approved else (None, REASON_HUMAN_REVIEW)
    if kind == "ladder_table":
        if verdict == "KEEP" or (verdict == "KEEP_IN_SAMPLE" and in_sample_ok):
            if repro_passed:
                return STRONG_EMPIRICAL, "ladder-keep-repro"
            return CONJECTURE, "ladder-keep-no-repro"
        return None, f"table-verdict-{verdict}"
    if kind in ("repro_node", "statistical"):
        if has_cost_model:
            return CONJECTURE, "cost-model-statement"
        return STRONG_EMPIRICAL, f"{kind}-population"
    if kind == "model_proof":
        return CONJECTURE, "model-proof"
    if kind == "counterexample_hunt_record":
        if verdict == "SURVIVED":
            return CONJECTURE, "hunt-survived"
        if verdict == "KILLED":
            return None, REASON_HUNT_KILLED
        return None, f"hunt-verdict-{verdict}"
    return None, f"unknown-kind-{kind}"


def strongest(results):
    best = None
    for pair in results:
        result = pair[1]
        if isinstance(result, Justification) and (best is None or rank(result.cls) > rank(best[1].cls)):
            best = pair
    return best


def _population(evidence):
    population = _load(evidence.get("population"))
    if not isinstance(population, dict):
        return None
    declared = _as_set(_load(evidence.get("assumptions"))) or frozenset()
    carried = _as_set(population.get("assumption_set"))
    if carried is None:
        return population
    return {**population, "assumption_set": carried | declared}


def justify(evidence, statement, ctx):
    evidence_hash = evidence.get("hash")
    kind = evidence.get("kind")
    ceiling = KIND_MAX_CLASS.get(kind)
    result = _judge(evidence, statement, ctx, kind, ceiling, evidence_hash)
    lg.info(
        "justify",
        statement=statement.get("hash"),
        evidence=evidence_hash,
        kind=kind,
        result=type(result).__name__,
        detail=getattr(result, "cls", None) or getattr(result, "field", None) or getattr(result, "reason", None),
    )
    return result


def _judge(evidence, statement, ctx, kind, ceiling, evidence_hash):
    if ctx.offered_class is not None and (ceiling is None or rank(ctx.offered_class) > rank(ceiling)):
        return LatticeViolation(f"{kind}-cannot-justify-{ctx.offered_class}", evidence_hash)
    if ctx.disowned:
        return Absent("disowned", evidence_hash)
    scope = _load(statement.get("scope"))
    population = _population(evidence)
    is_counterexample = kind == "counterexample_hunt_record" and evidence.get("verdict") == "KILLED"
    comparison = counterexample_coverage_violation if is_counterexample else coverage_violation
    field = comparison(population, scope)
    if field is not None:
        return CoverageViolation(field, evidence_hash)
    if ctx.inadmissible:
        return Absent(REASON_INADMISSIBLE, evidence_hash)
    if kind == "lean_artifact" and ctx.formalization_reason is not None:
        return Absent(ctx.formalization_reason, evidence_hash)
    in_sample = _load(evidence.get("in_sample_sizes"))
    in_sample_ok = contains(in_sample, scope.get("size_interval"))
    cls, reason = kind_class(
        kind,
        evidence.get("verdict"),
        repro_passed=ctx.repro_passed,
        in_sample_ok=in_sample_ok,
        has_cost_model=ctx.has_cost_model,
        approved=ctx.approved,
    )
    if reason == REASON_HUMAN_REVIEW:
        return Pending(REASON_HUMAN_REVIEW, evidence_hash)
    if reason == REASON_HUNT_KILLED:
        return Refutation(evidence_hash)
    if cls is None:
        return Absent(reason, evidence_hash)
    if ctx.statement_status == "refuted":
        return LatticeViolation("refuted-statement", evidence_hash)
    if ctx.grade == AUDIT_ONLY:
        return Absent(REASON_AUDIT_ONLY, evidence_hash)
    coverage = (
        cross_check_covers(ctx.producer_summary.get("cross_check"), ctx.attempt_inputs)
        if isinstance(ctx.producer_summary, dict) and ctx.producer_summary.get("cross_check") is not None
        else None
    )
    if ctx.repro_passed is None and repro.policy(ctx.grade, ctx.tier) == repro.RERUN_ON_DERIVE:
        reproduced, _ = kind_class(
            kind,
            evidence.get("verdict"),
            repro_passed=True,
            in_sample_ok=in_sample_ok,
            has_cost_model=ctx.has_cost_model,
            approved=ctx.approved,
        )
        if reproduced is not None and rank(weakest(reproduced, ceiling)) > rank(CONJECTURE):
            return Justification(CONJECTURE, kind, evidence_hash, REASON_REPRO_DEFERRED, cross_check_coverage=coverage)
    if producer_capped(ctx.producer_summary, ctx.attempt_inputs, coverage=coverage):
        ceiling = weakest(ceiling, CONJECTURE)
    return Justification(
        weakest(cls, ceiling),
        kind,
        evidence_hash,
        reason,
        ctx.gate_run_hash if kind == "lean_artifact" else None,
        ctx.review_verdict_hash if kind == "lean_artifact" else None,
        ctx.record_digest if kind == "lean_artifact" else None,
        ctx.file_offset if kind == "lean_artifact" else None,
        coverage,
    )
