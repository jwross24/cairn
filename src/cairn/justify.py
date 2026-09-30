import json
import sqlite3
from dataclasses import dataclass
from itertools import combinations
from math import prod
from pathlib import Path

from cairn import (
    canon,
    claims,
    cli,
    container,
    disagreement,
    exits,
    foundations,
    human_queue,
    laddertable,
    log,
    repro,
    substrate,
)
from cairn.errors import CliError

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


def _certificate_summary(sub, evidence):
    if evidence.get("producer_tag") == "gate":
        return None
    row = sub.get_certificate(evidence.get("producer_identity"))
    if row is None:
        return None
    return _load(row["selftest_summary"])


def _repro_passed(sub, evidence):
    digest = evidence.get("repro_record_hash")
    attempt_id = evidence.get("attempt_id")
    table_hash = (
        laddertable.mapped_table_for_attempt(sub, attempt_id)
        if evidence.get("kind") == laddertable.NODE_KIND and attempt_id
        else None
    )
    if table_hash is not None:
        if digest:
            row = claims.get_repro_record(sub, digest)
            if row is None or row["attempt_id"] != attempt_id:
                return None
            return bool(row["passed"]) if _table_bindings(sub, digest) == {table_hash} else None
        rows = [
            row
            for row in claims.repro_records_for_attempt(sub, attempt_id)
            if _table_bindings(sub, row["hash"]) == {table_hash}
        ]
        return bool(rows[-1]["passed"]) if rows else None
    if digest:
        row = claims.get_repro_record(sub, digest)
        return None if row is None else bool(row["passed"])
    rows = claims.repro_records_for_attempt(sub, attempt_id) if attempt_id else []
    return bool(rows[-1]["passed"]) if rows else None


def _table_bindings(sub, node_hash):
    rows = sub.conn.execute(
        "SELECT l.parent_hash FROM lineage l JOIN nodes n ON n.hash = l.parent_hash "
        "WHERE l.child_hash = ? AND l.edge_kind = ? AND n.kind = ?",
        (node_hash, substrate.EDGE_INPUT, laddertable.NODE_KIND),
    ).fetchall()
    return {row["parent_hash"] for row in rows}


def _member_attempts(sub, evidence):
    attempt_id = evidence.get("attempt_id")
    table_hash = (
        laddertable.mapped_table_for_attempt(sub, attempt_id)
        if evidence.get("kind") == laddertable.NODE_KIND and attempt_id
        else None
    )
    if table_hash is None:
        return () if attempt_id is None else (attempt_id,)
    return laddertable.attempt_ids_for_table(sub, table_hash)


def _disowned(sub, evidence):
    return any(
        row is not None and row["disowned_at"] is not None
        for attempt_id in _member_attempts(sub, evidence)
        if (row := sub.get_attempt(attempt_id)) is not None
    )


def _inadmissible(sub, evidence):
    return any(
        row is not None and bool(row["inadmissible"])
        for attempt_id in _member_attempts(sub, evidence)
        if (row := sub.get_attempt(attempt_id)) is not None
    )


def _grade(sub, evidence_hash):
    try:
        return sub.effective_grade(evidence_hash)
    except substrate.UnknownNode:
        return "Replayable"


def _attempt_inputs(sub, evidence):
    """The run's own inputs where a table records them; the declared population is weaker and is the fallback."""
    attempt_id = evidence.get("attempt_id")
    measured = laddertable.inputs_for_attempt(sub, attempt_id) if attempt_id else None
    if measured is not None:
        return measured
    return (_load(evidence.get("population")) or {}).get("param_ranges")


def _bound_gate_run(sub, digest):
    row = claims.get_gate_run(sub, digest)
    node = sub.get_node(digest)
    if row is None or node is None or node["kind"] != "gate_run":
        return None, "lean-gate-absent"
    canonical = bytes(node["canonical"])
    if substrate.node_hash_for("gate_run", canonical) != digest:
        return None, "lean-gate-canonical"
    try:
        run = canon.decode(claims.GATE_RUN, canonical)
    except canon.CanonError:
        return None, "lean-gate-canonical"
    if any((_load(row[name]) if name == "reasons" else row[name]) != value for name, value in run.items()):
        return None, "lean-gate-canonical"
    return row, None


