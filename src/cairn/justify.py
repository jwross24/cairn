import sqlite3
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
from cairn.justify_lattice import ACTOR as ACTOR
from cairn.justify_lattice import AUDIT_ONLY as AUDIT_ONLY
from cairn.justify_lattice import AUTHOR_SUPPLIED as AUTHOR_SUPPLIED
from cairn.justify_lattice import CLASSES as CLASSES
from cairn.justify_lattice import CONJECTURE as CONJECTURE
from cairn.justify_lattice import KIND_MAX_CLASS as KIND_MAX_CLASS
from cairn.justify_lattice import PROVEN as PROVEN
from cairn.justify_lattice import REASON_AUDIT_ONLY as REASON_AUDIT_ONLY
from cairn.justify_lattice import REASON_HUMAN_REVIEW as REASON_HUMAN_REVIEW
from cairn.justify_lattice import REASON_HUNT_KILLED as REASON_HUNT_KILLED
from cairn.justify_lattice import REASON_INADMISSIBLE as REASON_INADMISSIBLE
from cairn.justify_lattice import REASON_PREMISE_CEILING as REASON_PREMISE_CEILING
from cairn.justify_lattice import REASON_REPRO_DEFERRED as REASON_REPRO_DEFERRED
from cairn.justify_lattice import SPECULATION as SPECULATION
from cairn.justify_lattice import STRONG_EMPIRICAL as STRONG_EMPIRICAL
from cairn.justify_lattice import Absent as Absent
from cairn.justify_lattice import Context as Context
from cairn.justify_lattice import CoverageViolation as CoverageViolation
from cairn.justify_lattice import CrossCheckCoverage as CrossCheckCoverage
from cairn.justify_lattice import Derivation as Derivation
from cairn.justify_lattice import Justification as Justification
from cairn.justify_lattice import LatticeViolation as LatticeViolation
from cairn.justify_lattice import Pending as Pending
from cairn.justify_lattice import Refutation as Refutation
from cairn.justify_lattice import _as_set as _as_set
from cairn.justify_lattice import _box_union_volume as _box_union_volume
from cairn.justify_lattice import _box_volume as _box_volume
from cairn.justify_lattice import _clip_box as _clip_box
from cairn.justify_lattice import _cross_check_records as _cross_check_records
from cairn.justify_lattice import _interval as _interval
from cairn.justify_lattice import _judge as _judge
from cairn.justify_lattice import _load as _load
from cairn.justify_lattice import _origin_values as _origin_values
from cairn.justify_lattice import _population as _population
from cairn.justify_lattice import contains as contains
from cairn.justify_lattice import counterexample_coverage_violation as counterexample_coverage_violation
from cairn.justify_lattice import coverage_violation as coverage_violation
from cairn.justify_lattice import cross_check_covers as cross_check_covers
from cairn.justify_lattice import justify as justify
from cairn.justify_lattice import kind_class as kind_class
from cairn.justify_lattice import producer_capped as producer_capped
from cairn.justify_lattice import rank as rank
from cairn.justify_lattice import strongest as strongest
from cairn.justify_lattice import subset as subset
from cairn.justify_lattice import weakest as weakest

lg = log.get("justify")


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
    if evidence.get("kind") == "counterexample_hunt_record":
        if evidence.get("verdict") not in ("SURVIVED", "KILLED"):
            return ()
        from cairn import hunt

        return hunt.required_attempt_ids(sub, evidence)
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
        for attempt_id in _member_attempts(sub, evidence) or ()
        if (row := sub.get_attempt(attempt_id)) is not None
    )


def _inadmissible(sub, evidence):
    members = _member_attempts(sub, evidence)
    if members is None:
        return True
    return any(
        row is not None and bool(row["inadmissible"])
        for attempt_id in members
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
    reviews = claims.effective_review_verdicts(sub, statement["hash"], attest_path)
    review = next(
        (
            row
            for row in reviews
            if row["verdict"] == "approve" and (gate_run is None or row["gate_bundle_hash"] == gate_run["bundle_hash"])
        ),
        None,
    )
    if any(row["verdict"] != "approve" for row in reviews):
        review = None
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
