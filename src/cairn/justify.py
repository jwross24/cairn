import json
import os
import sqlite3
from dataclasses import dataclass

from cairn import claims, cli, exits, log, substrate
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


@dataclass(frozen=True)
class Justification:
    cls: str
    kind: str
    evidence_hash: str
    reason: str


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


@dataclass(frozen=True)
class Derivation:
    statement_hash: str
    tag: str
    justified_by: str | None
    results: tuple
    appended: bool
    refuted_by: str | None


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


def _origin_values(origins):
    if isinstance(origins, dict):
        values = []
        for entry in origins.values():
            values.extend(entry.values() if isinstance(entry, dict) else [entry])
        return values
    if isinstance(origins, (list, tuple)):
        return list(origins)
    return []


def cross_check_covers(cross_check, inputs):
    if not isinstance(cross_check, dict) or not isinstance(inputs, dict) or not inputs:
        return False
    ranges = cross_check.get("independent_range")
    if not isinstance(ranges, dict) or not ranges:
        return False
    return all(contains(ranges.get(axis), wanted) for axis, wanted in inputs.items())


def producer_capped(summary, inputs):
    if not isinstance(summary, dict):
        return False
    if not all(
        value == AUTHOR_SUPPLIED
        for value in _origin_values(summary.get("corpus_origins"))
    ):
        return False
    if summary.get("randomized_arm"):
        return False
    return not cross_check_covers(summary.get("cross_check"), inputs)


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
        return (
            (PROVEN, "lean-artifact-approved")
            if approved
            else (None, REASON_HUMAN_REVIEW)
        )
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
        if isinstance(result, Justification) and (
            best is None or rank(result.cls) > rank(best[1].cls)
        ):
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
        detail=getattr(result, "cls", None)
        or getattr(result, "field", None)
        or getattr(result, "reason", None),
    )
    return result


def _judge(evidence, statement, ctx, kind, ceiling, evidence_hash):
    if ctx.offered_class is not None and (
        ceiling is None or rank(ctx.offered_class) > rank(ceiling)
    ):
        return LatticeViolation(
            f"{kind}-cannot-justify-{ctx.offered_class}", evidence_hash
        )
    if ctx.disowned:
        return Absent("disowned", evidence_hash)
    scope = _load(statement.get("scope"))
    population = _population(evidence)
    field = coverage_violation(population, scope)
    if field is not None:
        return CoverageViolation(field, evidence_hash)
    in_sample = _load(evidence.get("in_sample_sizes"))
    cls, reason = kind_class(
        kind,
        evidence.get("verdict"),
        repro_passed=ctx.repro_passed,
        in_sample_ok=contains(in_sample, scope.get("size_interval")),
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
        ceiling = weakest(ceiling, CONJECTURE)
    if producer_capped(ctx.producer_summary, ctx.attempt_inputs):
        ceiling = weakest(ceiling, CONJECTURE)
    return Justification(weakest(cls, ceiling), kind, evidence_hash, reason)


def _certificate_summary(sub, evidence):
    if evidence.get("producer_tag") == "gate":
        return None
    row = sub.get_certificate(evidence.get("producer_identity"))
    if row is None:
        return None
    return _load(row["selftest_summary"])


def _repro_passed(sub, evidence):
    digest = evidence.get("repro_record_hash")
    if not digest:
        return None
    row = claims.get_repro_record(sub, digest)
    return None if row is None else bool(row["passed"])


def _disowned(sub, evidence):
    attempt_id = evidence.get("attempt_id")
    if not attempt_id:
        return False
    row = sub.get_attempt(attempt_id)
    return row is not None and row["disowned_at"] is not None


def _grade(sub, evidence_hash):
    try:
        return sub.effective_grade(evidence_hash)
    except substrate.UnknownNode:
        return "Replayable"


def context_for(sub, evidence, statement, attest_path, *, offered_class=None):
    population = _load(evidence.get("population")) or {}
    approved = any(
        row["verdict"] == "approve"
        for row in claims.visible_review_verdicts(sub, statement["hash"], attest_path)
    )
    return Context(
        grade=_grade(sub, evidence.get("hash")),
        repro_passed=_repro_passed(sub, evidence),
        has_cost_model=claims.has_cost_model(sub, statement["hash"]),
        approved=approved,
        disowned=_disowned(sub, evidence),
        statement_status=statement.get("status", "open"),
        producer_summary=_certificate_summary(sub, evidence),
        attempt_inputs=population.get("param_ranges"),
        offered_class=offered_class,
    )


def _current_tag(sub, statement_hash):
    history = claims.tag_history_for(sub, statement_hash)
    return history[-1]["to_tag"] if history else None


def _justification_record(result):
    fields = {"result": type(result).__name__}
    for name in ("cls", "kind", "reason", "field", "evidence_hash"):
        value = getattr(result, name, None)
        if value is not None:
            fields[name] = value
    return claims.to_json(fields)


def derive_tag(sub, statement_hash, attest_path, *, actor=ACTOR):
    statement = claims.get_claim_statement(sub, statement_hash)
    if statement is None:
        raise claims.UnknownStatement(f"no claim statement {statement_hash}")
    results = []
    for row in claims.evidence_for(sub, statement_hash):
        ctx = context_for(sub, row, statement, attest_path)
        results.append((row, justify(row, statement, ctx)))

    refuted_by = next(
        (row["hash"] for row, result in results if isinstance(result, Refutation)), None
    )
    best = strongest(results)
    tag = best[1].cls if best is not None else SPECULATION
    if refuted_by is not None:
        tag = SPECULATION

    from_tag = _current_tag(sub, statement_hash)
    justified_by = (
        refuted_by
        if refuted_by is not None
        else (best[0]["hash"] if best is not None else None)
    )
    appended = tag != from_tag
    if appended:
        claims.append_tag_history(
            sub,
            statement_hash,
            from_tag,
            tag,
            justified_by,
            _justification_record(best[1])
            if best is not None
            else claims.to_json({"result": "Refutation" if refuted_by else "Absent"}),
            actor,
        )
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
    )
    return Derivation(
        statement_hash,
        tag,
        best[0]["hash"] if best is not None else None,
        tuple(results),
        appended,
        refuted_by,
    )


def _configure(parser):
    parser.add_argument(
        "--statement",
        required=True,
        help="claim statement hash whose tag is derived from every evidence node targeting it",
    )


def _payload(sub, derivation):
    return {
        "statement_hash": derivation.statement_hash,
        "tag": derivation.tag,
        "justified_by": derivation.justified_by,
        "refuted_by": derivation.refuted_by,
        "appended": derivation.appended,
        "evidence": [
            {
                "hash": row["hash"],
                "kind": row["kind"],
                "result": type(result).__name__,
                "detail": getattr(result, "cls", None)
                or getattr(result, "field", None)
                or getattr(result, "reason", None),
            }
            for row, result in derivation.results
        ],
        "exit_code": exits.OK,
    }


def _run(ns):
    if not os.path.exists(ns.attest):
        raise CliError(
            exits.ENVIRONMENT,
            f"the attestation file {ns.attest} does not exist; a review verdict is visible only through its record",
            where=str(ns.attest),
            next_command=f"cairn attest init --attest {ns.attest} --bundle {ns.bundle} --pin {ns.pin}",
        )
    try:
        with substrate.Substrate.open(ns.db) as sub:
            derivation = derive_tag(sub, ns.statement, ns.attest)
            payload = _payload(sub, derivation)
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
        print(
            f"{payload['statement_hash']} {payload['tag']} {payload['justified_by'] or '-'}"
        )
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