def _formalization(sub, evidence, statement):
    from cairn import solutionplan

    if evidence.get("producer_tag") != "gate":
        return None, "lean-gate-absent"
    edges = [edge for edge in sub.lineage_of(evidence["hash"]) if edge["edge_kind"] == substrate.EDGE_INPUT]
    if len(edges) != 1 or edges[0]["parent_hash"] != evidence.get("producer_identity"):
        return None, "lean-gate-binding"
    digest = edges[0]["parent_hash"]
    run, reason = _bound_gate_run(sub, digest)
    if run is None:
        return None, reason
    if (
        run["gate"] != solutionplan.SUMMARY_GATE
        or run["plan_step"] != solutionplan.SUMMARY_STEP
        or run["statement_hash"] != statement["hash"]
        or run["pin_hash"] != run["bundle_hash"]
        or run["result"] != solutionplan.RESULT_PASS
        or not all(run[name] for name in ("formal_statement_hash", "renderer_hash", "prelude_hash"))
    ):
        return None, "lean-gate-binding"
    steps = [edge for edge in sub.lineage_of(digest) if edge["edge_kind"] == substrate.EDGE_INPUT]
    if len(steps) != len(solutionplan.STEP_KINDS):
        return None, "lean-gate-incomplete"
    names = set()
    for edge in steps:
        step, reason = _bound_gate_run(sub, edge["parent_hash"])
        if step is None:
            return None, reason
        if (
            step["gate"] != solutionplan.STEP_GATE
            or step["result"] != solutionplan.RESULT_PASS
            or not step["plan_step"]
            or step["plan_step"] in names
            or any(
                step[name] != run[name]
                for name in (
                    "statement_hash",
                    "formal_statement_hash",
                    "bundle_hash",
                    "pin_hash",
                    "renderer_hash",
                    "prelude_hash",
                    "arm",
                    "at",
                )
            )
        ):
            return None, "lean-gate-incomplete"
        names.add(step["plan_step"])
    if run["arm"] != container.GOLD_ARM:
        return run, f"lean-gate-arm:{run['arm']}"
    return run, None


def context_for(sub, evidence, statement, attest_path, *, offered_class=None):
    gate_run, formalization_reason = (
        _formalization(sub, evidence, statement) if evidence.get("kind") == "lean_artifact" else (None, None)
    )
    reviews = claims.visible_review_verdicts(sub, statement["hash"], attest_path)
    review = next(
        (
            row
            for row in reviews
            if row["verdict"] == "approve" and (gate_run is None or row["gate_bundle_hash"] == gate_run["bundle_hash"])
        ),
        None,
    )
    return Context(
        grade=_grade(sub, evidence.get("hash")),
        repro_passed=_repro_passed(sub, evidence),
        has_cost_model=claims.has_cost_model(sub, statement["hash"]),
        approved=review is not None,
        disowned=_disowned(sub, evidence),
        statement_status=statement.get("status", "open"),
        producer_summary=_certificate_summary(sub, evidence),
        attempt_inputs=_attempt_inputs(sub, evidence),
        offered_class=offered_class,
        tier=claims.ticket_tier_for(sub, statement["hash"]),
        inadmissible=_inadmissible(sub, evidence),
        formalization_reason=formalization_reason,
        gate_run_hash=None if gate_run is None else gate_run["run_id"],
        review_verdict_hash=None if review is None else claims._verdict_of(review).hash,
        record_digest=None if review is None else review["record_digest"],
        file_offset=None if review is None else review["file_offset"],
    )


def _current_tag(sub, statement_hash):
    history = claims.tag_history_for(sub, statement_hash)
    return history[-1]["to_tag"] if history else None


def _justification_record(result):
    fields = {"result": type(result).__name__}
    for name in (
        "cls",
        "kind",
        "reason",
        "field",
        "evidence_hash",
        "gate_run_hash",
        "review_verdict_hash",
        "record_digest",
        "file_offset",
    ):
        value = getattr(result, name, None)
        if value is not None:
            fields[name] = value
    coverage = getattr(result, "cross_check_coverage", None)
    if coverage is not None:
        fields["cross_check_coverage"] = coverage.record()
    return claims.to_json(fields)


def derive_tag(sub, statement_hash, attest_path, *, actor=ACTOR):
    statement = claims.get_claim_statement(sub, statement_hash)
    if statement is None:
        raise claims.UnknownStatement(f"no claim statement {statement_hash}")
    results = []
    for row in claims.evidence_for(sub, statement_hash):
        ctx = context_for(sub, row, statement, attest_path)
        results.append((row, justify(row, statement, ctx)))

    if any(isinstance(result, Pending) and result.reason == REASON_HUMAN_REVIEW for _, result in results):
        open_review = any(
            item["class"] == human_queue.STATEMENT_REVIEW
            and item["target_kind"] == human_queue.STATEMENT
            and item["target"] == statement_hash
            for item in human_queue.open_items(sub, attest_path)
        )
        if not open_review:
            human_queue.enqueue(
                sub,
                human_queue.Item(
                    human_queue.STATEMENT_REVIEW,
                    human_queue.STATEMENT,
                    statement_hash,
                    cli.now_iso(),
                    blocker=human_queue.STATEMENT_REVIEW,
                ),
            )

    refuted_by = next((row["hash"] for row, result in results if isinstance(result, Refutation)), None)
    best = strongest(results)
    tag = best[1].cls if best is not None else SPECULATION
    if refuted_by is not None:
        tag = SPECULATION
    deferred = tuple(
        row["hash"]
        for row, result in results
        if isinstance(result, Justification) and result.reason == REASON_REPRO_DEFERRED
    )

    from_tag = _current_tag(sub, statement_hash)
    # The tag_history trigger refuses a downgrade with no evidence pointer, so a derivation
    # with every node absent names the first lost node as the pointer behind the move.
    lost = next((row["hash"] for row, result in results if isinstance(result, Absent)), None)
    justified_by = refuted_by if refuted_by is not None else (best[0]["hash"] if best is not None else lost)
    record = (
        _justification_record(best[1])
        if best is not None
        else claims.to_json({"result": "Refutation" if refuted_by else "Absent"})
    )
    premise_cap = foundations.ceiling_for(sub, statement_hash)
    if premise_cap is not None and rank(tag) > rank(premise_cap[0]):
        tag, justified_by = premise_cap[0], premise_cap[1]
        record = claims.to_json({"result": "PremiseCeiling", "cls": tag, "premise": premise_cap[2]})
    freeze = disagreement.freeze_for(sub, statement_hash, attest_path)
    if freeze is not None and rank(tag) > rank(freeze[0]):
        tag, justified_by = freeze[0], freeze[1]
        record = claims.to_json({"result": "DisagreementFreeze", "cls": tag, "disagreement": freeze[2]})
    appended = tag != from_tag
    if appended:
        claims.append_tag_history(sub, statement_hash, from_tag, tag, justified_by, record, actor)
    if refuted_by is not None and statement["status"] == "open":
        claims.transition_status(sub, statement_hash, "refuted")
    lg.info(
        "derive_tag",
        statement=statement_hash,
        from_tag=from_tag,
        to_tag=tag,
        justified_by=justified_by,
        appended=appended,
        refuted_by=refuted_by,
        deferred=list(deferred),
        premise_cap=None if premise_cap is None else premise_cap[0],
    )
    return Derivation(
        statement_hash,
        tag,
        justified_by,
        tuple(results),
        appended,
        refuted_by,
        deferred,
        premise_cap,
    )


def _configure(parser):
    parser.add_argument(
        "--statement",
        required=True,
        help="claim statement hash whose tag is derived from every evidence node targeting it",
    )


def _payload(derivation):
    return {
        "statement_hash": derivation.statement_hash,
        "tag": derivation.tag,
        "justified_by": derivation.justified_by,
        "refuted_by": derivation.refuted_by,
        "appended": derivation.appended,
        "deferred": list(derivation.deferred),
        "premise_cap": None
        if derivation.premise_cap is None
        else {
            "tag": derivation.premise_cap[0],
            "evidence_hash": derivation.premise_cap[1],
            "premise": derivation.premise_cap[2],
        },
        "evidence": [
            {
                "hash": row["hash"],
                "kind": row["kind"],
                "result": type(result).__name__,
                "detail": getattr(result, "cls", None)
                or getattr(result, "field", None)
                or getattr(result, "reason", None),
                **(
                    {"cross_check_coverage": result.cross_check_coverage.record()}
                    if isinstance(result, Justification) and result.cross_check_coverage is not None
                    else {}
                ),
            }
            for row, result in derivation.results
        ],
        "exit_code": exits.OK,
    }


def _run(ns):
    if not Path(ns.attest).exists():
        raise CliError(
            exits.ENVIRONMENT,
            f"the attestation file {ns.attest} does not exist; a review verdict is visible only through its record",
            where=str(ns.attest),
            next_command=f"cairn attest init --attest {ns.attest} --bundle {ns.bundle} --pin {ns.pin}",
        )
    try:
        with substrate.Substrate.open(ns.db) as sub:
            derivation = derive_tag(sub, ns.statement, ns.attest)
            payload = _payload(derivation)
    except (sqlite3.IntegrityError, repro.ReproError) as exc:
        raise CliError(
            exits.GATE_REFUSED,
            f"the derivation of {ns.statement} was refused: {exc}",
            where=ns.statement,
            next_command="a downgrade needs an evidence pointer and a ticket tier stays within claims.TIERS",
        ) from None
    except substrate.WriterAlreadyOpen as exc:
        raise CliError(
            exits.CONFLICT,
            f"another writer already holds {ns.db}: {exc}",
            where=str(ns.db),
            next_command=f"cairn justify --statement {ns.statement} --db {ns.db}",
        ) from None
    except sqlite3.OperationalError as exc:
        raise CliError(
            exits.ENVIRONMENT,
            f"the substrate {ns.db} could not be opened: {exc}",
            where=str(ns.db),
            next_command=f"cairn startup-scan --db {ns.db}",
        ) from None
    except claims.UnknownStatement:
        raise CliError(
            exits.USER_INPUT,
            f"no claim statement {ns.statement} in {ns.db}",
            where=str(ns.statement),
            next_command=f"cairn m0-run --db {ns.db} --bundle {ns.bundle} --pin {ns.pin} --attest {ns.attest} --json",
        ) from None
    if getattr(ns, "json", False):
        cli.emit_json("justify", payload)
    else:
        print(f"{payload['statement_hash']} {payload['tag']} {payload['justified_by'] or '-'}")
        for row in payload["evidence"]:
            print(f"- {row['kind']} {row['hash']} {row['result']} {row['detail']}")
    return exits.OK


cli.register(
    "justify",
    _configure,
    _run,
    summary="derive a claim statement's calibration tag from every evidence node targeting it, and append the transition to its tag history",
    read_only=False,
    json=True,
)
